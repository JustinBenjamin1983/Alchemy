/**
 * FolderFilter Component
 *
 * Phase 3: Allows filtering findings by folder category.
 * Displays folder categories with counts and provides quick filtering.
 */
import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FolderOpen, X, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Finding,
  FolderCategory,
  FOLDER_CATEGORY_CONFIG,
  FOLDER_CATEGORY_ORDER,
  getFolderCategoryShortLabel,
} from "./types";

interface FolderFilterProps {
  findings: Finding[];
  selectedFolder: string | null;
  onFolderSelect: (folder: string | null) => void;
  className?: string;
}

interface FolderCount {
  category: FolderCategory;
  count: number;
  criticalCount: number;
  highCount: number;
}

export const FolderFilter: React.FC<FolderFilterProps> = ({
  findings,
  selectedFolder,
  onFolderSelect,
  className,
}) => {
  // Calculate counts by folder category
  const folderCounts = useMemo(() => {
    const counts: Record<string, FolderCount> = {};

    for (const finding of findings) {
      const folder = finding.folder_category;
      if (!folder) continue;

      if (!counts[folder]) {
        counts[folder] = {
          category: folder as FolderCategory,
          count: 0,
          criticalCount: 0,
          highCount: 0,
        };
      }

      counts[folder].count++;
      if (finding.severity === "critical") {
        counts[folder].criticalCount++;
      } else if (finding.severity === "high") {
        counts[folder].highCount++;
      }
    }

    // Sort by FOLDER_CATEGORY_ORDER
    return FOLDER_CATEGORY_ORDER.filter((cat) => counts[cat]).map(
      (cat) => counts[cat]
    );
  }, [findings]);

  // Count findings with folder vs without
  const findingsWithFolder = useMemo(
    () => findings.filter((f) => f.folder_category).length,
    [findings]
  );

  // If no findings have folder categories, don't show the filter
  if (findingsWithFolder === 0) {
    return null;
  }

  const selectedConfig = selectedFolder
    ? FOLDER_CATEGORY_CONFIG[selectedFolder as FolderCategory]
    : null;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={selectedFolder ? "secondary" : "outline"}
          size="sm"
          className={cn(
            "gap-2",
            selectedFolder && selectedConfig?.bgColor,
            selectedFolder && selectedConfig?.borderColor,
            className
          )}
        >
          <FolderOpen className="w-4 h-4" />
          {selectedFolder ? (
            <>
              <span className={selectedConfig?.color}>
                {getFolderCategoryShortLabel(selectedFolder)}
              </span>
              <X
                className="w-3 h-3 ml-1 hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onFolderSelect(null);
                }}
              />
            </>
          ) : (
            <>
              <span>By Folder</span>
              <ChevronDown className="w-3 h-3" />
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-2" align="start">
        <div className="space-y-1">
          <div className="text-xs font-medium text-muted-foreground px-2 py-1">
            Filter by Folder Category
          </div>

          {/* All folders option */}
          <button
            className={cn(
              "w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-sm transition-colors",
              !selectedFolder
                ? "bg-accent text-accent-foreground"
                : "hover:bg-accent/50"
            )}
            onClick={() => onFolderSelect(null)}
          >
            <span className="flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-muted-foreground" />
              All Folders
            </span>
            <Badge variant="secondary" className="text-xs">
              {findingsWithFolder}
            </Badge>
          </button>

          <div className="border-t my-1" />

          {/* Folder categories */}
          <AnimatePresence>
            {folderCounts.map((folder) => {
              const config = FOLDER_CATEGORY_CONFIG[folder.category];
              const isSelected = selectedFolder === folder.category;

              return (
                <motion.button
                  key={folder.category}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className={cn(
                    "w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-sm transition-colors",
                    isSelected
                      ? `${config.bgColor} ${config.borderColor} border`
                      : "hover:bg-accent/50"
                  )}
                  onClick={() => onFolderSelect(folder.category)}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-base">{config.icon}</span>
                    <span className={isSelected ? config.color : ""}>
                      {config.shortLabel}
                    </span>
                  </span>
                  <div className="flex items-center gap-1">
                    {folder.criticalCount > 0 && (
                      <Badge
                        variant="destructive"
                        className="text-[10px] px-1 py-0"
                      >
                        {folder.criticalCount}
                      </Badge>
                    )}
                    {folder.highCount > 0 && (
                      <Badge
                        variant="secondary"
                        className="text-[10px] px-1 py-0 bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                      >
                        {folder.highCount}
                      </Badge>
                    )}
                    <Badge variant="outline" className="text-[10px] px-1 py-0">
                      {folder.count}
                    </Badge>
                  </div>
                </motion.button>
              );
            })}
          </AnimatePresence>

          {folderCounts.length === 0 && (
            <div className="text-xs text-muted-foreground text-center py-2">
              No folder categories available
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
};

export default FolderFilter;
