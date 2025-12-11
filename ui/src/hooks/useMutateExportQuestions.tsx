// hooks/useMutateExportQuestions.tsx
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface ExportQuestionsParams {
  dd_id: string;
}

export const useMutateExportQuestions = () => {
  const axios = useAxiosWithAuth();

  const exportQuestions = async ({
    dd_id,
  }: ExportQuestionsParams): Promise<void> => {
    try {
      const response = await axios({
        url: `https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/DDQuestionsExport/${dd_id}`,
        method: "GET",
        responseType: "blob", // This is crucial for file downloads
      });

      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers["content-disposition"];
      let filename = `DD-QA-Report-${new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/[:-]/g, "")}.docx`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, "");
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      console.error("Export error:", error);
      throw new Error(
        `Export failed: ${error.response?.data?.message || error.message}`
      );
    }
  };

  return useMutation({
    mutationFn: exportQuestions,
    onSuccess: () => {
      toast.success("Q&A Report exported successfully!");
    },
    onError: (error: Error) => {
      console.error("Export error:", error);
      toast.error(`Failed to export report: ${error.message}`);
    },
  });
};
