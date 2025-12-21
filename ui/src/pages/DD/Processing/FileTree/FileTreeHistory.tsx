/**
 * FileTreeHistory Component
 *
 * Collapsible section at the bottom showing document change history.
 */
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronRight,
  ChevronDown,
  History,
  FolderInput,
  FilePlus,
  FileX,
  Pencil,
  Archive,
} from "lucide-react";
import { formatDistance } from "date-fns";
import { cn } from "@/lib/utils";
import { useGetDDDocsHistory } from "@/hooks/useGetDDDocsHistory";
import { HistoryEntry } from "./types";

// ============================================================================
// Action Icon Mapping
// ============================================================================

const ACTION_ICONS: Record<string, React.ReactNode> = {
  "ZIP uploaded": <Archive className="w-3.5 h-3.5 text-purple-500" />,
  Added: <FilePlus className="w-3.5 h-3.5 text-green-500" />,
  Moved: <FolderInput className="w-3.5 h-3.5 text-blue-500" />,
  Deleted: <FileX className="w-3.5 h-3.5 text-red-500" />,
  "File Renamed": <Pencil className="w-3.5 h-3.5 text-amber-500" />,
};

// ============================================================================
// Component Props
// ============================================================================

interface FileTreeHistoryProps {
  ddId: string;
}

// ============================================================================
// Component
// ============================================================================

export function FileTreeHistory({ ddId }: FileTreeHistoryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { data, refetch, isLoading } = useGetDDDocsHistory(ddId);

  // Fetch history when expanded
  useEffect(() => {
    if (isExpanded && ddId) {
      refetch();
    }
  }, [isExpanded, ddId, refetch]);

  const history: HistoryEntry[] = data?.history || [];
  const hasHistory = history.length > 0;

  return (
    <div className="border-t border-gray-200 dark:border-gray-700">
      {/* Header */}
      <button
        className="flex items-center gap-2 w-full px-4 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-gray-400">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </span>
        <History className="w-4 h-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          History
        </span>
        {hasHistory && (
          <span className="text-xs text-gray-400 ml-auto">
            {history.length} entries
          </span>
        )}
      </button>

      {/* Content */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="max-h-[180px] overflow-y-auto bg-gray-50/50 dark:bg-gray-900/30">
              {isLoading ? (
                <div className="px-4 py-6 text-center text-gray-400 text-sm">
                  Loading history...
                </div>
              ) : !hasHistory ? (
                <div className="px-4 py-6 text-center text-gray-400 text-sm">
                  No history yet
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {history.slice(0, 20).map((entry) => (
                    <div
                      key={entry.id}
                      className="px-4 py-2.5 flex items-start gap-3 hover:bg-white dark:hover:bg-gray-800/50 transition-colors"
                    >
                      {/* Action icon */}
                      <span className="flex-shrink-0 mt-0.5">
                        {ACTION_ICONS[entry.action] || (
                          <History className="w-3.5 h-3.5 text-gray-400" />
                        )}
                      </span>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2">
                          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                            {entry.action}
                          </span>
                          <span className="text-xs text-gray-400">
                            {formatDistance(
                              new Date(entry.action_at),
                              new Date(),
                              { addSuffix: true }
                            )}
                          </span>
                        </div>
                        <p
                          className="text-xs text-gray-500 truncate mt-0.5"
                          title={entry.original_file_name}
                        >
                          {entry.original_file_name}
                        </p>
                        {entry.action === "Moved" &&
                          entry.previous_folder &&
                          entry.current_folder && (
                            <p className="text-[10px] text-gray-400 mt-0.5">
                              {entry.previous_folder} → {entry.current_folder}
                            </p>
                          )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default FileTreeHistory;
