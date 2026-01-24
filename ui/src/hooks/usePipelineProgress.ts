// File: ui/src/hooks/usePipelineProgress.ts
// Hooks for DD pipeline progress tracking and stage management

import { useMutation, useQuery } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

// Pipeline stage type
export type PipelineStage =
  | "wizard"
  | "classification"
  | "checkpoint_a_missing_docs"
  | "readability_check"
  | "entity_mapping"
  | "checkpoint_b_entity_confirm"
  | "materiality_thresholds"
  | "pass_1_extract"
  | "pass_2_analyze"
  | "checkpoint_c_validation"
  | "pass_3_calculate"
  | "pass_4_cross_doc"
  | "pass_5_aggregate"
  | "pass_6_synthesize"
  | "pass_7_verify"
  | "store_display"
  | "refinement_loop"
  | "completed"
  | "failed";

// Pipeline phase type
export type PipelinePhase = "pre_processing" | "processing" | "post_processing";

// Stage metadata
export interface StageMetadata {
  id: PipelineStage;
  name: string;
  description: string;
  phase: PipelinePhase;
  order: number;
  is_checkpoint: boolean;
  requires_user_input: boolean;
  model: string | null;
  can_resume_from: boolean;
}

// Pipeline progress response
export interface PipelineProgressResponse {
  dd_id: string;
  checkpoint_id?: string;
  pipeline_stage: PipelineStage;
  current_stage_name: string;
  completed_stages: PipelineStage[];
  overall_progress: number;
  stage_progress: {
    classification: number;
    readability: number;
    entity_mapping: number;
    pass_1: number;
    pass_2: number;
    pass_3: number;
    pass_4: number;
    pass_5: number;
    pass_6: number;
    pass_7: number;
  };
  documents_processed: number;
  total_documents: number;
  findings_count: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    deal_blockers: number;
  };
  status: string;
  last_error: string | null;
  started_at: string | null;
  last_updated: string | null;
  paused_at: string | null;
  can_resume_from: PipelineStage[];
  checkpoints: PipelineStage[];
}

// Stage metadata response
export interface StageMetadataResponse {
  stages: StageMetadata[];
  phases: { id: PipelinePhase; name: string }[];
}

/**
 * Hook to fetch pipeline progress for a DD
 */
export function useGetPipelineProgress(ddId: string | null) {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["pipeline-progress", ddId],
    queryFn: async (): Promise<PipelineProgressResponse> => {
      const response = await axios.get(`/dd-pipeline-progress?dd_id=${ddId}`);
      return response.data;
    },
    enabled: !!ddId,
    refetchInterval: 5000, // Poll every 5 seconds during processing
  });
}

/**
 * Hook to fetch all stage metadata (for UI display)
 */
export function useGetStageMetadata() {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["pipeline-stage-metadata"],
    queryFn: async (): Promise<StageMetadataResponse> => {
      const response = await axios.get(`/dd-pipeline-progress?stages=metadata`);
      return response.data;
    },
    staleTime: Infinity, // Stage metadata never changes
  });
}

/**
 * Hook to resume from a specific stage
 */
export function useResumeFromStage() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({
      ddId,
      stage,
    }: {
      ddId: string;
      stage: PipelineStage;
    }) => {
      const response = await axios.post("/dd-pipeline-progress", {
        dd_id: ddId,
        action: "resume_from",
        stage,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["pipeline-progress", variables.ddId],
      });
    },
  });
}

/**
 * Hook to mark a stage as complete
 */
export function useMarkStageComplete() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({
      ddId,
      stage,
    }: {
      ddId: string;
      stage: PipelineStage;
    }) => {
      const response = await axios.post("/dd-pipeline-progress", {
        dd_id: ddId,
        action: "mark_complete",
        stage,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["pipeline-progress", variables.ddId],
      });
    },
  });
}

/**
 * Hook to pause pipeline processing
 */
export function usePausePipeline() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({ ddId }: { ddId: string }) => {
      const response = await axios.post("/dd-pipeline-progress", {
        dd_id: ddId,
        action: "pause",
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["pipeline-progress", variables.ddId],
      });
    },
  });
}

/**
 * Hook to update pipeline progress (for internal use)
 */
export function useUpdatePipelineProgress() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({
      ddId,
      updates,
    }: {
      ddId: string;
      updates: Partial<{
        pipeline_stage: PipelineStage;
        status: string;
        stage_progress: Partial<PipelineProgressResponse["stage_progress"]>;
        completed_stages: PipelineStage[];
        documents_processed: number;
        total_documents: number;
        last_error: string | null;
      }>;
    }) => {
      const response = await axios.put("/dd-pipeline-progress", {
        dd_id: ddId,
        ...updates,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["pipeline-progress", variables.ddId],
      });
    },
  });
}
