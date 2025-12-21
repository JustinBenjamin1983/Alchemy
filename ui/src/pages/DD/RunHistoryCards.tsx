/**
 * Run History Cards Component
 *
 * Displays cards for each analysis run at the top of the Risks tab.
 * - Clickable to select a run and view its findings
 * - Shows run name and date
 * - Edit name, delete run options
 * - Processing runs show "Still Processing" and are not clickable
 */
import React, { useState } from "react";
import { motion } from "framer-motion";
import { Calendar, Edit2, Trash2, Loader2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  useAnalysisRunsList,
  useUpdateAnalysisRun,
  useDeleteAnalysisRun,
  AnalysisRun,
} from "@/hooks/useAnalysisRuns";

interface RunHistoryCardsProps {
  ddId: string;
  selectedRunId: string | null;
  onSelectRun: (runId: string | null) => void;
}

export const RunHistoryCards: React.FC<RunHistoryCardsProps> = ({
  ddId,
  selectedRunId,
  onSelectRun,
}) => {
  const { data, isLoading } = useAnalysisRunsList(ddId);
  const updateRun = useUpdateAnalysisRun();
  const deleteRun = useDeleteAnalysisRun();

  const [editingRunId, setEditingRunId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [deleteConfirmRunId, setDeleteConfirmRunId] = useState<string | null>(null);

  const runs = data?.runs || [];

  // Format date for display (SAST timezone)
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Pending";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-ZA", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Africa/Johannesburg",
    });
  };

  // Start editing a run name
  const handleStartEdit = (run: AnalysisRun, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingRunId(run.run_id);
    setEditName(run.name);
  };

  // Save edited name
  const handleSaveEdit = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (editingRunId && editName.trim()) {
      await updateRun.mutateAsync({ runId: editingRunId, name: editName.trim() });
      setEditingRunId(null);
      setEditName("");
    }
  };

  // Cancel editing
  const handleCancelEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingRunId(null);
    setEditName("");
  };

  // Confirm delete
  const handleConfirmDelete = async () => {
    if (deleteConfirmRunId) {
      await deleteRun.mutateAsync(deleteConfirmRunId);
      // If we deleted the selected run, clear selection
      if (deleteConfirmRunId === selectedRunId) {
        onSelectRun(null);
      }
      setDeleteConfirmRunId(null);
    }
  };

  // Handle card click
  const handleCardClick = (run: AnalysisRun) => {
    // Don't allow selecting processing runs
    if (run.status === "processing") return;
    onSelectRun(run.run_id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">Loading runs...</span>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 text-sm">
        No analysis runs yet. Run Due Diligence from the Dashboard to create one.
      </div>
    );
  }

  return (
    <>
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Analysis Runs
        </h3>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {runs.map((run) => {
            const isSelected = run.run_id === selectedRunId;
            const isProcessing = run.status === "processing";
            const isEditing = editingRunId === run.run_id;

            return (
              <motion.div
                key={run.run_id}
                whileHover={!isProcessing ? { scale: 1.02 } : undefined}
                whileTap={!isProcessing ? { scale: 0.98 } : undefined}
                onClick={() => handleCardClick(run)}
                className={`
                  flex-shrink-0 min-w-[200px] max-w-[280px] p-3 rounded-lg border-2 transition-colors
                  ${isProcessing
                    ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700 cursor-not-allowed opacity-75"
                    : isSelected
                    ? "bg-blue-50 dark:bg-blue-900/20 border-blue-500 dark:border-blue-400 cursor-pointer"
                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 cursor-pointer"
                  }
                `}
              >
                {/* Header with name and actions */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  {isEditing ? (
                    <div className="flex items-center gap-1 flex-1">
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-7 text-sm"
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit(e as any);
                          if (e.key === "Escape") handleCancelEdit(e as any);
                        }}
                        autoFocus
                      />
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0"
                        onClick={handleSaveEdit}
                        disabled={updateRun.isPending}
                      >
                        <Check className="w-3 h-3 text-green-600" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0"
                        onClick={handleCancelEdit}
                      >
                        <X className="w-3 h-3 text-gray-500" />
                      </Button>
                    </div>
                  ) : (
                    <>
                      <h4 className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate flex-1">
                        {run.name}
                      </h4>
                      {!isProcessing && (
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={(e) => handleStartEdit(run, e)}
                          >
                            <Edit2 className="w-3 h-3 text-gray-400 hover:text-gray-600" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteConfirmRunId(run.run_id);
                            }}
                          >
                            <Trash2 className="w-3 h-3 text-gray-400 hover:text-red-500" />
                          </Button>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Date */}
                <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mb-2">
                  <Calendar className="w-3 h-3" />
                  <span>{formatDate(run.created_at)}</span>
                </div>

                {/* Status / Stats */}
                {isProcessing ? (
                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-xs font-medium">Still Processing</span>
                  </div>
                ) : (
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    {run.total_documents} docs • {run.findings_total} findings
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteConfirmRunId} onOpenChange={() => setDeleteConfirmRunId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Analysis Run?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this run and all its findings. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteRun.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : null}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
