/**
 * Enterprise Features Hooks
 * Phase 7: React Query hooks for Knowledge Graph, Risk Matrix, Collaboration, Reports
 *
 * These hooks provide data fetching for the Phase 7 enterprise features.
 * Implementation uses React Query patterns consistent with existing hooks.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAxiosWithAuth } from './useAxiosWithAuth';
import type {
  // Graph types
  GraphDataResponse,
  GraphViewType,

  // Risk Matrix types
  RiskMatrixResponse,

  // Collaboration types
  AssignmentsResponse,
  CommentsResponse,
  WorkflowStatusResponse,
  AssignmentStatus,

  // Report types
  TemplatesResponse,
  ExportJobsResponse,
  DownloadUrlResponse,
  GenerateReportResponse,
  ReportFormat,

  // User types
  User,
} from '../types/enterprise';

const API_BASE = import.meta.env.VITE_API_BASE_URL;

// ============================================================================
// Knowledge Graph Hooks
// ============================================================================

export interface UseGraphDataParams {
  ddId: string;
  viewType?: GraphViewType;
  focusNode?: string;
  depth?: number;
  includeDocuments?: boolean;
  enabled?: boolean;
}

/**
 * Fetch knowledge graph visualization data
 *
 * @example
 * const { data, isLoading } = useGraphData({
 *   ddId: '123',
 *   viewType: 'full',
 *   includeDocuments: false
 * });
 */
export function useGraphData({
  ddId,
  viewType = 'full',
  focusNode,
  depth = 2,
  includeDocuments = false,
  enabled = true,
}: UseGraphDataParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<GraphDataResponse>({
    queryKey: ['graphData', ddId, viewType, focusNode, depth, includeDocuments],
    queryFn: async () => {
      const params = new URLSearchParams({
        dd_id: ddId,
        view_type: viewType,
        depth: String(depth),
        include_documents: String(includeDocuments),
      });

      if (focusNode) {
        params.append('focus_node', focusNode);
      }

      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-graph-data?${params.toString()}`
      );
      return response.data;
    },
    enabled: enabled && !!ddId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// ============================================================================
// Risk Matrix Hooks
// ============================================================================

export interface UseRiskMatrixParams {
  ddId: string;
  runId?: string;
  enabled?: boolean;
}

/**
 * Fetch risk matrix and dashboard data
 *
 * @example
 * const { data, isLoading } = useRiskMatrix({ ddId: '123' });
 * console.log(data?.risk_score, data?.deal_blockers);
 */
export function useRiskMatrix({
  ddId,
  runId,
  enabled = true,
}: UseRiskMatrixParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<RiskMatrixResponse>({
    queryKey: ['riskMatrix', ddId, runId],
    queryFn: async () => {
      const params = new URLSearchParams({ dd_id: ddId });
      if (runId) {
        params.append('run_id', runId);
      }

      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-risk-matrix?${params.toString()}`
      );
      return response.data;
    },
    enabled: enabled && !!ddId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// ============================================================================
// Collaboration Hooks - Assignments
// ============================================================================

export interface UseAssignmentsParams {
  ddId: string;
  findingId?: string;
  userId?: string;
  enabled?: boolean;
}

/**
 * Fetch finding assignments
 *
 * @example
 * const { data } = useAssignments({ ddId: '123', userId: 'user-456' });
 */
export function useAssignments({
  ddId,
  findingId,
  userId,
  enabled = true,
}: UseAssignmentsParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<AssignmentsResponse>({
    queryKey: ['assignments', ddId, findingId, userId],
    queryFn: async () => {
      const params = new URLSearchParams({
        dd_id: ddId,
        action: 'get_assignments',
      });
      if (findingId) params.append('finding_id', findingId);
      if (userId) params.append('user_id', userId);

      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-collaboration?${params.toString()}`
      );
      return response.data;
    },
    enabled: enabled && !!ddId,
  });
}

export interface AssignFindingParams {
  ddId: string;
  findingId: string;
  assigneeId: string;
  assignedBy: string;
  dueDate?: string;
  notes?: string;
}

/**
 * Assign a finding to a user
 *
 * @example
 * const { mutate } = useAssignFinding();
 * mutate({ ddId: '123', findingId: 'f1', assigneeId: 'u1', assignedBy: 'u2' });
 */
export function useAssignFinding() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: AssignFindingParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'assign_finding',
          dd_id: params.ddId,
          finding_id: params.findingId,
          assignee_id: params.assigneeId,
          assigned_by: params.assignedBy,
          due_date: params.dueDate,
          notes: params.notes,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['assignments', params.ddId],
      });
    },
  });
}

export interface UnassignFindingParams {
  ddId: string;
  assignmentId: string;
  userId: string;
}

/**
 * Remove an assignment
 */
export function useUnassignFinding() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: UnassignFindingParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'unassign_finding',
          dd_id: params.ddId,
          assignment_id: params.assignmentId,
          user_id: params.userId,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['assignments', params.ddId],
      });
    },
  });
}

// ============================================================================
// Collaboration Hooks - Comments
// ============================================================================

export interface UseCommentsParams {
  findingId: string;
  enabled?: boolean;
}

/**
 * Fetch comments for a finding
 *
 * @example
 * const { data } = useComments({ findingId: 'f123' });
 */
export function useComments({ findingId, enabled = true }: UseCommentsParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<CommentsResponse>({
    queryKey: ['comments', findingId],
    queryFn: async () => {
      const params = new URLSearchParams({
        dd_id: '', // Placeholder - finding_id is sufficient
        action: 'get_comments',
        finding_id: findingId,
      });

      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-collaboration?${params.toString()}`
      );
      return response.data;
    },
    enabled: enabled && !!findingId,
  });
}

export interface AddCommentParams {
  ddId: string;
  findingId: string;
  userId: string;
  content: string;
  parentId?: string;
  mentionedUserIds?: string[];
}

/**
 * Add a comment to a finding
 */
export function useAddComment() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: AddCommentParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'add_comment',
          dd_id: params.ddId,
          finding_id: params.findingId,
          user_id: params.userId,
          content: params.content,
          parent_id: params.parentId,
          mentioned_user_ids: params.mentionedUserIds || [],
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['comments', params.findingId],
      });
    },
  });
}

export interface DeleteCommentParams {
  ddId: string;
  commentId: string;
  userId: string;
  findingId: string; // For cache invalidation
}

/**
 * Delete a comment
 */
export function useDeleteComment() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: DeleteCommentParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'delete_comment',
          dd_id: params.ddId,
          comment_id: params.commentId,
          user_id: params.userId,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['comments', params.findingId],
      });
    },
  });
}

// ============================================================================
// Collaboration Hooks - Workflows
// ============================================================================

export interface UseWorkflowStatusParams {
  ddId: string;
  runId?: string;
  enabled?: boolean;
}

/**
 * Fetch workflow status for a DD project
 */
export function useWorkflowStatus({
  ddId,
  runId,
  enabled = true,
}: UseWorkflowStatusParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<WorkflowStatusResponse>({
    queryKey: ['workflowStatus', ddId, runId],
    queryFn: async () => {
      const params = new URLSearchParams({
        dd_id: ddId,
        action: 'get_workflow_status',
      });
      if (runId) params.append('run_id', runId);

      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-collaboration?${params.toString()}`
      );
      return response.data;
    },
    enabled: enabled && !!ddId,
  });
}

export interface StartWorkflowParams {
  ddId: string;
  runId: string;
  createdBy: string;
  stages?: string[];
  workflowType?: 'standard' | 'expedited';
}

/**
 * Start a review workflow
 */
export function useStartWorkflow() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: StartWorkflowParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'start_workflow',
          dd_id: params.ddId,
          run_id: params.runId,
          created_by: params.createdBy,
          stages: params.stages,
          workflow_type: params.workflowType || 'standard',
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['workflowStatus', params.ddId],
      });
    },
  });
}

export interface ApproveStageParams {
  ddId: string;
  workflowId: string;
  userId: string;
  comments?: string;
}

/**
 * Approve the current workflow stage
 */
export function useApproveStage() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: ApproveStageParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'approve_stage',
          dd_id: params.ddId,
          workflow_id: params.workflowId,
          user_id: params.userId,
          comments: params.comments,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['workflowStatus', params.ddId],
      });
    },
  });
}

export interface RejectStageParams {
  ddId: string;
  workflowId: string;
  userId: string;
  comments: string; // Required for rejection
}

/**
 * Reject the current workflow stage
 */
export function useRejectStage() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: RejectStageParams) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-collaboration`,
        {
          action: 'reject_stage',
          dd_id: params.ddId,
          workflow_id: params.workflowId,
          user_id: params.userId,
          comments: params.comments,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['workflowStatus', params.ddId],
      });
    },
  });
}

// ============================================================================
// Report Generation Hooks
// ============================================================================

/**
 * Fetch available report templates
 */
export function useReportTemplates() {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<TemplatesResponse>({
    queryKey: ['reportTemplates'],
    queryFn: async () => {
      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-report-generate?action=list_templates`
      );
      return response.data;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

export interface UseExportJobsParams {
  ddId: string;
  enabled?: boolean;
}

/**
 * Fetch export job history for a DD project
 */
export function useExportJobs({ ddId, enabled = true }: UseExportJobsParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<ExportJobsResponse>({
    queryKey: ['exportJobs', ddId],
    queryFn: async () => {
      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-report-generate?action=get_export_jobs&dd_id=${ddId}`
      );
      return response.data;
    },
    enabled: enabled && !!ddId,
    refetchInterval: 5000, // Poll every 5 seconds for job status
  });
}

export interface UseDownloadUrlParams {
  jobId: string;
  enabled?: boolean;
}

/**
 * Get download URL for a completed export job
 */
export function useDownloadUrl({ jobId, enabled = true }: UseDownloadUrlParams) {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<DownloadUrlResponse>({
    queryKey: ['downloadUrl', jobId],
    queryFn: async () => {
      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-report-generate?action=get_download_url&job_id=${jobId}`
      );
      return response.data;
    },
    enabled: enabled && !!jobId,
    staleTime: 60 * 1000, // 1 minute (SAS URLs expire)
  });
}

export interface GenerateReportParams {
  ddId: string;
  runId?: string;
  format: 'pdf' | 'docx';
  templateId?: string;
  sections?: string[];
  createdBy?: string;
}

/**
 * Generate a DD report (PDF or DOCX)
 */
export function useGenerateReport() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<GenerateReportResponse, Error, GenerateReportParams>({
    mutationFn: async (params) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-report-generate`,
        {
          action: 'generate_report',
          dd_id: params.ddId,
          run_id: params.runId,
          format: params.format,
          template_id: params.templateId,
          sections: params.sections,
          created_by: params.createdBy,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['exportJobs', params.ddId],
      });
    },
  });
}

export interface ExportFindingsParams {
  ddId: string;
  runId?: string;
  createdBy?: string;
}

/**
 * Export findings to Excel
 */
export function useExportFindings() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<GenerateReportResponse, Error, ExportFindingsParams>({
    mutationFn: async (params) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-report-generate`,
        {
          action: 'export_findings',
          dd_id: params.ddId,
          run_id: params.runId,
          created_by: params.createdBy,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['exportJobs', params.ddId],
      });
    },
  });
}

export interface ExportGraphParams {
  ddId: string;
  createdBy?: string;
}

/**
 * Export knowledge graph data to JSON
 */
export function useExportGraph() {
  const axiosWithAuth = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<GenerateReportResponse, Error, ExportGraphParams>({
    mutationFn: async (params) => {
      const response = await axiosWithAuth.post(
        `${API_BASE}/dd-report-generate`,
        {
          action: 'export_graph',
          dd_id: params.ddId,
          created_by: params.createdBy,
        }
      );
      return response.data;
    },
    onSuccess: (_, params) => {
      queryClient.invalidateQueries({
        queryKey: ['exportJobs', params.ddId],
      });
    },
  });
}

// ============================================================================
// User Hooks
// ============================================================================

/**
 * Fetch list of users (for assignment dropdowns)
 */
export function useUsers() {
  const axiosWithAuth = useAxiosWithAuth();

  return useQuery<{ users: User[] }>({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await axiosWithAuth.get(
        `${API_BASE}/dd-collaboration?dd_id=&action=get_users`
      );
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
