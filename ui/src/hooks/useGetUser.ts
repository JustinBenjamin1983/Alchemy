import { useQuery } from "@tanstack/react-query";
import { aishopQueryClient, reactQueryDefaults } from "./reactQuerySetup";

export function useGetUser() {
  return useQuery({
    queryKey: [`get-user`],
    queryFn: () => {
      return aishopQueryClient.getQueryData([`get-user`]);
    },
    ...reactQueryDefaults,
  });
}
