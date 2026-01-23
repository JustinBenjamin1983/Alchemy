import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { reactQueryDefaults } from "./reactQuerySetup";
import { SynthesisData } from "./useAnalysisRuns";

// ============================================
// Types for Report Versions
// ============================================

export interface ReportVersionSummary {
  version_id: string;
  version: number;
  is_current: boolean;
  refinement_prompt?: string;
  change_summary?: string;
  created_at?: string;
  created_by?: string;
}

export interface VersionChange {
  section: string;
  change_type: "modify" | "add" | "remove";
  old_text?: string;
  new_text?: string;
  reasoning?: string;
}

export interface ReportVersion extends ReportVersionSummary {
  content: SynthesisData;
  changes?: VersionChange[];
}

export interface VersionListResponse {
  run_id: string;
  total_versions: number;
  versions: ReportVersionSummary[];
}

export interface VersionDiff {
  section: string;
  change_type: "modified" | "added" | "removed";
  diff?: string;
  item?: unknown;
  old_item?: unknown;
  new_item?: unknown;
}

export interface VersionCompareResponse {
  version1: number;
  version2: number;
  total_changes: number;
  diffs: VersionDiff[];
}

export interface RefinementProposal {
  proposal_id: string;
  run_id: string;
  section: string;
  change_type: "modify" | "add" | "remove";
  current_text?: string;
  proposed_text: string;
  reasoning: string;
  affected_findings?: string[];
  user_prompt: string;
  proposed_at: string;
}

export interface ProposeResponse {
  proposal: RefinementProposal;
  current_version: number;
}

export interface MergeResponse {
  version_id?: string;
  version?: number;
  is_current?: boolean;
  created_at?: string;
  change_summary?: string;
  status: "merged" | "discarded";
  message: string;
}

// ============================================
// Hooks
// ============================================

/**
 * Hook to list all report versions for a run
 */
export function useReportVersions(runId: string | undefined | null, enabled = true) {
  const axios = useAxiosWithAuth();

  return useQuery<VersionListResponse>({
    queryKey: ["report-versions", runId],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-report-versions?run_id=${runId}`,
        method: "GET",
      });
      return data;
    },
    enabled: !!runId && enabled,
    ...reactQueryDefaults,
  });
}

/**
 * Hook to get a specific version's full content
 */
export function useReportVersion(
  runId: string | undefined | null,
  version: number | undefined | null,
  enabled = true
) {
  const axios = useAxiosWithAuth();

  return useQuery<ReportVersion>({
    queryKey: ["report-version", runId, version],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-report-versions?run_id=${runId}&version=${version}`,
        method: "GET",
      });
      return data;
    },
    enabled: !!runId && version !== undefined && version !== null && enabled,
    ...reactQueryDefaults,
  });
}

/**
 * Hook to compare two versions
 */
export function useCompareVersions() {
  const axios = useAxiosWithAuth();

  return useMutation<VersionCompareResponse, Error, { runId: string; version1: number; version2: number }>({
    mutationFn: async ({ runId, version1, version2 }) => {
      const { data } = await axios({
        url: "/dd-refinement",
        method: "POST",
        data: {
          action: "compare",
          run_id: runId,
          version1,
          version2,
        },
      });
      return data;
    },
  });
}

/**
 * Hook to propose a refinement change via AI
 */
export function useProposeRefinement() {
  const axios = useAxiosWithAuth();

  return useMutation<ProposeResponse, Error, { runId: string; prompt: string }>({
    mutationFn: async ({ runId, prompt }) => {
      const { data } = await axios({
        url: "/dd-refinement",
        method: "POST",
        data: {
          action: "propose",
          run_id: runId,
          prompt,
        },
      });
      return data;
    },
  });
}

/**
 * Hook to merge or discard a proposed refinement
 */
export function useMergeRefinement() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<MergeResponse, Error, {
    runId: string;
    proposal: RefinementProposal;
    action: "merge" | "discard" | "edit";
    editedText?: string;
  }>({
    mutationFn: async ({ runId, proposal, action, editedText }) => {
      const { data } = await axios({
        url: "/dd-refinement",
        method: "POST",
        data: {
          action: "merge",
          run_id: runId,
          proposal,
          merge_action: action,
          edited_text: editedText,
        },
      });
      return data;
    },
    onSuccess: (_, variables) => {
      // Invalidate version list to refresh
      queryClient.invalidateQueries({ queryKey: ["report-versions", variables.runId] });
    },
  });
}

/**
 * Hook to download a report version as JSON
 */
export function useDownloadVersion() {
  const axios = useAxiosWithAuth();

  return useMutation<Blob, Error, { runId: string; version: number; filename?: string }>({
    mutationFn: async ({ runId, version, filename }) => {
      const { data } = await axios({
        url: `/dd-report-versions?run_id=${runId}&version=${version}`,
        method: "GET",
      });

      // Convert to JSON blob
      const jsonBlob = new Blob([JSON.stringify(data.content, null, 2)], {
        type: "application/json",
      });

      // Trigger download
      const url = URL.createObjectURL(jsonBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `dd-report-v${version}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      return jsonBlob;
    },
  });
}
