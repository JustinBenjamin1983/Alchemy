// hooks/useGetEvalRubric.ts
import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface RubricItem {
  name: string;
  description?: string;
  points?: number;
  expected_finding?: string;
  keywords?: string[];
}

export interface RubricData {
  critical_red_flags?: RubricItem[];
  amber_flags?: RubricItem[];
  cross_document_connections?: RubricItem[];
  intelligent_questions?: {
    criteria?: string;
    points?: number;
  };
  missing_documents?: RubricItem[];
  overall_quality?: {
    criteria?: string;
    points?: number;
  };
}

export interface EvalRubric {
  id: string;
  name: string;
  description: string | null;
  rubric_data: RubricData;
  total_points: number;
  dd_id: string | null;
  dd_name: string | null;
  created_at: string | null;
  created_by: string | null;
}

export function useGetEvalRubric(rubricId: string | null) {
  const axios = useAxiosWithAuth();

  const getEvalRubric = async (): Promise<EvalRubric> => {
    const { data } = await axios({
      url: `/dd-eval-rubric-get?rubric_id=${rubricId}`,
      method: "GET",
    });
    return data;
  };

  return useQuery({
    queryKey: ["eval-rubric", rubricId],
    queryFn: getEvalRubric,
    enabled: !!rubricId,
    ...reactQueryDefaults,
  });
}
