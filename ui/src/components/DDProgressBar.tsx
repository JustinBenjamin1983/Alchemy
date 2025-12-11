// components/DDProgressBar.tsx
import { useState } from "react";
import { useDDProgress } from "@/hooks/useDDProgress";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import { DocumentUploadReport } from "./DocumentUploadReport";
import { useGetDD } from "@/hooks/useGetDD";

export const DDProgressBar = ({ ddId }: { ddId?: string }) => {
  const { data: progressData } = useDDProgress(ddId);
  const { data: ddData } = useGetDD(ddId, !!ddId);
  const [showReport, setShowReport] = useState(false);

  if (!progressData) return null;

  const {
    total,
    complete,
    unsupported,
    failed,
    inProgress,
    notStarted,
    percent,
  } = progressData;

  // Calculate percentages for the multi-segment progress bar
  const completePercent = total ? (complete / total) * 100 : 0;
  const unsupportedPercent = total ? (unsupported / total) * 100 : 0;
  const failedPercent = total ? (failed / total) * 100 : 0;

  // Check if there are any issues to show
  const hasIssues = failed > 0 || unsupported > 0;

  return (
    <>
      <div className="flex items-center gap-3">
        <div className="flex flex-col gap-1 w-64">
          {/* Multi-segment progress bar */}
          <div className="w-full bg-gray-200 rounded h-2 overflow-hidden flex">
            {/* Green segment for completed */}
            <div
              className="bg-green-500 h-full transition-all duration-500"
              style={{ width: `${completePercent}%` }}
            />
            {/* Orange segment for unsupported */}
            <div
              className="bg-orange-500 h-full transition-all duration-500"
              style={{ width: `${unsupportedPercent}%` }}
            />
            {/* Red segment for failed */}
            <div
              className="bg-red-500 h-full transition-all duration-500"
              style={{ width: `${failedPercent}%` }}
            />
            {/* Remaining space stays gray for pending/in-progress */}
          </div>

          {/* Status text */}
          <div className="text-xs text-gray-600">
            <span className="font-medium">
              {complete}/{total} complete ({percent}%)
            </span>
            {(unsupported > 0 || failed > 0) && (
              <span className="ml-2">
                •{" "}
                {[
                  unsupported > 0 && `${unsupported} unsupported`,
                  failed > 0 && `${failed} failed`,
                ]
                  .filter(Boolean)
                  .join(", ")}
              </span>
            )}
            {inProgress > 0 && (
              <span className="ml-2">• {inProgress} in progress</span>
            )}
          </div>
        </div>

        {/* Document report button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowReport(true)}
          className={`h-8 w-8 p-0 ${
            hasIssues
              ? "border-orange-500 text-orange-600 hover:bg-orange-50"
              : "border-gray-300 text-gray-600 hover:bg-gray-50"
          }`}
          title={
            hasIssues
              ? "View document processing issues"
              : "View document processing report"
          }
        >
          <FileText className="h-4 w-4" />
        </Button>
      </div>

      {/* Document Upload Report Dialog */}
      <DocumentUploadReport
        open={showReport}
        onOpenChange={setShowReport}
        ddData={ddData}
      />
    </>
  );
};
