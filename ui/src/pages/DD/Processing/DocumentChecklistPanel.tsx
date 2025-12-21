/**
 * Document Checklist Panel
 *
 * Displays documents with readability status, checkboxes for selection,
 * and actions for failed documents (replace/delete).
 */
import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Loader2,
  RefreshCw,
  Trash2,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface DocumentItem {
  document_id: string;
  original_file_name: string;
  type: string;
  readability_status: "pending" | "checking" | "ready" | "failed";
  readability_error?: string | null;
  processing_status?: string;
  size_in_bytes?: number;
}

interface DocumentChecklistPanelProps {
  documents: DocumentItem[];
  selectedDocIds: Set<string>;
  onSelectionChange: (docIds: Set<string>) => void;
  onReplaceDocument?: (docId: string) => void;
  onDeleteDocument?: (docId: string) => void;
  onRecheckReadability?: (docIds?: string[]) => void;
  isCheckingReadability?: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
}

const statusConfig = {
  pending: {
    icon: <div className="w-4 h-4 rounded-full border-2 border-gray-300" />,
    color: "text-gray-400",
    bg: "",
    label: "Pending",
  },
  checking: {
    icon: <Loader2 className="w-4 h-4 animate-spin text-blue-500" />,
    color: "text-blue-500",
    bg: "",
    label: "Checking",
  },
  ready: {
    icon: <Check className="w-4 h-4 text-green-600" />,
    color: "text-green-600",
    bg: "",
    label: "Ready",
  },
  failed: {
    icon: <X className="w-4 h-4 text-red-600" />,
    color: "text-red-600",
    bg: "bg-red-50",
    label: "Failed",
  },
};

export const DocumentChecklistPanel: React.FC<DocumentChecklistPanelProps> = ({
  documents,
  selectedDocIds,
  onSelectionChange,
  onReplaceDocument,
  onDeleteDocument,
  onRecheckReadability,
  isCheckingReadability = false,
  isCollapsed = false,
  onToggleCollapse,
  className = "",
}) => {
  // Filter out original/ZIP files - only show processable documents
  const processableDocuments = useMemo(() => {
    return documents.filter(
      (doc) =>
        !doc.original_file_name?.endsWith(".zip") &&
        doc.readability_status !== undefined
    );
  }, [documents]);

  // Summary counts
  const summary = useMemo(() => {
    return processableDocuments.reduce(
      (acc, doc) => {
        const status = doc.readability_status || "pending";
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      },
      { pending: 0, checking: 0, ready: 0, failed: 0 } as Record<string, number>
    );
  }, [processableDocuments]);

  // Documents that can be selected (ready or failed, not pending/checking)
  const selectableDocuments = processableDocuments.filter(
    (d) => d.readability_status === "ready" || d.readability_status === "failed"
  );
  const readyDocuments = processableDocuments.filter(
    (d) => d.readability_status === "ready"
  );
  const allSelectableSelected =
    selectableDocuments.length > 0 &&
    selectableDocuments.every((d) => selectedDocIds.has(d.document_id));
  const someSelected =
    selectableDocuments.some((d) => selectedDocIds.has(d.document_id)) &&
    !allSelectableSelected;

  // Handle select all toggle
  const handleSelectAll = () => {
    if (allSelectableSelected) {
      // Deselect all
      onSelectionChange(new Set());
    } else {
      // Select all selectable documents (ready + failed)
      const selectableIds = new Set(selectableDocuments.map((d) => d.document_id));
      onSelectionChange(selectableIds);
    }
  };

  // Handle individual document toggle
  const handleToggleDocument = (docId: string) => {
    const newSelection = new Set(selectedDocIds);
    if (newSelection.has(docId)) {
      newSelection.delete(docId);
    } else {
      newSelection.add(docId);
    }
    onSelectionChange(newSelection);
  };

  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg overflow-hidden transition-shadow hover:shadow-xl",
        className
      )}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-700 dark:to-gray-700 border-b border-gray-200 dark:border-gray-600 cursor-pointer"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            Documents ({processableDocuments.length})
          </h3>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {/* Status Summary */}
          <div className="flex items-center gap-2">
            {summary.ready > 0 && (
              <span className="flex items-center gap-1 text-green-600">
                <Check className="w-3 h-3" />
                {summary.ready}
              </span>
            )}
            {summary.failed > 0 && (
              <span className="flex items-center gap-1 text-red-600">
                <X className="w-3 h-3" />
                {summary.failed}
              </span>
            )}
            {(summary.checking > 0 || isCheckingReadability) && (
              <span className="flex items-center gap-1 text-blue-500">
                <Loader2 className="w-3 h-3 animate-spin" />
                {summary.checking > 0 ? summary.checking : "Checking..."}
              </span>
            )}
          </div>
          {/* Recheck Button */}
          {onRecheckReadability && (
            <Button
              size="sm"
              className="h-7 px-3 text-xs rounded-full bg-green-600 hover:bg-green-700 text-white"
              onClick={(e) => {
                e.stopPropagation();
                // If docs are selected, only recheck those; otherwise recheck all
                const selectedArray = Array.from(selectedDocIds);
                onRecheckReadability(selectedArray.length > 0 ? selectedArray : undefined);
              }}
              disabled={isCheckingReadability}
            >
              <RefreshCw
                className={cn(
                  "w-3.5 h-3.5 mr-1 text-white",
                  isCheckingReadability && "animate-spin"
                )}
              />
              {isCheckingReadability ? "Checking..." : "Run Doc Readability Check"}
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <AnimatePresence initial={false}>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Select All Row */}
            <div className="px-4 py-2.5 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 flex items-center gap-2">
              <Checkbox
                checked={someSelected ? "indeterminate" : allSelectableSelected}
                onCheckedChange={handleSelectAll}
                disabled={selectableDocuments.length === 0}
              />
              <span className="text-sm text-gray-600">
                {allSelectableSelected
                  ? "Deselect All"
                  : `Select All (${readyDocuments.length} ready${summary.failed > 0 ? `, ${summary.failed} failed` : ""})`}
              </span>
            </div>

            {/* Document List */}
            <div className="max-h-[400px] overflow-y-auto">
              {processableDocuments.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-500">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No documents to process</p>
                </div>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {processableDocuments.map((doc) => {
                    const status =
                      statusConfig[doc.readability_status] ||
                      statusConfig.pending;
                    const isReady = doc.readability_status === "ready";
                    const isFailed = doc.readability_status === "failed";

                    return (
                      <li
                        key={doc.document_id}
                        className={cn(
                          "px-4 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors",
                          status.bg,
                          isFailed && "border-l-4 border-l-red-500"
                        )}
                      >
                        {/* Checkbox - enabled for ready and failed docs, disabled for pending/checking */}
                        <Checkbox
                          checked={selectedDocIds.has(doc.document_id)}
                          onCheckedChange={() =>
                            handleToggleDocument(doc.document_id)
                          }
                          disabled={doc.readability_status === "pending" || doc.readability_status === "checking"}
                        />

                        {/* Status Icon */}
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="flex-shrink-0">{status.icon}</div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>
                                {status.label}
                                {isFailed && doc.readability_error && (
                                  <>: {doc.readability_error}</>
                                )}
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        {/* Document Info */}
                        <div className="flex-1 min-w-0">
                          <p
                            className={cn(
                              "text-sm truncate",
                              isFailed ? "text-red-700" : "text-gray-900"
                            )}
                            title={doc.original_file_name}
                          >
                            {doc.original_file_name}
                          </p>
                          {isFailed && doc.readability_error && (
                            <p className="text-xs text-red-600 truncate mt-0.5">
                              {doc.readability_error}
                            </p>
                          )}
                        </div>

                        {/* File Type Badge */}
                        <span className="text-xs text-gray-400 uppercase flex-shrink-0">
                          {doc.type}
                        </span>

                        {/* Actions for Failed Documents */}
                        {isFailed && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            {onReplaceDocument && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        onReplaceDocument(doc.document_id);
                                      }}
                                    >
                                      <RefreshCw className="w-3.5 h-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Replace document</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                            {onDeleteDocument && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteDocument(doc.document_id);
                                      }}
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Remove document</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {/* Footer Summary */}
            {summary.failed > 0 && (
              <div className="px-4 py-2.5 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800 flex items-center gap-2 text-sm text-red-700 dark:text-red-400">
                <AlertTriangle className="w-4 h-4" />
                <span>
                  {summary.failed} document{summary.failed !== 1 ? "s" : ""}{" "}
                  failed readability check
                </span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DocumentChecklistPanel;
