/**
 * Enterprise Features Type Definitions
 * Phase 7: Knowledge Graph, Risk Matrix, Collaboration, Reports
 *
 * These interfaces define the TypeScript types for the Phase 7 enterprise
 * features API responses and component props.
 */

// ============================================================================
// Common Types
// ============================================================================

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'none';

export type DealImpact =
  | 'deal_blocker'
  | 'condition_precedent'
  | 'price_chip'
  | 'warranty_indemnity'
  | 'post_closing'
  | 'noted';

export interface User {
  id: string;
  name: string;
  email: string;
  role?: string;
}

export interface UserReference {
  id: string | null;
  name: string | null;
  email?: string | null;
}

// ============================================================================
// Knowledge Graph Types (DDGraphData)
// ============================================================================

export type GraphNodeType = 'party' | 'agreement' | 'trigger' | 'obligation' | 'document';

export type GraphViewType = 'full' | 'parties' | 'agreements' | 'triggers' | 'cluster' | 'obligations';

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  color: string;
  shape: 'circle' | 'square' | 'triangle' | 'diamond' | 'rectangle';
  size: number;
  metadata: GraphNodeMetadata;
}

export interface GraphNodeMetadata {
  // Party metadata
  party_type?: string;
  role?: string;
  jurisdiction?: string;
  document_count?: number;
  agreement_count?: number;

  // Agreement metadata
  full_name?: string;
  agreement_type?: string;
  document_id?: string;
  document_name?: string;
  has_coc?: boolean;
  has_consent?: boolean;
  has_assignment_restriction?: boolean;
  effective_date?: string;
  expiry_date?: string;
  risk_level?: 'low' | 'medium' | 'high' | 'critical';

  // Trigger metadata
  trigger_type?: string;
  description?: string;
  consequences?: string;
  clause_reference?: string;
  agreement_name?: string;

  // Obligation metadata
  obligation_type?: string;
  is_material?: boolean;
  amount?: number;
  currency?: string;

  // Document metadata
  doc_type?: string;
  folder_category?: string;
}

export type GraphEdgeType =
  | 'HAS_TRIGGER'
  | 'PARTY_TO'
  | 'REQUIRES_CONSENT'
  | 'HAS_OBLIGATION';

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  label?: string;
  color: string;
  width: number;
  dashed?: boolean;
  metadata?: {
    clause_reference?: string;
  };
}

export interface GraphCluster {
  id: string;
  nodes: string[];
  size: number;
  types: Record<GraphNodeType, number>;
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  parties: number;
  agreements: number;
  triggers: number;
  obligations: number;
  coc_agreements: number;
  consent_required: number;
}

export interface GraphMetadata {
  dd_id: string;
  view_type: GraphViewType;
  include_documents: boolean;
  generated_at: string;
}

export interface GraphDataResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: GraphCluster[];
  stats: GraphStats;
  metadata: GraphMetadata;
}

// Graph visualization component props
export interface KnowledgeGraphProps {
  ddId: string;
  viewType?: GraphViewType;
  focusNode?: string;
  depth?: number;
  includeDocuments?: boolean;
  onNodeClick?: (node: GraphNode) => void;
  onNodeDoubleClick?: (node: GraphNode) => void;
  width?: number;
  height?: number;
}

// ============================================================================
// Risk Matrix Types (DDRiskMatrix)
// ============================================================================

export interface SeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
  none: number;
}

export interface CategoryBreakdown {
  [category: string]: SeverityBreakdown & { total: number };
}

export interface DealBlocker {
  id: string;
  title: string;
  description: string | null;
  folder_category: string | null;
  risk_category: string | null;
  recommendation: string | null;
}

export interface CoCAnalysis {
  total_agreements: number;
  agreements_with_coc: number;
  agreements_requiring_consent: number;
  coc_risk_percentage: number;
}

export interface FinancialExposure {
  currency: string;
  total_value: number;
  count: number;
}

export interface RiskMatrixGrid {
  rows: string[]; // ['Rare', 'Unlikely', 'Possible', 'Likely', 'Almost Certain']
  cols: string[]; // ['Insignificant', 'Minor', 'Moderate', 'Major', 'Catastrophic']
  cells: number[][]; // 5x5 grid of counts
}

export interface TopRisk {
  id: string;
  title: string;
  description: string | null;
  severity: Severity;
  risk_category: string | null;
  folder_category: string | null;
  recommendation: string | null;
  document_id: string | null;
  clause_reference: string | null;
  deal_impact: DealImpact | null;
  financial_exposure: {
    amount: number | null;
    currency: string | null;
  } | null;
}

export interface RiskMatrixResponse {
  dd_id: string;
  run_id: string;
  generated_at: string;

  // Overall metrics
  risk_score: number; // 0-100
  risk_rating: 'Low' | 'Medium' | 'High' | 'Critical';
  total_findings: number;

  // Breakdowns
  severity_breakdown: SeverityBreakdown;
  folder_breakdown: CategoryBreakdown;
  category_breakdown: CategoryBreakdown;

  // Key risks
  deal_blockers: DealBlocker[];
  deal_blocker_count: number;

  // Change of control analysis
  coc_analysis: CoCAnalysis;

  // Financial exposure
  financial_exposure: {
    from_graph: FinancialExposure[];
    from_findings: FinancialExposure[];
  };
  total_exposure: Record<string, number>;

  // Risk matrix (5x5 grid)
  risk_matrix: RiskMatrixGrid;

  // Top 10 risks
  top_risks: TopRisk[];
}

// Risk matrix component props
export interface RiskMatrixDashboardProps {
  ddId: string;
  runId?: string;
  showFullMatrix?: boolean;
  onDealBlockerClick?: (blocker: DealBlocker) => void;
  onTopRiskClick?: (risk: TopRisk) => void;
}

// ============================================================================
// Collaboration Types (DDCollaboration)
// ============================================================================

// Assignment types
export type AssignmentStatus = 'pending' | 'in_progress' | 'completed';

export interface FindingAssignment {
  id: string;
  finding_id: string;
  assignee: UserReference;
  assigned_by: UserReference;
  assigned_at: string;
  due_date: string | null;
  status: AssignmentStatus;
  notes: string | null;
  completed_at: string | null;
  finding: {
    description: string | null;
    severity: Severity | null;
    folder_category: string | null;
  };
}

export interface AssignmentStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
}

export interface AssignmentsResponse {
  assignments: FindingAssignment[];
  stats: AssignmentStats;
}

// Comment types
export interface FindingComment {
  id: string;
  finding_id: string;
  user: UserReference;
  content: string;
  parent_id: string | null;
  mentioned_user_ids: string[];
  created_at: string;
  updated_at: string | null;
  is_deleted: boolean;
  replies: FindingComment[];
}

export interface CommentsResponse {
  finding_id: string;
  comments: FindingComment[];
  total_count: number;
}

// Workflow types
export type WorkflowStatus = 'pending' | 'in_progress' | 'completed' | 'rejected';

export type WorkflowStage =
  | 'initial_review'
  | 'partner_review'
  | 'final_approval'
  | string;

export interface WorkflowApproval {
  id: string;
  stage: WorkflowStage;
  status: 'approved' | 'rejected';
  approver: UserReference;
  approved_at: string;
  comments: string | null;
}

export interface ReviewWorkflow {
  id: string;
  dd_id: string;
  run_id: string | null;
  workflow_type: 'standard' | 'expedited';
  current_stage: WorkflowStage;
  stages: WorkflowStage[];
  stage_progress: {
    current: number;
    total: number;
  };
  status: WorkflowStatus;
  created_by: UserReference;
  created_at: string;
  completed_at: string | null;
  approvals: WorkflowApproval[];
}

export interface WorkflowStatusResponse {
  dd_id: string;
  workflows: ReviewWorkflow[];
  active_workflow: ReviewWorkflow | null;
}

// Collaboration component props
export interface FindingAssignmentsProps {
  ddId: string;
  findingId?: string;
  userId?: string;
  onAssign?: (findingId: string, assigneeId: string) => void;
  onUnassign?: (assignmentId: string) => void;
  showStats?: boolean;
}

export interface FindingCommentsProps {
  findingId: string;
  ddId: string;
  userId: string;
  onCommentAdded?: (comment: FindingComment) => void;
  allowThreading?: boolean;
  allowMentions?: boolean;
}

export interface WorkflowStatusProps {
  ddId: string;
  runId?: string;
  onApprove?: (workflowId: string) => void;
  onReject?: (workflowId: string, reason: string) => void;
  showTimeline?: boolean;
}

// ============================================================================
// Report Generation Types (DDReportGenerate)
// ============================================================================

export type ReportFormat = 'pdf' | 'docx' | 'xlsx' | 'json';

export type ExportType = 'full_report' | 'findings_export' | 'graph_export';

export type ExportJobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ReportTemplate {
  id: string;
  name: string;
  description: string | null;
  format: ReportFormat;
  report_type: string;
}

export interface ExportJob {
  id: string;
  dd_id: string;
  export_type: ExportType;
  format: ReportFormat;
  status: ExportJobStatus;
  file_path: string | null;
  error_message: string | null;
  created_by: UserReference;
  created_at: string;
  completed_at: string | null;
}

export interface TemplatesResponse {
  templates: ReportTemplate[];
}

export interface ExportJobsResponse {
  jobs: ExportJob[];
}

export interface DownloadUrlResponse {
  url?: string;
  format?: ReportFormat;
  error?: string;
}

export interface GenerateReportRequest {
  action: 'generate_report';
  dd_id: string;
  run_id?: string;
  format: 'pdf' | 'docx';
  template_id?: string;
  sections?: string[];
  created_by?: string;
}

export interface ExportFindingsRequest {
  action: 'export_findings';
  dd_id: string;
  run_id?: string;
  created_by?: string;
}

export interface ExportGraphRequest {
  action: 'export_graph';
  dd_id: string;
  created_by?: string;
}

export interface GenerateReportResponse {
  success: boolean;
  job_id: string;
  file_path?: string;
  message?: string;
  error?: string;
  findings_count?: number;
  stats?: {
    parties: number;
    agreements: number;
    triggers: number;
  };
}

// Report generation component props
export interface ReportGeneratorProps {
  ddId: string;
  runId?: string;
  userId?: string;
  onReportGenerated?: (job: ExportJob) => void;
  defaultFormat?: ReportFormat;
  showTemplates?: boolean;
}

export interface ExportHistoryProps {
  ddId: string;
  limit?: number;
  onDownload?: (job: ExportJob) => void;
  showPending?: boolean;
}

// ============================================================================
// Audit Log Types
// ============================================================================

export type AuditEventType =
  | 'document_uploaded'
  | 'document_classified'
  | 'document_moved'
  | 'document_deleted'
  | 'document_viewed'
  | 'analysis_started'
  | 'analysis_completed'
  | 'analysis_failed'
  | 'finding_created'
  | 'finding_updated'
  | 'finding_assigned'
  | 'finding_approved'
  | 'finding_rejected'
  | 'finding_escalated'
  | 'comment_added'
  | 'comment_edited'
  | 'comment_deleted'
  | 'workflow_started'
  | 'workflow_stage_completed'
  | 'workflow_approved'
  | 'workflow_rejected'
  | 'report_generated'
  | 'report_exported'
  | 'report_downloaded'
  | 'report_shared'
  | 'dd_accessed'
  | 'dd_created'
  | 'dd_deleted'
  | 'graph_queried'
  | 'system_error'
  | 'rate_limit_hit';

export interface AuditLogEntry {
  id: string;
  event_type: AuditEventType;
  user_id: string | null;
  entity_type: string;
  entity_id: string;
  dd_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
  user_name: string | null;
  user_email: string | null;
}

export interface AuditSummary {
  dd_id: string;
  event_counts: Record<AuditEventType, number>;
  unique_users: User[];
  timeline: Array<{
    date: string;
    count: number;
  }>;
  total_events: number;
}

export interface AuditTrailProps {
  ddId?: string;
  entityType?: string;
  entityId?: string;
  limit?: number;
  onEventClick?: (event: AuditLogEntry) => void;
}

// ============================================================================
// API Hook Return Types
// ============================================================================

export interface UseGraphDataOptions {
  ddId: string;
  viewType?: GraphViewType;
  focusNode?: string;
  depth?: number;
  includeDocuments?: boolean;
  enabled?: boolean;
}

export interface UseRiskMatrixOptions {
  ddId: string;
  runId?: string;
  enabled?: boolean;
}

export interface UseCollaborationOptions {
  ddId: string;
  findingId?: string;
  userId?: string;
  enabled?: boolean;
}

export interface UseReportGenerateOptions {
  ddId: string;
  onSuccess?: (response: GenerateReportResponse) => void;
  onError?: (error: Error) => void;
}

// ============================================================================
// Utility Types
// ============================================================================

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

export interface MutationResponse<T> {
  mutate: (data: unknown) => Promise<T>;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  data: T | null;
}
