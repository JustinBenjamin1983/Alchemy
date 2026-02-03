// hooks/useGetEvalRubrics.ts
import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface EvalRubricSummary {
  id: string;
  name: string;
  description: string | null;
  total_points: number;
  dd_id: string | null;
  created_at: string | null;
  created_by: string | null;
  summary: {
    critical_red_flags_count: number;
    amber_flags_count: number;
    cross_document_connections_count: number;
    missing_documents_count: number;
  };
}

export function useGetEvalRubrics() {
  const axios = useAxiosWithAuth();

  const getEvalRubrics = async (): Promise<{ rubrics: EvalRubricSummary[] }> => {
    const { data } = await axios({
      url: "/dd-eval-rubric-list",
      method: "GET",
    });
    return data;
  };

  return useQuery({
    queryKey: ["eval-rubrics"],
    queryFn: getEvalRubrics,
    ...reactQueryDefaults,
  });
}
