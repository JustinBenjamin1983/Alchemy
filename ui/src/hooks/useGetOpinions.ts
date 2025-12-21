import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetOpinions(enabled: boolean = true) {
  const axios = useAxiosWithAuth();

  const getOpinions = async () => {
    const axiosOptions = {
      url: `/opinions`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: ["get-opinions"],
    queryFn: getOpinions,
    enabled,
    ...reactQueryDefaults,
  });
}
