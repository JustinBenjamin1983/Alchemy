import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetDDListing(
  filter:
    | "involves_me"
    | "doesnt_involve_me"
    | "owned_by_me"
    | "im_a_member"
    | "im_not_a_member"
) {
  const axios = useAxiosWithAuth();

  const getDDListing = async () => {
    const axiosOptions = {
      url: `/dd-list?filter_type=${filter}`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    return data;
  };

  return useQuery({
    queryKey: [`get-dds-${filter}`],
    queryFn: () => getDDListing(),
    ...reactQueryDefaults,
  });
}
