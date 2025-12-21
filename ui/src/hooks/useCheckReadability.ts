import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface ReadabilityResult {
  doc_id: string;
  filename: string;
  file_type: string;
  status: "pending" | "checking" | "ready" | "failed";
  error: string | null;
}

interface ReadabilityResponse {
  dd_id: string;
  total_documents: number;
  results: ReadabilityResult[];
  summary: {
    ready: number;
    failed: number;
    checking: number;
  };
}

interface CheckReadabilityParams {
  dd_id: string;
  doc_ids?: string[];
}

export function useCheckReadability() {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  return useMutation<ReadabilityResponse, Error, CheckReadabilityParams>({
    mutationFn: async ({ dd_id, doc_ids }: CheckReadabilityParams) => {
      const { data } = await axios({
        url: "/dd-check-readability",
        method: "POST",
        data: { dd_id, doc_ids },
      });
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate the DD query to refresh document statuses
      queryClient.invalidateQueries({ queryKey: ["dd", variables.dd_id] });
    },
  });
}

export type { ReadabilityResult, ReadabilityResponse };
