import { useMutation } from "@tanstack/react-query";

import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateSaveOpinion() {
  const axios = useAxiosWithAuth();

  async function _mutateSaveOpinion(data: any) {
    const axiosOptions = {
      url: "/opinion",
      method: "PUT",
      data,
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateSaveOpinion,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({ queryKey: ["get-opinions"] });
      aishopQueryClient.invalidateQueries({
        queryKey: ["get-opinion", data["id"]],
      });
    },
  });
}
