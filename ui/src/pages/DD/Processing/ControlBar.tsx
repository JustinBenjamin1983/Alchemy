/**
 * ControlBar - Unified action bar for DD Console
 *
 * Clean horizontal toolbar with three logical groups:
 * 1. Document Prep (Classify, Readability)
 * 2. Accuracy Mode (segmented control)
 * 3. Primary Action (Run Due Diligence)
 */
import React from "react";
import {
  Play,
  Pause,
  Square,
  Loader2,
  RotateCcw,
  FolderCog,
  ScanText,
  Zap,
  Scale,
  Target,
  Crown,
  Check,
} from "lucide-react";
// Note: FolderPlus removed as Add Folder button is not in this component
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ModelTier } from "./AccuracyTierSelector";
import { cn } from "@/lib/utils";

interface ControlBarProps {
  onClassifyDocs: () => void;
  isClassifying: boolean;
  onAddFolder: () => void;
  onRunReadability: () => void;
  isCheckingReadability: boolean;
  readabilityComplete: boolean;
  readyCount: number;
  failedCount: number;
  selectedTier: ModelTier;
  onTierChange: (tier: ModelTier) => void;
  onRunDD: () => void;
  canRunDD: boolean;
  runDDTooltip: string;
  docsToProcessCount: number;
  isProcessing: boolean;
  isPaused: boolean;
  onPauseResume: () => void;
  onCancel: () => void;
  isCancelling: boolean;
  showRestart: boolean;
  onRestart: () => void;
  isRestarting: boolean;
  disabled?: boolean;
}

const TIER_OPTIONS: { id: ModelTier; label: string; fullName: string; icon: React.ReactNode; desc: string }[] = [
  { id: "cost_optimized", label: "Eco", fullName: "Economy", icon: <Zap className="h-3.5 w-3.5" />, desc: "~R18/100 docs, 85% accuracy" },
  { id: "balanced", label: "Bal", fullName: "Balanced", icon: <Scale className="h-3.5 w-3.5" />, desc: "~R25/100 docs, 90% accuracy" },
  { id: "high_accuracy", label: "High", fullName: "High Accuracy", icon: <Target className="h-3.5 w-3.5" />, desc: "~R35/100 docs, 93% accuracy" },
  { id: "maximum_accuracy", label: "Max", fullName: "Maximum", icon: <Crown className="h-3.5 w-3.5" />, desc: "~R50/100 docs, 95% accuracy" },
];

export const ControlBar: React.FC<ControlBarProps> = ({
  onClassifyDocs,
  isClassifying,
  onAddFolder,
  onRunReadability,
  isCheckingReadability,
  readabilityComplete,
  readyCount,
  failedCount,
  selectedTier,
  onTierChange,
  onRunDD,
  canRunDD,
  runDDTooltip,
  docsToProcessCount,
  isProcessing,
  isPaused,
  onPauseResume,
  onCancel,
  isCancelling,
  showRestart,
  onRestart,
  isRestarting,
  disabled = false,
}) => {
  // Processing mode - minimal bar with processing controls
  if (isProcessing) {
    return (
      <div className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 shadow-sm mb-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <div className="flex items-center gap-2.5">
            <Loader2 className="h-4 w-4 animate-spin text-[#ff6b00]" />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Processing <span className="font-semibold">{docsToProcessCount}</span> documents...
            </span>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={onPauseResume}
              className="h-8 px-3 text-xs border-gray-300 bg-white hover:bg-gray-50 transition-all duration-200 hover:scale-105 hover:shadow-md"
            >
              {isPaused ? (
                <><Play className="mr-1.5 h-3.5 w-3.5" />Resume</>
              ) : (
                <><Pause className="mr-1.5 h-3.5 w-3.5" />Pause</>
              )}
            </Button>
            {showRestart && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRestart}
                disabled={isRestarting}
                className="h-8 px-3 text-xs border-gray-300 bg-white hover:bg-gray-50 transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <RotateCcw className={cn("mr-1.5 h-3.5 w-3.5", isRestarting && "animate-spin")} />
                Restart
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onCancel}
              disabled={isCancelling}
              className="h-8 px-3 text-xs text-red-600 border-red-300 bg-white hover:bg-red-50 transition-all duration-200 hover:scale-105 hover:shadow-md"
            >
              <Square className={cn("mr-1.5 h-3.5 w-3.5", isCancelling && "animate-pulse")} />
              Cancel
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Normal mode - three-group layout
  return (
    <TooltipProvider delayDuration={300}>
      <div className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 shadow-sm mb-4">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 lg:gap-6">

          {/* GROUP 1: Document Preparation */}
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onClassifyDocs}
                  disabled={disabled || isClassifying}
                  className="h-9 w-32 text-sm font-medium border-gray-300 bg-white hover:bg-gray-50 gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md"
                >
                  {isClassifying ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FolderCog className="h-4 w-4 text-purple-500" />
                  )}
                  Classify
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2">
                <p className="text-sm text-white">AI document folder auto-classification</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRunReadability}
                  disabled={disabled || isCheckingReadability}
                  className={cn(
                    "h-9 w-32 text-sm font-medium border-gray-300 bg-white hover:bg-gray-50 gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md",
                    readabilityComplete && failedCount === 0 && "border-green-400 bg-green-50 text-green-700 hover:bg-green-100"
                  )}
                >
                  {isCheckingReadability ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : readabilityComplete && failedCount === 0 ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <ScanText className="h-4 w-4 text-blue-500" />
                  )}
                  Readability
                  {readabilityComplete && (
                    <span className={cn(
                      "text-xs font-semibold",
                      failedCount > 0 ? "text-amber-600" : "text-green-600"
                    )}>
                      {readyCount}{failedCount > 0 && `/${failedCount}`}
                    </span>
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2">
                <p className="text-sm text-white">Click to check document readability before performing a DD run</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Visual Divider - hidden on mobile */}
          <div className="hidden lg:block w-px h-8 bg-gray-300 dark:bg-gray-600" />

          {/* GROUP 2: Accuracy Mode Selector (Segmented Control) */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600 dark:text-gray-400 font-medium">Accuracy:</span>
            <div className="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden shadow-sm">
              {TIER_OPTIONS.map((tier, index) => {
                const isSelected = selectedTier === tier.id;
                const isFirst = index === 0;
                return (
                  <Tooltip key={tier.id}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => onTierChange(tier.id)}
                        disabled={disabled}
                        className={cn(
                          "flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-all duration-200",
                          !isFirst && "border-l border-gray-300 dark:border-gray-600",
                          isSelected
                            ? "bg-[#ff6b00] text-white hover:bg-[#e55f00]"
                            : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:scale-105",
                          disabled && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        {tier.icon}
                        {tier.label}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2">
                      <p className="text-sm font-semibold text-white">{tier.fullName}</p>
                      <p className="text-sm text-blue-200">{tier.desc}</p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          {/* Visual Divider - hidden on mobile */}
          <div className="hidden lg:block w-px h-8 bg-gray-300 dark:bg-gray-600" />

          {/* GROUP 3: Primary Action */}
          <div className="flex items-center gap-2 w-full lg:w-auto justify-end">
            {showRestart && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRestart}
                disabled={isRestarting}
                className="h-9 px-3 text-sm font-medium text-amber-600 border-amber-300 bg-white hover:bg-amber-50 transition-all duration-200 hover:scale-105 hover:shadow-md"
              >
                <RotateCcw className={cn("mr-1.5 h-4 w-4", isRestarting && "animate-spin")} />
                Restart
              </Button>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="flex-1 lg:flex-none">
                  <Button
                    onClick={onRunDD}
                    disabled={!canRunDD}
                    className={cn(
                      "h-10 px-5 text-sm font-semibold shadow-sm w-full lg:w-auto gap-2 transition-all duration-200",
                      canRunDD
                        ? "bg-[#ff6b00] hover:bg-[#e55f00] text-white hover:scale-105 hover:shadow-lg"
                        : "bg-gray-200 text-gray-400 cursor-not-allowed"
                    )}
                  >
                    <Play className="h-4 w-4" />
                    Run Due Diligence
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2">
                <p className="text-sm text-white">{runDDTooltip}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
};

export default ControlBar;
