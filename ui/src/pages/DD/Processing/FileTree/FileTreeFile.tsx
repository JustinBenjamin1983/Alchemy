/**
 * FileTreeFile Component
 *
 * Renders a file item in the tree with:
 * - Status indicator (ready/failed/pending/checking)
 * - Confidence indicator (high/medium/low based on AI classification)
 * - File type icon (PDF/DOC/XLS/etc.)
 * - Filename with truncation
 * - File type badge
 */
import React from "react";
import {
  FileText,
  File,
  FileSpreadsheet,
  Presentation,
  Image,
  Check,
  X,
  Circle,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { TreeNode, ReadabilityStatus, ClassificationStatus } from "./types";

// ============================================================================
// File Icon Configuration
// ============================================================================

const FILE_ICON_MAP: Record<
  string,
  { icon: React.ElementType; color: string }
> = {
  pdf: { icon: FileText, color: "text-red-500" },
  doc: { icon: FileText, color: "text-blue-500" },
  docx: { icon: FileText, color: "text-blue-500" },
  xls: { icon: FileSpreadsheet, color: "text-green-600" },
  xlsx: { icon: FileSpreadsheet, color: "text-green-600" },
  csv: { icon: FileSpreadsheet, color: "text-green-600" },
  ppt: { icon: Presentation, color: "text-orange-500" },
  pptx: { icon: Presentation, color: "text-orange-500" },
  txt: { icon: FileText, color: "text-gray-500" },
  rtf: { icon: FileText, color: "text-gray-500" },
  png: { icon: Image, color: "text-purple-500" },
  jpg: { icon: Image, color: "text-purple-500" },
  jpeg: { icon: Image, color: "text-purple-500" },
  gif: { icon: Image, color: "text-purple-500" },
};

const DEFAULT_FILE_ICON = { icon: File, color: "text-gray-400" };

// ============================================================================
// Status Configuration
// ============================================================================

const STATUS_MAP: Record<
  ReadabilityStatus,
  { icon: React.ElementType; color: string; label: string; animate?: boolean }
> = {
  ready: { icon: Check, color: "text-green-600", label: "Ready for analysis" },
  failed: { icon: X, color: "text-red-600", label: "Failed readability check" },
  pending: { icon: Circle, color: "text-gray-400", label: "Pending check" },
  checking: {
    icon: Loader2,
    color: "text-blue-500",
    label: "Checking...",
    animate: true,
  },
};

// ============================================================================
// Confidence Configuration
// ============================================================================

type ConfidenceLevel = "high" | "medium" | "low" | "pending";

function getConfidenceLevel(confidence: number | undefined): ConfidenceLevel {
  if (confidence === undefined || confidence === null) return "pending";
  if (confidence >= 80) return "high";
  if (confidence >= 60) return "medium";
  return "low";
}

const CONFIDENCE_CONFIG: Record<
  ConfidenceLevel,
  { color: string; bgColor: string; label: string }
> = {
  high: {
    color: "text-green-600",
    bgColor: "bg-green-500",
    label: "High confidence classification",
  },
  medium: {
    color: "text-amber-600",
    bgColor: "bg-amber-500",
    label: "Medium confidence - may need review",
  },
  low: {
    color: "text-red-600",
    bgColor: "bg-red-500",
    label: "Low confidence - needs review",
  },
  pending: {
    color: "text-gray-400",
    bgColor: "bg-gray-400",
    label: "Classification pending",
  },
};

// ============================================================================
// Component Props
// ============================================================================

interface FileTreeFileProps {
  node: TreeNode;
  isSelected: boolean;
}

// ============================================================================
// Component
// ============================================================================

export function FileTreeFile({ node, isSelected }: FileTreeFileProps) {
  // Get file icon based on extension
  const fileExt = (node.fileType || "").toLowerCase();
  const fileIconConfig = FILE_ICON_MAP[fileExt] ?? DEFAULT_FILE_ICON;
  const FileIcon = fileIconConfig.icon;

  // Get status config
  const status = node.readabilityStatus || "pending";
  const statusConfig = STATUS_MAP[status];
  const StatusIcon = statusConfig.icon;

  // Get classification confidence config
  const confidenceLevel = getConfidenceLevel(node.aiConfidence);
  const confidenceConfig = CONFIDENCE_CONFIG[confidenceLevel];
  const isClassified = node.classificationStatus === "classified";
  const hasConfidence = node.aiConfidence !== undefined && node.aiConfidence !== null;

  // Build tooltip content for classification
  const classificationTooltip = isClassified
    ? `${confidenceConfig.label}\n${node.aiCategory || "Unknown"} → ${node.aiDocumentType || "Unknown"}\nConfidence: ${node.aiConfidence}%`
    : confidenceConfig.label;

  return (
    <>
      {/* Status indicator */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className={cn("flex-shrink-0", statusConfig.color)}>
              <StatusIcon
                className={cn("w-3.5 h-3.5", statusConfig.animate && "animate-spin")}
              />
            </span>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-xs">
            {statusConfig.label}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Classification confidence indicator */}
      {hasConfidence && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex-shrink-0 ml-1 flex items-center">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    confidenceConfig.bgColor
                  )}
                />
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs max-w-xs whitespace-pre-line">
              {classificationTooltip}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      {/* File type icon */}
      <span className={cn("flex-shrink-0 ml-1", fileIconConfig.color)}>
        <FileIcon className="w-4 h-4" />
      </span>

      {/* Filename */}
      <span
        className={cn(
          "flex-1 truncate ml-2 text-sm",
          isSelected ? "font-medium" : "font-normal",
          status === "failed" && "text-red-700"
        )}
        title={node.name}
      >
        {node.name}
      </span>

      {/* AI Category badge (if classified) */}
      {isClassified && node.aiCategory && (
        <span
          className={cn(
            "text-[10px] uppercase flex-shrink-0 ml-2 px-1.5 py-0.5 rounded",
            confidenceLevel === "low"
              ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              : confidenceLevel === "medium"
              ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
              : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
          )}
          title={`${node.aiCategory} → ${node.aiSubcategory || ""}`}
        >
          {node.aiCategory.replace(/^\d+_/, "")}
        </span>
      )}

      {/* File type badge (shown only if not classified) */}
      {(!isClassified || !node.aiCategory) && node.fileType && (
        <span className="text-[10px] text-gray-400 uppercase flex-shrink-0 ml-2 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
          {node.fileType}
        </span>
      )}
    </>
  );
}

export default FileTreeFile;
