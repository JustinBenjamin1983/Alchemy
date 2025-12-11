import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetDD(dd_id, enabled = true) {
  const axios = useAxiosWithAuth();

  const getDD = async () => {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-get?dd_id=${dd_id}`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-dd-${dd_id}`],
    queryFn: () => getDD(),
    ...reactQueryDefaults,
    enabled,
  });
}
