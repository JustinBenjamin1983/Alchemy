/**
 * DD Processing Dashboard Types
 *
 * TypeScript interfaces for the real-time processing visualization.
 */

// Processing pass definitions - 7 passes in the enhanced pipeline
export type ProcessingPass =
  | 'extract'    // Pass 1: Haiku extraction
  | 'analyze'    // Pass 2: Sonnet analysis
  | 'calculate'  // Pass 2.5: Python calculations
  | 'crossdoc'   // Pass 3: Opus cross-document
  | 'aggregate'  // Pass 3.5: Python aggregation
  | 'synthesize' // Pass 4: Sonnet synthesis
  | 'verify';    // Pass 5: Opus verification

// Status colors used across all passes
export const STATUS_COLORS = {
  default: '#d1d5db',    // gray-300 - light grey (pending)
  active: '#22c55e',     // green-500 - actively processing
  success: '#22c55e',    // green-500 - completion
  failed: '#dc2626',     // red-600 - failure
};

// Ring colors for concentric visualization (Apple Watch style)
// Option K: Blue 3D v2 (dark blue outer, bigger contrast jumps toward center)
export const RING_COLORS = {
  extract:    '#1e3a8a', // Dark blue (not black)
  analyze:    '#1d4ed8', // Royal blue
  calculate:  '#2563eb', // Blue
  crossdoc:   '#3b82f6', // Bright blue
  aggregate:  '#60a5fa', // Sky blue
  synthesize: '#93c5fd', // Light blue
  verify:     '#bfdbfe', // Pale blue (maximum glow)
};

// Order of passes for concentric rings (outside to inside)
export const PASS_ORDER: ProcessingPass[] = [
  'extract',
  'analyze',
  'calculate',
  'crossdoc',
  'aggregate',
  'synthesize',
  'verify'
];

export const PASS_CONFIG: Record<ProcessingPass, {
  label: string;
  shortLabel: string;
  color: string;
  ringColor: string;
  description: string;
}> = {
  extract: {
    label: 'Extracting Key Data',
    shortLabel: 'Extract',
    color: RING_COLORS.extract,
    ringColor: RING_COLORS.extract,
    description: 'Identifying clauses, dates, parties, and financial terms'
  },
  analyze: {
    label: 'Analysing Documents',
    shortLabel: 'Analyse',
    color: RING_COLORS.analyze,
    ringColor: RING_COLORS.analyze,
    description: 'Reviewing each document for risks and issues'
  },
  calculate: {
    label: 'Calculating Exposures',
    shortLabel: 'Calculate',
    color: RING_COLORS.calculate,
    ringColor: RING_COLORS.calculate,
    description: 'Computing financial exposures from extracted data'
  },
  crossdoc: {
    label: 'Cross-Document Analysis',
    shortLabel: 'Cross-Doc',
    color: RING_COLORS.crossdoc,
    ringColor: RING_COLORS.crossdoc,
    description: 'Finding conflicts and cascade effects across documents'
  },
  aggregate: {
    label: 'Aggregating Results',
    shortLabel: 'Aggregate',
    color: RING_COLORS.aggregate,
    ringColor: RING_COLORS.aggregate,
    description: 'Combining calculations across all documents'
  },
  synthesize: {
    label: 'Synthesising Findings',
    shortLabel: 'Synthesise',
    color: RING_COLORS.synthesize,
    ringColor: RING_COLORS.synthesize,
    description: 'Consolidating results and generating recommendations'
  },
  verify: {
    label: 'Verifying Analysis',
    shortLabel: 'Verify',
    color: RING_COLORS.verify,
    ringColor: RING_COLORS.verify,
    description: 'Final quality check on deal-blockers and calculations'
  }
};

// Processing status
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'paused' | 'cancelled';

// Document status during processing
export interface DocumentStatus {
  id: string;
  filename: string;
  docType: string;
  status: 'queued' | 'processing' | 'completed' | 'error';
  currentPass?: ProcessingPass;
  progress?: number; // 0-100
  error?: string;
}

// Live finding from SSE stream
export interface LiveFinding {
  id: string;
  findingId: string;
  timestamp: Date;
  sourceDocument: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  dealImpact: 'deal_blocker' | 'condition_precedent' | 'price_chip' | 'warranty_indemnity' | 'post_closing' | 'noted';
  description: string;
  pass: ProcessingPass;
  clauseReference?: string;
  financialExposure?: {
    amount: number;
    currency: string;
  };
}

// Phase 4: Compression stats
export interface CompressionStats {
  totalDocuments: number;
  totalOriginalTokens: number;
  totalCompressedTokens: number;
  compressionRatio: number; // percentage reduction
  byPriority: Record<string, {
    count: number;
    originalTokens: number;
    compressedTokens: number;
  }>;
  errors: number;
}

// Phase 4: Batch stats
export interface BatchStats {
  totalBatches: number;
  totalDocuments: number;
  totalTokens: number;
  strategy: 'by_folder' | 'by_size' | 'mixed';
  docsPerBatch: {
    min: number;
    max: number;
    avg: number;
  };
  tokensPerBatch: {
    min: number;
    max: number;
    avg: number;
  };
  priorityDistribution: {
    critical: number;
    high: number;
    other: number;
  };
}

// Overall progress state
export interface ProcessingProgress {
  ddId: string;
  runId?: string;
  status: ProcessingStatus;
  currentPass: ProcessingPass;
  currentStage?: string;
  currentDocumentName?: string;

  // Pass completion
  passProgress: Record<ProcessingPass, {
    status: ProcessingStatus;
    progress: number; // 0-100
    itemsProcessed: number;
    totalItems: number;
  }>;

  // Document tracking
  documents: DocumentStatus[];
  documentsProcessed: number;
  totalDocuments: number;

  // Timing
  startedAt: Date;
  lastUpdated?: Date;
  estimatedCompletion?: Date;
  elapsedSeconds: number;

  // Cost tracking
  totalInputTokens: number;
  totalOutputTokens: number;
  estimatedCostUsd: number;

  // Finding counts
  findingCounts: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    positive: number;
    dealBlockers: number;
    conditionsPrecedent: number;
    warranties: number;
    indemnities: number;
  };

  // Error state
  lastError?: string;
  retryCount: number;

  // Phase 4: Compression & Batching
  compressionEnabled?: boolean;
  batchingEnabled?: boolean;
  totalBatches?: number;
  batchesCompleted?: number;
  compressionStats?: CompressionStats;
  batchStats?: BatchStats;
}

// SSE event types
export type SSEEventType =
  | 'progress'
  | 'finding'
  | 'document_started'
  | 'document_completed'
  | 'pass_started'
  | 'pass_completed'
  | 'error'
  | 'complete';

export interface SSEEvent<T = unknown> {
  type: SSEEventType;
  timestamp: string;
  data: T;
}

// Risk summary for counters
export interface RiskSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  positive: number;
  dealBlockers: number;
  conditionsPrecedent: number;
  warranties: number;
  indemnities: number;
  completionPercent: number;
  totalExposure: number;
  currency: string;
}

// Animation state for rings
export interface RingAnimationState {
  pass: ProcessingPass;
  isActive: boolean;
  progress: number;
  pulseIntensity: number;
}

// Particle for flow animation
export interface Particle {
  id: string;
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
  angle: number;
}
