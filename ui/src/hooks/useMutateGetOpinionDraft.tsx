import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateGetOpinionDraft() {
  const axios = useAxiosWithAuth();
  async function _mutateGetOpinionDraft({ opinion_id, draft_id }) {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/get_draft?opinion_id=${opinion_id}&draft_id=${draft_id}`,
      method: "GET",
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateGetOpinionDraft,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-draft`, variables["opinion_id"], variables["draft_id"]],
      });
    },
  });
}
