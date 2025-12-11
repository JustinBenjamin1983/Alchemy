// hooks/useMutateSaveStagingDraft.ts - UPDATED TO USE SAVE_DRAFT ENDPOINT
import { useMutation } from "@tanstack/react-query";
import { aishopQueryClient } from "./reactQuerySetup";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

export function useMutateSaveStagingDraft() {
  const axios = useAxiosWithAuth();

  async function _mutateSaveStagingDraft({
    opinion_id,
    draft,
  }: {
    opinion_id: string;
    draft: any;
  }) {
    console.log("💾 Saving staging draft for opinion:", opinion_id);

    // Calculate draft size for logging
    const draftSize = JSON.stringify(draft).length;
    console.log("📊 Draft content size:", draftSize, "bytes");
    console.log("📦 All drafts now go to blob storage");

    const axiosOptions = {
      url: "/save_draft",
      method: "POST",
      data: {
        opinion_id,
        draft,
        // NOTE: No version_name parameter = staging draft
        // version_name: undefined  // This tells the backend it's a staging draft
      },
      timeout: 30000, // 30 second timeout
    };

    const result = await axios(axiosOptions);
    console.log("✅ Staging draft saved successfully:", result.data);
    return result;
  }

  return useMutation({
    mutationFn: _mutateSaveStagingDraft,
    retry: 2, // Retry failed requests up to 2 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000), // Exponential backoff
    onSuccess: (data, variables) => {
      console.log("✅ Staging draft mutation successful");

      // Use a more reliable invalidation strategy
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-opinion`, variables.opinion_id],
      });

      // Also invalidate any related queries
      aishopQueryClient.invalidateQueries({
        queryKey: [`get-opinion`],
        exact: false,
      });
    },
    onError: (error, variables) => {
      console.error("❌ Staging draft save failed:", error);
      console.error("📋 Variables:", variables);
    },
  });
}

// Optional: Add a hook for manually triggering a save with better error handling
export function useSaveStagingDraftWithRetry() {
  const mutateSaveStagingDraft = useMutateSaveStagingDraft();

  const saveWithRetry = async (
    opinion_id: string,
    draft: any,
    maxRetries = 3
  ) => {
    let lastError: any;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(
          `💾 Save attempt ${attempt}/${maxRetries} for opinion ${opinion_id}`
        );

        const result = await mutateSaveStagingDraft.mutateAsync({
          opinion_id,
          draft,
        });

        console.log(`✅ Save successful on attempt ${attempt}`);
        return result;
      } catch (error) {
        lastError = error;
        console.error(`❌ Save attempt ${attempt} failed:`, error);

        if (attempt < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
          console.log(`⏳ Waiting ${delay}ms before retry...`);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError;
  };

  return { saveWithRetry, ...mutateSaveStagingDraft };
}
