// File: ui/src/pages/OpinionWriter/DiffViewer.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DiffChange {
  type: "addition" | "deletion" | "unchanged";
  text: string;
  changeId?: string;
}

interface DiffViewerProps {
  originalText: string;
  currentText: string;
  appliedChanges: Array<{
    id: string;
    type: "replace" | "insert" | "delete";
    startIndex: number;
    endIndex: number;
    originalText?: string;
    newText?: string;
    reasoning?: string;
  }>;
  showDiff: boolean;
  onToggleDiff: () => void;
}

export const DiffViewer = ({
  originalText,
  currentText,
  appliedChanges,
  showDiff,
  onToggleDiff,
}: DiffViewerProps) => {
  const generateDiffSegments = (): DiffChange[] => {
    if (!showDiff || appliedChanges.length === 0) {
      return [{ type: "unchanged", text: currentText }];
    }

    // Sort changes by startIndex to process them in order
    const sortedChanges = [...appliedChanges].sort(
      (a, b) => a.startIndex - b.startIndex
    );

    const segments: DiffChange[] = [];
    let lastIndex = 0;

    sortedChanges.forEach((change) => {
      // Add unchanged text before this change
      if (change.startIndex > lastIndex) {
        const unchangedText = originalText.substring(
          lastIndex,
          change.startIndex
        );
        if (unchangedText) {
          segments.push({ type: "unchanged", text: unchangedText });
        }
      }

      // Add the change
      if (change.type === "delete") {
        // Show deleted text
        if (change.originalText) {
          segments.push({
            type: "deletion",
            text: change.originalText,
            changeId: change.id,
          });
        }
        lastIndex = change.endIndex;
      } else if (change.type === "insert") {
        // Show inserted text
        if (change.newText) {
          segments.push({
            type: "addition",
            text: change.newText,
            changeId: change.id,
          });
        }
        lastIndex = change.startIndex;
      } else if (change.type === "replace") {
        // Show both deletion and addition
        if (change.originalText) {
          segments.push({
            type: "deletion",
            text: change.originalText,
            changeId: change.id,
          });
        }
        if (change.newText) {
          segments.push({
            type: "addition",
            text: change.newText,
            changeId: change.id,
          });
        }
        lastIndex = change.endIndex;
      }
    });

    // Add any remaining unchanged text
    if (lastIndex < originalText.length) {
      const remainingText = originalText.substring(lastIndex);
      if (remainingText) {
        segments.push({ type: "unchanged", text: remainingText });
      }
    }

    return segments;
  };

  const diffSegments = generateDiffSegments();

  return (
    <div className="space-y-3">
      {/* Toggle Button */}
      <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-center gap-2">
          <div className="text-sm font-medium text-blue-900">
            {showDiff ? "Showing Changes" : "Clean View"}
          </div>
          {appliedChanges.length > 0 && (
            <div className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
              {appliedChanges.length} change(s) applied
            </div>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleDiff}
          className="flex items-center gap-2"
        >
          {showDiff ? (
            <>
              <EyeOff className="w-4 h-4" />
              Hide Changes
            </>
          ) : (
            <>
              <Eye className="w-4 h-4" />
              Show Changes
            </>
          )}
        </Button>
      </div>

      {/* Legend when diff is shown */}
      {showDiff && appliedChanges.length > 0 && (
        <div className="flex items-center gap-4 text-xs bg-gray-50 border rounded-lg p-2">
          <div className="flex items-center gap-1">
            <span className="bg-green-200 text-green-800 px-2 py-1 rounded">
              Added
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="bg-red-200 text-red-800 line-through px-2 py-1 rounded">
              Removed
            </span>
          </div>
        </div>
      )}

      {/* Diff Content */}
      <div className="max-h-[700px] overflow-y-auto p-6 rounded-lg bg-white border text-sm">
        <div className="prose prose-sm max-w-none whitespace-pre-wrap leading-relaxed">
          {diffSegments.map((segment, index) => {
            if (segment.type === "addition") {
              return (
                <span
                  key={index}
                  className="bg-green-100 text-green-900 border-b-2 border-green-400 px-1"
                  title="Added by AI"
                >
                  {segment.text}
                </span>
              );
            } else if (segment.type === "deletion") {
              return (
                <span
                  key={index}
                  className="bg-red-100 text-red-900 line-through border-b-2 border-red-400 px-1"
                  title="Removed by AI"
                >
                  {segment.text}
                </span>
              );
            } else {
              return <span key={index}>{segment.text}</span>;
            }
          })}
        </div>
      </div>
    </div>
  );
};
