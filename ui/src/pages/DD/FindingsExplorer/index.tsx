/**
 * Findings Explorer - Three-Panel Layout
 *
 * A professional, minimalist interface for exploring DD findings:
 * - Left Panel: Document Navigator (filter by document)
 * - Middle Panel: Findings List (grouped by severity)
 * - Right Panel: Finding Detail (full context + AI chat)
 */

export { FindingsExplorer } from './FindingsExplorer';
export { RunSelector } from './RunSelector';
export { DocumentNavigator } from './DocumentNavigator';
export { FindingsList } from './FindingsList';
export { FindingDetail } from './FindingDetail';
export type { Finding, DocumentWithFindings, RunInfo } from './types';
