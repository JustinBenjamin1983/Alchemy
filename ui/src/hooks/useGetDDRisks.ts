import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetDDRisks(dd_id) {
  const axios = useAxiosWithAuth();

  const getDDRisks = async () => {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-risks?dd_id=${dd_id}`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-dd-risks-${dd_id}`],
    queryFn: () => getDDRisks(),
    ...reactQueryDefaults,
  });
}
