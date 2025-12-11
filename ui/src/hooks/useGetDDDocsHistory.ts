import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetDDDocsHistory(dd_id) {
  const axios = useAxiosWithAuth();

  const getDDListing = async () => {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-get_docs_history?dd_id=${dd_id}`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-dds-docs-history-${dd_id}`],
    queryFn: () => getDDListing(),
    ...reactQueryDefaults,
    enabled: false,
  });
}
