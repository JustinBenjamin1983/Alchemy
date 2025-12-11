// File: ui/src/hooks/useMutateGenerateOpinion.tsx

import { useMutation } from "@tanstack/react-query";

import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateGenerateOpinion() {
  const axios = useAxiosWithAuth();

  async function _mutateGenerateOpinion(data: any) {
    const axiosOptions = {
      url: "/generateopinion",
      method: "PUT",
      data,
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateGenerateOpinion,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-opinions`],
      });
    },
  });
}
