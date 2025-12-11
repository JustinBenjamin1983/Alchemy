import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";
import { aishopQueryClient } from "./reactQuerySetup";

export function useMutatePerspectiveRiskFindingSetIsReviewed() {
  const axios = useAxiosWithAuth();

  async function _mutatePerspectiveRiskFindingSetIsReviewed(data: {
    dd_id: string;
    perspective_risk_finding_id: string;
  }) {
    const axiosOptions = {
      url: "https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-perspectiveriskfindingisreviewed",
      method: "PUT",
      data,
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutatePerspectiveRiskFindingSetIsReviewed,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-risk-results-${variables.dd_id}`],
      });
    },
  });
}
