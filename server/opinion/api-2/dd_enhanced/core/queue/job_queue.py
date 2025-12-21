"""
Job queue system for parallel document processing.

Supports:
- Redis for production (distributed, persistent)
- In-memory fallback for development (single process)

Automatically detects Redis availability at startup.
"""

from typing import Dict, List, Any, Optional, Protocol
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import json
import uuid
import threading
import time
import heapq
import logging
import os

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(Enum):
    PASS1_EXTRACT = "pass1_extract"
    PASS2_ANALYZE = "pass2_analyze"
    ENTITY_EXTRACT = "entity_extract"
    COMPRESS = "compress"
    BATCH_ANALYZE = "batch_analyze"
    CLUSTER_SYNTHESIZE = "cluster_synthesize"
    CROSS_CLUSTER_SYNTHESIZE = "cross_cluster_synthesize"
    DEAL_SYNTHESIZE = "deal_synthesize"


@dataclass
class Job:
    """Represents a processing job."""
    job_id: str
    job_type: JobType
    dd_id: str
    run_id: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: int = 5  # 1 = highest, 10 = lowest
    retry_count: int = 0
    max_retries: int = 3
    estimated_tokens: int = 2000
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    worker_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type.value,
            'dd_id': self.dd_id,
            'run_id': self.run_id,
            'payload': self.payload,
            'status': self.status.value,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'estimated_tokens': self.estimated_tokens,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'worker_id': self.worker_id
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary."""
        return Job(
            job_id=data['job_id'],
            job_type=JobType(data['job_type']),
            dd_id=data['dd_id'],
            run_id=data['run_id'],
            payload=data['payload'],
            status=JobStatus(data['status']),
            priority=data['priority'],
            retry_count=data['retry_count'],
            max_retries=data['max_retries'],
            estimated_tokens=data.get('estimated_tokens', 2000),
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error_message=data.get('error_message'),
            worker_id=data.get('worker_id')
        )


class JobQueueInterface(ABC):
    """Abstract interface for job queue implementations."""

    @abstractmethod
    def enqueue(self, job: Job) -> str:
        """Add a job to the queue."""
        pass

    @abstractmethod
    def enqueue_batch(self, jobs: List[Job]) -> List[str]:
        """Add multiple jobs to the queue efficiently."""
        pass

    @abstractmethod
    def dequeue(self, dd_id: str, job_types: List[JobType], timeout: int = 5) -> Optional[Job]:
        """Get the next job from the queue."""
        pass

    @abstractmethod
    def complete(self, job_id: str, result: Dict[str, Any]):
        """Mark a job as completed with result."""
        pass

    @abstractmethod
    def fail(self, job: Job, error_message: str):
        """Mark a job as failed, potentially requeue for retry."""
        pass

    @abstractmethod
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a job."""
        pass

    @abstractmethod
    def get_run_progress(self, run_id: str) -> Dict[str, Any]:
        """Get overall progress for a DD run."""
        pass

    @abstractmethod
    def clear_run(self, dd_id: str, run_id: str):
        """Clear all jobs for a specific run."""
        pass


class InMemoryJobQueue(JobQueueInterface):
    """
    In-memory job queue for development/testing.
    Thread-safe but single-process only.
    """

    def __init__(self):
        self.jobs: Dict[str, Job] = {}  # job_id -> Job
        self.queues: Dict[str, List[tuple]] = {}  # queue_key -> [(priority, timestamp, job_id)]
        self.results: Dict[str, Dict[str, Any]] = {}  # job_id -> result
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        logger.info("Initialized in-memory job queue")

    def _queue_key(self, dd_id: str, job_type: JobType) -> str:
        return f"{dd_id}:{job_type.value}"

    def enqueue(self, job: Job) -> str:
        with self.lock:
            job.status = JobStatus.QUEUED
            self.jobs[job.job_id] = job

            queue_key = self._queue_key(job.dd_id, job.job_type)
            if queue_key not in self.queues:
                self.queues[queue_key] = []

            # Use heap for priority queue (priority, timestamp, job_id)
            heapq.heappush(
                self.queues[queue_key],
                (job.priority, job.created_at.timestamp(), job.job_id)
            )
            self.condition.notify_all()

        return job.job_id

    def enqueue_batch(self, jobs: List[Job]) -> List[str]:
        job_ids = []
        with self.lock:
            for job in jobs:
                job.status = JobStatus.QUEUED
                self.jobs[job.job_id] = job

                queue_key = self._queue_key(job.dd_id, job.job_type)
                if queue_key not in self.queues:
                    self.queues[queue_key] = []

                heapq.heappush(
                    self.queues[queue_key],
                    (job.priority, job.created_at.timestamp(), job.job_id)
                )
                job_ids.append(job.job_id)

            self.condition.notify_all()

        logger.info(f"Enqueued batch of {len(jobs)} jobs")
        return job_ids

    def dequeue(self, dd_id: str, job_types: List[JobType], timeout: int = 5) -> Optional[Job]:
        end_time = time.time() + timeout

        with self.condition:
            while True:
                # Try each job type in order
                for job_type in job_types:
                    queue_key = self._queue_key(dd_id, job_type)
                    queue = self.queues.get(queue_key, [])

                    while queue:
                        _, _, job_id = heapq.heappop(queue)
                        job = self.jobs.get(job_id)

                        if job and job.status == JobStatus.QUEUED:
                            job.status = JobStatus.PROCESSING
                            job.started_at = datetime.utcnow()
                            return job

                # No jobs available, wait
                remaining = end_time - time.time()
                if remaining <= 0:
                    return None

                self.condition.wait(timeout=min(remaining, 0.5))

    def complete(self, job_id: str, result: Dict[str, Any]):
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.result = result
            self.results[job_id] = result

    def fail(self, job: Job, error_message: str):
        with self.lock:
            stored_job = self.jobs.get(job.job_id)
            if not stored_job:
                return

            stored_job.retry_count = job.retry_count + 1
            stored_job.error_message = error_message

            if stored_job.retry_count < stored_job.max_retries:
                # Requeue with lower priority
                stored_job.status = JobStatus.RETRYING
                stored_job.priority = min(10, job.priority + 1)
                stored_job.started_at = None

                queue_key = self._queue_key(job.dd_id, job.job_type)
                if queue_key not in self.queues:
                    self.queues[queue_key] = []

                heapq.heappush(
                    self.queues[queue_key],
                    (stored_job.priority, datetime.utcnow().timestamp(), job.job_id)
                )
                self.condition.notify_all()
                logger.info(f"Job {job.job_id} queued for retry ({stored_job.retry_count}/{stored_job.max_retries})")
            else:
                stored_job.status = JobStatus.FAILED
                stored_job.completed_at = datetime.utcnow()
                logger.warning(f"Job {job.job_id} failed permanently after {stored_job.retry_count} retries")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                return job.to_dict()
            return None

    def get_run_progress(self, run_id: str) -> Dict[str, Any]:
        with self.lock:
            stats = {
                'total': 0,
                'pending': 0,
                'queued': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'retrying': 0,
                'by_type': {}
            }

            for job in self.jobs.values():
                if job.run_id == run_id:
                    stats['total'] += 1
                    status_key = job.status.value
                    stats[status_key] = stats.get(status_key, 0) + 1

                    # Track by job type
                    type_key = job.job_type.value
                    if type_key not in stats['by_type']:
                        stats['by_type'][type_key] = {'total': 0, 'completed': 0, 'failed': 0}
                    stats['by_type'][type_key]['total'] += 1
                    if job.status == JobStatus.COMPLETED:
                        stats['by_type'][type_key]['completed'] += 1
                    elif job.status == JobStatus.FAILED:
                        stats['by_type'][type_key]['failed'] += 1

            return stats

    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.results.get(job_id)

    def clear_run(self, dd_id: str, run_id: str):
        with self.lock:
            # Remove jobs for this run
            jobs_to_remove = [
                job_id for job_id, job in self.jobs.items()
                if job.run_id == run_id
            ]
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                if job_id in self.results:
                    del self.results[job_id]

            # Clear queues for this dd_id
            keys_to_clear = [k for k in self.queues.keys() if k.startswith(f"{dd_id}:")]
            for key in keys_to_clear:
                self.queues[key] = []

            logger.info(f"Cleared {len(jobs_to_remove)} jobs for run {run_id}")


class RedisJobQueue(JobQueueInterface):
    """
    Redis-based job queue for production.
    Supports distributed processing across multiple workers.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        import redis
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.queue_key_prefix = "dd_job_queue"
        self.job_key_prefix = "dd_job"
        self.result_key_prefix = "dd_job_result"
        self.run_jobs_prefix = "dd_run_jobs"
        logger.info(f"Initialized Redis job queue: {redis_url}")

    def _queue_key(self, dd_id: str, job_type: JobType) -> str:
        return f"{self.queue_key_prefix}:{dd_id}:{job_type.value}"

    def _job_key(self, job_id: str) -> str:
        return f"{self.job_key_prefix}:{job_id}"

    def _result_key(self, job_id: str) -> str:
        return f"{self.result_key_prefix}:{job_id}"

    def _run_jobs_key(self, run_id: str) -> str:
        return f"{self.run_jobs_prefix}:{run_id}"

    def enqueue(self, job: Job) -> str:
        job.status = JobStatus.QUEUED
        job_data = json.dumps(job.to_dict())

        pipe = self.redis.pipeline()
        pipe.set(self._job_key(job.job_id), job_data)
        pipe.zadd(self._queue_key(job.dd_id, job.job_type), {job.job_id: job.priority})
        pipe.sadd(self._run_jobs_key(job.run_id), job.job_id)
        pipe.execute()

        return job.job_id

    def enqueue_batch(self, jobs: List[Job]) -> List[str]:
        job_ids = []
        pipe = self.redis.pipeline()

        for job in jobs:
            job.status = JobStatus.QUEUED
            job_data = json.dumps(job.to_dict())

            pipe.set(self._job_key(job.job_id), job_data)
            pipe.zadd(self._queue_key(job.dd_id, job.job_type), {job.job_id: job.priority})
            pipe.sadd(self._run_jobs_key(job.run_id), job.job_id)
            job_ids.append(job.job_id)

        pipe.execute()
        logger.info(f"Enqueued batch of {len(jobs)} jobs to Redis")
        return job_ids

    def dequeue(self, dd_id: str, job_types: List[JobType], timeout: int = 5) -> Optional[Job]:
        end_time = time.time() + timeout

        while time.time() < end_time:
            for job_type in job_types:
                queue_key = self._queue_key(dd_id, job_type)

                # Get highest priority job (lowest score)
                result = self.redis.zpopmin(queue_key, count=1)

                if result:
                    job_id, _ = result[0]

                    # Get job data
                    job_data = self.redis.get(self._job_key(job_id))
                    if not job_data:
                        continue

                    data = json.loads(job_data)

                    # Update status to processing
                    data['status'] = JobStatus.PROCESSING.value
                    data['started_at'] = datetime.utcnow().isoformat()
                    self.redis.set(self._job_key(job_id), json.dumps(data))

                    return Job.from_dict(data)

            # No jobs available, wait briefly
            time.sleep(0.1)

        return None

    def complete(self, job_id: str, result: Dict[str, Any]):
        job_data = self.redis.get(self._job_key(job_id))
        if job_data:
            data = json.loads(job_data)
            data['status'] = JobStatus.COMPLETED.value
            data['completed_at'] = datetime.utcnow().isoformat()
            self.redis.set(self._job_key(job_id), json.dumps(data))

        # Store result (expire after 24 hours)
        self.redis.set(
            self._result_key(job_id),
            json.dumps(result),
            ex=86400
        )

    def fail(self, job: Job, error_message: str):
        job_data = self.redis.get(self._job_key(job.job_id))
        if not job_data:
            return

        data = json.loads(job_data)
        data['retry_count'] = job.retry_count + 1
        data['error_message'] = error_message

        if data['retry_count'] < job.max_retries:
            # Requeue with lower priority
            data['status'] = JobStatus.RETRYING.value
            data['priority'] = min(10, job.priority + 1)
            data['started_at'] = None
            self.redis.set(self._job_key(job.job_id), json.dumps(data))

            queue_key = self._queue_key(job.dd_id, job.job_type)
            self.redis.zadd(queue_key, {job.job_id: data['priority']})
            logger.info(f"Job {job.job_id} queued for retry ({data['retry_count']}/{job.max_retries})")
        else:
            data['status'] = JobStatus.FAILED.value
            data['completed_at'] = datetime.utcnow().isoformat()
            self.redis.set(self._job_key(job.job_id), json.dumps(data))
            logger.warning(f"Job {job.job_id} failed permanently")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job_data = self.redis.get(self._job_key(job_id))
        if job_data:
            return json.loads(job_data)
        return None

    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        result_data = self.redis.get(self._result_key(job_id))
        if result_data:
            return json.loads(result_data)
        return None

    def get_run_progress(self, run_id: str) -> Dict[str, Any]:
        stats = {
            'total': 0,
            'pending': 0,
            'queued': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'retrying': 0,
            'by_type': {}
        }

        # Get all job IDs for this run
        job_ids = self.redis.smembers(self._run_jobs_key(run_id))

        for job_id in job_ids:
            job_data = self.redis.get(self._job_key(job_id))
            if job_data:
                data = json.loads(job_data)
                stats['total'] += 1

                status = data.get('status', 'pending')
                stats[status] = stats.get(status, 0) + 1

                # Track by job type
                type_key = data.get('job_type', 'unknown')
                if type_key not in stats['by_type']:
                    stats['by_type'][type_key] = {'total': 0, 'completed': 0, 'failed': 0}
                stats['by_type'][type_key]['total'] += 1
                if status == 'completed':
                    stats['by_type'][type_key]['completed'] += 1
                elif status == 'failed':
                    stats['by_type'][type_key]['failed'] += 1

        return stats

    def clear_run(self, dd_id: str, run_id: str):
        # Get all job IDs for this run
        job_ids = self.redis.smembers(self._run_jobs_key(run_id))

        if job_ids:
            pipe = self.redis.pipeline()
            for job_id in job_ids:
                pipe.delete(self._job_key(job_id))
                pipe.delete(self._result_key(job_id))
            pipe.delete(self._run_jobs_key(run_id))
            pipe.execute()

        logger.info(f"Cleared {len(job_ids)} jobs for run {run_id}")


def create_job_queue(redis_url: Optional[str] = None) -> JobQueueInterface:
    """
    Factory function to create the appropriate job queue.
    Tries Redis first, falls back to in-memory.
    """
    redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")

    try:
        import redis
        # Test Redis connection
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        logger.info("Redis available, using RedisJobQueue")
        return RedisJobQueue(redis_url)
    except Exception as e:
        logger.warning(f"Redis not available ({e}), using InMemoryJobQueue")
        return InMemoryJobQueue()


def create_job(
    job_type: JobType,
    dd_id: str,
    run_id: str,
    payload: Dict[str, Any],
    priority: int = 5,
    estimated_tokens: int = 2000
) -> Job:
    """Helper function to create a job with a unique ID."""
    return Job(
        job_id=f"{job_type.value}_{uuid.uuid4().hex[:12]}",
        job_type=job_type,
        dd_id=dd_id,
        run_id=run_id,
        payload=payload,
        priority=priority,
        estimated_tokens=estimated_tokens
    )
