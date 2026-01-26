import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface EntityMapEntry {
  id?: string;
  entity_name: string;
  registration_number?: string;
  relationship_to_target: string;
  relationship_detail?: string;
  ownership_percentage?: number;
  confidence: number;
  documents_appearing_in: string[];
  evidence?: string;
  requires_human_confirmation?: boolean;
  human_confirmed?: boolean;
  human_confirmation_value?: string;
  has_conflict?: boolean;
  conflict_details?: string;
}

interface EntityMappingSummary {
  total_unique_entities: number;
  entities_needing_confirmation: number;
  entities_confirmed?: number;
  high_confidence_entities?: number;
  target_subsidiaries: number;
  counterparties: number;
  unknown_relationships?: number;
}

interface TargetEntityInfo {
  name: string;
  registration_number?: string;
  transaction_type?: string;
  deal_structure?: string;
}

interface ClientEntityInfo {
  name: string;
  role?: string;
  deal_structure?: string;
}

interface ShareholderInfo {
  name: string;
  ownership_percentage?: number;
}

interface EntityMappingResponse {
  dd_id: string;
  run_id?: string;
  status: string;
  total_documents_processed?: number;
  entity_map: EntityMapEntry[];
  summary: EntityMappingSummary;
  checkpoint_recommended?: boolean;
  checkpoint_reason?: string;
  stored_count?: number;
  cost?: {
    total_cost: number;
    total_tokens: number;
  };
  // Wizard data for organogram display
  target_entity?: TargetEntityInfo;
  client_entity?: ClientEntityInfo;
  shareholders?: ShareholderInfo[];
}

interface EntityMappingParams {
  ddId: string;
  runId?: string;
  maxDocs?: number;
}

/**
 * Hook to run entity mapping (POST)
 */
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
      queryClient.invalidateQueries({ queryKey: ["entity-map", variables.ddId] });
    },
  });
}

/**
 * Hook to fetch stored entity map (GET)
 */
export function useGetEntityMap(ddId: string | undefined, enabled: boolean = true) {
  const axios = useAxiosWithAuth();

  return useQuery<EntityMappingResponse>({
    queryKey: ["entity-map", ddId],
    queryFn: async () => {
      const response = await axios.get("/dd-entity-mapping", {
        params: { dd_id: ddId },
      });
      return response.data;
    },
    enabled: !!ddId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

interface ModifyEntityMapParams {
  ddId: string;
  instruction: string;
  currentEntityMap?: EntityMapEntry[];
}

interface ModifyEntityMapResponse {
  success: boolean;
  entity_map: EntityMapEntry[];
  changes_made: Array<{
    entity_name: string;
    change_type: string;
    description: string;
  }>;
  explanation: string;
  error?: string;
}

/**
 * Hook to modify entity map using AI (PUT)
 */
export function useModifyEntityMap() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ddId, instruction, currentEntityMap }: ModifyEntityMapParams): Promise<ModifyEntityMapResponse> => {
      const response = await axios.put("/dd-entity-mapping", {
        dd_id: ddId,
        instruction,
        current_entity_map: currentEntityMap,
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Don't invalidate immediately - let the user decide to confirm
      console.log("[useModifyEntityMap] AI modification complete:", data.explanation);
    },
  });
}

interface ConfirmEntityMapParams {
  ddId: string;
  entityMap: EntityMapEntry[];
}

interface ConfirmEntityMapResponse {
  success: boolean;
  confirmed_count: number;
  message: string;
  errors?: string[];
}

/**
 * Hook to confirm and save the final entity map (PATCH)
 */
export function useConfirmEntityMap() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ddId, entityMap }: ConfirmEntityMapParams): Promise<ConfirmEntityMapResponse> => {
      const response = await axios.patch("/dd-entity-mapping", {
        dd_id: ddId,
        entity_map: entityMap,
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Invalidate entity map query to refetch confirmed state
      queryClient.invalidateQueries({ queryKey: ["entity-map", variables.ddId] });
      console.log("[useConfirmEntityMap] Entity map confirmed:", data.message);
    },
  });
}

export type { EntityMappingResponse, EntityMapEntry, EntityMappingSummary, ModifyEntityMapResponse, ConfirmEntityMapResponse };
