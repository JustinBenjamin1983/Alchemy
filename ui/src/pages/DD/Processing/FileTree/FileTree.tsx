/**
 * FileTree Component
 *
 * Main container for VS Code-style file tree.
 * Supports two modes:
 * 1. Classification mode: Shows AI-proposed categories with move/approve functionality
 * 2. Normal mode: Shows actual folder structure with selection/readability
 */
import React, { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Loader2,
  RefreshCw,
  Upload,
  FolderPlus,
  Folder,
  FileText,
  MoreHorizontal,
  ExternalLink,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { Trash2, Plus, ArrowRight, Pencil } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

// Hooks
import { useGetDD } from "@/hooks/useGetDD";
import { useMutateDDFolderAdd } from "@/hooks/useMutateDDFolderAdd";
import { useMutateDDFolderDelete } from "@/hooks/useMutateDDFolderDelete";
import { useMutateDDFileMove } from "@/hooks/useMutateDDFileMove";
import { useMutateDDFileRename } from "@/hooks/useMutateDDFileRename";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import { BlueprintRequirements, CategoryRequirements } from "@/hooks/useBlueprintRequirements";

// Local components
import { FileTreeProvider } from "./FileTreeContext";
import { FileTreeNode } from "./FileTreeNode";
import { FileTreeContextMenu } from "./FileTreeContextMenu";
import { FileTreeUploadZone } from "./FileTreeUploadZone";
import { FileTreeHistory } from "./FileTreeHistory";
import { TreeNode, FolderFromAPI } from "./types";
import { buildTreeFromFolders, countFiles, countFilesByStatus } from "./utils";

// Transaction type info for badge display
import { TRANSACTION_TYPE_INFO, TransactionTypeCode } from "../../Wizard/types";

// ============================================================================
// Types for Classification Mode
// ============================================================================

export interface CategoryCount {
  category: string;
  displayName: string;
  count: number;
  relevance: "critical" | "high" | "medium" | "low" | "n/a";
}

export interface CategoryDocument {
  id: string;
  name: string;
  type?: string;
  confidence?: number;
  subcategory?: string;
  readabilityStatus?: "pending" | "checking" | "ready" | "failed";
  conversionStatus?: "pending" | "converting" | "converted" | "failed" | null;
}

// ============================================================================
// Blueprint Requirements Section Component
// ============================================================================

interface BlueprintRequirementsSectionProps {
  requirements: CategoryRequirements;
  transactionType: string;
  categoryDistribution?: CategoryCount[];
  onMoveDocument?: (docId: string, fromCategory: string, toCategory: string) => void;
  onUploadFiles?: (files: File[], targetFolderId?: string) => void;
}

function BlueprintRequirementsSection({
  requirements,
  transactionType,
  categoryDistribution,
  onMoveDocument,
  onUploadFiles,
}: BlueprintRequirementsSectionProps) {
  // Only show if there are expected documents
  if (!requirements.expected_documents || requirements.expected_documents.length === 0) {
    return null;
  }

  const hasMissing = requirements.missing_documents.length > 0;
  const foundCount = requirements.found_documents.filter(d => d.matched_type).length;
  const totalExpected = requirements.expected_documents.length;

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-gray-600 dark:text-gray-400">
          Expected Documents ({foundCount}/{totalExpected})
        </p>
        {hasMissing && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
            {requirements.missing_documents.length} missing
          </span>
        )}
      </div>
      <div className="space-y-1.5">
        {requirements.expected_documents.map((docType) => {
          const foundDoc = requirements.found_documents.find(
            (d) => d.matched_type === docType
          );
          const isFound = !!foundDoc;
          const isMissing = requirements.missing_documents.includes(docType);

          if (isFound) {
            // Show found document with green checkmark
            return (
              <div
                key={docType}
                className="flex items-center gap-2 text-xs py-1.5 px-2 rounded bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span className="flex-1 text-green-700 dark:text-green-400 font-medium">{docType}</span>
                <span className="text-[10px] text-green-600 dark:text-green-500">Found</span>
              </div>
            );
          }

          // Show missing document as dotted placeholder
          return (
            <div
              key={docType}
              className="flex items-center gap-2 text-xs py-2 px-2 rounded border-2 border-dashed border-amber-300 dark:border-amber-700 bg-amber-50/50 dark:bg-amber-900/10 hover:bg-amber-100/50 dark:hover:bg-amber-900/20 transition-colors cursor-pointer"
              title={`Drop or upload "${docType}" document here`}
            >
              <div className="w-6 h-6 rounded border border-dashed border-amber-400 dark:border-amber-600 flex items-center justify-center flex-shrink-0">
                <FileText className="w-3.5 h-3.5 text-amber-400 dark:text-amber-500" />
              </div>
              <span className="flex-1 text-amber-700 dark:text-amber-400">{docType}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-200/50 text-amber-700 dark:bg-amber-800/50 dark:text-amber-400">
                MISSING
              </span>
            </div>
          );
        })}
      </div>
      {hasMissing && (
        <p className="text-[10px] text-amber-600 dark:text-amber-400 mt-2 italic text-center">
          Drag documents here or upload to fill missing slots
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Component Props
// ============================================================================

interface FileTreeProps {
  ddId: string;
  selectedDocIds: Set<string>;
  onSelectionChange: (docIds: Set<string>) => void;
  onUploadFiles?: (files: File[], targetFolderId?: string) => void;
  onRecheckReadability?: (docIds?: string[]) => void;
  isCheckingReadability?: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;

  // Classification mode props
  isClassificationMode?: boolean;
  transactionType?: string | null;
  categoryDistribution?: CategoryCount[];
  documentsByCategory?: Record<string, CategoryDocument[]>;
  classifiedCount?: number;
  totalDocuments?: number;
  isMovingDocument?: boolean;
  onMoveDocument?: (docId: string, fromCategory: string, toCategory: string) => void;
  onAddCategory?: (categoryName: string) => void;
  onDeleteCategory?: (category: string) => void;
  onRenameCategory?: (category: string, newName: string) => void;

  // Classification action props
  onClassifyDocuments?: (reset: boolean) => void;
  isClassifying?: boolean;

  // Document deletion
  onDeleteDocuments?: (documentIds: string[]) => void;
  isDeletingDocuments?: boolean;

  // Hide header action buttons (when using external ControlBar)
  hideHeaderActions?: boolean;

  // Blueprint requirements for Checkpoint A
  blueprintRequirements?: BlueprintRequirements;
}

// ============================================================================
// Component
// ============================================================================

export function FileTree({
  ddId,
  selectedDocIds,
  onSelectionChange,
  onUploadFiles,
  onRecheckReadability,
  isCheckingReadability = false,
  isCollapsed = false,
  onToggleCollapse,
  className,
  // Classification mode props
  isClassificationMode = false,
  transactionType,
  categoryDistribution = [],
  documentsByCategory = {},
  classifiedCount = 0,
  totalDocuments = 0,
  isMovingDocument = false,
  onMoveDocument,
  onAddCategory,
  onDeleteCategory,
  onRenameCategory,
  // Classification action props
  onClassifyDocuments,
  isClassifying = false,
  // Document deletion
  onDeleteDocuments,
  isDeletingDocuments = false,
  // Hide header actions
  hideHeaderActions = false,
  // Blueprint requirements
  blueprintRequirements,
}: FileTreeProps) {
  // Toast for error notifications
  const { toast } = useToast();

  // Get transaction type info for display
  const typeCode = transactionType as TransactionTypeCode | undefined;
  const typeInfo = typeCode ? TRANSACTION_TYPE_INFO[typeCode] : null;

  // Track expanded categories in classification mode
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Add folder dialog state
  const [showAddFolderDialog, setShowAddFolderDialog] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [folderToDelete, setFolderToDelete] = useState<{ category: string; displayName: string; count: number } | null>(null);
  const [folderToRename, setFolderToRename] = useState<{ category: string; displayName: string } | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [fileToDelete, setFileToDelete] = useState<{ docId: string; name: string; category: string } | null>(null);
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploadTargetFolder, setUploadTargetFolder] = useState<string>("");
  const [pendingUploadFiles, setPendingUploadFiles] = useState<File[]>([]);

  // Selection state for classification mode bulk actions
  const [classificationSelectedDocs, setClassificationSelectedDocs] = useState<Map<string, { docId: string; category: string }>>(new Map());

  // Total document count for select all functionality
  const allDocsCount = useMemo(() => {
    return categoryDistribution.reduce((total, cat) => {
      const docs = documentsByCategory[cat.category] || [];
      return total + docs.length;
    }, 0);
  }, [categoryDistribution, documentsByCategory]);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // Helper to find documents for a category, handling key mismatches
  // e.g., "Commercial" vs "02_Commercial" or "02_Commercial" vs "Commercial"
  const getDocsForCategory = useCallback((category: string): CategoryDocument[] => {
    // Try exact match first
    if (documentsByCategory[category]?.length > 0) {
      return documentsByCategory[category];
    }

    // Normalize the category name (strip number prefix and underscores)
    const normalize = (cat: string) => cat.replace(/^\d+_/, "").replace(/_/g, " ").toLowerCase();
    const normalizedCategory = normalize(category);

    // Search for a matching key in documentsByCategory
    for (const [key, docs] of Object.entries(documentsByCategory)) {
      if (normalize(key) === normalizedCategory && docs.length > 0) {
        return docs;
      }
    }

    return [];
  }, [documentsByCategory]);

  const handleAddFolder = () => {
    if (newFolderName.trim() && onAddCategory) {
      onAddCategory(newFolderName.trim());
      setNewFolderName("");
      setShowAddFolderDialog(false);
    }
  };

  const handleDeleteFolder = () => {
    if (folderToDelete && onDeleteCategory) {
      onDeleteCategory(folderToDelete.category);
      setFolderToDelete(null);
    }
  };

  const handleRenameFolder = () => {
    if (folderToRename && renameValue.trim()) {
      // TODO: Implement folder rename when API is available
      // For now, we can add an onRenameCategory prop if needed
      console.log("Rename folder:", folderToRename.category, "to", renameValue.trim());
      setFolderToRename(null);
      setRenameValue("");
    }
  };

  const handleDeleteFile = () => {
    if (fileToDelete && onDeleteDocuments) {
      onDeleteDocuments([fileToDelete.docId]);
      setFileToDelete(null);
    }
  };

  const handleBulkDelete = () => {
    if (onDeleteDocuments && classificationSelectedDocs.size > 0) {
      const docIds = Array.from(classificationSelectedDocs.keys());
      onDeleteDocuments(docIds);
      setClassificationSelectedDocs(new Map());
    }
    setShowBulkDeleteConfirm(false);
  };

  // Toggle single doc selection
  const toggleDocSelection = (docId: string, category: string) => {
    setClassificationSelectedDocs((prev) => {
      const next = new Map(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.set(docId, { docId, category });
      }
      return next;
    });
  };

  // Toggle all docs in a category
  const toggleCategorySelection = useCallback((category: string) => {
    const docs = getDocsForCategory(category);
    const allSelected = docs.every((doc) => classificationSelectedDocs.has(doc.id));

    setClassificationSelectedDocs((prev) => {
      const next = new Map(prev);
      if (allSelected) {
        // Deselect all in this category
        docs.forEach((doc) => next.delete(doc.id));
      } else {
        // Select all in this category
        docs.forEach((doc) => next.set(doc.id, { docId: doc.id, category }));
      }
      return next;
    });
  }, [getDocsForCategory, classificationSelectedDocs]);

  // Check if all docs in category are selected
  const isCategoryFullySelected = useCallback((category: string) => {
    const docs = getDocsForCategory(category);
    return docs.length > 0 && docs.every((doc) => classificationSelectedDocs.has(doc.id));
  }, [getDocsForCategory, classificationSelectedDocs]);

  // Check if some docs in category are selected
  const isCategoryPartiallySelected = useCallback((category: string) => {
    const docs = getDocsForCategory(category);
    const selectedCount = docs.filter((doc) => classificationSelectedDocs.has(doc.id)).length;
    return selectedCount > 0 && selectedCount < docs.length;
  }, [getDocsForCategory, classificationSelectedDocs]);

  // Bulk move selected docs to a target category
  const handleBulkMove = (targetCategory: string) => {
    if (!onMoveDocument) return;

    classificationSelectedDocs.forEach(({ docId, category }) => {
      if (category !== targetCategory) {
        onMoveDocument(docId, category, targetCategory);
      }
    });

    // Clear selection after move
    setClassificationSelectedDocs(new Map());
  };

  // Data fetching
  const { data: ddData, refetch } = useGetDD(ddId, !!ddId);
  const folders: FolderFromAPI[] = ddData?.folders || [];

  // Mutations
  const mutateFolderAdd = useMutateDDFolderAdd();
  const mutateFolderDelete = useMutateDDFolderDelete();
  const mutateFileMove = useMutateDDFileMove();
  const mutateFileRename = useMutateDDFileRename();
  const mutateGetLink = useMutateGetLink();

  // Local state
  const [isDraggingExternal, setIsDraggingExternal] = useState(false);

  // Build tree from folders
  const treeData = useMemo(
    () => buildTreeFromFolders(folders),
    [folders]
  );

  // Calculate summary counts
  const totalFiles = useMemo(() => countFiles(treeData), [treeData]);
  const statusCounts = useMemo(() => countFilesByStatus(treeData), [treeData]);

  // Actions for context
  const actions = useMemo(
    () => ({
      previewFile: (docId: string) => {
        mutateGetLink.mutate(
          { doc_id: docId, is_dd: true },
          {
            onSuccess: (data) => {
              window.open(data.data.url, "_blank", "noopener,noreferrer");
            },
            onError: (error: any) => {
              console.error("Failed to get document link:", error);
              const errorMessage = error?.response?.data?.message || error?.message || "Unknown error";
              toast({
                title: "Failed to open document",
                description: errorMessage,
                variant: "destructive",
              });
            },
          }
        );
      },
      downloadFile: (docId: string) => {
        mutateGetLink.mutate(
          { doc_id: docId, is_dd: true },
          {
            onSuccess: (data) => {
              // Trigger download
              const link = document.createElement("a");
              link.href = data.data.url;
              link.download = "";
              link.click();
            },
            onError: (error: any) => {
              console.error("Failed to get document link:", error);
              const errorMessage = error?.response?.data?.message || error?.message || "Unknown error";
              toast({
                title: "Failed to download document",
                description: errorMessage,
                variant: "destructive",
              });
            },
          }
        );
      },
      moveFile: (docId: string, fromFolderId: string, toFolderId: string) => {
        mutateFileMove.mutate({
          dd_id: ddId,
          doc_id: docId,
          folder_from_id: fromFolderId,
          folder_to_id: toFolderId,
        });
      },
      renameFile: (docId: string, newName: string) => {
        mutateFileRename.mutate({
          dd_id: ddId,
          doc_id: docId,
          new_doc_name: newName,
        });
      },
      deleteFile: (docId: string) => {
        // TODO: Implement file delete when API is available
        console.log("Delete file:", docId);
      },
      addFolder: (folderName: string, parentFolderId?: string) => {
        mutateFolderAdd.mutate({
          dd_id: ddId,
          folder_name: folderName,
          parent_folder_id: parentFolderId,
        });
      },
      deleteFolder: (folderId: string) => {
        mutateFolderDelete.mutate({
          dd_id: ddId,
          folder_id: folderId,
        });
      },
      renameFolder: (folderId: string, newName: string) => {
        // TODO: Implement folder rename when API is available
        console.log("Rename folder:", folderId, newName);
      },
      uploadFiles: (files: File[], targetFolderId?: string) => {
        onUploadFiles?.(files, targetFolderId);
      },
      refetch: () => refetch(),
    }),
    [
      ddId,
      mutateGetLink,
      mutateFileMove,
      mutateFileRename,
      mutateFolderAdd,
      mutateFolderDelete,
      onUploadFiles,
      refetch,
      toast,
    ]
  );

  // Drag handlers for external files
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes("Files")) {
      setIsDraggingExternal(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set to false if leaving the container entirely
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX;
    const y = e.clientY;
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setIsDraggingExternal(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDraggingExternal(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        onUploadFiles?.(files);
      }
    },
    [onUploadFiles]
  );

  // ============================================================================
  // Classification Mode Render
  // ============================================================================
  if (isClassificationMode) {
    return (
      <div
        className={cn(
          "bg-white dark:bg-gray-800 rounded-xl border border-gray-300 dark:border-gray-600 shadow-lg overflow-hidden flex flex-col",
          className
        )}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b bg-alchemyPrimaryNavyBlue border-gray-700 cursor-pointer"
          onClick={onToggleCollapse}
        >
          <div className="flex items-center gap-3">
            {/* Collapse Chevron */}
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-white/70 flex-shrink-0" />
            ) : (
              <ChevronDown className="w-4 h-4 text-white/70 flex-shrink-0" />
            )}

            {/* Select All Checkbox */}
            {!isCollapsed && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={
                          allDocsCount > 0 && classificationSelectedDocs.size === allDocsCount
                        }
                        ref={(el) => {
                          if (el) {
                            (el as any).indeterminate =
                              classificationSelectedDocs.size > 0 &&
                              classificationSelectedDocs.size < allDocsCount;
                          }
                        }}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            // Select all documents
                            const newSelection = new Map<string, { docId: string; category: string }>();
                            categoryDistribution.forEach((cat) => {
                              const docs = documentsByCategory[cat.category] || [];
                              docs.forEach((doc) => {
                                newSelection.set(doc.id, { docId: doc.id, category: cat.category });
                              });
                            });
                            setClassificationSelectedDocs(newSelection);
                          } else {
                            // Deselect all
                            setClassificationSelectedDocs(new Map());
                          }
                        }}
                        className="h-4 w-4 border-white/50"
                      />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                    <p className="text-xs">
                      {classificationSelectedDocs.size === allDocsCount ? "Deselect all" : "Select all"} documents
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}

            <h3 className="font-medium text-white">
              Documents ({totalDocuments})
            </h3>
            {typeInfo && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <Badge
                        variant="outline"
                        className="text-xs py-0 px-1.5 bg-white/20 border-white/30 text-white cursor-help"
                      >
                        {typeInfo.name}
                      </Badge>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                    <p className="text-xs font-medium">Blueprint: {typeInfo.name}</p>
                    <p className="text-xs text-gray-300 mt-0.5">{typeInfo.description}</p>
                    <p className="text-xs text-blue-300 mt-1">Folders organised based on this transaction type.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>

          {/* Actions - hidden when using external ControlBar */}
          {!hideHeaderActions && (
            <div className="flex items-center gap-3 text-xs">
              {/* Classify Docs Button - always visible */}
              {onClassifyDocuments && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs border-white/30 bg-white/10 text-white hover:bg-white/20 transition-all duration-200 hover:scale-105 hover:shadow-md"
                          onClick={(e) => {
                            e.stopPropagation();
                            onClassifyDocuments(true); // Reset and reclassify all
                          }}
                          disabled={isClassifying}
                        >
                          {isClassifying ? (
                            <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                          ) : (
                            <RefreshCw className="w-3.5 h-3.5 mr-1" />
                          )}
                          {isClassifying ? "Classifying..." : "Classify Docs"}
                        </Button>
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-xs bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                      <p className="text-xs font-medium">AI Document Classification</p>
                      <p className="text-xs text-gray-300 mt-1">
                        Automatically classify all documents into appropriate folders based on their content using AI analysis.
                      </p>
                      <p className="text-xs text-purple-300 mt-1">
                        Click to reclassify all documents.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              {onUploadFiles && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2 text-xs transition-all duration-200 hover:scale-105 hover:shadow-md"
                  onClick={() => {
                    // Reset and show dialog
                    setUploadTargetFolder(categoryDistribution[0]?.category || "");
                    setShowUploadDialog(true);
                  }}
                >
                  <Upload className="w-3.5 h-3.5 mr-1" />
                  Upload
                </Button>
              )}
              {onAddCategory && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2 text-xs transition-all duration-200 hover:scale-105 hover:shadow-md"
                  onClick={() => setShowAddFolderDialog(true)}
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Add Folder
                </Button>
              )}
              {onRecheckReadability && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>
                        <Button
                          size="sm"
                          className="h-7 px-3 text-xs rounded-full bg-green-600 hover:bg-green-700 text-white transition-all duration-200 hover:scale-105 hover:shadow-md"
                          onClick={() => {
                            const selectedArray = Array.from(classificationSelectedDocs.keys());
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
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-xs bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                      <p className="text-xs font-medium">Verify Document Readability</p>
                      <p className="text-xs text-gray-300 mt-1">
                        Checks that all documents can be read and processed by the AI.
                        This is a required step before running Due Diligence analysis.
                      </p>
                      <p className="text-xs text-blue-300 mt-1">
                        {classificationSelectedDocs.size > 0
                          ? `Will check ${classificationSelectedDocs.size} selected document(s)`
                          : "Will check all documents"}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          )}
        </div>

        {/* Collapsible Content */}
        <AnimatePresence initial={false}>
          {!isCollapsed && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col flex-1 overflow-hidden"
            >
        {/* Category List */}
        <ScrollArea className="flex-1 h-[400px]">
          <div className="p-2 space-y-1">
            {categoryDistribution.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <Folder className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No documents classified yet</p>
              </div>
            ) : (
              categoryDistribution.map((cat) => {
                const isExpanded = expandedCategories.has(cat.category);
                const docs = getDocsForCategory(cat.category);

                const isNeedsReview = cat.category === "99_Needs_Review";
                const hasNeedsReviewDocs = isNeedsReview && cat.count > 0;

                return (
                  <div key={cat.category} className="rounded-lg overflow-hidden">
                    {/* Category Row */}
                    <div
                      className={cn(
                        "flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors group/row",
                        hasNeedsReviewDocs
                          ? "bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/30 border-amber-300 dark:border-amber-700"
                          : "bg-gray-100 dark:bg-gray-700/50 hover:bg-gray-200 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600",
                        "border rounded-lg"
                      )}
                      onClick={() => toggleCategory(cat.category)}
                    >
                      {/* Folder checkbox */}
                      {cat.count > 0 && (
                        <Checkbox
                          checked={isCategoryFullySelected(cat.category)}
                          ref={(el) => {
                            if (el) {
                              (el as any).indeterminate = isCategoryPartiallySelected(cat.category);
                            }
                          }}
                          onCheckedChange={() => toggleCategorySelection(cat.category)}
                          onClick={(e) => e.stopPropagation()}
                          className="flex-shrink-0"
                        />
                      )}
                      {cat.count === 0 && <div className="w-4" />}
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      )}
                      {hasNeedsReviewDocs ? (
                        <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                      ) : (
                        <Folder className="w-4 h-4 text-gray-500 flex-shrink-0" />
                      )}
                      <span className={cn(
                        "flex-1 text-sm font-medium truncate",
                        hasNeedsReviewDocs ? "text-amber-700 dark:text-amber-400" : "text-gray-700 dark:text-gray-200"
                      )}>
                        {cat.displayName}
                      </span>
                      <Badge
                        variant="secondary"
                        className={cn(
                          "text-xs",
                          hasNeedsReviewDocs && "bg-amber-200 text-amber-800 dark:bg-amber-800 dark:text-amber-200"
                        )}
                      >
                        {cat.count}
                      </Badge>
                      {/* Folder readability status indicator */}
                      {cat.count > 0 && (() => {
                        const allReady = docs.length > 0 && docs.every(d => d.readabilityStatus === "ready");
                        const anyFailed = docs.some(d => d.readabilityStatus === "failed");
                        const anyChecking = docs.some(d => d.readabilityStatus === "checking");

                        if (allReady) {
                          return (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-200 dark:bg-emerald-800/40">
                                    <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="left" className="bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                                  <p className="text-xs">All {docs.length} document(s) ready</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          );
                        }
                        if (anyFailed) {
                          const failedCount = docs.filter(d => d.readabilityStatus === "failed").length;
                          return (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="flex items-center justify-center w-5 h-5 rounded-full bg-red-100 dark:bg-red-900/30">
                                    <X className="w-3 h-3 text-red-600" />
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="left" className="bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                                  <p className="text-xs">{failedCount} document(s) failed readability</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          );
                        }
                        if (anyChecking) {
                          return (
                            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                          );
                        }
                        return null;
                      })()}
                      {/* Folder 3-dots menu */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 shadow-sm"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setUploadTargetFolder(cat.category);
                              setPendingUploadFiles([]);
                              setShowUploadDialog(true);
                            }}
                          >
                            <Upload className="w-4 h-4 mr-2" />
                            Upload Documents
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setFolderToRename({
                                category: cat.category,
                                displayName: cat.displayName,
                              });
                              setRenameValue(cat.displayName);
                            }}
                          >
                            <Pencil className="w-4 h-4 mr-2" />
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-red-600 focus:text-red-600"
                            onClick={(e) => {
                              e.stopPropagation();
                              setFolderToDelete({
                                category: cat.category,
                                displayName: cat.displayName,
                                count: cat.count,
                              });
                            }}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    {/* Expanded Documents */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.15 }}
                          className="overflow-hidden"
                        >
                          <div className="ml-6 mt-1 space-y-2 pb-2">
                            {/* Blueprint Expected Documents Section */}
                            {blueprintRequirements?.requirements?.[cat.category] && !isNeedsReview && (
                              <BlueprintRequirementsSection
                                requirements={blueprintRequirements.requirements[cat.category]}
                                transactionType={blueprintRequirements.transaction_name || transactionType || ""}
                                categoryDistribution={categoryDistribution}
                                onMoveDocument={onMoveDocument}
                                onUploadFiles={onUploadFiles}
                              />
                            )}

                            {/* Special banner for 99_Needs_Review folder */}
                            {hasNeedsReviewDocs && (
                              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3 mb-2">
                                <div className="flex items-start gap-2">
                                  <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                                  <div className="text-xs">
                                    <p className="font-medium text-amber-800 dark:text-amber-300">
                                      These documents require manual classification
                                    </p>
                                    <p className="text-amber-700 dark:text-amber-400 mt-1">
                                      Use the "Move to folder" option in each document's menu to assign it to the correct category folder.
                                      Readability check is blocked until all documents are classified.
                                    </p>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Documents List */}
                            {docs.length > 0 && (
                              <div className="space-y-0.5">
                                {docs.map((doc) => (
                              <div
                                key={doc.id}
                                className={cn(
                                  "flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700/50 group",
                                  classificationSelectedDocs.has(doc.id) && "bg-blue-50 dark:bg-blue-900/20"
                                )}
                              >
                                <Checkbox
                                  checked={classificationSelectedDocs.has(doc.id)}
                                  onCheckedChange={() => toggleDocSelection(doc.id, cat.category)}
                                  className="flex-shrink-0"
                                />
                                {/* Readability Status Indicator */}
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <span className="flex-shrink-0">
                                        {doc.readabilityStatus === "ready" && (
                                          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-200 dark:bg-emerald-800/40">
                                            <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                                          </span>
                                        )}
                                        {doc.readabilityStatus === "failed" && (
                                          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-red-100 dark:bg-red-900/30">
                                            <X className="w-3 h-3 text-red-600" />
                                          </span>
                                        )}
                                        {doc.readabilityStatus === "checking" && (
                                          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/30">
                                            <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
                                          </span>
                                        )}
                                        {(!doc.readabilityStatus || doc.readabilityStatus === "pending") && (
                                          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700">
                                            <FileText className="w-3 h-3 text-gray-400" />
                                          </span>
                                        )}
                                      </span>
                                    </TooltipTrigger>
                                    <TooltipContent side="left" className="bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                                      <p className="text-xs">
                                        {doc.readabilityStatus === "ready" && "Document readable"}
                                        {doc.readabilityStatus === "failed" && "Document not readable"}
                                        {doc.readabilityStatus === "checking" && "Checking readability..."}
                                        {(!doc.readabilityStatus || doc.readabilityStatus === "pending") && "Readability not checked"}
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <span className="flex-1 text-xs text-gray-600 dark:text-gray-300 truncate">
                                  {doc.name}
                                </span>

                                {/* Confidence Score */}
                                {doc.confidence !== undefined && (
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <span
                                          className={cn(
                                            "text-xs font-medium cursor-help",
                                            doc.confidence >= 80
                                              ? "text-green-600"
                                              : doc.confidence >= 60
                                              ? "text-amber-600"
                                              : "text-red-600"
                                          )}
                                        >
                                          {doc.confidence}%
                                        </span>
                                      </TooltipTrigger>
                                      <TooltipContent side="left" className="bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                                        <p className="text-xs">AI classification confidence</p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                )}

                                {/* Conversion indicator - shows when doc was converted to PDF */}
                                {doc.conversionStatus === "converted" && (
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <span className="inline-flex items-center gap-0.5 text-[9px] px-1 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 font-medium cursor-help">
                                          <Check className="w-2.5 h-2.5" />
                                          PDF Converted
                                        </span>
                                      </TooltipTrigger>
                                      <TooltipContent side="left" className="bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                                        <p className="text-xs">Converted to PDF for analysis</p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                )}

                                {/* File 3-dots menu */}
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <button
                                      className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 shadow-sm"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <MoreHorizontal className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                                    </button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end" className="w-56">
                                    {/* View and Download options */}
                                    <DropdownMenuItem
                                      onClick={() => actions.previewFile(doc.id)}
                                    >
                                      <ExternalLink className="w-4 h-4 mr-2" />
                                      View in new tab
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => actions.downloadFile(doc.id)}
                                    >
                                      <Download className="w-4 h-4 mr-2" />
                                      Download
                                    </DropdownMenuItem>
                                    {onMoveDocument && <DropdownMenuSeparator />}
                                    {onMoveDocument && (
                                      <DropdownMenuSub>
                                        <DropdownMenuSubTrigger>
                                          <Folder className="w-4 h-4 mr-2" />
                                          Move to folder
                                        </DropdownMenuSubTrigger>
                                        <DropdownMenuSubContent className="max-h-[300px] overflow-y-auto">
                                          {categoryDistribution
                                            .filter((c) => c.category !== cat.category)
                                            .map((targetCat) => (
                                              <DropdownMenuItem
                                                key={targetCat.category}
                                                onClick={() => {
                                                  onMoveDocument(
                                                    doc.id,
                                                    cat.category,
                                                    targetCat.category
                                                  );
                                                }}
                                                disabled={isMovingDocument}
                                              >
                                                <Folder className="w-4 h-4 mr-2 text-gray-400" />
                                                {targetCat.displayName}
                                              </DropdownMenuItem>
                                            ))}
                                        </DropdownMenuSubContent>
                                      </DropdownMenuSub>
                                    )}
                                    {onMoveDocument && <DropdownMenuSeparator />}
                                    <DropdownMenuItem
                                      className="text-red-600 focus:text-red-600"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setFileToDelete({
                                          docId: doc.id,
                                          name: doc.name,
                                          category: cat.category,
                                        });
                                      }}
                                    >
                                      <Trash2 className="w-4 h-4 mr-2" />
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                                ))}
                              </div>
                            )}

                            {/* Empty state when no docs and no expected docs */}
                            {docs.length === 0 && !blueprintRequirements?.requirements?.[cat.category]?.expected_documents?.length && (
                              <div className="text-center py-3 text-gray-500 text-xs">
                                <FileText className="w-5 h-5 mx-auto mb-1 opacity-50" />
                                <p>No documents in this folder</p>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>

        {/* Bulk Action Bar - shown when items are selected */}
        <AnimatePresence>
          {classificationSelectedDocs.size > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <div className="px-4 py-2 border-t border-b bg-blue-50 dark:bg-blue-900/20 flex items-center justify-between">
                <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
                  {classificationSelectedDocs.size} document{classificationSelectedDocs.size > 1 ? "s" : ""} selected
                </span>
                <div className="flex items-center gap-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="sm" className="h-7 text-xs bg-blue-600 hover:bg-blue-700 transition-all duration-200 hover:scale-105 hover:shadow-md">
                        <ArrowRight className="w-3.5 h-3.5 mr-1" />
                        Move to folder
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="max-h-[300px] overflow-y-auto">
                      {categoryDistribution.map((targetCat) => (
                        <DropdownMenuItem
                          key={targetCat.category}
                          onClick={() => handleBulkMove(targetCat.category)}
                          disabled={isMovingDocument}
                        >
                          <Folder className="w-4 h-4 mr-2 text-gray-400" />
                          {targetCat.displayName}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="h-7 text-xs transition-all duration-200 hover:scale-105 hover:shadow-md"
                    onClick={() => setShowBulkDeleteConfirm(true)}
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                    Delete
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs text-gray-500 hover:text-gray-700 transition-all duration-200 hover:scale-105"
                    onClick={() => setClassificationSelectedDocs(new Map())}
                  >
                    Clear
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Add Folder Dialog */}
        <Dialog open={showAddFolderDialog} onOpenChange={setShowAddFolderDialog}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Add New Folder</DialogTitle>
              <DialogDescription>
                Create a new folder category for document organisation.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Label htmlFor="folderName" className="text-sm font-medium">
                Folder Name
              </Label>
              <Input
                id="folderName"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="e.g., Regulatory Approvals"
                className="mt-1.5"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAddFolder();
                  }
                }}
              />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowAddFolderDialog(false);
                  setNewFolderName("");
                }}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleAddFolder}
                disabled={!newFolderName.trim()}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <FolderPlus className="w-4 h-4 mr-1" />
                Add Folder
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Folder Confirmation Dialog */}
        <Dialog open={!!folderToDelete} onOpenChange={() => setFolderToDelete(null)}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Delete Folder</DialogTitle>
              <DialogDescription>
                {folderToDelete?.count === 0 ? (
                  <>Are you sure you want to delete "{folderToDelete?.displayName}"?</>
                ) : (
                  <>
                    "{folderToDelete?.displayName}" contains {folderToDelete?.count} document(s).
                    Move them to another folder first, or they will be marked as "Needs Review".
                  </>
                )}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFolderToDelete(null)}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDeleteFolder}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete Folder
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Rename Folder Dialog */}
        <Dialog open={!!folderToRename} onOpenChange={() => setFolderToRename(null)}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Rename Folder</DialogTitle>
              <DialogDescription>
                Enter a new name for "{folderToRename?.displayName}".
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Label htmlFor="renameValue" className="text-sm font-medium">
                Folder Name
              </Label>
              <Input
                id="renameValue"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                placeholder="Enter new name"
                className="mt-1.5"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleRenameFolder();
                  }
                }}
              />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFolderToRename(null);
                  setRenameValue("");
                }}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleRenameFolder}
                disabled={!renameValue.trim() || renameValue.trim() === folderToRename?.displayName}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <Pencil className="w-4 h-4 mr-1" />
                Rename
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete File Confirmation Dialog */}
        <Dialog open={!!fileToDelete} onOpenChange={() => setFileToDelete(null)}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Delete Document</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete "{fileToDelete?.name}"? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFileToDelete(null)}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDeleteFile}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Bulk Delete Confirmation Dialog */}
        <Dialog open={showBulkDeleteConfirm} onOpenChange={setShowBulkDeleteConfirm}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Delete {classificationSelectedDocs.size} Document{classificationSelectedDocs.size > 1 ? "s" : ""}</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete {classificationSelectedDocs.size} selected document{classificationSelectedDocs.size > 1 ? "s" : ""}? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowBulkDeleteConfirm(false)}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleBulkDelete}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Delete {classificationSelectedDocs.size} Document{classificationSelectedDocs.size > 1 ? "s" : ""}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Upload with Folder Selection Dialog */}
        <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
          <DialogContent className="sm:max-w-[450px] max-h-[85vh] flex flex-col overflow-hidden">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-blue-600" />
                Upload Documents
              </DialogTitle>
              <DialogDescription>
                {uploadTargetFolder
                  ? `Upload files to "${categoryDistribution.find((c) => c.category === uploadTargetFolder)?.displayName || uploadTargetFolder}"`
                  : "Select the target folder and choose files to upload."}
              </DialogDescription>
            </DialogHeader>
            <div className="py-4 space-y-4 overflow-y-auto flex-1 min-h-0">
              <div>
                <Label htmlFor="targetFolder" className="text-sm font-medium">
                  Target Folder
                </Label>
                <select
                  id="targetFolder"
                  value={uploadTargetFolder}
                  onChange={(e) => setUploadTargetFolder(e.target.value)}
                  className="mt-1.5 w-full h-9 px-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {categoryDistribution.map((cat) => (
                    <option key={cat.category} value={cat.category}>
                      {cat.displayName}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-sm font-medium">Files</Label>
                <div
                  className={cn(
                    "mt-1.5 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-colors",
                    pendingUploadFiles.length > 0 ? "p-3" : "p-6"
                  )}
                  onClick={() => {
                    const input = document.createElement("input");
                    input.type = "file";
                    input.multiple = true;
                    input.accept = ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt";
                    input.onchange = (e) => {
                      const files = Array.from((e.target as HTMLInputElement).files || []);
                      if (files.length > 0) {
                        setPendingUploadFiles((prev) => [...prev, ...files]);
                      }
                    };
                    input.click();
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    e.currentTarget.classList.add("border-blue-500", "bg-blue-50/50", "dark:bg-blue-900/20");
                  }}
                  onDragLeave={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    e.currentTarget.classList.remove("border-blue-500", "bg-blue-50/50", "dark:bg-blue-900/20");
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    e.currentTarget.classList.remove("border-blue-500", "bg-blue-50/50", "dark:bg-blue-900/20");
                    const files = Array.from(e.dataTransfer.files);
                    if (files.length > 0) {
                      setPendingUploadFiles((prev) => [...prev, ...files]);
                    }
                  }}
                >
                  <Upload className={cn("mx-auto mb-1 text-gray-400", pendingUploadFiles.length > 0 ? "w-5 h-5" : "w-8 h-8 mb-2")} />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {pendingUploadFiles.length > 0 ? "Click to add more files" : "Drag files here or click to browse"}
                  </p>
                  {pendingUploadFiles.length === 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      PDF, DOC, DOCX, XLS, XLSX supported
                    </p>
                  )}
                </div>
                {pendingUploadFiles.length > 0 && (
                  <div className="mt-3 border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-100 dark:divide-gray-800 max-h-[200px] overflow-y-auto">
                    {pendingUploadFiles.map((file, i) => (
                      <div key={i} className="flex items-center justify-between px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-800/50">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          <span className="truncate text-gray-700 dark:text-gray-300">{file.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingUploadFiles((prev) => prev.filter((_, idx) => idx !== i));
                          }}
                          className="ml-2 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-red-500 flex-shrink-0"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowUploadDialog(false);
                  setPendingUploadFiles([]);
                }}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={pendingUploadFiles.length === 0 || !uploadTargetFolder}
                onClick={() => {
                  if (onUploadFiles && pendingUploadFiles.length > 0) {
                    onUploadFiles(pendingUploadFiles, uploadTargetFolder);
                  }
                  setShowUploadDialog(false);
                  setPendingUploadFiles([]);
                }}
                className="transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <Upload className="w-4 h-4 mr-1" />
                Upload {pendingUploadFiles.length > 0 ? `${pendingUploadFiles.length} File(s)` : ""}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // ============================================================================
  // Normal Mode Render
  // ============================================================================
  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl border border-gray-300 dark:border-gray-600 shadow-lg overflow-hidden transition-shadow hover:shadow-xl",
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-alchemyPrimaryNavyBlue border-b border-gray-700 cursor-pointer"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-white/70" />
          ) : (
            <ChevronDown className="w-4 h-4 text-white/70" />
          )}
          <h3 className="font-medium text-white">
            Documents ({totalFiles})
          </h3>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {/* Status Summary */}
          <div className="flex items-center gap-2">
            {statusCounts.ready > 0 && (
              <span className="flex items-center gap-1 text-green-400">
                <Check className="w-3 h-3" />
                {statusCounts.ready}
              </span>
            )}
            {statusCounts.failed > 0 && (
              <span className="flex items-center gap-1 text-red-400">
                <X className="w-3 h-3" />
                {statusCounts.failed}
              </span>
            )}
            {(statusCounts.checking > 0 || isCheckingReadability) && (
              <span className="flex items-center gap-1 text-blue-300">
                <Loader2 className="w-3 h-3 animate-spin" />
                {statusCounts.checking > 0
                  ? statusCounts.checking
                  : "Checking..."}
              </span>
            )}
          </div>

          {/* Header action buttons - hidden when using external ControlBar */}
          {!hideHeaderActions && (
            <>
              {/* Classify Docs Button - always visible */}
              {onClassifyDocuments && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs border-white/30 bg-white/10 text-white hover:bg-white/20 transition-all duration-200 hover:scale-105 hover:shadow-md"
                          onClick={(e) => {
                            e.stopPropagation();
                            onClassifyDocuments(true); // Reset and reclassify all
                          }}
                          disabled={isClassifying}
                        >
                          {isClassifying ? (
                            <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                          ) : (
                            <RefreshCw className="w-3.5 h-3.5 mr-1" />
                          )}
                          {isClassifying ? "Classifying..." : "Classify Docs"}
                        </Button>
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-xs bg-alchemyPrimaryNavyBlue text-white border-alchemyPrimaryNavyBlue">
                      <p className="text-xs font-medium">AI Document Classification</p>
                      <p className="text-xs text-gray-300 mt-1">
                        Automatically classify all documents into appropriate folders based on their content using AI analysis.
                      </p>
                      <p className="text-xs text-purple-300 mt-1">
                        Click to reclassify all documents.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}

              {/* Readability Check Button */}
              {onRecheckReadability && (
                <Button
                  size="sm"
                  className="h-7 px-3 text-xs rounded-full bg-green-600 hover:bg-green-700 text-white"
                  onClick={(e) => {
                    e.stopPropagation();
                    const selectedArray = Array.from(selectedDocIds);
                    onRecheckReadability(
                      selectedArray.length > 0 ? selectedArray : undefined
                    );
                  }}
                  disabled={isCheckingReadability}
                >
                  <RefreshCw
                    className={cn(
                      "w-3.5 h-3.5 mr-1 text-white",
                      isCheckingReadability && "animate-spin"
                    )}
                  />
                  {isCheckingReadability
                    ? "Checking..."
                    : "Run Doc Readability Check"}
                </Button>
              )}
            </>
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
            <FileTreeProvider
              treeData={treeData}
              selectedIds={selectedDocIds}
              onSelectionChange={onSelectionChange}
              actions={actions}
            >
              {/* Tree content */}
              <div className="relative">
                {/* Upload zone overlay */}
                <AnimatePresence>
                  {isDraggingExternal && <FileTreeUploadZone />}
                </AnimatePresence>

                {/* Tree nodes */}
                <ScrollArea className="h-[400px]">
                  <div className="p-2">
                    {treeData.length === 0 ? (
                      <div className="px-4 py-8 text-center text-gray-500">
                        <Upload className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No documents yet</p>
                        <p className="text-xs text-gray-400 mt-1">
                          Drag and drop files here to upload
                        </p>
                      </div>
                    ) : (
                      treeData.map((node) => (
                        <FileTreeNode key={node.id} node={node} />
                      ))
                    )}
                  </div>
                </ScrollArea>
              </div>

              {/* Context menu */}
              <FileTreeContextMenu />
            </FileTreeProvider>

            {/* History section */}
            <FileTreeHistory ddId={ddId} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default FileTree;
