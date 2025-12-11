/**
 * DD Processing Dashboard Hooks
 *
 * Custom React hooks for real-time processing data and accessibility.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  ProcessingProgress,
  LiveFinding,
  ProcessingPass,
  ProcessingStatus,
  SSEEvent,
  DocumentStatus
} from './types';

/**
 * Hook to detect user's reduced motion preference
 */
export function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return reducedMotion;
}

/**
 * Hook to poll processing progress from the backend
 */
export function useProcessingProgress(
  ddId: string,
  pollInterval: number = 2000
): {
  progress: ProcessingProgress | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
} {
  const [progress, setProgress] = useState<ProcessingProgress | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchProgress = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/dd-progress-enhanced?dd_id=${ddId}`,
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Transform backend data to our format
      const transformed: ProcessingProgress = {
        ddId: data.dd_id,
        status: data.status as ProcessingStatus,
        currentPass: data.current_pass as ProcessingPass,
        currentStage: data.current_stage,
        currentDocumentName: data.current_document_name ?? undefined,

        passProgress: {
          extract: {
            status: getPassStatus(data, 'extract'),
            progress: data.pass_progress?.extract?.progress ?? 0,
            itemsProcessed: data.pass_progress?.extract?.items_processed ?? 0,
            totalItems: data.pass_progress?.extract?.total_items ?? 0
          },
          analyze: {
            status: getPassStatus(data, 'analyze'),
            progress: data.pass_progress?.analyze?.progress ?? 0,
            itemsProcessed: data.pass_progress?.analyze?.items_processed ?? 0,
            totalItems: data.pass_progress?.analyze?.total_items ?? 0
          },
          crossdoc: {
            status: getPassStatus(data, 'crossdoc'),
            progress: data.pass_progress?.crossdoc?.progress ?? 0,
            itemsProcessed: data.pass_progress?.crossdoc?.items_processed ?? 0,
            totalItems: data.pass_progress?.crossdoc?.total_items ?? 0
          },
          synthesize: {
            status: getPassStatus(data, 'synthesize'),
            progress: data.pass_progress?.synthesize?.progress ?? 0,
            itemsProcessed: data.pass_progress?.synthesize?.items_processed ?? 0,
            totalItems: data.pass_progress?.synthesize?.total_items ?? 0
          }
        },

        documents: (data.documents ?? []).map((d: Record<string, unknown>) => ({
          id: d.id as string,
          filename: d.filename as string,
          docType: d.doc_type as string,
          status: d.status as DocumentStatus['status'],
          currentPass: d.current_pass as ProcessingPass | undefined,
          progress: d.progress as number | undefined,
          error: d.error as string | undefined
        })),
        documentsProcessed: data.documents_processed ?? 0,
        totalDocuments: data.total_documents ?? 0,

        startedAt: new Date(data.started_at),
        estimatedCompletion: data.estimated_completion
          ? new Date(data.estimated_completion)
          : undefined,
        elapsedSeconds: data.elapsed_seconds ?? 0,

        totalInputTokens: data.total_input_tokens ?? 0,
        totalOutputTokens: data.total_output_tokens ?? 0,
        estimatedCostUsd: data.estimated_cost_usd ?? 0,

        findingCounts: {
          total: data.finding_counts?.total ?? 0,
          critical: data.finding_counts?.critical ?? 0,
          high: data.finding_counts?.high ?? 0,
          medium: data.finding_counts?.medium ?? 0,
          low: data.finding_counts?.low ?? 0,
          dealBlockers: data.finding_counts?.deal_blockers ?? 0,
          conditionsPrecedent: data.finding_counts?.conditions_precedent ?? 0
        },

        lastError: data.last_error,
        retryCount: data.retry_count ?? 0
      };

      setProgress(transformed);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch progress');
    } finally {
      setIsLoading(false);
    }
  }, [ddId]);

  // Initial fetch and polling
  useEffect(() => {
    fetchProgress();

    intervalRef.current = setInterval(fetchProgress, pollInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchProgress, pollInterval]);

  // Stop polling when completed or failed
  useEffect(() => {
    if (progress?.status === 'completed' || progress?.status === 'failed') {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [progress?.status]);

  return { progress, isLoading, error, refetch: fetchProgress };
}

/**
 * Helper to determine pass status from backend data
 */
function getPassStatus(
  data: Record<string, unknown>,
  pass: ProcessingPass
): ProcessingStatus {
  const passOrder: ProcessingPass[] = ['extract', 'analyze', 'crossdoc', 'synthesize'];
  const currentIndex = passOrder.indexOf(data.current_pass as ProcessingPass);
  const passIndex = passOrder.indexOf(pass);

  if (data.status === 'completed') return 'completed';
  if (data.status === 'failed') {
    if (passIndex <= currentIndex) return 'failed';
    return 'pending';
  }

  if (passIndex < currentIndex) return 'completed';
  if (passIndex === currentIndex) return 'processing';
  return 'pending';
}

/**
 * Hook for Server-Sent Events to receive live findings
 */
export function useLiveFindings(
  ddId: string,
  maxFindings: number = 50
): {
  findings: LiveFinding[];
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
} {
  const [findings, setFindings] = useState<LiveFinding[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource(
        `/api/dd-findings-stream?dd_id=${ddId}`
      );
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const sseEvent: SSEEvent<LiveFinding> = JSON.parse(event.data);

          if (sseEvent.type === 'finding' && sseEvent.data) {
            const finding: LiveFinding = {
              ...sseEvent.data,
              id: sseEvent.data.id || `finding-${Date.now()}`,
              timestamp: new Date(sseEvent.timestamp)
            };

            setFindings((prev) => {
              const updated = [finding, ...prev];
              // Keep only the most recent findings
              return updated.slice(0, maxFindings);
            });
          }
        } catch (e) {
          console.error('Error parsing SSE event:', e);
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();

        // Exponential backoff for reconnection
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;

        if (reconnectAttempts.current < 10) {
          setError(`Connection lost. Reconnecting in ${delay / 1000}s...`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          setError('Unable to connect to live findings stream');
        }
      };
    } catch (e) {
      setError('Failed to establish SSE connection');
      setIsConnected(false);
    }
  }, [ddId, maxFindings]);

  const reconnect = useCallback(() => {
    reconnectAttempts.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { findings, isConnected, error, reconnect };
}

/**
 * Hook to calculate elapsed time with live updates
 */
export function useElapsedTime(startedAt: Date | null): string {
  const [elapsed, setElapsed] = useState('00:00');

  useEffect(() => {
    if (!startedAt) {
      setElapsed('00:00');
      return;
    }

    const updateElapsed = () => {
      const now = new Date();
      const diff = Math.floor((now.getTime() - startedAt.getTime()) / 1000);
      const minutes = Math.floor(diff / 60);
      const seconds = diff % 60;
      setElapsed(`${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [startedAt]);

  return elapsed;
}

/**
 * Hook to animate number changes
 */
export function useAnimatedNumber(
  targetValue: number,
  duration: number = 500
): number {
  const [displayValue, setDisplayValue] = useState(targetValue);
  const previousValue = useRef(targetValue);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const startValue = previousValue.current;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startValue + (targetValue - startValue) * eased);

      setDisplayValue(current);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        previousValue.current = targetValue;
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [targetValue, duration]);

  return displayValue;
}

/**
 * Hook to format currency with animation
 */
export function useAnimatedCurrency(
  value: number,
  currency: string = 'USD'
): string {
  const animatedValue = useAnimatedNumber(value * 100) / 100;

  return useMemo(() => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(animatedValue);
  }, [animatedValue, currency]);
}

/**
 * Hook to start async DD processing
 * Returns 202 immediately, frontend polls for progress
 */
export function useStartProcessing(): {
  startProcessing: (ddId: string, options?: { includeTier3?: boolean; useClusteredPass3?: boolean }) => Promise<{
    status: string;
    checkpointId: string;
    totalDocuments: number;
  }>;
  isStarting: boolean;
  error: string | null;
} {
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startProcessing = useCallback(async (
    ddId: string,
    options: { includeTier3?: boolean; useClusteredPass3?: boolean } = {}
  ) => {
    setIsStarting(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/dd-process-enhanced-start?dd_id=${ddId}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            include_tier3: options.includeTier3 ?? false,
            use_clustered_pass3: options.useClusteredPass3 ?? true
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }

      return {
        status: data.status,
        checkpointId: data.checkpoint_id,
        totalDocuments: data.total_documents
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start processing';
      setError(message);
      throw err;
    } finally {
      setIsStarting(false);
    }
  }, []);

  return { startProcessing, isStarting, error };
}
