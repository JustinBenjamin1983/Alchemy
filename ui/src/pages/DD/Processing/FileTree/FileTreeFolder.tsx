/**
 * FileTreeFolder Component
 *
 * Renders a folder item in the tree with:
 * - Expand/collapse chevron
 * - Folder icon (changes based on content)
 * - Folder name
 * - Document count badge
 */
import React from "react";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  FolderPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { TreeNode } from "./types";

// ============================================================================
// Component Props
// ============================================================================

interface FileTreeFolderProps {
  node: TreeNode;
  isExpanded: boolean;
  isSelected: boolean;
  hasSelectedChildren: boolean;
  onToggleExpand: () => void;
}

// ============================================================================
// Component
// ============================================================================

export function FileTreeFolder({
  node,
  isExpanded,
  isSelected,
  hasSelectedChildren,
  onToggleExpand,
}: FileTreeFolderProps) {
  const hasChildren = node.children && node.children.length > 0;
  const fileCount = node.documentCount || 0;

  // Determine folder icon
  const FolderIcon = isExpanded ? FolderOpen : hasChildren ? Folder : FolderPlus;

  return (
    <>
      {/* Expand/collapse chevron */}
      <button
        className={cn(
          "flex-shrink-0 p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors",
          !hasChildren && "invisible"
        )}
        onClick={(e) => {
          e.stopPropagation();
          onToggleExpand();
        }}
        tabIndex={-1}
      >
        {isExpanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>

      {/* Folder icon */}
      <span
        className={cn(
          "flex-shrink-0",
          isSelected || hasSelectedChildren
            ? "text-blue-600"
            : "text-amber-500"
        )}
      >
        <FolderIcon className="w-4 h-4" />
      </span>

      {/* Folder name */}
      <span
        className={cn(
          "flex-1 truncate ml-1.5 text-sm",
          isSelected ? "font-semibold" : "font-medium"
        )}
        title={node.name}
      >
        {node.name}
      </span>

      {/* Document count badge */}
      {fileCount > 0 && (
        <span
          className={cn(
            "text-[10px] flex-shrink-0 ml-2 px-1.5 py-0.5 rounded-full",
            isSelected
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
              : "bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
          )}
        >
          {fileCount}
        </span>
      )}
    </>
  );
}

export default FileTreeFolder;
