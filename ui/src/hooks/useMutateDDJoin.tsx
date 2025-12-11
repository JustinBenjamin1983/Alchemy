//  File: ui/src/hooks/useMutateDDJoin.tsx

import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDJoin() {
  const axios = useAxiosWithAuth();

  async function _mutateJoinDD({ dd_id, lens, risks }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-join",
      method: "PUT",
      data: { dd_id, lens, risks },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateJoinDD,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds`],
      });
    },
  });
}
