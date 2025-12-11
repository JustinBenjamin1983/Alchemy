// hooks/useGetDDQuestions.ts
import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface ReferencedDoc {
  doc_id: string;
  filename: string;
  page_number: string;
  folder_path: string;
}

interface DDQuestion {
  id: string;
  question: string;
  answer: string | null;
  asked_by: string;
  folder_id: string | null;
  document_id: string | null;
  folder_name: string | null;
  document_name: string | null;
  created_at: string;
  referenced_documents: ReferencedDoc[];
}

export function useGetDDQuestions(ddId?: string) {
  const axios = useAxiosWithAuth();

  const fetchDDQuestions = async (): Promise<DDQuestion[]> => {
    const { data } = await axios({
      url: `/dd-questions?dd_id=${ddId}`,
      method: "GET",
    });
    return data;
  };

  return useQuery({
    queryKey: ["dd-questions", ddId],
    queryFn: fetchDDQuestions,
    enabled: !!ddId,
    refetchInterval: 30_000, // Refetch every 30 seconds to get new questions
  });
}
