import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetGlobalOpinionDocs() {
  const axios = useAxiosWithAuth();

  const getGlobalOpinionDocs = async () => {
    const axiosOptions = {
      url: `/global_opinion_docs`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-global-opinion-docs`],
    queryFn: () => getGlobalOpinionDocs(),
    ...reactQueryDefaults,
  });
}
