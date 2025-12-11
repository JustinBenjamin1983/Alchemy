import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateCreateOpinion() {
  const axios = useAxiosWithAuth();

  async function _mutateCreateOpinion(data: any) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/aishop-test-32434/addopinion",
      method: "POST",
      data,
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateCreateOpinion,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-opinions`],
      });
    },
  });
}
