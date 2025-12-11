/**
 * DD Processing Dashboard Types
 *
 * TypeScript interfaces for the real-time processing visualization.
 */

// Processing pass definitions
export type ProcessingPass = 'extract' | 'analyze' | 'crossdoc' | 'synthesize';

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
    color: '#3B82F6', // blue-500
    ringColor: 'rgba(59, 130, 246, 0.8)',
    description: 'Identifying clauses, dates, parties, and financial terms'
  },
  analyze: {
    label: 'Analyzing Documents',
    shortLabel: 'Analyze',
    color: '#8B5CF6', // violet-500
    ringColor: 'rgba(139, 92, 246, 0.8)',
    description: 'Reviewing each document for risks and issues'
  },
  crossdoc: {
    label: 'Cross-Document Analysis',
    shortLabel: 'Cross-Doc',
    color: '#EC4899', // pink-500
    ringColor: 'rgba(236, 72, 153, 0.8)',
    description: 'Finding conflicts and cascade effects across documents'
  },
  synthesize: {
    label: 'Synthesizing Findings',
    shortLabel: 'Synthesize',
    color: '#10B981', // emerald-500
    ringColor: 'rgba(16, 185, 129, 0.8)',
    description: 'Consolidating results and generating recommendations'
  }
};

// Processing status
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'paused';

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

// Overall progress state
export interface ProcessingProgress {
  ddId: string;
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
    dealBlockers: number;
    conditionsPrecedent: number;
  };

  // Error state
  lastError?: string;
  retryCount: number;
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
  critical: number;
  high: number;
  medium: number;
  low: number;
  dealBlockers: number;
  conditionsPrecedent: number;
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
