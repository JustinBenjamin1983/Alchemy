// hooks/useGetEvaluations.ts
import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface EvaluationSummary {
  id: string;
  rubric_id: string;
  rubric_name: string | null;
  run_id: string;
  run_name: string | null;
  dd_id: string | null;
  dd_name: string | null;
  status: "pending" | "evaluating" | "completed" | "failed";
  total_score: number | null;
  percentage: number | null;
  performance_band: "EXCELLENT" | "GOOD" | "ADEQUATE" | "BELOW_EXPECTATIONS" | "FAILURE" | null;
  evaluation_model: string;
  created_at: string | null;
  completed_at: string | null;
}

interface UseGetEvaluationsParams {
  dd_id?: string;
  rubric_id?: string;
  run_id?: string;
  status?: string;
}

export function useGetEvaluations(params: UseGetEvaluationsParams = {}) {
  const axios = useAxiosWithAuth();

  const getEvaluations = async (): Promise<{ evaluations: EvaluationSummary[] }> => {
    const queryParams = new URLSearchParams();
    if (params.dd_id) queryParams.append("dd_id", params.dd_id);
    if (params.rubric_id) queryParams.append("rubric_id", params.rubric_id);
    if (params.run_id) queryParams.append("run_id", params.run_id);
    if (params.status) queryParams.append("status", params.status);

    const queryString = queryParams.toString();
    const url = queryString ? `/dd-evaluation-list?${queryString}` : "/dd-evaluation-list";

    const { data } = await axios({
      url,
      method: "GET",
    });
    return data;
  };

  return useQuery({
    queryKey: ["evaluations", params],
    queryFn: getEvaluations,
    ...reactQueryDefaults,
  });
}
