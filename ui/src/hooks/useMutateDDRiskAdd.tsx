//  File: ui/src/hooks/useMutateDDRiskAdd.tsx

import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

// Define types for the mutation parameters
type SingleRiskParams = {
  dd_id: string;
  category: string;
  detail: string;
  folder_scope?: string;
  risks?: never; // Ensure risks is not present in single mode
};

type BatchRiskParams = {
  dd_id: string;
  risks: Array<{
    category: string;
    detail: string;
    folder_scope: string;
  }>;
  category?: never; // Ensure individual params are not present in batch mode
  detail?: never;
  folder_scope?: never;
};

type RiskAddParams = SingleRiskParams | BatchRiskParams;

export function useMutateDDRiskAdd() {
  const axios = useAxiosWithAuth();

  async function _mutateRiskAdd(params: RiskAddParams) {
    let requestData;

    if ("risks" in params && params.risks) {
      // Batch mode - array of risks
      requestData = {
        dd_id: params.dd_id,
        risks: params.risks,
      };
    } else {
      // Single mode - individual risk (backward compatibility)
      const singleParams = params as SingleRiskParams;
      requestData = {
        dd_id: singleParams.dd_id,
        category: singleParams.category,
        detail: singleParams.detail,
        folder_scope: singleParams.folder_scope || "All Folders",
      };
    }

    const axiosOptions = {
      url: "/dd-risk-add",
      method: "POST",
      data: requestData,
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateRiskAdd,
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
