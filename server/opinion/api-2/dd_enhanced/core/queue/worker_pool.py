"""
Worker pool for parallel document processing.

Manages a pool of worker threads that process jobs from the queue.
Configurable via environment variable: DD_PARALLEL_WORKERS (default: 10)
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
import threading
import time
import logging
import os

from .job_queue import JobQueueInterface, Job, JobType, JobStatus
from .rate_limiter import get_rate_limiter, RateLimiter, RateLimitedContext

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for worker pool."""
    num_workers: int = 10
    poll_interval: float = 0.5
    shutdown_timeout: float = 60.0
    job_timeout: float = 300.0  # 5 minutes per job

    @classmethod
    def from_env(cls) -> 'WorkerConfig':
        """Create config from environment variables."""
        return cls(
            num_workers=int(os.environ.get("DD_PARALLEL_WORKERS", "10")),
            poll_interval=float(os.environ.get("DD_WORKER_POLL_INTERVAL", "0.5")),
            shutdown_timeout=float(os.environ.get("DD_WORKER_SHUTDOWN_TIMEOUT", "60")),
            job_timeout=float(os.environ.get("DD_JOB_TIMEOUT", "300"))
        )


@dataclass
class WorkerStats:
    """Statistics for a single worker."""
    worker_id: int
    jobs_processed: int = 0
    jobs_failed: int = 0
    total_processing_time_ms: int = 0
    is_running: bool = False
    current_job_id: Optional[str] = None
    current_job_type: Optional[str] = None
    last_job_completed_at: Optional[datetime] = None


class DocumentWorker:
    """
    Worker that processes document analysis jobs.
    """

    def __init__(
        self,
        worker_id: int,
        job_queue: JobQueueInterface,
        rate_limiter: RateLimiter,
        job_handlers: Dict[JobType, Callable],
        db_writer: Optional[Callable] = None
    ):
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.rate_limiter = rate_limiter
        self.job_handlers = job_handlers
        self.db_writer = db_writer  # Callback to write job status to Postgres

        self.stats = WorkerStats(worker_id=worker_id)
        self.current_job: Optional[Job] = None

    def process_job(self, job: Job) -> Dict[str, Any]:
        """Process a single job."""
        handler = self.job_handlers.get(job.job_type)
        if not handler:
            raise ValueError(f"No handler registered for job type: {job.job_type}")

        estimated_tokens = job.estimated_tokens or 2000

        with RateLimitedContext(estimated_tokens=estimated_tokens, timeout=300) as ctx:
            if not ctx.acquired:
                raise TimeoutError("Timed out waiting for rate limit permission")

            # Execute the handler
            start_time = time.time()
            result = handler(job)
            duration_ms = int((time.time() - start_time) * 1000)

            # Report actual tokens if available
            if isinstance(result, dict) and 'tokens_used' in result:
                ctx.report_tokens(result['tokens_used'])

            return {
                'result': result,
                'duration_ms': duration_ms,
                'worker_id': self.worker_id
            }

    def run(
        self,
        dd_id: str,
        job_types: List[JobType],
        stop_event: threading.Event
    ):
        """
        Main worker loop - continuously process jobs until stopped.
        """
        self.stats.is_running = True
        logger.info(f"Worker {self.worker_id} started for DD {dd_id}")

        while not stop_event.is_set():
            job = None
            start_time = None

            try:
                # Try to get a job
                job = self.job_queue.dequeue(dd_id, job_types, timeout=1)

                if not job:
                    # No jobs available, continue polling
                    continue

                self.current_job = job
                self.stats.current_job_id = job.job_id
                self.stats.current_job_type = job.job_type.value
                job.worker_id = self.worker_id
                start_time = time.time()

                logger.info(f"Worker {self.worker_id} processing job {job.job_id} ({job.job_type.value})")

                # Write to Postgres (start)
                if self.db_writer:
                    self._write_job_start(job)

                # Process the job
                result = self.process_job(job)

                # Mark completed
                self.job_queue.complete(job.job_id, result)
                self.stats.jobs_processed += 1
                self.stats.last_job_completed_at = datetime.utcnow()

                duration_ms = result.get('duration_ms', 0)
                self.stats.total_processing_time_ms += duration_ms

                # Write to Postgres (complete)
                if self.db_writer:
                    self._write_job_complete(job, result)

                logger.info(f"Worker {self.worker_id} completed job {job.job_id} in {duration_ms}ms")

            except Exception as e:
                error_message = str(e)
                if job:
                    logger.error(f"Worker {self.worker_id} failed job {job.job_id}: {error_message}")
                    self.job_queue.fail(job, error_message)
                    self.stats.jobs_failed += 1

                    # Write to Postgres (fail)
                    if self.db_writer:
                        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0
                        self._write_job_fail(job, error_message, duration_ms)
                else:
                    logger.error(f"Worker {self.worker_id} error: {error_message}")

            finally:
                self.current_job = None
                self.stats.current_job_id = None
                self.stats.current_job_type = None

        self.stats.is_running = False
        logger.info(f"Worker {self.worker_id} stopped "
                   f"(processed: {self.stats.jobs_processed}, failed: {self.stats.jobs_failed})")

    def _write_job_start(self, job: Job):
        """Write job start to Postgres."""
        try:
            self.db_writer('start', {
                'run_id': job.run_id,
                'job_id': job.job_id,
                'job_type': job.job_type.value,
                'document_id': job.payload.get('document_id'),
                'batch_id': job.payload.get('batch_id'),
                'cluster_id': job.payload.get('cluster_id'),
                'status': 'processing',
                'priority': job.priority,
                'retry_count': job.retry_count,
                'estimated_tokens': job.estimated_tokens,
                'worker_id': self.worker_id,
                'started_at': datetime.utcnow()
            })
        except Exception as e:
            logger.warning(f"Failed to write job start to Postgres: {e}")

    def _write_job_complete(self, job: Job, result: Dict[str, Any]):
        """Write job completion to Postgres."""
        try:
            self.db_writer('complete', {
                'run_id': job.run_id,
                'job_id': job.job_id,
                'status': 'completed',
                'completed_at': datetime.utcnow(),
                'duration_ms': result.get('duration_ms', 0),
                'actual_tokens': result.get('result', {}).get('tokens_used'),
                'result_summary': self._summarize_result(result.get('result', {}))
            })
        except Exception as e:
            logger.warning(f"Failed to write job completion to Postgres: {e}")

    def _write_job_fail(self, job: Job, error_message: str, duration_ms: int):
        """Write job failure to Postgres."""
        try:
            self.db_writer('fail', {
                'run_id': job.run_id,
                'job_id': job.job_id,
                'status': 'failed' if job.retry_count >= job.max_retries else 'retrying',
                'completed_at': datetime.utcnow() if job.retry_count >= job.max_retries else None,
                'duration_ms': duration_ms,
                'error_message': error_message[:1000],
                'retry_count': job.retry_count + 1
            })
        except Exception as e:
            logger.warning(f"Failed to write job failure to Postgres: {e}")

    def _summarize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of job result for storage."""
        if not result:
            return {}

        summary = {}

        # Extract common fields
        if 'findings_count' in result:
            summary['findings_count'] = result['findings_count']
        if 'entities_count' in result:
            summary['entities_count'] = result['entities_count']
        if 'tokens_used' in result:
            summary['tokens_used'] = result['tokens_used']
        if 'compression_ratio' in result:
            summary['compression_ratio'] = result['compression_ratio']

        return summary


class WorkerPool:
    """
    Manages a pool of document processing workers.
    """

    def __init__(
        self,
        job_queue: JobQueueInterface,
        config: WorkerConfig = None,
        db_session=None
    ):
        self.job_queue = job_queue
        self.config = config or WorkerConfig.from_env()
        self.rate_limiter = get_rate_limiter()
        self.db_session = db_session

        self.workers: List[DocumentWorker] = []
        self.executor: Optional[ThreadPoolExecutor] = None
        self.futures: List[Future] = []
        self.stop_event = threading.Event()
        self.job_handlers: Dict[JobType, Callable] = {}
        self.is_running = False

        logger.info(f"WorkerPool initialized with {self.config.num_workers} workers")

    def register_handler(self, job_type: JobType, handler: Callable):
        """
        Register a handler function for a job type.

        Handler signature: (job: Job) -> Dict[str, Any]
        """
        self.job_handlers[job_type] = handler
        logger.debug(f"Registered handler for {job_type.value}")

    def _db_writer(self, action: str, data: Dict[str, Any]):
        """Write job status to Postgres for audit trail."""
        if not self.db_session:
            return

        try:
            if action == 'start':
                self.db_session.execute("""
                    INSERT INTO dd_job_execution
                    (run_id, job_id, job_type, document_id, batch_id, cluster_id,
                     status, priority, retry_count, estimated_tokens, worker_id, started_at)
                    VALUES (%(run_id)s, %(job_id)s, %(job_type)s, %(document_id)s,
                            %(batch_id)s, %(cluster_id)s, %(status)s, %(priority)s,
                            %(retry_count)s, %(estimated_tokens)s, %(worker_id)s, %(started_at)s)
                    ON CONFLICT (run_id, job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    retry_count = EXCLUDED.retry_count,
                    worker_id = EXCLUDED.worker_id,
                    started_at = EXCLUDED.started_at
                """, data)

            elif action == 'complete':
                self.db_session.execute("""
                    UPDATE dd_job_execution
                    SET status = %(status)s,
                        completed_at = %(completed_at)s,
                        duration_ms = %(duration_ms)s,
                        actual_tokens = %(actual_tokens)s,
                        result_summary = %(result_summary)s
                    WHERE run_id = %(run_id)s AND job_id = %(job_id)s
                """, data)

            elif action == 'fail':
                self.db_session.execute("""
                    UPDATE dd_job_execution
                    SET status = %(status)s,
                        completed_at = %(completed_at)s,
                        duration_ms = %(duration_ms)s,
                        error_message = %(error_message)s,
                        retry_count = %(retry_count)s
                    WHERE run_id = %(run_id)s AND job_id = %(job_id)s
                """, data)

            self.db_session.commit()

        except Exception as e:
            logger.warning(f"Failed to write job status to Postgres: {e}")
            try:
                self.db_session.rollback()
            except Exception:
                pass

    def start(self, dd_id: str, job_types: List[JobType]):
        """Start the worker pool."""
        if self.is_running:
            logger.warning("Worker pool already running")
            return

        logger.info(f"Starting worker pool with {self.config.num_workers} workers for DD {dd_id}")

        self.stop_event.clear()
        self.is_running = True
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.num_workers,
            thread_name_prefix="dd_worker"
        )

        for i in range(self.config.num_workers):
            worker = DocumentWorker(
                worker_id=i,
                job_queue=self.job_queue,
                rate_limiter=self.rate_limiter,
                job_handlers=self.job_handlers,
                db_writer=self._db_writer if self.db_session else None
            )
            self.workers.append(worker)

            future = self.executor.submit(worker.run, dd_id, job_types, self.stop_event)
            self.futures.append(future)

        logger.info(f"Started {len(self.workers)} workers")

    def stop(self, wait: bool = True):
        """Stop the worker pool."""
        if not self.is_running:
            return

        logger.info("Stopping worker pool...")
        self.stop_event.set()

        if wait and self.executor:
            # Wait for workers to finish current jobs
            self.executor.shutdown(wait=True, cancel_futures=False)

        self.workers.clear()
        self.futures.clear()
        self.is_running = False
        logger.info("Worker pool stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics."""
        worker_stats = []
        for worker in self.workers:
            worker_stats.append({
                'worker_id': worker.stats.worker_id,
                'is_running': worker.stats.is_running,
                'jobs_processed': worker.stats.jobs_processed,
                'jobs_failed': worker.stats.jobs_failed,
                'current_job_id': worker.stats.current_job_id,
                'current_job_type': worker.stats.current_job_type,
                'avg_processing_time_ms': (
                    worker.stats.total_processing_time_ms // max(worker.stats.jobs_processed, 1)
                )
            })

        return {
            'num_workers': len(self.workers),
            'active_workers': sum(1 for w in self.workers if w.stats.is_running),
            'total_processed': sum(w.stats.jobs_processed for w in self.workers),
            'total_failed': sum(w.stats.jobs_failed for w in self.workers),
            'workers': worker_stats,
            'rate_limiter': self.rate_limiter.get_stats()
        }

    def wait_for_completion(
        self,
        run_id: str,
        timeout: float = None,
        poll_interval: float = 2.0,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """
        Wait for all jobs in a run to complete.

        Args:
            run_id: Run ID to wait for
            timeout: Maximum time to wait (None = no timeout)
            poll_interval: Seconds between progress checks
            progress_callback: Optional callback(progress_dict) for updates

        Returns:
            True if all jobs completed successfully, False otherwise
        """
        start_time = time.time()
        last_progress = None

        while True:
            progress = self.job_queue.get_run_progress(run_id)

            # Report progress if changed
            if progress_callback and progress != last_progress:
                progress_callback(progress)
                last_progress = progress

            pending = progress.get('pending', 0) + progress.get('queued', 0)
            processing = progress.get('processing', 0)

            if pending == 0 and processing == 0:
                # All jobs finished
                failed = progress.get('failed', 0)
                completed = progress.get('completed', 0)

                if failed > 0:
                    logger.warning(f"Run completed with {failed} failed jobs out of {completed + failed}")
                    return False
                else:
                    logger.info(f"Run completed successfully: {completed} jobs")
                    return True

            if timeout and (time.time() - start_time) >= timeout:
                logger.error(f"Timeout waiting for run completion "
                            f"(pending: {pending}, processing: {processing})")
                return False

            time.sleep(poll_interval)

    def get_failed_jobs(self, run_id: str) -> List[Dict[str, Any]]:
        """Get list of failed jobs for a run."""
        progress = self.job_queue.get_run_progress(run_id)

        # This is a simplified implementation - in production,
        # you'd query the job queue or database for failed job details
        failed_jobs = []

        # For in-memory queue, we can access jobs directly
        if hasattr(self.job_queue, 'jobs'):
            for job in self.job_queue.jobs.values():
                if job.run_id == run_id and job.status == JobStatus.FAILED:
                    failed_jobs.append({
                        'job_id': job.job_id,
                        'job_type': job.job_type.value,
                        'document_id': job.payload.get('document_id'),
                        'error_message': job.error_message,
                        'retry_count': job.retry_count
                    })

        return failed_jobs
