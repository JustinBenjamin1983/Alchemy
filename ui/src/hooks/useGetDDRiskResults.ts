//  File: ui/src/hooks/useGetDDRiskResults.tsx

import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetDDRiskResults(dd_id: string | null, run_id?: string | null) {
  const axios = useAxiosWithAuth();

  const getDDRiskResults = async () => {
    // Build query params
    let url = `/dd-risks-results?dd_id=${dd_id}`;
    if (run_id) {
      url += `&run_id=${run_id}`;
    }

    const axiosOptions = {
      url,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-dd-risk-results`, dd_id, run_id],
    queryFn: () => getDDRiskResults(),
    enabled: !!dd_id,
    ...reactQueryDefaults,
  });
}
