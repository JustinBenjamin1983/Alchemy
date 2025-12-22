/**
 * Process Log Component
 *
 * Displays a scrollable log of processing events with attorney-friendly language.
 * Auto-scrolls to latest entry and supports collapsing.
 * Supports drag-to-resize height.
 */
import React, { useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Loader2,
  Clock,
  FileText,
  Search,
  AlertTriangle,
  Info,
  GripHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type LogEntryType =
  | "info"
  | "success"
  | "error"
  | "warning"
  | "progress"
  | "document";

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: LogEntryType;
  message: string;
  details?: string;
}

export interface CurrentlyProcessingInfo {
  documentName: string;
  passLabel: string;
  itemsProcessed?: number;
  totalItems?: number;
}

interface ProcessLogProps {
  entries: LogEntry[];
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
  maxHeight?: string;
  title?: string;
  summary?: string;
  currentlyProcessing?: CurrentlyProcessingInfo | null;
}

const entryConfig: Record<
  LogEntryType,
  { icon: React.ReactNode; color: string }
> = {
  info: {
    icon: <Info className="w-3.5 h-3.5" />,
    color: "text-gray-500",
  },
  success: {
    icon: <Check className="w-3.5 h-3.5" />,
    color: "text-green-600",
  },
  error: {
    icon: <X className="w-3.5 h-3.5" />,
    color: "text-red-600",
  },
  warning: {
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    color: "text-amber-600",
  },
  progress: {
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    color: "text-blue-500",
  },
  document: {
    icon: <FileText className="w-3.5 h-3.5" />,
    color: "text-indigo-500",
  },
};

const formatTime = (date: Date): string => {
  return date.toLocaleTimeString("en-ZA", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Africa/Johannesburg",
  });
};

export const ProcessLog: React.FC<ProcessLogProps> = ({
  entries,
  isCollapsed = false,
  onToggleCollapse,
  className = "",
  maxHeight = "250px",
  title = "Process Log",
  summary,
  currentlyProcessing,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number>(250);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ startY: number; startHeight: number } | null>(null);

  // Auto-scroll to bottom when new entries are added
  useEffect(() => {
    if (scrollRef.current && !isCollapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries, isCollapsed]);

  // Handle drag to resize - track delta from start position for smooth dragging
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragStartRef.current = { startY: e.clientY, startHeight: height };
    setIsDragging(true);
  }, [height]);

  useEffect(() => {
    if (!isDragging) return;

    let animationFrameId: number | null = null;
    const scrollThreshold = 50; // Start scrolling when within 50px of viewport edge
    const scrollSpeed = 10; // Pixels to scroll per frame

    const handleMouseMove = (e: MouseEvent) => {
      if (dragStartRef.current) {
        const deltaY = e.clientY - dragStartRef.current.startY;
        const newHeight = dragStartRef.current.startHeight + deltaY;
        // Clamp between 100px and 1200px (increased max for extended scrolling)
        setHeight(Math.max(100, Math.min(1200, newHeight)));

        // Auto-scroll when near bottom of viewport
        const viewportHeight = window.innerHeight;
        const distanceFromBottom = viewportHeight - e.clientY;

        if (distanceFromBottom < scrollThreshold) {
          // Scroll down - speed increases as you get closer to edge
          const scrollAmount = scrollSpeed * (1 - distanceFromBottom / scrollThreshold);
          window.scrollBy(0, scrollAmount);
          // Adjust the start reference to account for scroll
          dragStartRef.current.startY -= scrollAmount;
        } else if (e.clientY < scrollThreshold) {
          // Scroll up when near top
          const scrollAmount = scrollSpeed * (1 - e.clientY / scrollThreshold);
          window.scrollBy(0, -scrollAmount);
          dragStartRef.current.startY += scrollAmount;
        }
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      dragStartRef.current = null;
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };

    // Prevent text selection during drag
    document.body.style.userSelect = "none";
    document.body.style.cursor = "ns-resize";

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [isDragging]);

  // Calculate summary counts
  const counts = entries.reduce(
    (acc, entry) => {
      if (entry.type === "success") acc.success++;
      else if (entry.type === "error") acc.errors++;
      return acc;
    },
    { success: 0, errors: 0 }
  );

  return (
    <div
      ref={containerRef}
      className={cn(
        "bg-white dark:bg-gray-800 rounded-xl border border-gray-300 dark:border-gray-600 shadow-lg overflow-hidden transition-shadow hover:shadow-xl",
        className
      )}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-alchemyPrimaryNavyBlue border-b border-gray-700 cursor-pointer"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-2">
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-white/70" />
          ) : (
            <ChevronDown className="w-4 h-4 text-white/70" />
          )}
          <h3 className="font-medium text-white">{title}</h3>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {entries.length > 0 && (
            <>
              {counts.success > 0 && (
                <span className="flex items-center gap-1 text-green-400">
                  <Check className="w-3 h-3" />
                  {counts.success}
                </span>
              )}
              {counts.errors > 0 && (
                <span className="flex items-center gap-1 text-red-400">
                  <X className="w-3 h-3" />
                  {counts.errors}
                </span>
              )}
              <span className="text-white/40">|</span>
            </>
          )}
          <span className="text-white/70">{entries.length} entries</span>
        </div>
      </div>

      {/* Content */}
      <AnimatePresence initial={false}>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Log Entries - Light professional style */}
            <div
              ref={scrollRef}
              className="overflow-y-auto text-sm bg-gray-50 dark:bg-gray-900"
              style={{ height: `${height}px` }}
            >
              {/* Currently Processing Indicator - Sticky at top of scroll area */}
              {currentlyProcessing && (
                <div className="sticky top-0 z-10 px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-blue-100 dark:bg-blue-900/30">
                      <Loader2 className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="font-medium text-blue-900 dark:text-blue-100 truncate" title={currentlyProcessing.documentName}>
                          {currentlyProcessing.documentName}
                        </span>
                        <span className="text-xs text-blue-600 dark:text-blue-400 font-medium uppercase tracking-wide flex-shrink-0">
                          Processing
                        </span>
                      </div>
                      <p className="text-xs text-blue-600/70 dark:text-blue-400/70 mt-0.5">
                        {currentlyProcessing.passLabel}
                        {currentlyProcessing.itemsProcessed !== undefined && currentlyProcessing.totalItems !== undefined && (
                          <> · {currentlyProcessing.itemsProcessed} of {currentlyProcessing.totalItems} docs</>
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {entries.length === 0 && !currentlyProcessing ? (
                <div className="px-4 py-12 text-center text-gray-400">
                  <Clock className="w-8 h-8 mx-auto mb-3 opacity-40" />
                  <p className="text-gray-500">No activity yet</p>
                  <p className="text-xs text-gray-400 mt-1">Events will appear here as processing runs</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {entries.map((entry) => {
                    const config = entryConfig[entry.type];
                    return (
                      <div
                        key={entry.id}
                        className={cn(
                          "flex items-start gap-3 px-4 py-3 hover:bg-white dark:hover:bg-gray-800/50 transition-colors",
                          entry.type === "error" && "bg-red-50 dark:bg-red-950/20",
                          entry.type === "success" && "bg-green-50/50 dark:bg-green-950/10",
                          entry.type === "warning" && "bg-amber-50/50 dark:bg-amber-950/10"
                        )}
                      >
                        {/* Icon with background */}
                        <div className={cn(
                          "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5",
                          entry.type === "success" && "bg-green-100 dark:bg-green-900/30",
                          entry.type === "error" && "bg-red-100 dark:bg-red-900/30",
                          entry.type === "warning" && "bg-amber-100 dark:bg-amber-900/30",
                          entry.type === "info" && "bg-gray-100 dark:bg-gray-800",
                          entry.type === "progress" && "bg-blue-100 dark:bg-blue-900/30",
                          entry.type === "document" && "bg-indigo-100 dark:bg-indigo-900/30"
                        )}>
                          <span className={config.color}>
                            {config.icon}
                          </span>
                        </div>

                        {/* Message content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-baseline justify-between gap-2">
                            <span className={cn("font-medium text-gray-900 dark:text-gray-100")}>
                              {entry.message}
                            </span>
                            <span className="text-xs text-gray-400 flex-shrink-0 tabular-nums">
                              {formatTime(entry.timestamp)}
                            </span>
                          </div>
                          {entry.details && (
                            <p
                              className={cn(
                                "mt-1 text-sm",
                                entry.type === "error" || entry.type === "warning"
                                  ? "text-gray-600 dark:text-gray-400"
                                  : "text-gray-500 dark:text-gray-500"
                              )}
                            >
                              {entry.details}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer Summary */}
            {summary && (
              <div className="px-4 py-2.5 bg-gray-100 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-400">
                {summary}
              </div>
            )}

            {/* Drag Handle */}
            <div
              className={cn(
                "flex items-center justify-center py-1.5 bg-gray-100 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 cursor-ns-resize hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors",
                isDragging && "bg-gray-300 dark:bg-gray-500"
              )}
              onMouseDown={handleMouseDown}
            >
              <GripHorizontal className="w-4 h-4 text-gray-400 dark:text-gray-500" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Helper function to create log entries
export const createLogEntry = (
  type: LogEntryType,
  message: string,
  details?: string
): LogEntry => ({
  id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  timestamp: new Date(),
  type,
  message,
  details,
});

export default ProcessLog;
