import { useMutation } from "@tanstack/react-query";

import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateToggleOpinionDoc() {
  const axios = useAxiosWithAuth();

  async function _mutateToggleOpinionDoc({
    opinion_id,
    doc_id,
  }: {
    opinion_id: string;
    doc_id: string;
  }) {
    const axiosOptions = {
      url: "/opinion_doc",
      method: "PUT",
      data: {
        opinion_id,
        doc_id,
        type: "toggle_doc",
      },
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateToggleOpinionDoc,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({ queryKey: ["get-opinions"] });
    },
  });
}
