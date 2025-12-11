import { useMutation, useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface MissingDocument {
  name: string;
  category: string;
  folder: string;
  priority: "critical" | "required" | "recommended" | "optional";
  description: string;
  request_template: string;
}

export interface GetMissingDocumentsRequest {
  transaction_type: string;
  uploaded_docs: string[];
  priority_threshold?: "critical" | "required" | "recommended" | "optional";
}

export function useMutateGetMissingDocuments() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async (request: GetMissingDocumentsRequest) => {
      const response = await axios.post("/dd-document-registry", request, {
        params: { action: "missing" },
      });

      return response.data.data as MissingDocument[];
    },
  });
}

// Alternative query-based hook for when you want to refetch automatically
export function useGetMissingDocuments(
  transactionType: string | null,
  uploadedDocs: string[],
  priorityThreshold: "critical" | "required" | "recommended" | "optional" = "required"
) {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["missing-documents", transactionType, uploadedDocs, priorityThreshold],
    queryFn: async () => {
      if (!transactionType) return [];

      const response = await axios.post(
        "/dd-document-registry",
        {
          transaction_type: transactionType,
          uploaded_docs: uploadedDocs,
          priority_threshold: priorityThreshold,
        },
        { params: { action: "missing" } }
      );

      return response.data.data as MissingDocument[];
    },
    enabled: !!transactionType,
  });
}
