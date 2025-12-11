//  File: ui/src/hooks/useGetDDRiskResults.tsx

import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetDDRiskResults(dd_id) {
  const axios = useAxiosWithAuth();

  const getDDRiskResults = async () => {
    const axiosOptions = {
      url: `/dd-risks-results?dd_id=${dd_id}`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-dd-risk-results-${dd_id}`],
    queryFn: () => getDDRiskResults(),
    ...reactQueryDefaults,
  });
}
