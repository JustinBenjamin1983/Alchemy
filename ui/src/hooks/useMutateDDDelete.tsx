import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDDelete() {
  const axios = useAxiosWithAuth();

  async function _mutateDDDelete({ dd_id }: { dd_id: string }) {
    const axiosOptions = {
      url: "/dd-delete",
      method: "POST",
      data: { dd_id },
    };
    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateDDDelete,
    onSuccess: (data, variables) => {
      // Invalidate DD listing to refresh the sidebar - matches useGetDDListing query key pattern
      aishopQueryClient.invalidateQueries({
        queryKey: ["get-dds-involves_me"],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: ["get-dds-owned_by_me"],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: ["get-dds-im_a_member"],
      });
      // Invalidate the specific DD query
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dd-${variables.dd_id}`],
      });
    },
  });
}
