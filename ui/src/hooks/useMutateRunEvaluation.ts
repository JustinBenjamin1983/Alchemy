// hooks/useMutateRunEvaluation.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { EvaluationScores } from "./useGetEvaluation";

interface RunEvaluationParams {
  rubric_id: string;
  run_id: string;
}

interface RunEvaluationResponse {
  id: string;
  status: "completed" | "failed";
  scores?: EvaluationScores;
  total_score?: number;
  max_score?: number;
  percentage?: number;
  performance_band?: string;
  error?: string;
}

export const useMutateRunEvaluation = () => {
  const axios = useAxiosWithAuth();
  const queryClient = useQueryClient();

  const runEvaluation = async (params: RunEvaluationParams): Promise<RunEvaluationResponse> => {
    const { data } = await axios({
      url: "/dd-evaluation-run",
      method: "POST",
      data: params,
    });
    return data;
  };

  return useMutation({
    mutationFn: runEvaluation,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["evaluations"] });
      if (data.status === "completed") {
        toast.success(
          `Evaluation complete: ${data.total_score}/${data.max_score} (${data.percentage}%) - ${data.performance_band}`
        );
      } else {
        toast.error(`Evaluation failed: ${data.error}`);
      }
    },
    onError: (error: any) => {
      console.error("Run evaluation error:", error);
      const message = error.response?.data?.error || error.message || "Failed to run evaluation";
      toast.error(message);
    },
  });
};
