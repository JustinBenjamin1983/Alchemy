import { useMutation } from "@tanstack/react-query";

import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDeleteGlobalOpinionDoc() {
  const axios = useAxiosWithAuth();
  async function _mutateDeleteGlobalOpinionDoc({
    opinion_id,
    doc_id,
  }: {
    opinion_id: string;
    doc_id: string;
  }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/opinion_doc",
      method: "PUT",
      data: {
        opinion_id,
        doc_id,
        type: "delete_global_doc",
      },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateDeleteGlobalOpinionDoc,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({ queryKey: ["get-opinions"] });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-global-opinion-docs`],
      });
    },
  });
}
