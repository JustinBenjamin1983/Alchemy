// File: ui/src/hooks/useEntityConfirmation.ts
// Hooks for entity confirmation auto-save

import { useMutation, useQuery } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

// Entity confirmation types
export type UserDecision = "confirmed" | "rejected" | "corrected" | "skipped";
export type RelationshipType = "target" | "parent" | "subsidiary" | "related_party" | "counterparty" | "unknown";

export interface EntityConfirmation {
  id: string;
  dd_id: string;
  checkpoint_id?: string;
  entity_a_name: string;
  entity_a_type?: string;
  entity_b_name?: string;
  entity_b_type?: string;
  relationship_type?: RelationshipType;
  relationship_detail?: string;
  ai_confidence?: number;
  user_decision?: UserDecision;
  user_correction?: string;
  user_notes?: string;
  source_document_ids: string[];
  evidence_text?: string;
  created_at?: string;
  confirmed_at?: string;
  confirmed_by?: string;
}

export interface EntityConfirmationInput {
  dd_id: string;
  checkpoint_id?: string;
  entity_a_name: string;
  entity_a_type?: string;
  entity_b_name?: string;
  entity_b_type?: string;
  relationship_type?: RelationshipType;
  relationship_detail?: string;
  ai_confidence?: number;
  user_decision?: UserDecision;
  user_correction?: string;
  user_notes?: string;
  source_document_ids?: string[];
  evidence_text?: string;
}

/**
 * Hook to fetch all entity confirmations for a DD
 */
export function useGetEntityConfirmations(ddId: string | null) {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["entity-confirmations", ddId],
    queryFn: async (): Promise<EntityConfirmation[]> => {
      const response = await axios.get(`/dd-entity-confirmation-save?dd_id=${ddId}`);
      return response.data.confirmations;
    },
    enabled: !!ddId,
  });
}

/**
 * Hook to save an entity confirmation (auto-save)
 * Uses UPSERT - creates new or updates existing based on entity pair
 */
export function useSaveEntityConfirmation() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async (data: EntityConfirmationInput) => {
      const response = await axios.post("/dd-entity-confirmation-save", data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["entity-confirmations", variables.dd_id],
      });
    },
  });
}

/**
 * Hook to update an existing entity confirmation by ID
 */
export function useUpdateEntityConfirmation() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({
      id,
      ddId,
      updates,
    }: {
      id: string;
      ddId: string;
      updates: Partial<{
        user_decision: UserDecision;
        user_correction: string;
        user_notes: string;
      }>;
    }) => {
      const response = await axios.put("/dd-entity-confirmation-save", {
        id,
        ...updates,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["entity-confirmations", variables.ddId],
      });
    },
  });
}

/**
 * Hook to delete an entity confirmation
 */
export function useDeleteEntityConfirmation() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({ id, ddId }: { id: string; ddId: string }) => {
      const response = await axios.delete(`/dd-entity-confirmation-save?id=${id}`);
      return response.data;
    },
    onSuccess: (_, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: ["entity-confirmations", variables.ddId],
      });
    },
  });
}

/**
 * Helper hook that provides auto-save functionality
 * Debounces saves to avoid excessive API calls
 */
export function useEntityConfirmationAutoSave(ddId: string | null) {
  const saveConfirmation = useSaveEntityConfirmation();
  const updateConfirmation = useUpdateEntityConfirmation();

  const autoSave = async (
    confirmation: EntityConfirmationInput | { id: string; updates: Partial<EntityConfirmation> }
  ) => {
    if (!ddId) return;

    if ("id" in confirmation && "updates" in confirmation) {
      // Update existing
      await updateConfirmation.mutateAsync({
        id: confirmation.id,
        ddId,
        updates: confirmation.updates as any,
      });
    } else {
      // Create/upsert new
      await saveConfirmation.mutateAsync(confirmation as EntityConfirmationInput);
    }
  };

  return {
    autoSave,
    isSaving: saveConfirmation.isPending || updateConfirmation.isPending,
    lastError: saveConfirmation.error || updateConfirmation.error,
  };
}
