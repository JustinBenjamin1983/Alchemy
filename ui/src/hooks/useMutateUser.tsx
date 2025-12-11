import { useMutation } from "@tanstack/react-query";

import { aishopQueryClient } from "./reactQuerySetup";

export function useMutateUser() {
  async function _mutationUserQuery({ name, email, likelyLoggedOut = false }) {
    return Promise.resolve({});
  }

  return useMutation({
    mutationFn: _mutationUserQuery,
    onSuccess: (data: any, variables) => {
      aishopQueryClient.setQueryData([`get-user`], {
        name: variables.name,
        email: variables.email,
        likelyLoggedOut: variables.likelyLoggedOut,
      });
    },
  });
}
