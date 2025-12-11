import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export interface ClassifyDocumentRequest {
  filename: string;
  content_preview?: string;
  transaction_type: string;
}

export interface ClassifyDocumentResponse {
  category: string;
  folder: string;
  confidence: number;
}

export function useMutateClassifyDocument() {
  const axios = useAxiosWithAuth();

  return useMutation({
    mutationFn: async (request: ClassifyDocumentRequest) => {
      const response = await axios.post("/dd-document-registry", request, {
        params: { action: "classify" },
      });

      return response.data.data as ClassifyDocumentResponse;
    },
  });
}
