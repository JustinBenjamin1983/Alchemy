import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDRiskEdit() {
  const axios = useAxiosWithAuth();

  async function _mutateRiskEdit({ dd_id, perspective_risk_id, detail }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-risk-update",
      method: "PUT",
      data: { perspective_risk_id, detail, dd_id },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateRiskEdit,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-${variables.dd_id}`],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-risks-${variables.dd_id}`],
      });
    },
  });
}
