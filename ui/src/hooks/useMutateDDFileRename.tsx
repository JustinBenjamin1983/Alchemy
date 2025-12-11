import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDFileRename() {
  const axios = useAxiosWithAuth();

  async function _mutateFileRename({ dd_id, doc_id, new_doc_name }) {
    const axiosOptions = {
      url: "/dd-filerename",
      method: "PUT",
      data: { dd_id, doc_id, new_doc_name },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateFileRename,
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
