import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDUploadSingleFile() {
  const axios = useAxiosWithAuth();
  async function _mutationDDUploadSingleFile({
    data,
    file,
  }: {
    data: {
      dd_id: string;
      folder_id: string;
    };
    file: any;
  }) {
    var fd = new FormData();
    fd.append("file", file);
    for (const [key, value] of Object.entries(data)) {
      fd.append(
        key,
        !(value as any).join ? value + "" : (value as any).join(",")
      );
    }
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-fileupload",
      method: "POST",
      data: fd,
    };
    const response = await axios(axiosOptions);

    return response;
  }

  return useMutation({
    mutationFn: _mutationDDUploadSingleFile,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds`],
      });
    },
  });
}
