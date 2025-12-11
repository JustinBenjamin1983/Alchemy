// DDTop.tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DDProgressBar } from "@/components/DDProgressBar";
import { Trash2, Loader2, Play, Activity } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DEV_MODE } from "@/authConfig";
import { useProcessAllDocuments } from "@/hooks/useProcessAllDocuments";

type ScreenState =
  | "Documents"
  | "Wizard-Chooser"
  | "Wizard-NewProject"
  | "Wizard-JoinProject"
  | "DocumentErrors"
  | "Search"
  | "Risks"
  | "Questions"
  | "DocumentChanges"
  | "ShowReport"
  | "Processing";

interface DDTopProps {
  ddId: string;
  ddName: string;
  docHistoryCount?: number;
  screenState: ScreenState;
  setScreenState: (state: ScreenState) => void;
  onDelete?: (ddId: string) => void;
  isDeleting?: boolean;
  onGenerateReport?: () => void;
  isGeneratingReport?: boolean;
}

export function DDTop({
  ddId,
  ddName,
  docHistoryCount,
  screenState,
  setScreenState,
  onDelete,
  isDeleting = false,
  onGenerateReport,
  isGeneratingReport = false,
}: DDTopProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showProcessDialog, setShowProcessDialog] = useState(false);
  const processAllDocs = useProcessAllDocuments(ddId);

  const handleDeleteClick = () => {
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = () => {
    if (onDelete) {
      onDelete(ddId);
    }
    setShowDeleteDialog(false);
  };

  return (
    <>
      <header className="flex flex-col shrink-0 gap-3 p-4 border-b bg-white">
        {ddName && (
          <>
            {/* Top row: Title and Progress Bar */}
            <div className="flex justify-between items-center">
              <p className="font-semibold text-gray-700 text-lg">{ddName}</p>
              <div className="flex items-center gap-3">
                <DDProgressBar ddId={ddId} />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDeleteClick}
                  disabled={isDeleting}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                >
                  {isDeleting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
            {/* Bottom row: Navigation Buttons */}
            <div className="flex gap-4 justify-start">
              <Button
                className={
                  screenState === "Documents"
                    ? "bg-alchemyPrimaryGoldenWeb"
                    : ""
                }
                variant="outline"
                onClick={() => setScreenState("Documents")}
              >
                Documents
              </Button>
              <Button
                className={
                  screenState === "DocumentChanges"
                    ? "bg-alchemyPrimaryGoldenWeb"
                    : ""
                }
                variant="outline"
                onClick={() => setScreenState("DocumentChanges")}
              >
                Document Changes
                {docHistoryCount && (
                  <div className="pl-2">
                    <Badge variant="destructive">{docHistoryCount}</Badge>
                  </div>
                )}
              </Button>
              <Button
                className={
                  screenState === "Search" ? "bg-alchemyPrimaryGoldenWeb" : ""
                }
                variant="outline"
                onClick={() => setScreenState("Search")}
              >
                Search
              </Button>
              <Button
                className={
                  screenState === "Risks" ? "bg-alchemyPrimaryGoldenWeb" : ""
                }
                variant="outline"
                onClick={() => setScreenState("Risks")}
              >
                Risks
              </Button>
              <Button
                className={
                  screenState === "Questions"
                    ? "bg-alchemyPrimaryGoldenWeb"
                    : ""
                }
                variant="outline"
                onClick={() => setScreenState("Questions")}
              >
                Questions
              </Button>
              <Button
                className={
                  screenState === "Processing"
                    ? "bg-alchemyPrimaryGoldenWeb"
                    : ""
                }
                variant="outline"
                onClick={() => setScreenState("Processing")}
              >
                <Activity className="mr-2 h-4 w-4" />
                Processing
              </Button>
              <Button
                variant="outline"
                onClick={() => setScreenState("Wizard-Chooser")}
              >
                Start / join
              </Button>
              {DEV_MODE && (
                <Button
                  className="bg-green-600 hover:bg-green-700 text-white"
                  variant="outline"
                  onClick={() => {
                    console.log("[DDTop] Process All Docs clicked, ddId:", ddId, "isPending:", processAllDocs.isPending);
                    processAllDocs.mutate();
                  }}
                  disabled={processAllDocs.isPending}
                >
                  {processAllDocs.isPending ? (
                    <Loader2 className="animate-spin mr-2 h-4 w-4" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  {processAllDocs.isPending ? "Processing..." : "Process All Docs"}
                </Button>
              )}
              <Button
                className="bg-alchemyPrimaryNavyBlue text-white"
                variant="outline"
                onClick={onGenerateReport}
                disabled={isGeneratingReport || !onGenerateReport}
              >
                {isGeneratingReport && (
                  <Loader2 className="animate-spin mr-2 h-4 w-4" />
                )}
                Generate Report
              </Button>
            </div>
          </>
        )}
      </header>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="w-[60%] max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Due Diligence</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{ddName}"? This action will
              permanently remove all documents, search index entries, risk
              assessments, and related data. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={isDeleting}
            >
              {isDeleting && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Delete Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
