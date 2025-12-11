import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetOpinions() {
  const axios = useAxiosWithAuth();

  const getOpinions = async () => {
    const axiosOptions = {
      url: `https://apim-func-test-123123123412.azure-api.net/aishop-test-32434/opinions`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: ["get-opinions"],
    queryFn: getOpinions,
    ...reactQueryDefaults,
  });
}
