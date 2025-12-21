/**
 * FileTree Barrel Exports
 */

// Main component
export { FileTree } from "./FileTree";
export { default } from "./FileTree";

// Types
export type {
  TreeNode,
  FolderFromAPI,
  DocumentFromAPI,
  ReadabilityStatus,
  HistoryEntry,
  FileTreeState,
  FileTreeActions,
} from "./types";

// Utilities
export {
  buildTreeFromFolders,
  flattenTree,
  getAllDescendantIds,
  getAllFileIds,
  getFileExtension,
  getFileIcon,
  formatFileSize,
  findNodeById,
  getAllFolderIds,
  countFiles,
  countFilesByStatus,
} from "./utils";

// Context
export {
  FileTreeProvider,
  useFileTreeContext,
  handleNodeSelection,
  isFolderFullySelected,
  isFolderPartiallySelected,
} from "./FileTreeContext";

// Subcomponents (for advanced usage)
export { FileTreeNode } from "./FileTreeNode";
export { FileTreeFile } from "./FileTreeFile";
export { FileTreeFolder } from "./FileTreeFolder";
export { FileTreeContextMenu } from "./FileTreeContextMenu";
export { FileTreeUploadZone } from "./FileTreeUploadZone";
export { FileTreeHistory } from "./FileTreeHistory";
