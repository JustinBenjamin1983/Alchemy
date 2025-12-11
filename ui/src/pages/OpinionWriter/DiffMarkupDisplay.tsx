// File: ui/src/pages/OpinionWriter/DiffMarkupDisplay.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Check, X, Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";
import * as Diff from "diff";

interface DiffMarkupDisplayProps {
  originalText: string;
  modifiedText: string;
  onAcceptChanges: () => void;
  onRejectChanges: () => void;
  className?: string;
}

export const DiffMarkupDisplay = ({
  originalText,
  modifiedText,
  onAcceptChanges,
  onRejectChanges,
  className,
}: DiffMarkupDisplayProps) => {
  const [showMarkup, setShowMarkup] = useState(true);

  // Generate diff
  const changes = Diff.diffWords(originalText, modifiedText);

  // Render the diff with markup
  const renderDiff = () => {
    return changes.map((change, index) => {
      if (change.added) {
        return (
          <span
            key={index}
            className="bg-green-100 text-green-800 border-b-2 border-green-400 px-0.5"
            title="Added by Alchemio"
          >
            {change.value}
          </span>
        );
      }
      if (change.removed) {
        return (
          <span
            key={index}
            className="bg-red-100 text-red-800 line-through px-0.5"
            title="Removed by Alchemio"
          >
            {change.value}
          </span>
        );
      }
      return <span key={index}>{change.value}</span>;
    });
  };

  // Count changes
  const addedCount = changes.filter((c) => c.added).length;
  const removedCount = changes.filter((c) => c.removed).length;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Controls header */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-sm">
              <span className="inline-block w-3 h-3 bg-green-400 rounded"></span>
              <span className="text-green-700 font-medium">
                {addedCount} additions
              </span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              <span className="inline-block w-3 h-3 bg-red-400 rounded"></span>
              <span className="text-red-700 font-medium">
                {removedCount} deletions
              </span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowMarkup(!showMarkup)}
            className="h-8 px-2"
          >
            {showMarkup ? (
              <>
                <EyeOff className="w-4 h-4 mr-1" />
                <span className="text-xs">Hide Markup</span>
              </>
            ) : (
              <>
                <Eye className="w-4 h-4 mr-1" />
                <span className="text-xs">Show Markup</span>
              </>
            )}
          </Button>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={onAcceptChanges}
            className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
          >
            <Check className="w-4 h-4" />
            Accept All Changes
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onRejectChanges}
            className="border-red-300 text-red-700 hover:bg-red-50 flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            Reject Changes
          </Button>
        </div>
      </div>

      {/* Content display */}
      <div className="bg-white rounded-lg border p-6 max-h-[700px] overflow-y-auto">
        <div className="prose prose-sm max-w-none whitespace-pre-wrap font-mono text-sm leading-relaxed">
          {showMarkup ? renderDiff() : modifiedText}
        </div>
      </div>

      {/* Legend */}
      <div className="text-xs text-gray-500 flex items-center gap-4 px-2">
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 bg-green-100 border border-green-400"></span>
          <span>Added text (green)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 bg-red-100"></span>
          <span>Removed text (red, strikethrough)</span>
        </div>
      </div>
    </div>
  );
};
