import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateGetPrecedents() {
  const axios = useAxiosWithAuth();
  async function _mutateGetPrecedents({ opinion_id }) {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/precedents`,
      method: "PUT",
      data: { opinion_id },
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateGetPrecedents,
  });
}
