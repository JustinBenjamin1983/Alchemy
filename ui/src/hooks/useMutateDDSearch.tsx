import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateDDSearch() {
  const axios = useAxiosWithAuth();

  async function _mutateDDSearch({ folder_id, dd_id, prompt, keyword_only }) {
    const axiosOptions = {
      url: `/dd-search`,
      method: "PUT",
      data: {
        folder_id,
        dd_id,
        prompt,
        keyword_only,
      },
    };

    const result = await axios(axiosOptions);

    return result;
  }

  return useMutation({
    mutationFn: _mutateDDSearch,
  });
}
