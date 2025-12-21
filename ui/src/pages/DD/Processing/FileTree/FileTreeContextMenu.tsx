/**
 * FileTreeContextMenu Component
 *
 * Right-click context menu for files and folders.
 * - Files: Preview, Download, Rename, Move, Delete
 * - Folders: New Folder, Rename, Delete
 */
import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  Eye,
  Download,
  Pencil,
  FolderInput,
  Trash2,
  FolderPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useFileTreeContext } from "./FileTreeContext";

// ============================================================================
// Menu Item Component
// ============================================================================

interface MenuItemProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
  disabled?: boolean;
}

function MenuItem({
  icon,
  label,
  onClick,
  variant = "default",
  disabled = false,
}: MenuItemProps) {
  return (
    <button
      className={cn(
        "flex items-center gap-2 w-full px-3 py-2 text-sm text-left transition-colors",
        variant === "default" &&
          "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700",
        variant === "danger" &&
          "text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30",
        disabled && "opacity-50 cursor-not-allowed"
      )}
      onClick={onClick}
      disabled={disabled}
    >
      {icon}
      {label}
    </button>
  );
}

// ============================================================================
// Separator Component
// ============================================================================

function MenuSeparator() {
  return <div className="border-t border-gray-200 dark:border-gray-600 my-1" />;
}

// ============================================================================
// Main Component
// ============================================================================

export function FileTreeContextMenu() {
  const {
    contextMenuNode,
    contextMenuPosition,
    closeContextMenu,
    startRename,
    actions,
  } = useFileTreeContext();

  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeContextMenu();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeContextMenu();
      }
    };

    if (contextMenuNode) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [contextMenuNode, closeContextMenu]);

  if (!contextMenuNode || !contextMenuPosition) {
    return null;
  }

  const isFile = contextMenuNode.type === "file";
  const isFolder = contextMenuNode.type === "folder";

  // Adjust position to stay within viewport
  const adjustedPosition = { ...contextMenuPosition };
  const menuWidth = 200;
  const menuHeight = isFile ? 220 : 150;

  if (adjustedPosition.x + menuWidth > window.innerWidth) {
    adjustedPosition.x = window.innerWidth - menuWidth - 10;
  }
  if (adjustedPosition.y + menuHeight > window.innerHeight) {
    adjustedPosition.y = window.innerHeight - menuHeight - 10;
  }

  const menu = (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[180px] bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 animate-in fade-in zoom-in-95 duration-100"
      style={{
        left: adjustedPosition.x,
        top: adjustedPosition.y,
      }}
    >
      {/* File actions */}
      {isFile && (
        <>
          <MenuItem
            icon={<Eye className="w-4 h-4" />}
            label="Preview"
            onClick={() => {
              actions.previewFile(contextMenuNode.id);
              closeContextMenu();
            }}
          />
          <MenuItem
            icon={<Download className="w-4 h-4" />}
            label="Download"
            onClick={() => {
              actions.downloadFile(contextMenuNode.id);
              closeContextMenu();
            }}
          />
          <MenuSeparator />
        </>
      )}

      {/* Folder actions */}
      {isFolder && (
        <>
          <MenuItem
            icon={<FolderPlus className="w-4 h-4" />}
            label="New Folder"
            onClick={() => {
              const name = prompt("Enter folder name:");
              if (name) {
                actions.addFolder(name, contextMenuNode.id);
              }
              closeContextMenu();
            }}
          />
          <MenuSeparator />
        </>
      )}

      {/* Common actions */}
      <MenuItem
        icon={<Pencil className="w-4 h-4" />}
        label="Rename"
        onClick={() => {
          startRename(contextMenuNode.id);
        }}
      />

      {isFile && (
        <MenuItem
          icon={<FolderInput className="w-4 h-4" />}
          label="Move to..."
          onClick={() => {
            // TODO: Open folder picker dialog
            alert("Move to folder - coming soon");
            closeContextMenu();
          }}
        />
      )}

      <MenuSeparator />

      <MenuItem
        icon={<Trash2 className="w-4 h-4" />}
        label="Delete"
        variant="danger"
        onClick={() => {
          const confirmMsg = isFile
            ? `Delete "${contextMenuNode.name}"?`
            : `Delete folder "${contextMenuNode.name}" and all its contents?`;

          if (confirm(confirmMsg)) {
            if (isFile) {
              actions.deleteFile(contextMenuNode.id);
            } else {
              actions.deleteFolder(contextMenuNode.id);
            }
          }
          closeContextMenu();
        }}
      />
    </div>
  );

  return createPortal(menu, document.body);
}

export default FileTreeContextMenu;
