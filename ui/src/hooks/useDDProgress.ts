// hooks/useDDProgress.ts
import { useQuery } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

/** Shape of one document coming back from GET /dd/:id */
interface Doc {
  document_id: string;
  original_file_name: string;
  type: string;
  uploaded_at: string;
  processing_status?: string;
  size_in_bytes: number;
  is_original: boolean;
}

interface Folder {
  folder_id: string;
  folder_name: string;
  level: number;
  hierarchy: string;
  documents?: Doc[];
}

/** -------------------------------------------
 * Calculate progress straight from GET-DD data
 * ------------------------------------------ */
export function useDDProgress(ddId?: string) {
  const axios = useAxiosWithAuth();

  /** GET /dd/:id — same call your `useGetDD` hook makes */
  const fetchDD = async () => {
    const { data } = await axios({
      url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/dd-get?dd_id=${ddId}`,
      method: "GET",
    });
    return data as { folders?: Folder[]; name?: string };
  };

  return useQuery({
    queryKey: ["dd", ddId],
    queryFn: fetchDD,
    enabled: !!ddId,
    /** poll so the bar keeps moving while docs finish processing */
    refetchInterval: 4_000,
    /** convert the DD payload → { total, complete, …, percent } */
    select: (dd) => {
      const docs = dd?.folders?.flatMap((f) => f.documents ?? []) ?? [];

      const total = docs.length;
      const complete = docs.filter(
        (d) => d.processing_status?.toLowerCase() === "complete"
      ).length;
      const unsupported = docs.filter(
        (d) => d.processing_status?.toLowerCase() === "unsupported"
      ).length;
      const failed = docs.filter(
        (d) => d.processing_status?.toLowerCase() === "failed"
      ).length;
      const inProgress = docs.filter(
        (d) => d.processing_status?.toLowerCase() === "in progress"
      ).length;
      const notStarted = docs.filter(
        (d) => d.processing_status?.toLowerCase() === "queued"
      ).length;

      // Calculate progress: Complete documents / Total documents
      // Note: This gives the percentage of successfully processed documents
      const percent = total ? Math.round((complete / total) * 100) : 0;

      // Alternative calculation if you want to include "finished" documents (complete + unsupported + failed):
      // const finished = complete + unsupported + failed;
      // const percent = total ? Math.round((finished / total) * 100) : 0;

      return {
        total,
        complete,
        unsupported,
        failed,
        inProgress,
        notStarted,
        percent,
        // Include the full data for the report
        rawData: dd,
      };
    },
  });
}
