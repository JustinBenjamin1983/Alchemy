import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDFolderDelete() {
  const axios = useAxiosWithAuth();

  async function _mutateFolderDelete({ dd_id, folder_id }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-folder",
      method: "DELETE",
      data: { dd_id, folder_id },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateFolderDelete,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-${variables.dd_id}`],
      });
    },
  });
}
