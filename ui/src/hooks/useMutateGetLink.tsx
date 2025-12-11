import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateGetLink() {
  const axios = useAxiosWithAuth();
  async function _mutateGetLink({ doc_id, is_dd = false }) {
    const axiosOptions = {
      url: `/link?doc_id=${doc_id}&is_dd=${is_dd}`,
      method: "GET",
    };

    const result = await axios(axiosOptions);
    return result;
  }

  return useMutation({
    mutationFn: _mutateGetLink,
  });
}
