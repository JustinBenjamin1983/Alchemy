// DDTop.tsx
import { Button } from "@/components/ui/button";
import { Trash2, Loader2, Activity } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TRANSACTION_TYPE_INFO, TransactionTypeCode } from "./Wizard/types";

type ScreenState =
  | "Wizard-Chooser"
  | "Wizard-NewProject"
  | "Wizard-JoinProject"
  | "Analysis"
  | "Processing";

interface DDTopProps {
  ddId: string;
  ddName: string;
  transactionType?: string | null;
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
  transactionType,
  screenState,
  setScreenState,
  onDelete,
  isDeleting = false,
  onGenerateReport,
  isGeneratingReport = false,
}: DDTopProps) {
  // Get transaction type info for display
  const typeCode = transactionType as TransactionTypeCode | undefined;
  const typeInfo = typeCode ? TRANSACTION_TYPE_INFO[typeCode] : null;
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

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
            {/* Title row */}
            <p className="font-semibold text-gray-700 text-lg">
              {ddName}
              {typeInfo && (
                <span className="text-gray-500 font-normal">
                  {" "}&mdash; {typeInfo.name}
                </span>
              )}
            </p>
            {/* Navigation Buttons */}
            <div className="flex gap-4 justify-between items-center">
              <div className="flex gap-4">
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
                  Console
                </Button>
                <Button
                  className={
                    screenState === "Analysis" ? "bg-alchemyPrimaryGoldenWeb" : ""
                  }
                  variant="outline"
                  onClick={() => setScreenState("Analysis")}
                >
                  Analysis
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setScreenState("Wizard-Chooser")}
                >
                  Start / join
                </Button>
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
              {/* Delete button - positioned at far right */}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDeleteClick}
                disabled={isDeleting}
                className="text-gray-400 hover:text-red-600 hover:bg-red-50"
                title="Delete project"
              >
                {isDeleting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
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
