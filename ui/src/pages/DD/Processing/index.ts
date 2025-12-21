/**
 * DD Processing Dashboard Module
 *
 * Exports all components and types for the real-time processing visualization.
 */

// Main dashboard component
export { DDProcessingDashboard } from './DDProcessingDashboard';
export { default } from './DDProcessingDashboard';

// Sub-components
export { PipelineRings } from './PipelineRings';
export { LiveFindingsFeed, RiskSummaryCounters } from './FindingsFeed';
export { DocumentStatusGrid, DocumentCard, ProcessingShimmer } from './DocumentStatus';
export { TransactionSummary } from './TransactionSummary';
export { DocumentChecklistPanel } from './DocumentChecklistPanel';
export { ProcessLog, createLogEntry } from './ProcessLog';
export { FileTree } from './FileTree';

// Hooks
export {
  useReducedMotion,
  useProcessingProgress,
  useLiveFindings,
  useElapsedTime,
  useAnimatedNumber,
  useAnimatedCurrency
} from './hooks';

// Types
export type {
  ProcessingPass,
  ProcessingStatus,
  DocumentStatus,
  LiveFinding,
  ProcessingProgress,
  SSEEventType,
  SSEEvent,
  RiskSummary,
  RingAnimationState,
  Particle
} from './types';

export { PASS_CONFIG } from './types';

// Animation variants
export {
  ringPulseVariants,
  ringProgressVariants,
  particleVariants,
  findingCardVariants,
  severityPulseVariants,
  shimmerVariants,
  counterVariants,
  staggerContainerVariants,
  staggerChildVariants,
  passTransitionVariants,
  statusIconVariants,
  progressBarVariants,
  glowVariants,
  tickerVariants,
  celebrationVariants,
  reducedMotionVariants,
  SPRING_GENTLE,
  SPRING_BOUNCY,
  SPRING_SNAPPY,
  EASE_OUT_EXPO,
  EASE_OUT_QUART,
  EASE_IN_OUT_CUBIC
} from './animations';
