import { useMutation, useQueryClient } from "@tanstack/react-query";
import { DEV_MODE } from "@/authConfig";

interface ProcessResult {
  filename: string;
  status: "processed" | "error";
  risks_found?: number;
  summary?: string;
  message?: string;
}

interface ProcessAllResponse {
  message: string;
  processed: number;
  total_documents: number;
  risks_found: number;
  results: ProcessResult[];
}

export function useProcessAllDocuments(ddId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<ProcessAllResponse> => {
      console.log("[useProcessAllDocuments] Starting mutation, ddId:", ddId, "DEV_MODE:", DEV_MODE);

      if (!ddId) {
        console.error("[useProcessAllDocuments] Error: DD ID is required");
        throw new Error("DD ID is required");
      }

      if (!DEV_MODE) {
        console.error("[useProcessAllDocuments] Error: Not in dev mode");
        throw new Error("This feature is only available in dev mode");
      }

      console.log("[useProcessAllDocuments] Calling API...");
      const response = await fetch(`/api/dd-process-all-dev?dd_id=${ddId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      console.log("[useProcessAllDocuments] Response status:", response.status);

      if (!response.ok) {
        const error = await response.json();
        console.error("[useProcessAllDocuments] API error:", error);
        throw new Error(error.error || "Failed to process documents");
      }

      const result = await response.json();
      console.log("[useProcessAllDocuments] Success:", result);
      return result;
    },
    onSuccess: (data) => {
      console.log("[useProcessAllDocuments] onSuccess - invalidating queries", data);
      // Invalidate related queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ["dd", ddId] });
      queryClient.invalidateQueries({ queryKey: ["ddRiskResults", ddId] });
      queryClient.invalidateQueries({ queryKey: ["ddRisks", ddId] });
      queryClient.invalidateQueries({ queryKey: ["ddProgress", ddId] });
    },
    onError: (error) => {
      console.error("[useProcessAllDocuments] onError:", error);
    },
  });
}
