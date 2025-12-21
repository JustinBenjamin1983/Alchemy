// hooks/useOrganisationProgress.ts
/**
 * Hook to poll DDOrganisationProgress endpoint for document classification status.
 * Used during the "organising" phase before DD processing can begin.
 */
import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export type OrganisationStatus =
  | "pending"
  | "classifying"
  | "classified"    // Phase 2: Classification complete, ready for folder organisation
  | "organising"
  | "organised"     // Phase 2: Folders created, documents moved, ready for readability
  | "completed"
  | "failed"
  | "cancelled";

export interface OrganisationProgress {
  dd_id: string;
  status: OrganisationStatus;
  totalDocuments: number;
  classifiedCount: number;
  lowConfidenceCount: number;
  failedCount: number;
  percentComplete: number;
  categoryCounts: Record<string, number>;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  updatedAt: string | null;
  // Phase 2: Organisation tracking
  organisedCount?: number;
  needsReviewCount?: number;
  organisedAt?: string | null;
}

interface OrganisationProgressResponse {
  dd_id: string;
  status: OrganisationStatus;
  total_documents: number;
  classified_count: number;
  low_confidence_count: number;
  failed_count: number;
  percent_complete: number;
  category_counts: Record<string, number>;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string | null;
}

/**
 * Poll organisation/classification progress for a DD project.
 * Polls every 2 seconds while status is 'classifying' or 'organising'.
 * Stops polling when status is 'completed' or 'failed'.
 *
 * @param ddId - The DD project ID to poll progress for
 * @param enabled - Whether polling should be enabled (default: true if ddId provided)
 */
export function useOrganisationProgress(
  ddId: string | undefined,
  enabled: boolean = true
) {
  const axios = useAxiosWithAuth();

  const fetchProgress = async (): Promise<OrganisationProgress> => {
    const { data } = await axios({
      url: `/dd-organisation-progress?dd_id=${ddId}`,
      method: "GET",
    });

    const response = data as OrganisationProgressResponse;

    // Transform snake_case to camelCase
    return {
      dd_id: response.dd_id,
      status: response.status,
      totalDocuments: response.total_documents,
      classifiedCount: response.classified_count,
      lowConfidenceCount: response.low_confidence_count,
      failedCount: response.failed_count,
      percentComplete: response.percent_complete,
      categoryCounts: response.category_counts || {},
      errorMessage: response.error_message,
      startedAt: response.started_at,
      completedAt: response.completed_at,
      updatedAt: response.updated_at,
    };
  };

  return useQuery({
    queryKey: ["organisation-progress", ddId],
    queryFn: fetchProgress,
    enabled: !!ddId && enabled,
    // Poll every 2 seconds while classifying or organising
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling when completed or failed
      if (status === "completed" || status === "failed") {
        return false;
      }
      // Poll every 2 seconds during active classification
      return 2000;
    },
    // Keep previous data while fetching to prevent UI flicker
    placeholderData: (previousData) => previousData,
    // Retry on failure
    retry: 3,
    retryDelay: 1000,
  });
}

/**
 * Hook to trigger document classification for a DD project.
 * Called when organisation status is 'pending'.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useClassifyDocuments() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ddId, reset = false }: { ddId: string; reset?: boolean }) => {
      const { data } = await axios({
        url: "/dd-classify-documents",
        method: "POST",
        data: { dd_id: ddId, reset },
      });
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate the organisation progress query to refresh
      queryClient.invalidateQueries({
        queryKey: ["organisation-progress", variables.ddId],
      });
      // Also invalidate the DD query to refresh document data
      queryClient.invalidateQueries({ queryKey: ["dd", variables.ddId] });
    },
  });
}

/**
 * Hook to trigger folder organisation for a DD project.
 * Creates blueprint folders and moves documents based on AI classification.
 * Called when organisation status is 'classified'.
 */
export function useOrganiseFolders() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ddId,
      transactionType,
    }: {
      ddId: string;
      transactionType?: string;
    }) => {
      const { data } = await axios({
        url: "/dd-organise-folders",
        method: "POST",
        data: { dd_id: ddId, transaction_type: transactionType },
      });
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({
        queryKey: ["organisation-progress", variables.ddId],
      });
      queryClient.invalidateQueries({ queryKey: ["dd", variables.ddId] });
    },
  });
}

/**
 * Hook to manually assign a document to a different folder.
 * Used after folders have been created (organised phase).
 */
export function useDocumentAssign() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ddId,
      documentId,
      targetFolderId,
      reason,
    }: {
      ddId: string;
      documentId: string;
      targetFolderId: string;
      reason?: string;
    }) => {
      const { data } = await axios({
        url: "/dd-document-assign",
        method: "POST",
        data: {
          dd_id: ddId,
          document_id: documentId,
          target_folder_id: targetFolderId,
          reason,
        },
      });
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["dd", variables.ddId] });
    },
  });
}

/**
 * Hook to reassign a document's category during the classification review phase.
 * Used before folders are created (classified phase) to update ai_category.
 */
export function useDocumentReassign() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ddId,
      documentId,
      targetCategory,
      reason,
    }: {
      ddId: string;
      documentId: string;
      targetCategory: string;
      reason?: string;
    }) => {
      const { data } = await axios({
        url: "/dd-document-reassign",
        method: "POST",
        data: {
          dd_id: ddId,
          document_id: documentId,
          target_category: targetCategory,
          reason,
        },
      });
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["dd", variables.ddId] });
      queryClient.invalidateQueries({
        queryKey: ["organisation-progress", variables.ddId],
      });
      queryClient.invalidateQueries({ queryKey: [`get-dd-${variables.ddId}`] });
    },
  });
}

/**
 * Hook to cancel document classification/organisation for a DD project.
 * Stops the current classifying or organising process.
 */
export function useCancelOrganisation() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ddId: string) => {
      const { data } = await axios({
        url: `/dd-process-cancel?dd_id=${ddId}`,
        method: "POST",
      });
      return data;
    },
    onSuccess: (data, ddId) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({
        queryKey: ["organisation-progress", ddId],
      });
      queryClient.invalidateQueries({ queryKey: ["dd", ddId] });
    },
  });
}

export type { OrganisationProgressResponse };
