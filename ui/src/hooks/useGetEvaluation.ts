// hooks/useGetEvaluation.ts
import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface ScoringItem {
  rubric_item: string;
  matched_finding?: string;
  score: number;
  max: number;
  notes?: string;
}

export interface CategoryScore {
  found?: ScoringItem[];
  missed?: ScoringItem[];
  score: number;
  max: number;
}

export interface IntelligentQuestionsScore {
  assessment: string;
  examples?: string[];
  score: number;
  max: number;
}

export interface OverallQualityScore {
  assessment: string;
  strengths?: string[];
  weaknesses?: string[];
  score: number;
  max: number;
}

export interface MissingDocumentsScore {
  flagged?: { category: string; score: number; max: number }[];
  not_flagged?: { category: string; score: number; max: number }[];
  score: number;
  max: number;
}

export interface EvaluationScores {
  critical_red_flags?: CategoryScore;
  amber_flags?: CategoryScore;
  cross_document_connections?: CategoryScore;
  intelligent_questions?: IntelligentQuestionsScore;
  missing_documents?: MissingDocumentsScore;
  overall_quality?: OverallQualityScore;
  summary?: {
    total_score: number;
    max_score: number;
    key_gaps?: string[];
    key_strengths?: string[];
  };
}

export interface Evaluation {
  id: string;
  rubric_id: string;
  rubric_name: string | null;
  rubric_total_points: number | null;
  run_id: string;
  run_name: string | null;
  dd_id: string | null;
  dd_name: string | null;
  status: "pending" | "evaluating" | "completed" | "failed";
  scores: EvaluationScores | null;
  total_score: number | null;
  percentage: number | null;
  performance_band: "EXCELLENT" | "GOOD" | "ADEQUATE" | "BELOW_EXPECTATIONS" | "FAILURE" | null;
  evaluation_model: string;
  raw_response: string | null;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export function useGetEvaluation(evaluationId: string | null) {
  const axios = useAxiosWithAuth();

  const getEvaluation = async (): Promise<Evaluation> => {
    const { data } = await axios({
      url: `/dd-evaluation-get?evaluation_id=${evaluationId}`,
      method: "GET",
    });
    return data;
  };

  return useQuery({
    queryKey: ["evaluation", evaluationId],
    queryFn: getEvaluation,
    enabled: !!evaluationId,
    ...reactQueryDefaults,
  });
}
