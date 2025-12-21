/**
 * FileTree Types
 *
 * TypeScript interfaces and configuration for VS Code-style file tree.
 */
import React from "react";
import {
  FileText,
  File,
  FileSpreadsheet,
  Presentation,
  Check,
  X,
  Circle,
  Loader2,
} from "lucide-react";

// ============================================================================
// Core Types
// ============================================================================

export type ReadabilityStatus = "pending" | "checking" | "ready" | "failed";
export type ClassificationStatus = "pending" | "classifying" | "classified" | "failed";
export type FolderRelevance = "critical" | "high" | "medium" | "low" | "n/a";
export type FolderAssignmentSource = "original_zip" | "ai" | "manual";

export interface TreeNode {
  id: string;
  name: string;
  type: "folder" | "file";
  level: number;
  parentId: string | null;
  children?: TreeNode[];

  // File-specific properties
  fileType?: string;
  readabilityStatus?: ReadabilityStatus;
  processingStatus?: string;
  sizeInBytes?: number;

  // AI Classification properties (Phase 1)
  classificationStatus?: ClassificationStatus;
  aiCategory?: string;
  aiSubcategory?: string;
  aiDocumentType?: string;
  aiConfidence?: number;
  aiKeyParties?: string[];

  // Folder-specific properties
  hasChildren?: boolean;
  documentCount?: number;

  // Phase 2: Blueprint Folder properties
  folderCategory?: string;  // e.g., "01_Corporate"
  isBlueprintFolder?: boolean;
  expectedDocTypes?: string[];
  sortOrder?: number;
  relevance?: FolderRelevance;

  // Phase 2: Document organisation properties
  originalFolderId?: string;
  folderAssignmentSource?: FolderAssignmentSource;
}

export interface FolderFromAPI {
  folder_id: string;
  folder_name: string;
  hierarchy: string;
  level: number;
  has_children: boolean;
  documents?: DocumentFromAPI[];

  // Phase 2: Blueprint Folder Organisation fields
  folder_category?: string;  // e.g., "01_Corporate", "02_Commercial"
  is_blueprint_folder?: boolean;
  expected_doc_types?: string[];
  sort_order?: number;
  relevance?: FolderRelevance;
  document_count?: number;
}

export interface DocumentFromAPI {
  document_id: string;
  original_file_name: string;
  type: string;
  readability_status?: ReadabilityStatus;
  readability_error?: string | null;
  processing_status?: string;
  size_in_bytes?: number;

  // AI Classification fields (Phase 1)
  classification_status?: ClassificationStatus;
  ai_category?: string;
  ai_subcategory?: string;
  ai_document_type?: string;
  ai_confidence?: number;
  ai_key_parties?: string[];

  // Phase 2: Folder Organisation fields
  original_folder_id?: string;  // Preserves original ZIP folder for audit trail
  folder_assignment_source?: FolderAssignmentSource;  // How doc was assigned: 'original_zip', 'ai', 'manual'
}

// ============================================================================
// State Types
// ============================================================================

export interface FileTreeState {
  selectedIds: Set<string>;
  expandedFolderIds: Set<string>;
  contextMenuNode: TreeNode | null;
  contextMenuPosition: { x: number; y: number } | null;
  renamingNodeId: string | null;
  isDraggingExternal: boolean;
}

export interface FileTreeActions {
  // Selection
  selectNode: (id: string, isShift?: boolean, isCtrl?: boolean) => void;
  selectAll: () => void;
  clearSelection: () => void;

  // Expansion
  toggleExpand: (folderId: string) => void;
  expandAll: () => void;
  collapseAll: () => void;

  // Context menu
  openContextMenu: (node: TreeNode, position: { x: number; y: number }) => void;
  closeContextMenu: () => void;

  // Rename
  startRename: (nodeId: string) => void;
  commitRename: (newName: string) => void;
  cancelRename: () => void;

  // CRUD operations (via mutations)
  previewFile: (docId: string) => void;
  downloadFile: (docId: string) => void;
  moveFile: (docId: string, fromFolderId: string, toFolderId: string) => void;
  renameFile: (docId: string, newName: string) => void;
  deleteFile: (docId: string) => void;
  addFolder: (folderName: string, parentFolderId?: string) => void;
  deleteFolder: (folderId: string) => void;
  renameFolder: (folderId: string, newName: string) => void;
}

// ============================================================================
// History Types
// ============================================================================

export interface HistoryEntry {
  id: number;
  doc_id: string;
  dd_id: string;
  original_file_name: string;
  previous_folder?: string;
  current_folder?: string;
  action: "ZIP uploaded" | "Added" | "Moved" | "Deleted" | "File Renamed";
  by_user?: string;
  action_at: string;
}

// ============================================================================
// Icon Configuration
// ============================================================================

export interface FileIconConfig {
  icon: React.ReactNode;
  color: string;
}

export const FILE_ICONS: Record<string, FileIconConfig> = {
  pdf: { icon: React.createElement(FileText, { className: "w-4 h-4" }), color: "text-red-500" },
  doc: { icon: React.createElement(FileText, { className: "w-4 h-4" }), color: "text-blue-500" },
  docx: { icon: React.createElement(FileText, { className: "w-4 h-4" }), color: "text-blue-500" },
  xls: { icon: React.createElement(FileSpreadsheet, { className: "w-4 h-4" }), color: "text-green-600" },
  xlsx: { icon: React.createElement(FileSpreadsheet, { className: "w-4 h-4" }), color: "text-green-600" },
  ppt: { icon: React.createElement(Presentation, { className: "w-4 h-4" }), color: "text-orange-500" },
  pptx: { icon: React.createElement(Presentation, { className: "w-4 h-4" }), color: "text-orange-500" },
  txt: { icon: React.createElement(FileText, { className: "w-4 h-4" }), color: "text-gray-500" },
  default: { icon: React.createElement(File, { className: "w-4 h-4" }), color: "text-gray-400" },
};

// ============================================================================
// Status Configuration
// ============================================================================

export interface StatusConfig {
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  label: string;
}

export const STATUS_CONFIG: Record<ReadabilityStatus, StatusConfig> = {
  ready: {
    icon: React.createElement(Check, { className: "w-3 h-3" }),
    color: "text-green-600",
    bgColor: "bg-green-100",
    label: "Ready",
  },
  failed: {
    icon: React.createElement(X, { className: "w-3 h-3" }),
    color: "text-red-600",
    bgColor: "bg-red-100",
    label: "Failed",
  },
  pending: {
    icon: React.createElement(Circle, { className: "w-3 h-3" }),
    color: "text-gray-400",
    bgColor: "bg-gray-100",
    label: "Pending",
  },
  checking: {
    icon: React.createElement(Loader2, { className: "w-3 h-3 animate-spin" }),
    color: "text-blue-500",
    bgColor: "bg-blue-100",
    label: "Checking",
  },
};
