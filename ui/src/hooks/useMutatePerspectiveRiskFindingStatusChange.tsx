import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { aishopQueryClient } from "./reactQuerySetup";

export function useMutatePerspectiveRiskFindingStatusChange() {
  const axios = useAxiosWithAuth();

  async function _mutatePerspectiveRiskFindingStatusChange(data: {
    dd_id: string;
    perspective_risk_finding_id: string;
    status: string; // 'New', 'Red', 'Amber', 'Deleted'
  }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-perspectiveriskfindingstatus",
      method: "PUT",
      data,
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutatePerspectiveRiskFindingStatusChange,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-risk-results-${variables.dd_id}`],
      });
    },
  });
}
