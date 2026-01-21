import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { reactQueryDefaults } from "./reactQuerySetup";

// Synthesis data from Pass 4
export interface SynthesisData {
  executive_summary: string;
  deal_assessment: {
    can_proceed?: boolean;
    blocking_issues?: string[];
    key_risks?: string[];
    overall_risk_rating?: "high" | "medium" | "low";
  };
  financial_exposures: {
    items?: Array<{
      source: string;
      type: string;
      amount: number;
      calculation: string;
      triggered_by: string;
      risk_level: string;
    }>;
    total?: number;
    currency?: string;
    calculation_notes?: string[];
  };
  deal_blockers: Array<{
    issue?: string;
    description?: string;
    source?: string;
    why_blocking?: string;
    resolution_path?: string;
    resolution_timeline?: string;
    owner?: string;
    severity?: string;
    deal_impact?: string;
  }>;
  conditions_precedent: Array<{
    cp_number?: number;
    description?: string;
    category?: string;
    source?: string;
    responsible_party?: string;
    target_date?: string;
    status?: string;
    is_deal_blocker?: boolean;
  }>;
  // Warranties register - recommended warranties for client protection
  warranties_register?: Array<{
    warranty_number?: number;
    category?: string;
    description?: string;
    detailed_wording?: string;
    from_party?: string;
    to_party?: string;
    source_finding?: string;
    typical_cap?: string;
    survival_period?: string;
    priority?: "critical" | "high" | "medium";
    is_fundamental?: boolean;
    disclosure_required?: string;
  }>;
  // Indemnities register - recommended indemnities based on DD findings
  indemnities_register?: Array<{
    indemnity_number?: number;
    category?: string;
    description?: string;
    detailed_wording?: string;
    from_party?: string;
    to_party?: string;
    trigger_event?: string;
    source_finding?: string;
    quantified_exposure?: string;
    typical_cap?: string;
    survival_period?: string;
    priority?: "critical" | "high" | "medium";
    escrow_recommendation?: string;
  }>;
  recommendations: string[];
}

export interface AnalysisRun {
  run_id: string;
  dd_id: string;
  run_number: number;
  name: string;
  status: "pending" | "processing" | "completed" | "failed";
  selected_documents: { id: string; name: string }[];
  total_documents: number;
  documents_processed: number;
  findings_total: number;
  findings_critical: number;
  findings_high: number;
  findings_medium: number;
  findings_low: number;
  estimated_cost_usd: number;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  last_error: string | null;
  // Token/cost tracking
  total_tokens?: number;
  total_cost?: number;
  // Synthesis data from Pass 4
  synthesis_data?: SynthesisData | null;
}

interface RunsListResponse {
  runs: AnalysisRun[];
}

interface CreateRunResponse {
  run_id: string;
  dd_id: string;
  run_number: number;
  name: string;
  status: string;
  selected_document_ids: string[];
  total_documents: number;
  created_at: string;
}

// Hook to list all runs for a DD
export function useAnalysisRunsList(ddId: string | undefined, enabled = true) {
  const axios = useAxiosWithAuth();

  return useQuery<RunsListResponse>({
    queryKey: ["analysis-runs", ddId],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-analysis-run-list?dd_id=${ddId}`,
        method: "GET",
      });
      return data;
    },
    enabled: !!ddId && enabled,
    refetchInterval: 10000, // Refresh every 10 seconds to catch status changes
    ...reactQueryDefaults,
  });
}

// Hook to create a new run
export function useCreateAnalysisRun() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ddId,
      selectedDocumentIds,
    }: {
      ddId: string;
      selectedDocumentIds: string[];
    }): Promise<CreateRunResponse> => {
      const { data } = await axios({
        url: "/dd-analysis-run-create",
        method: "POST",
        data: {
          dd_id: ddId,
          selected_document_ids: selectedDocumentIds,
        },
      });
      return data;
    },
    onSuccess: (data) => {
      // Invalidate the runs list to refresh
      queryClient.invalidateQueries({ queryKey: ["analysis-runs", data.dd_id] });
    },
  });
}

// Hook to update run name
export function useUpdateAnalysisRun() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      runId,
      name,
    }: {
      runId: string;
      name: string;
    }) => {
      const { data } = await axios({
        url: "/dd-analysis-run-update",
        method: "POST",
        data: {
          run_id: runId,
          name: name,
        },
      });
      return data;
    },
    onSuccess: () => {
      // Invalidate all runs queries to refresh
      queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}

// Hook to delete a run
export function useDeleteAnalysisRun() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: string) => {
      const { data } = await axios({
        url: "/dd-analysis-run-delete",
        method: "POST",
        data: {
          run_id: runId,
        },
      });
      return data;
    },
    onSuccess: () => {
      // Invalidate all runs queries to refresh
      queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}

// Hook to start processing for a run
export function useStartRunProcessing() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: string) => {
      const { data } = await axios({
        url: `/dd-process-enhanced-start?run_id=${runId}`,
        method: "POST",
      });
      return data;
    },
    onSuccess: () => {
      // Invalidate runs to refresh status
      queryClient.invalidateQueries({ queryKey: ["analysis-runs"] });
    },
  });
}
