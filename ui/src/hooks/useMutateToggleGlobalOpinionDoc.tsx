import { useMutation } from "@tanstack/react-query";

import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateToggleGlobalOpinionDoc() {
  const axios = useAxiosWithAuth();

  async function _mutateToggleGlobalOpinionDoc({
    opinion_id,
    doc_id,
    doc_name,
  }: {
    opinion_id: string;
    doc_id: string;
    doc_name: string;
  }) {
    const axiosOptions = {
      url: "/opinion_doc",
      method: "PUT",
      data: {
        opinion_id,
        doc_id,
        doc_name,
        type: "toggle_global_docs",
      },
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateToggleGlobalOpinionDoc,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({ queryKey: ["get-opinions"] });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-global-opinion-docs`],
      });
    },
  });
}
