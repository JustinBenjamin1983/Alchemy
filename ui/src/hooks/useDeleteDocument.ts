// hooks/useDeleteDocument.ts
/**
 * Hook to delete documents from a DD project.
 */
import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface DeleteDocumentParams {
  ddId: string;
  documentIds: string[];
}

interface DeleteDocumentResult {
  success: boolean;
  deleted_count: number;
  errors?: string[];
}

export function useDeleteDocument() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async ({ ddId, documentIds }: DeleteDocumentParams): Promise<DeleteDocumentResult> => {
      const response = await axios.post("/dd-delete-document", {
        dd_id: ddId,
        document_ids: documentIds,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate DD data to refresh document lists
      aishopQueryClient.invalidateQueries({ queryKey: ["dd", variables.ddId] });
      aishopQueryClient.invalidateQueries({ queryKey: ["dd-organisation-progress", variables.ddId] });
      aishopQueryClient.invalidateQueries({ queryKey: ["blueprint-requirements"] });
    },
  });
}
