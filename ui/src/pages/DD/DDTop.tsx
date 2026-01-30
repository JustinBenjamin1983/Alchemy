// DDTop.tsx
import { Button } from "@/components/ui/button";
import { Trash2, Loader2, Activity, ChevronUp, ChevronDown } from "lucide-react";
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

export type ScreenState =
  | "Wizard-Chooser"
  | "Wizard-NewProject"
  | "Wizard-JoinProject"
  | "Wizard-OpenProject"
  | "Wizard-Enhanced"
  | "Analysis"
  | "Processing"
  | "Documents"
  | "DocumentErrors"
  | "Search"
  | "Questions"
  | "DocumentChanges"
  | "ShowReport"
  | "MissingDocs"
  | "CheckpointA";

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
  isHeaderCollapsed?: boolean;
  onToggleHeaderCollapse?: () => void;
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
  isHeaderCollapsed = false,
  onToggleHeaderCollapse,
}: DDTopProps) {
  // Get transaction type info for display
  const typeCode = transactionType as TransactionTypeCode | undefined;
  const typeInfo = typeCode ? TRANSACTION_TYPE_INFO[typeCode] : null;
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDeleteClick = () => {
    console.log("[DDTop] Delete button clicked, opening dialog");
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = () => {
    console.log("[DDTop] Confirm delete clicked, ddId:", ddId);
    if (onDelete) {
      onDelete(ddId);
    } else {
      console.error("[DDTop] onDelete prop is not defined!");
    }
    setShowDeleteDialog(false);
  };

  return (
    <>
      <header className="relative flex flex-col shrink-0 border-b bg-white transition-all duration-300 mb-3">
        {ddName && (
          <div className={`transition-all duration-300 ${isHeaderCollapsed ? 'px-4 py-1' : 'p-4 pb-2'}`}>
            {/* Title row - always visible */}
            <div className="flex items-center gap-3">
              <p className={`font-semibold text-gray-700 transition-all duration-300 ${isHeaderCollapsed ? 'text-xs' : 'text-lg'}`}>
                {ddName}
                {typeInfo && (
                  <span className="text-gray-500 font-normal">
                    {" "}&mdash; {typeInfo.name}
                  </span>
                )}
              </p>
            </div>
            {/* Navigation Buttons - hidden when collapsed */}
            <div className={`flex gap-4 justify-between items-center overflow-hidden transition-all duration-300 ${isHeaderCollapsed ? 'max-h-0 opacity-0 mt-0' : 'max-h-20 opacity-100 mt-3'}`}>
              <div className="flex gap-4">
                <Button
                  className={`transition-all duration-200 hover:scale-105 hover:shadow-md ${
                    screenState === "CheckpointA"
                      ? "bg-alchemyPrimaryOrange text-white hover:bg-alchemyPrimaryOrange/90"
                      : "hover:border-gray-400"
                  }`}
                  variant="outline"
                  onClick={() => setScreenState("CheckpointA")}
                >
                  Console
                </Button>
                <Button
                  className={`transition-all duration-200 hover:scale-105 hover:shadow-md ${
                    screenState === "Analysis"
                      ? "bg-alchemyPrimaryOrange text-white hover:bg-alchemyPrimaryOrange/90"
                      : "hover:border-gray-400"
                  }`}
                  variant="outline"
                  onClick={() => setScreenState("Analysis")}
                >
                  Analysis
                </Button>
                <Button
                  className="transition-all duration-200 hover:scale-105 hover:shadow-md hover:border-gray-400"
                  variant="outline"
                  onClick={() => setScreenState("Wizard-Chooser")}
                >
                  Start / join
                </Button>
                <Button
                  className="bg-alchemyPrimaryNavyBlue text-white transition-all duration-200 hover:scale-105 hover:shadow-md hover:bg-alchemyPrimaryNavyBlue/90"
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
                className="text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all duration-200 hover:scale-110"
                title="Delete project"
              >
                {isDeleting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        )}
        {/* Header collapse toggle - centered on bottom edge of header */}
        {onToggleHeaderCollapse && (
          <button
            onClick={onToggleHeaderCollapse}
            className="absolute left-1/2 -translate-x-1/2 bottom-0 translate-y-1/2 z-10 flex h-6 w-6 items-center justify-center rounded-full bg-alchemyPrimaryNavyBlue hover:bg-alchemyPrimaryNavyBlue/80 transition-colors shadow-md"
            aria-label={isHeaderCollapsed ? "Expand header" : "Collapse header"}
            title={isHeaderCollapsed ? "Expand header" : "Collapse header"}
          >
            {isHeaderCollapsed ? (
              <ChevronDown className="h-3 w-3 text-white" />
            ) : (
              <ChevronUp className="h-3 w-3 text-white" />
            )}
          </button>
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
              className="transition-all duration-200 hover:scale-105 hover:shadow-md hover:border-gray-400"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="transition-all duration-200 hover:scale-105 hover:shadow-md"
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
