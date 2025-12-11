// hooks/useGetOpinion.ts - FIXED VERSION
import { useQuery } from "@tanstack/react-query";
import { reactQueryDefaults } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useGetOpinion(opinionId: string | null) {
  const axios = useAxiosWithAuth();

  const getOpinion = async (opinionId: string) => {
    console.log("🔄 Fetching opinion:", opinionId);

    const axiosOptions = {
      url: `/opinion?id=${opinionId}`,
      method: "GET",
    };

    const { data } = await axios(axiosOptions);
    console.log("✅ Opinion fetched successfully:", {
      id: data.id,
      hasStaging: !!data.staging_draft,
      draftsCount: data.drafts?.length || 0,
    });

    return data;
  };

  return useQuery({
    queryKey: [`get-opinion`, opinionId],
    queryFn: () => getOpinion(opinionId!),
    ...reactQueryDefaults,
    // FIX: Enable the query when we have an opinion ID
    enabled: !!opinionId, // This was the main issue!
    // Add retry logic for better reliability
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
