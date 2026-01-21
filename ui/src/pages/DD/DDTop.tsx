// DDTop.tsx
import { Button } from "@/components/ui/button";
import { Trash2, Loader2, Activity, ChevronLeft, ChevronRight } from "lucide-react";
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
import { useSidebar } from "@/components/ui/sidebar";

type ScreenState =
  | "Wizard-Chooser"
  | "Wizard-NewProject"
  | "Wizard-JoinProject"
  | "Wizard-OpenProject"
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
  const { toggleSidebar, state } = useSidebar();

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
      <header className="flex flex-col shrink-0 gap-3 p-4 border-b bg-white">
        {ddName && (
          <>
            {/* Title row with sidebar toggle */}
            <div className="flex items-center gap-3">
              <button
                onClick={toggleSidebar}
                className="flex h-8 w-8 items-center justify-center rounded-md bg-gray-100 hover:bg-gray-200 transition-colors"
                aria-label="Toggle Sidebar"
              >
                {state === "expanded" ? (
                  <ChevronLeft className="h-5 w-5 text-gray-600" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-600" />
                )}
              </button>
              <p className="font-semibold text-gray-700 text-lg">
                {ddName}
                {typeInfo && (
                  <span className="text-gray-500 font-normal">
                    {" "}&mdash; {typeInfo.name}
                  </span>
                )}
              </p>
            </div>
            {/* Navigation Buttons */}
            <div className="flex gap-4 justify-between items-center">
              <div className="flex gap-4">
                <Button
                  className={`transition-all duration-200 hover:scale-105 hover:shadow-md ${
                    screenState === "Processing"
                      ? "bg-alchemyPrimaryOrange text-white hover:bg-alchemyPrimaryOrange/90"
                      : "hover:border-gray-400"
                  }`}
                  variant="outline"
                  onClick={() => setScreenState("Processing")}
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
