// hooks/useMutateDeleteOpinion.ts
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface DeleteOpinionParams {
  opinion_id: string;
}

interface DeleteOpinionResponse {
  success: boolean;
  message: string;
  opinion_id: string;
  drafts_deleted: number;
  cleanup_errors?: string[] | null;
}

export const useMutateDeleteOpinion = () => {
  const axios = useAxiosWithAuth();

  const deleteOpinion = async ({
    opinion_id,
  }: DeleteOpinionParams): Promise<DeleteOpinionResponse> => {
    try {
      const response = await axios({
        url: `/opiniondelete/${opinion_id}`,
        method: "DELETE",
      });

      return response.data;
    } catch (error: any) {
      console.error("Delete opinion error:", error);
      throw new Error(
        `Delete failed: ${error.response?.data?.error || error.message}`
      );
    }
  };

  return useMutation({
    mutationFn: deleteOpinion,
    onSuccess: (data) => {
      toast.success(data.message || "Opinion deleted successfully");

      // Show additional info if there were cleanup issues
      if (data.cleanup_errors && data.cleanup_errors.length > 0) {
        toast.warning(
          `Opinion deleted, but ${data.cleanup_errors.length} draft cleanup issues occurred`
        );
      }
    },
    onError: (error: Error) => {
      const errorMessage = error.message || "Failed to delete opinion";
      toast.error(errorMessage);
      console.error("Delete opinion error:", error);
    },
  });
};
