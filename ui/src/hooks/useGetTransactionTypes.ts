import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface BlueprintInfo {
  name: string;
  description: string;
  risk_categories: number;
  total_questions: number;
}

export interface TransactionType {
  code: string;
  name: string;
  document_count: number;
  folder_count: number;
  priority_counts: {
    critical: number;
    required: number;
    recommended: number;
    optional: number;
  };
  blueprint: BlueprintInfo | null;
}

export function useGetTransactionTypes() {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["transaction-types"],
    queryFn: async () => {
      const response = await axios.get("/dd-document-registry", {
        params: { action: "transaction_types" },
      });

      return response.data.data as TransactionType[];
    },
  });
}
