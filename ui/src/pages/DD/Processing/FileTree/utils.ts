/**
 * FileTree Utilities
 *
 * Functions for transforming folder data into tree structure and tree operations.
 */
import { TreeNode, FolderFromAPI, FILE_ICONS } from "./types";

/**
 * Build a nested tree structure from flat folder array.
 * Each folder contains its documents as children.
 */
export function buildTreeFromFolders(folders: FolderFromAPI[]): TreeNode[] {
  if (!folders || folders.length === 0) {
    return [];
  }

  // Filter out the system "root" folder - it's just a container artifact
  const filteredFolders = folders.filter(
    (f) => !(f.folder_name.toLowerCase() === "root" && f.level === 0)
  );

  // Sort folders by hierarchy path for proper ordering
  const sortedFolders = [...filteredFolders].sort((a, b) =>
    a.hierarchy.localeCompare(b.hierarchy)
  );

  // Create lookup map: folder_id -> TreeNode
  const folderMap = new Map<string, TreeNode>();
  const rootNodes: TreeNode[] = [];

  // Collect any documents from the filtered-out root folder to add at top level
  const rootFolder = folders.find(
    (f) => f.folder_name.toLowerCase() === "root" && f.level === 0
  );
  if (rootFolder?.documents?.length) {
    rootFolder.documents.forEach((doc) => {
      rootNodes.push({
        id: doc.document_id,
        name: doc.original_file_name,
        type: "file",
        level: 0,
        parentId: null,
        fileType: getFileExtension(doc.original_file_name) || doc.type,
        readabilityStatus: doc.readability_status ?? "pending",
        processingStatus: doc.processing_status,
        sizeInBytes: doc.size_in_bytes,
        // AI Classification fields
        classificationStatus: doc.classification_status,
        aiCategory: doc.ai_category,
        aiSubcategory: doc.ai_subcategory,
        aiDocumentType: doc.ai_document_type,
        aiConfidence: doc.ai_confidence,
        aiKeyParties: doc.ai_key_parties,
        // Phase 2: Folder organisation fields
        originalFolderId: doc.original_folder_id,
        folderAssignmentSource: doc.folder_assignment_source,
      });
    });
  }

  // First pass: create all folder nodes
  sortedFolders.forEach((folder) => {
    const folderNode: TreeNode = {
      id: folder.folder_id,
      name: folder.folder_name,
      type: "folder",
      level: folder.level,
      parentId: findParentFolderId(folder.hierarchy, sortedFolders),
      children: [],
      hasChildren: folder.has_children,
      documentCount: folder.document_count ?? folder.documents?.length ?? 0,
      // Phase 2: Blueprint folder fields
      folderCategory: folder.folder_category,
      isBlueprintFolder: folder.is_blueprint_folder,
      expectedDocTypes: folder.expected_doc_types,
      sortOrder: folder.sort_order,
      relevance: folder.relevance,
    };

    // Add documents as children of this folder
    folder.documents?.forEach((doc) => {
      folderNode.children!.push({
        id: doc.document_id,
        name: doc.original_file_name,
        type: "file",
        level: folder.level + 1,
        parentId: folder.folder_id,
        fileType: getFileExtension(doc.original_file_name) || doc.type,
        readabilityStatus: doc.readability_status ?? "pending",
        processingStatus: doc.processing_status,
        sizeInBytes: doc.size_in_bytes,
        // AI Classification fields
        classificationStatus: doc.classification_status,
        aiCategory: doc.ai_category,
        aiSubcategory: doc.ai_subcategory,
        aiDocumentType: doc.ai_document_type,
        aiConfidence: doc.ai_confidence,
        aiKeyParties: doc.ai_key_parties,
        // Phase 2: Folder organisation fields
        originalFolderId: doc.original_folder_id,
        folderAssignmentSource: doc.folder_assignment_source,
      });
    });

    folderMap.set(folder.folder_id, folderNode);
  });

  // Second pass: build hierarchy by attaching children to parents
  sortedFolders.forEach((folder) => {
    const node = folderMap.get(folder.folder_id);
    if (!node) return;

    if (folder.level === 0) {
      rootNodes.push(node);
    } else {
      const parentId = node.parentId;
      if (parentId) {
        const parentNode = folderMap.get(parentId);
        if (parentNode) {
          // Insert folder before its documents (folders first, then files)
          const existingChildren = parentNode.children || [];
          const folderChildren = existingChildren.filter((c) => c.type === "folder");
          const fileChildren = existingChildren.filter((c) => c.type === "file");
          parentNode.children = [...folderChildren, node, ...fileChildren];
        }
      }
    }
  });

  // Sort children: folders first (by sortOrder if blueprint, then alphabetically), then files (alphabetically)
  const sortChildren = (nodes: TreeNode[]): TreeNode[] => {
    return nodes.sort((a, b) => {
      // Separate folders and files
      if (a.type !== b.type) {
        return a.type === "folder" ? -1 : 1;
      }

      // For folders, sort blueprint folders by sortOrder, then others alphabetically
      if (a.type === "folder") {
        // Blueprint folders first, sorted by sortOrder
        if (a.isBlueprintFolder && b.isBlueprintFolder) {
          return (a.sortOrder ?? 99) - (b.sortOrder ?? 99);
        }
        if (a.isBlueprintFolder) return -1;
        if (b.isBlueprintFolder) return 1;
      }

      // Default: alphabetical sort
      return a.name.localeCompare(b.name);
    }).map((node) => {
      if (node.children && node.children.length > 0) {
        node.children = sortChildren(node.children);
      }
      return node;
    });
  };

  return sortChildren(rootNodes);
}

/**
 * Find the parent folder ID based on hierarchy path.
 */
function findParentFolderId(
  hierarchy: string,
  folders: FolderFromAPI[]
): string | null {
  const parts = hierarchy.split("/").filter(Boolean);
  if (parts.length <= 1) return null;

  const parentPath = "/" + parts.slice(0, -1).join("/");
  const parent = folders.find((f) => f.hierarchy === parentPath);
  return parent?.folder_id ?? null;
}

/**
 * Flatten tree to array for keyboard navigation and selection operations.
 */
export function flattenTree(
  nodes: TreeNode[],
  expandedIds: Set<string> = new Set()
): TreeNode[] {
  const result: TreeNode[] = [];

  const flatten = (nodeList: TreeNode[]) => {
    nodeList.forEach((node) => {
      result.push(node);
      if (
        node.type === "folder" &&
        node.children &&
        expandedIds.has(node.id)
      ) {
        flatten(node.children);
      }
    });
  };

  flatten(nodes);
  return result;
}

/**
 * Get all descendant IDs of a folder (for folder selection).
 */
export function getAllDescendantIds(node: TreeNode): string[] {
  const ids: string[] = [];

  const collect = (n: TreeNode) => {
    if (n.children) {
      n.children.forEach((child) => {
        ids.push(child.id);
        if (child.type === "folder") {
          collect(child);
        }
      });
    }
  };

  collect(node);
  return ids;
}

/**
 * Get all file IDs from a node (for selection - only files matter for processing).
 */
export function getAllFileIds(node: TreeNode): string[] {
  const ids: string[] = [];

  const collect = (n: TreeNode) => {
    if (n.type === "file") {
      ids.push(n.id);
    }
    if (n.children) {
      n.children.forEach(collect);
    }
  };

  if (node.type === "file") {
    return [node.id];
  }

  collect(node);
  return ids;
}

/**
 * Extract file extension from filename.
 */
export function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  if (parts.length < 2) return "";
  return parts[parts.length - 1].toLowerCase();
}

/**
 * Get file icon configuration based on file type.
 */
export function getFileIcon(fileType: string | undefined) {
  const ext = (fileType || "").toLowerCase();
  return FILE_ICONS[ext] ?? FILE_ICONS.default;
}

/**
 * Format file size in human-readable format.
 */
export function formatFileSize(bytes: number | undefined): string {
  if (!bytes) return "";

  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Find a node by ID in the tree.
 */
export function findNodeById(
  nodes: TreeNode[],
  id: string
): TreeNode | undefined {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNodeById(node.children, id);
      if (found) return found;
    }
  }
  return undefined;
}

/**
 * Get all folder IDs in the tree (for expand all).
 */
export function getAllFolderIds(nodes: TreeNode[]): string[] {
  const ids: string[] = [];

  const collect = (nodeList: TreeNode[]) => {
    nodeList.forEach((node) => {
      if (node.type === "folder") {
        ids.push(node.id);
        if (node.children) {
          collect(node.children);
        }
      }
    });
  };

  collect(nodes);
  return ids;
}

/**
 * Count total files in tree.
 */
export function countFiles(nodes: TreeNode[]): number {
  let count = 0;

  const countRecursive = (nodeList: TreeNode[]) => {
    nodeList.forEach((node) => {
      if (node.type === "file") {
        count++;
      }
      if (node.children) {
        countRecursive(node.children);
      }
    });
  };

  countRecursive(nodes);
  return count;
}

/**
 * Count files by readability status.
 */
export function countFilesByStatus(nodes: TreeNode[]): Record<string, number> {
  const counts: Record<string, number> = {
    ready: 0,
    failed: 0,
    pending: 0,
    checking: 0,
  };

  const countRecursive = (nodeList: TreeNode[]) => {
    nodeList.forEach((node) => {
      if (node.type === "file" && node.readabilityStatus) {
        counts[node.readabilityStatus] = (counts[node.readabilityStatus] || 0) + 1;
      }
      if (node.children) {
        countRecursive(node.children);
      }
    });
  };

  countRecursive(nodes);
  return counts;
}
