import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGenerateSAS() {
  const axios = useAxiosWithAuth();

  async function _generateSAS({ filename }: { filename: string }) {
    const response = await axios.post("/dd-generate-sas", { filename });
    return response.data;
  }

  return useMutation({
    mutationFn: _generateSAS,
  });
}
