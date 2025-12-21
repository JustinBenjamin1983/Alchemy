/**
 * OrganisationReview Component
 *
 * Displays the AI-organised folder structure for user review before processing.
 * Shows:
 * - Category distribution chart with expandable folders
 * - Documents in each folder
 * - Documents needing review (low confidence)
 * - Approve/Reject buttons for organisation
 *
 * Phase 2 of Document Organisation.
 */
import React, { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderOpen,
  AlertTriangle,
  Check,
  X,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  FileText,
  ArrowRight,
  File,
  MoreHorizontal,
  ArrowRightLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { TRANSACTION_TYPE_INFO, TransactionTypeCode } from "../Wizard/types";

// ============================================================================
// Types
// ============================================================================

export interface CategoryCount {
  category: string;
  displayName: string;
  count: number;
  relevance: "critical" | "high" | "medium" | "low" | "n/a";
}

export interface NeedsReviewDocument {
  id: string;
  name: string;
  suggestedCategory: string;
  confidence: number;
  reason?: string;
}

export interface CategoryDocument {
  id: string;
  name: string;
  type?: string;
  confidence?: number;
  subcategory?: string;
}

export interface OrganisationReviewProps {
  ddId: string;
  status: "classified" | "organising" | "organised" | "failed";
  totalDocuments: number;
  classifiedCount: number;
  needsReviewCount: number;
  categoryDistribution: CategoryCount[];
  documentsNeedingReview: NeedsReviewDocument[];
  documentsByCategory?: Record<string, CategoryDocument[]>;
  transactionType?: string | null;
  isLoading?: boolean;
  isMovingDocument?: boolean;
  onApprove: () => void;
  onReorganise: () => void;
  onDocumentClick?: (docId: string) => void;
  onMoveDocument?: (docId: string, fromCategory: string, toCategory: string) => void;
}

// ============================================================================
// Relevance Configuration
// ============================================================================

const RELEVANCE_CONFIG: Record<
  string,
  { color: string; bgColor: string; borderColor: string }
> = {
  critical: {
    color: "text-red-700 dark:text-red-400",
    bgColor: "bg-red-100 dark:bg-red-900/30",
    borderColor: "border-red-300 dark:border-red-800",
  },
  high: {
    color: "text-orange-700 dark:text-orange-400",
    bgColor: "bg-orange-100 dark:bg-orange-900/30",
    borderColor: "border-orange-300 dark:border-orange-800",
  },
  medium: {
    color: "text-blue-700 dark:text-blue-400",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
    borderColor: "border-blue-300 dark:border-blue-800",
  },
  low: {
    color: "text-gray-600 dark:text-gray-400",
    bgColor: "bg-gray-100 dark:bg-gray-800",
    borderColor: "border-gray-300 dark:border-gray-700",
  },
  "n/a": {
    color: "text-amber-700 dark:text-amber-400",
    bgColor: "bg-amber-100 dark:bg-amber-900/30",
    borderColor: "border-amber-300 dark:border-amber-800",
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

function getCategoryDisplayName(category: string): string {
  // Convert "01_Corporate" to "Corporate"
  const parts = category.split("_");
  if (parts.length > 1) {
    return parts.slice(1).join(" ");
  }
  return category;
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 80) return "text-green-600";
  if (confidence >= 60) return "text-amber-600";
  return "text-red-600";
}

// ============================================================================
// Category Bar Component
// ============================================================================

interface CategoryBarProps {
  category: CategoryCount;
  documents?: CategoryDocument[];
  allCategories: CategoryCount[];
  isExpanded: boolean;
  onToggle: () => void;
  onDocumentClick?: (docId: string) => void;
  onMoveDocument?: (docId: string, fromCategory: string, toCategory: string) => void;
}

const CategoryBar: React.FC<CategoryBarProps> = ({
  category,
  documents = [],
  allCategories,
  isExpanded,
  onToggle,
  onDocumentClick,
  onMoveDocument,
}) => {
  return (
    <div className="rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
      {/* Category Header */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex items-center gap-3 p-2 cursor-pointer transition-all hover:shadow-sm bg-gray-100 dark:bg-gray-800"
        onClick={onToggle}
      >
        {/* Expand/Collapse Chevron */}
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronRight className="w-4 h-4 text-gray-500" />
        </motion.div>

        <FolderOpen className="w-4 h-4 flex-shrink-0 text-gray-600 dark:text-gray-400" />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium truncate text-gray-700 dark:text-gray-300">
              {category.displayName}
            </span>
            <Badge
              variant="secondary"
              className="ml-2 text-xs text-gray-600 dark:text-gray-400 bg-gray-200 dark:bg-gray-700"
            >
              {category.count}
            </Badge>
          </div>
        </div>
      </motion.div>

      {/* Expanded Document List */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="bg-white/50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
              {documents.length > 0 ? (
                <div className="py-1">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-2 px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
                    >
                      <File className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                      <span
                        className="text-xs text-gray-700 dark:text-gray-300 truncate flex-1 cursor-pointer"
                        onClick={() => onDocumentClick?.(doc.id)}
                      >
                        {doc.name}
                      </span>
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
                            <TooltipContent side="left">
                              <p className="text-xs">AI classification confidence</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                      {/* Move to dropdown */}
                      {onMoveDocument && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              className="p-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 shadow-sm"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <MoreHorizontal className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuLabel className="text-xs">Move to folder</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            {allCategories
                              .filter((cat) => cat.category !== category.category)
                              .map((targetCat) => (
                                <DropdownMenuItem
                                  key={targetCat.category}
                                  className="text-xs cursor-pointer"
                                  onClick={() => onMoveDocument(doc.id, category.category, targetCat.category)}
                                >
                                  <ArrowRightLeft className="w-3 h-3 mr-2" />
                                  {targetCat.displayName}
                                </DropdownMenuItem>
                              ))}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-4 py-3 text-xs text-gray-500 italic text-center">
                  No documents in this folder
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ============================================================================
// Needs Review Card Component
// ============================================================================

interface NeedsReviewCardProps {
  document: NeedsReviewDocument;
  onClick?: () => void;
}

const NeedsReviewCard: React.FC<NeedsReviewCardProps> = ({
  document,
  onClick,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 p-3 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
      onClick={onClick}
    >
      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
          {document.name}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Suggested:
          </span>
          <Badge variant="outline" className="text-xs">
            {getCategoryDisplayName(document.suggestedCategory)}
          </Badge>
          <span
            className={cn(
              "text-xs font-medium",
              getConfidenceColor(document.confidence)
            )}
          >
            {document.confidence}%
          </span>
        </div>
      </div>

      <ArrowRight className="w-4 h-4 text-gray-400" />
    </motion.div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const OrganisationReview: React.FC<OrganisationReviewProps> = ({
  ddId,
  status,
  totalDocuments,
  classifiedCount,
  needsReviewCount,
  categoryDistribution,
  documentsNeedingReview,
  documentsByCategory = {},
  transactionType,
  isLoading = false,
  isMovingDocument = false,
  onApprove,
  onReorganise,
  onDocumentClick,
  onMoveDocument,
}) => {
  // Get transaction type info for display
  const typeCode = transactionType as TransactionTypeCode | undefined;
  const typeInfo = typeCode ? TRANSACTION_TYPE_INFO[typeCode] : null;

  // Track which categories are expanded
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

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

  // Separate "Needs Review" from other categories
  const { needsReviewCategory, otherCategories } = useMemo(() => {
    const needsReview = categoryDistribution.find(
      (c) => c.category === "99_Needs_Review"
    );
    const others = categoryDistribution.filter(
      (c) => c.category !== "99_Needs_Review"
    );
    return { needsReviewCategory: needsReview, otherCategories: others };
  }, [categoryDistribution]);

  // Status message
  const statusMessage = useMemo(() => {
    switch (status) {
      case "classified":
        return "Documents have been classified. Click 'Organise' to create folders.";
      case "organising":
        return "Creating folders and organising documents...";
      case "organised":
        return "Documents have been organised into folders. Review and approve to continue.";
      case "failed":
        return "Organisation failed. Please try again.";
      default:
        return "";
    }
  }, [status]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50 dark:bg-gray-800/50">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Folder Organisation Review
            </h3>
            {typeInfo && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="outline"
                      className="text-xs py-0 px-1.5 bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 cursor-help"
                    >
                      <span className="mr-1">{typeInfo.icon}</span>
                      {typeInfo.name}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p className="text-xs font-medium">Blueprint: {typeInfo.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{typeInfo.description}</p>
                    <p className="text-xs text-blue-600 mt-1">Folders are organised based on this transaction type.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {statusMessage}
          </p>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs">
          <div className="text-center">
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {classifiedCount}
            </div>
            <div className="text-gray-500 dark:text-gray-400">Classified</div>
          </div>
          {needsReviewCount > 0 && (
            <div className="text-center">
              <div className="text-lg font-bold text-amber-600">
                {needsReviewCount}
              </div>
              <div className="text-amber-600">Need Review</div>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Category Distribution */}
          <section>
            <h4 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-3">
              Folder Distribution
            </h4>
            <div className="space-y-2">
              <AnimatePresence>
                {otherCategories.map((category, index) => (
                  <motion.div
                    key={category.category}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <CategoryBar
                      category={category}
                      documents={documentsByCategory[category.category] || []}
                      allCategories={categoryDistribution}
                      isExpanded={expandedCategories.has(category.category)}
                      onToggle={() => toggleCategory(category.category)}
                      onDocumentClick={onDocumentClick}
                      onMoveDocument={onMoveDocument}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </section>

          {/* Needs Review Section */}
          {needsReviewCategory && needsReviewCategory.count > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <h4 className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide">
                  Needs Review ({needsReviewCategory.count})
                </h4>
              </div>

              <div className="p-3 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10">
                <p className="text-xs text-amber-700 dark:text-amber-400 mb-3">
                  These documents have low classification confidence and may
                  need manual review.
                </p>

                {documentsNeedingReview.length > 0 ? (
                  <div className="space-y-2">
                    {documentsNeedingReview.slice(0, 5).map((doc) => (
                      <NeedsReviewCard
                        key={doc.id}
                        document={doc}
                        onClick={() => onDocumentClick?.(doc.id)}
                      />
                    ))}
                    {documentsNeedingReview.length > 5 && (
                      <p className="text-xs text-center text-amber-600 dark:text-amber-400 pt-2">
                        +{documentsNeedingReview.length - 5} more documents
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                    Document details loading...
                  </p>
                )}
              </div>
            </section>
          )}

          {/* Empty state */}
          {categoryDistribution.length === 0 && !isLoading && (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No documents have been classified yet
              </p>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer Actions */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-t bg-gray-50 dark:bg-gray-800/50">
        <Button
          variant="outline"
          size="sm"
          onClick={onReorganise}
          disabled={isLoading || status === "organising"}
        >
          <RefreshCw
            className={cn("w-4 h-4 mr-2", isLoading && "animate-spin")}
          />
          Re-organise
        </Button>

        <div className="flex items-center gap-2">
          {needsReviewCount > 0 && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    {needsReviewCount} need review
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  You can still approve, but these documents may need manual
                  review
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          <Button
            size="sm"
            onClick={onApprove}
            disabled={
              isLoading ||
              status === "organising" ||
              categoryDistribution.length === 0
            }
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            <Check className="w-4 h-4 mr-2" />
            Approve & Continue
          </Button>
        </div>
      </div>
    </div>
  );
};

export default OrganisationReview;
