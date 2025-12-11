import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface DocumentRequestListResponse {
  markdown: string;
  transaction_type: string;
  priority: string;
}

export function useGetDocumentRequestList(
  transactionType: string | null,
  priority: "critical" | "required" | "recommended" | "optional" = "required"
) {
  const axios = useAxiosWithAuth();

  return useQuery({
    queryKey: ["document-request-list", transactionType, priority],
    queryFn: async () => {
      if (!transactionType) return null;

      const response = await axios.get("/dd-document-registry", {
        params: {
          action: "request_list",
          transaction_type: transactionType,
          priority: priority,
        },
      });

      return response.data.data as DocumentRequestListResponse;
    },
    enabled: !!transactionType,
  });
}
