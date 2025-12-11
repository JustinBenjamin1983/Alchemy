import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDDelete() {
  const axios = useAxiosWithAuth();

  async function _mutateDDDelete({ dd_id }: { dd_id: string }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-delete",
      method: "POST",
      data: { dd_id },
    };
    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateDDDelete,
    onSuccess: (data, variables) => {
      // Invalidate DD listing to refresh the list
      aishopQueryClient.invalidateQueries({
        queryKey: ["get-dd-listing"],
      });
      // Invalidate the specific DD query
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-${variables.dd_id}`],
      });
    },
  });
}
