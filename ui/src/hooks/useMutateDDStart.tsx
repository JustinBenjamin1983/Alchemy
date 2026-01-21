// File: ui/src/hooks/useMutateDDStart.tsx

import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDStart() {
  const axios = useAxiosWithAuth();
  async function _mutationDDStart({
    data,
  }: {
    data: {
      name: string;
      briefing: string;
      blobUrl: string;
      transactionType?: string;
      projectSetup?: unknown;
    };
  }) {
    const response = await axios.post("/dd-start", data);
    return response;
  }

  return useMutation({
    mutationFn: _mutationDDStart,
    onSuccess: (data, variables) => {
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds`],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds-${"im_not_a_member"}`],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds-${"involves_me"}`],
      });
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-dds-${"owned_by_me"}`],
      });
    },
  });
}
