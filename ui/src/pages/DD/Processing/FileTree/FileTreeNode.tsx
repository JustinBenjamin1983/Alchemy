/**
 * FileTreeNode Component
 *
 * Recursive component that renders either a file or folder.
 * Handles:
 * - Click for selection
 * - Double-click for expand (folder) or preview (file)
 * - Right-click for context menu
 * - Drag and drop for file moving
 * - Keyboard navigation
 */
import React, { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { TreeNode } from "./types";
import { FileTreeFile } from "./FileTreeFile";
import { FileTreeFolder } from "./FileTreeFolder";
import {
  useFileTreeContext,
  handleNodeSelection,
  isFolderFullySelected,
  isFolderPartiallySelected,
} from "./FileTreeContext";
import { getAllFileIds } from "./utils";

// ============================================================================
// Component Props
// ============================================================================

interface FileTreeNodeProps {
  node: TreeNode;
}

// ============================================================================
// Component
// ============================================================================

export function FileTreeNode({ node }: FileTreeNodeProps) {
  const {
    treeData,
    selectedIds,
    onSelectionChange,
    expandedIds,
    toggleExpand,
    openContextMenu,
    renamingNodeId,
    startRename,
    cancelRename,
    actions,
  } = useFileTreeContext();

  const [isDragOver, setIsDragOver] = useState(false);
  const [renameValue, setRenameValue] = useState(node.name);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const isExpanded = node.type === "folder" && expandedIds.has(node.id);
  const isRenaming = renamingNodeId === node.id;

  // Selection state
  const isFile = node.type === "file";
  const isSelected = isFile
    ? selectedIds.has(node.id)
    : isFolderFullySelected(node, selectedIds);
  const isPartiallySelected =
    node.type === "folder" && isFolderPartiallySelected(node, selectedIds);
  const hasSelectedChildren =
    node.type === "folder" &&
    getAllFileIds(node).some((id) => selectedIds.has(id));

  // Focus rename input when entering rename mode
  useEffect(() => {
    if (isRenaming && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [isRenaming]);

  // Handle click (selection)
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      const isCtrlKey = e.ctrlKey || e.metaKey;
      const newSelection = handleNodeSelection(
        node,
        selectedIds,
        treeData,
        isCtrlKey
      );
      onSelectionChange(newSelection);
    },
    [node, selectedIds, treeData, onSelectionChange]
  );

  // Handle double-click (expand folder or preview file)
  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (node.type === "folder") {
        toggleExpand(node.id);
      } else {
        actions.previewFile(node.id);
      }
    },
    [node, toggleExpand, actions]
  );

  // Handle right-click (context menu)
  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      openContextMenu(node, { x: e.clientX, y: e.clientY });
    },
    [node, openContextMenu]
  );

  // Handle checkbox change
  const handleCheckboxChange = useCallback(
    (checked: boolean | "indeterminate") => {
      if (checked === "indeterminate") return;

      const fileIds = getAllFileIds(node);
      const newSelection = new Set(selectedIds);

      if (checked) {
        fileIds.forEach((id) => newSelection.add(id));
      } else {
        fileIds.forEach((id) => newSelection.delete(id));
      }

      onSelectionChange(newSelection);
    },
    [node, selectedIds, onSelectionChange]
  );

  // Drag handlers (for moving files between folders)
  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      if (node.type !== "file") {
        e.preventDefault();
        return;
      }
      e.dataTransfer.setData(
        "application/json",
        JSON.stringify({
          nodeId: node.id,
          nodeType: node.type,
          parentId: node.parentId,
          name: node.name,
        })
      );
      e.dataTransfer.effectAllowed = "move";
    },
    [node]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      if (node.type === "folder") {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        setIsDragOver(true);
      }
    },
    [node.type]
  );

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      if (node.type !== "folder") return;

      try {
        const data = JSON.parse(e.dataTransfer.getData("application/json"));
        if (data.nodeType === "file" && data.parentId !== node.id) {
          actions.moveFile(data.nodeId, data.parentId, node.id);
        }
      } catch {
        // Ignore invalid drag data
      }
    },
    [node, actions]
  );

  // Rename handlers
  const handleRenameSubmit = useCallback(() => {
    if (renameValue.trim() && renameValue !== node.name) {
      if (node.type === "file") {
        actions.renameFile(node.id, renameValue.trim());
      } else {
        actions.renameFolder(node.id, renameValue.trim());
      }
    }
    cancelRename();
  }, [renameValue, node, actions, cancelRename]);

  const handleRenameKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        handleRenameSubmit();
      } else if (e.key === "Escape") {
        setRenameValue(node.name);
        cancelRename();
      }
    },
    [handleRenameSubmit, node.name, cancelRename]
  );

  // Indentation (24px per level for clearer hierarchy)
  const indent = node.level * 24;

  return (
    <div>
      {/* Node row */}
      <div
        className={cn(
          "group flex items-center gap-1 py-1.5 px-2 rounded-lg cursor-pointer select-none transition-colors",
          isSelected && "bg-blue-100 dark:bg-blue-900/40",
          !isSelected && "hover:bg-gray-200 dark:hover:bg-gray-700/50",
          isDragOver && "bg-blue-50 ring-2 ring-blue-300 dark:ring-blue-600"
        )}
        style={{ paddingLeft: `${indent + 8}px` }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
        draggable={node.type === "file"}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Checkbox */}
        <Checkbox
          checked={isPartiallySelected ? "indeterminate" : isSelected}
          onCheckedChange={handleCheckboxChange}
          onClick={(e) => e.stopPropagation()}
          className="flex-shrink-0"
        />

        {/* Render folder or file content */}
        {isRenaming ? (
          <Input
            ref={renameInputRef}
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onBlur={handleRenameSubmit}
            onKeyDown={handleRenameKeyDown}
            onClick={(e) => e.stopPropagation()}
            className="h-6 text-sm flex-1"
          />
        ) : node.type === "folder" ? (
          <FileTreeFolder
            node={node}
            isExpanded={isExpanded}
            isSelected={isSelected}
            hasSelectedChildren={hasSelectedChildren}
            onToggleExpand={() => toggleExpand(node.id)}
          />
        ) : (
          <FileTreeFile node={node} isSelected={isSelected} />
        )}
      </div>

      {/* Children (for expanded folders) */}
      <AnimatePresence initial={false}>
        {node.type === "folder" && isExpanded && node.children && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            {node.children.map((child) => (
              <FileTreeNode key={child.id} node={child} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default FileTreeNode;
