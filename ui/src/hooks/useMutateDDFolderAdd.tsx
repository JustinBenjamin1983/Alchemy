import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDFolderAdd() {
  const axios = useAxiosWithAuth();

  async function _mutateFolderAdd({ dd_id, folder_name, parent_folder_id }) {
    const axiosOptions = {
      url: "/dd-folder",
      method: "POST",
      data: { dd_id, folder_name, parent_folder_id },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateFolderAdd,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-${variables.dd_id}`],
      });
    },
  });
}
