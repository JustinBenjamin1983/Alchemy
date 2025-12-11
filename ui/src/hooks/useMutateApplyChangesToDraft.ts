// hooks/useMutateApplyChangesToDraft.ts
import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export type ApplyChangesToDraftRequest = {
  opinion_id: string;
  draft_text: string;
  draft_id?: string;
};

export type ApplyChangesToDraftResponse = {
  success: boolean;
  message: string;
  draft_id: string;
  updated_on: string;
  status: string;
};

export const useMutateApplyChangesToDraft = () => {
  const axios = useAxiosWithAuth();

  const applyChangesToDraft = async (request: ApplyChangesToDraftRequest) => {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/apply_changes`,
      method: "POST",
      data: request,
    };
    const { data } = await axios(axiosOptions);
    return data;
  };

  return useMutation<
    ApplyChangesToDraftResponse,
    Error,
    ApplyChangesToDraftRequest
  >({
    mutationFn: applyChangesToDraft,
    onSuccess: (data) => {
      console.log("✅ Draft changes applied successfully:", data);
    },
    onError: (error) => {
      console.error("❌ Failed to apply draft changes:", error);
    },
  });
};
