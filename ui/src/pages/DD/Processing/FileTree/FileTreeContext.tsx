/**
 * FileTree Context
 *
 * Provides state management for the file tree component.
 */
import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";
import { TreeNode } from "./types";
import { getAllFileIds, getAllFolderIds, findNodeById } from "./utils";

// ============================================================================
// Context Types
// ============================================================================

interface FileTreeContextValue {
  // Tree data
  treeData: TreeNode[];

  // Selection state
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;

  // Expansion state
  expandedIds: Set<string>;
  toggleExpand: (folderId: string) => void;
  expandAll: () => void;
  collapseAll: () => void;

  // Context menu
  contextMenuNode: TreeNode | null;
  contextMenuPosition: { x: number; y: number } | null;
  openContextMenu: (node: TreeNode, position: { x: number; y: number }) => void;
  closeContextMenu: () => void;

  // Rename
  renamingNodeId: string | null;
  startRename: (nodeId: string) => void;
  cancelRename: () => void;

  // Drag state
  isDraggingExternal: boolean;
  setIsDraggingExternal: (isDragging: boolean) => void;

  // Actions (provided by parent)
  actions: FileTreeActions;
}

interface FileTreeActions {
  previewFile: (docId: string) => void;
  downloadFile: (docId: string) => void;
  moveFile: (docId: string, fromFolderId: string, toFolderId: string) => void;
  renameFile: (docId: string, newName: string) => void;
  deleteFile: (docId: string) => void;
  addFolder: (folderName: string, parentFolderId?: string) => void;
  deleteFolder: (folderId: string) => void;
  renameFolder: (folderId: string, newName: string) => void;
  uploadFiles: (files: File[], targetFolderId?: string) => void;
  refetch: () => void;
}

interface FileTreeProviderProps {
  children: React.ReactNode;
  treeData: TreeNode[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  actions: FileTreeActions;
}

// ============================================================================
// Context
// ============================================================================

const FileTreeContext = createContext<FileTreeContextValue | null>(null);

// ============================================================================
// Provider
// ============================================================================

export function FileTreeProvider({
  children,
  treeData,
  selectedIds,
  onSelectionChange,
  actions,
}: FileTreeProviderProps) {
  // Expansion state - auto-expand root level folders
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => {
    const rootFolders = treeData
      .filter((node) => node.type === "folder" && node.level === 0)
      .map((node) => node.id);
    return new Set(rootFolders);
  });

  // Context menu state
  const [contextMenuNode, setContextMenuNode] = useState<TreeNode | null>(null);
  const [contextMenuPosition, setContextMenuPosition] = useState<{
    x: number;
    y: number;
  } | null>(null);

  // Rename state
  const [renamingNodeId, setRenamingNodeId] = useState<string | null>(null);

  // External drag state
  const [isDraggingExternal, setIsDraggingExternal] = useState(false);

  // Toggle folder expansion
  const toggleExpand = useCallback((folderId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  }, []);

  // Expand all folders
  const expandAll = useCallback(() => {
    const allFolderIds = getAllFolderIds(treeData);
    setExpandedIds(new Set(allFolderIds));
  }, [treeData]);

  // Collapse all folders
  const collapseAll = useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  // Open context menu
  const openContextMenu = useCallback(
    (node: TreeNode, position: { x: number; y: number }) => {
      setContextMenuNode(node);
      setContextMenuPosition(position);
    },
    []
  );

  // Close context menu
  const closeContextMenu = useCallback(() => {
    setContextMenuNode(null);
    setContextMenuPosition(null);
  }, []);

  // Start rename
  const startRename = useCallback((nodeId: string) => {
    setRenamingNodeId(nodeId);
    closeContextMenu();
  }, [closeContextMenu]);

  // Cancel rename
  const cancelRename = useCallback(() => {
    setRenamingNodeId(null);
  }, []);

  // Memoized context value
  const value = useMemo<FileTreeContextValue>(
    () => ({
      treeData,
      selectedIds,
      onSelectionChange,
      expandedIds,
      toggleExpand,
      expandAll,
      collapseAll,
      contextMenuNode,
      contextMenuPosition,
      openContextMenu,
      closeContextMenu,
      renamingNodeId,
      startRename,
      cancelRename,
      isDraggingExternal,
      setIsDraggingExternal,
      actions,
    }),
    [
      treeData,
      selectedIds,
      onSelectionChange,
      expandedIds,
      toggleExpand,
      expandAll,
      collapseAll,
      contextMenuNode,
      contextMenuPosition,
      openContextMenu,
      closeContextMenu,
      renamingNodeId,
      startRename,
      cancelRename,
      isDraggingExternal,
      actions,
    ]
  );

  return (
    <FileTreeContext.Provider value={value}>
      {children}
    </FileTreeContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useFileTreeContext() {
  const context = useContext(FileTreeContext);
  if (!context) {
    throw new Error("useFileTreeContext must be used within FileTreeProvider");
  }
  return context;
}

// ============================================================================
// Selection Helpers
// ============================================================================

/**
 * Handle node selection with folder logic.
 * When a folder is selected, all its file descendants are selected.
 */
export function handleNodeSelection(
  node: TreeNode,
  currentSelection: Set<string>,
  treeData: TreeNode[],
  isCtrlKey: boolean = false
): Set<string> {
  const newSelection = new Set(currentSelection);

  // Get all file IDs for this node (or just the node ID if it's a file)
  const fileIds = getAllFileIds(node);

  if (isCtrlKey) {
    // Toggle selection
    const allSelected = fileIds.every((id) => newSelection.has(id));
    if (allSelected) {
      fileIds.forEach((id) => newSelection.delete(id));
    } else {
      fileIds.forEach((id) => newSelection.add(id));
    }
  } else {
    // Replace selection
    newSelection.clear();
    fileIds.forEach((id) => newSelection.add(id));
  }

  return newSelection;
}

/**
 * Check if a folder has all its files selected.
 */
export function isFolderFullySelected(
  node: TreeNode,
  selectedIds: Set<string>
): boolean {
  if (node.type !== "folder") return false;
  const fileIds = getAllFileIds(node);
  if (fileIds.length === 0) return false;
  return fileIds.every((id) => selectedIds.has(id));
}

/**
 * Check if a folder has some (but not all) files selected.
 */
export function isFolderPartiallySelected(
  node: TreeNode,
  selectedIds: Set<string>
): boolean {
  if (node.type !== "folder") return false;
  const fileIds = getAllFileIds(node);
  if (fileIds.length === 0) return false;
  const selectedCount = fileIds.filter((id) => selectedIds.has(id)).length;
  return selectedCount > 0 && selectedCount < fileIds.length;
}
