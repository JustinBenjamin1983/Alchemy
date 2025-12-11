import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateSaveDraft() {
  const axios = useAxiosWithAuth();

  async function _mutateSaveDraft({
    opinion_id,
    draft,
    version_name,
  }: {
    opinion_id: string;
    draft: any;
    version_name: string;
  }) {
    const axiosOptions = {
      url: "/save_draft",
      method: "POST",
      data: {
        opinion_id,
        draft,
        version_name,
      },
    };
    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateSaveDraft,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-opinion`, variables["opinion_id"]],
      });
    },
  });
}
