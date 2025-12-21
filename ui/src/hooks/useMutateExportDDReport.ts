// hooks/useMutateExportDDReport.ts
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface ExportDDReportParams {
  dd_id: string;
  run_id?: string | null;
  report_type?: "preliminary" | "final";
}

export const useMutateExportDDReport = () => {
  const axios = useAxiosWithAuth();

  const exportReport = async ({
    dd_id,
    run_id,
    report_type = "preliminary",
  }: ExportDDReportParams): Promise<void> => {
    console.log('[ExportDDReport] Starting export:', { dd_id, run_id, report_type });
    try {
      let apiUrl = `/dd-export-report?dd_id=${dd_id}&report_type=${report_type}`;
      if (run_id) {
        apiUrl += `&run_id=${run_id}`;
      }
      console.log('[ExportDDReport] Fetching:', apiUrl);

      const response = await axios({
        url: apiUrl,
        method: "GET",
        responseType: "blob",
      });

      console.log('[ExportDDReport] Response received:', response.status);

      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers["content-disposition"];
      const typeLabel = report_type === "final" ? "Final" : "Preliminary";
      let filename = `DD_${typeLabel}_Report_${new Date()
        .toISOString()
        .slice(0, 10)}.docx`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, "");
        }
      }

      // Create download link
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error: any) {
      console.error("Export error:", error);

      // Try to parse error message from blob response
      if (error.response?.data instanceof Blob) {
        try {
          const text = await error.response.data.text();
          const parsed = JSON.parse(text);
          throw new Error(parsed.error || "Export failed");
        } catch {
          throw new Error("Export failed. Please try again.");
        }
      }

      throw new Error(
        `Export failed: ${error.response?.data?.error || error.message}`
      );
    }
  };

  return useMutation({
    mutationFn: exportReport,
    onSuccess: (_, variables) => {
      const typeLabel = variables.report_type === "final" ? "Final" : "Preliminary";
      toast.success(`${typeLabel} DD Report exported successfully!`);
    },
    onError: (error: Error) => {
      console.error("Export error:", error);
      toast.error(`Failed to export report: ${error.message}`);
    },
  });
};
