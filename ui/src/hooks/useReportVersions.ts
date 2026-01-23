import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { reactQueryDefaults } from "./reactQuerySetup";

// ============================================
// Types for Report Versions
// ============================================

export interface ReportChange {
  section: string;
  change_type: 'add' | 'remove' | 'modify';
  old_text?: string;
  new_text?: string;
  reasoning?: string;
}

export interface ReportVersionSummary {
  version_id: string;
  version: number;
  is_current: boolean;
  refinement_prompt?: string;
  change_summary?: string;
  created_at?: string;
  created_by?: string;
}

export interface ReportVersionFull extends ReportVersionSummary {
  content: Record<string, unknown>;
  changes?: ReportChange[];
}

export interface VersionListResponse {
  run_id: string;
  total_versions: number;
  versions: ReportVersionSummary[];
}

export interface RefinementProposal {
  proposal_id: string;
  run_id: string;
  user_prompt: string;
  proposed_at: string;
  section: string;
  change_type: 'add' | 'remove' | 'modify';
  current_text?: string;
  proposed_text: string;
  reasoning: string;
  affected_findings?: string[];
}

export interface ProposeResponse {
  proposal: RefinementProposal;
  current_version: number;
}

export interface MergeResponse {
  version_id?: string;
  version?: number;
  is_current?: boolean;
  status: 'merged' | 'discarded';
  message: string;
  change_summary?: string;
}

export interface VersionDiff {
  section: string;
  change_type: 'added' | 'removed' | 'modified';
  diff?: string;
  item?: Record<string, unknown>;
  old_item?: Record<string, unknown>;
  new_item?: Record<string, unknown>;
}

export interface CompareResponse {
  version1: number;
  version2: number;
  total_changes: number;
  diffs: VersionDiff[];
}

// ============================================
// Hooks
// ============================================

/**
 * Hook to list all report versions for a run
 */
export function useReportVersions(runId: string | undefined, enabled = true) {
  const axios = useAxiosWithAuth();

  return useQuery<VersionListResponse>({
    queryKey: ["report-versions", runId],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-report-versions/${runId}`,
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
export function useReportVersionContent(
  runId: string | undefined,
  version: number | undefined,
  enabled = true
) {
  const axios = useAxiosWithAuth();

  return useQuery<ReportVersionFull>({
    queryKey: ["report-version-content", runId, version],
    queryFn: async () => {
      const { data } = await axios({
        url: `/dd-report-versions/${runId}/${version}`,
        method: "GET",
      });
      return data;
    },
    enabled: !!runId && version !== undefined && enabled,
    ...reactQueryDefaults,
  });
}

/**
 * Hook to get the current (latest) version content
 */
export function useCurrentReportVersion(runId: string | undefined, enabled = true) {
  const axios = useAxiosWithAuth();

  return useQuery<ReportVersionFull>({
    queryKey: ["report-version-current", runId],
    queryFn: async () => {
      // Without a version param, backend returns current version
      const { data } = await axios({
        url: `/dd-report-versions/${runId}`,
        method: "GET",
      });
      // If we get a list, find the current one
      if (data.versions) {
        const current = data.versions.find((v: ReportVersionSummary) => v.is_current);
        if (current) {
          // Fetch full content
          const { data: fullData } = await axios({
            url: `/dd-report-versions/${runId}/${current.version}`,
            method: "GET",
          });
          return fullData;
        }
      }
      return data;
    },
    enabled: !!runId && enabled,
    ...reactQueryDefaults,
  });
}

/**
 * Hook to propose a refinement to the report
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
          prompt: prompt,
        },
      });
      return data;
    },
  });
}

/**
 * Hook to merge/apply a proposed refinement
 */
export function useMergeRefinement() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<MergeResponse, Error, {
    runId: string;
    proposal: RefinementProposal;
    action: 'merge' | 'discard' | 'edit';
    editedText?: string;
  }>({
    mutationFn: async ({ runId, proposal, action, editedText }) => {
      const { data } = await axios({
        url: "/dd-refinement",
        method: "POST",
        data: {
          action: "merge",
          run_id: runId,
          proposal: proposal,
          merge_action: action,
          edited_text: editedText,
        },
      });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["report-versions", variables.runId] });
      queryClient.invalidateQueries({ queryKey: ["report-version-current", variables.runId] });
    },
  });
}

/**
 * Hook to compare two versions
 */
export function useCompareVersions() {
  const axios = useAxiosWithAuth();

  return useMutation<CompareResponse, Error, {
    runId: string;
    version1: number;
    version2: number;
  }>({
    mutationFn: async ({ runId, version1, version2 }) => {
      const { data } = await axios({
        url: "/dd-refinement",
        method: "POST",
        data: {
          action: "compare",
          run_id: runId,
          version1: version1,
          version2: version2,
        },
      });
      return data;
    },
  });
}

/**
 * Alias for useReportVersionContent for backward compatibility
 */
export const useReportVersion = useReportVersionContent;

/**
 * Hook to download a specific version as JSON
 */
export function useDownloadVersion() {
  const axios = useAxiosWithAuth();

  return useMutation<void, Error, {
    runId: string;
    version: number;
    filename?: string;
  }>({
    mutationFn: async ({ runId, version, filename }) => {
      const { data } = await axios({
        url: `/dd-report-versions/${runId}/${version}`,
        method: "GET",
      });

      // Create and trigger download
      const content = data.content || data;
      const blob = new Blob([JSON.stringify(content, null, 2)], {
        type: "application/json",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || `dd-report-v${version}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}
