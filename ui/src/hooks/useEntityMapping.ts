import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface EntityMapEntry {
  entity_name: string;
  relationship_to_target: string;
  confidence: number;
  documents_appearing_in: string[];
  requires_human_confirmation: boolean;
}

interface EntityMappingSummary {
  total_unique_entities: number;
  entities_needing_confirmation: number;
  target_subsidiaries: number;
  counterparties: number;
}

interface EntityMappingResponse {
  dd_id: string;
  run_id?: string;
  status: string;
  total_documents_processed: number;
  entity_map: EntityMapEntry[];
  summary: EntityMappingSummary;
  checkpoint_recommended: boolean;
  checkpoint_reason?: string;
  stored_count: number;
  cost?: {
    total_cost: number;
    total_tokens: number;
  };
}

interface EntityMappingParams {
  ddId: string;
  runId?: string;
  maxDocs?: number;
}

export default function useEntityMapping() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ddId, runId, maxDocs }: EntityMappingParams): Promise<EntityMappingResponse> => {
      const response = await axios.post("/dd-entity-mapping", {
        dd_id: ddId,
        run_id: runId,
        max_docs: maxDocs,
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ["dd", variables.ddId] });
      queryClient.invalidateQueries({ queryKey: ["dd-progress", variables.ddId] });
    },
  });
}

export type { EntityMappingResponse, EntityMapEntry, EntityMappingSummary };
