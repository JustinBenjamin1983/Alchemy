import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateUploadFile() {
  const axios = useAxiosWithAuth();
  async function _mutationUploadFile({ data, file }: { data: any; file: any }) {
    var fd = new FormData();
    fd.append("file", file);
    for (const [key, value] of Object.entries(data)) {
      fd.append(
        key,
        !(value as any).join ? value + "" : (value as any).join(",")
      );
    }
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/upload",
      method: "POST",
      data: fd,
    };
    const response = await axios(axiosOptions);

    return response;
  }

  return useMutation({
    mutationFn: _mutationUploadFile,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-opinion`, data["opinion_id"]],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-global-opinion-docs`],
      });
    },
  });
}
