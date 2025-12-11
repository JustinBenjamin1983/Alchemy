import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDFileMove() {
  const axios = useAxiosWithAuth();

  async function _mutateFileMove({
    dd_id,
    doc_id,
    folder_from_id,
    folder_to_id,
  }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-filemove",
      method: "PUT",
      data: { dd_id, doc_id, folder_from_id, folder_to_id },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateFileMove,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-${variables.dd_id}`],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds-docs-history-${variables.dd_id}`],
      });
    },
  });
}
