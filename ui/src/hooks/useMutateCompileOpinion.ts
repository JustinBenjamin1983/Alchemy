// src/hooks/useMutateCompileOpinion.ts
import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

type CompilePayload = {
  opinion_id: string;
  to: string;
  date: string;
  re: string;
  staging_draft_text?: string;
  template_docx_b64?: string;
  template_filename?: string;
};

export type CompileResponse = {
  success: boolean;
  echo?: {
    to: string;
    date: string;
    re: string;
    draft_chars: number;
    draft_head: string;
  };
  message?: string;
};

export function useMutateCompileOpinion() {
  const axios = useAxiosWithAuth();
  return useMutation({
    mutationFn: (data: CompilePayload) =>
      axios({
        url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/compile_opinion",
        method: "POST",
        data,
      }),
  });
}
