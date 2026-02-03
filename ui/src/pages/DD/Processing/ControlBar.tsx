/**
 * ControlBar - Unified action bar for DD Console
 *
 * Now uses DDPipelineTimeline for a sequential chevron-flow display showing:
 * - Pre-Processing: Classify, Readability, Entity Map, View Entities
 * - Analysis: Extract & Assess
 * - Validation: Checkpoint C
 * - Synthesis: Synthesise Report
 *
 * NOTE: Accuracy Mode and Restart sections are commented out for future use
 */
import React from "react";
import {
  Play,
  Pause,
  Square,
  Loader2,
  RotateCcw,
  // NOTE: These icons are now handled by DDPipelineTimeline
  // FolderCog,
  // ScanText,
  // Zap,
  // Scale,
  // Target,
  // Crown,
  // Check,
  // Network,
  // Eye,
  // FileSearch,
  // FileText,
  // ClipboardCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
// NOTE: Tooltips are now handled inside DDPipelineTimeline
// import {
//   Tooltip,
//   TooltipContent,
//   TooltipProvider,
//   TooltipTrigger,
// } from "@/components/ui/tooltip";
import { ModelTier } from "./AccuracyTierSelector";
import { cn } from "@/lib/utils";
import { DDPipelineTimeline, buildPipelineSteps, DDPipelineState, DDPipelineCallbacks } from "./DDPipelineTimeline";

interface ControlBarProps {
  onClassifyDocs: () => void;
  isClassifying: boolean;
  classificationComplete: boolean;
  classificationFailed?: boolean;
  onAddFolder: () => void;
  onRunReadability: () => void;
  isCheckingReadability: boolean;
  readabilityComplete: boolean;
  readabilityFailed?: boolean;
  readyCount: number;
  failedCount: number;
  // Checkpoint A blocking condition
  canRunReadability?: boolean;
  needsReviewCount?: number;
  // Entity Mapping
  onRunEntityMapping: () => void;
  isRunningEntityMapping: boolean;
  entityMappingComplete: boolean;
  entityMappingFailed?: boolean;
  canRunEntityMapping?: boolean;
  entityCount?: number;
  // View Entity Map
  onViewEntityMap: () => void;
  hasEntityMap: boolean;
  // Analyze Documents (Pass 1-2)
  onAnalyzeDocuments: () => void;
  isAnalyzing: boolean;
  canAnalyze?: boolean;
  analyzeComplete: boolean;
  analyzeFailed?: boolean;
  // Checkpoint C (post-analysis validation)
  onViewCheckpointC: () => void;
  isCreatingCheckpoint?: boolean;
  hasCheckpointC: boolean;
  checkpointCFailed?: boolean;
  checkpointCStatus?: 'awaiting_user_input' | 'completed' | 'skipped';
  // Generate Report (Pass 3-7)
  onGenerateReport: () => void;
  isGenerating: boolean;
  canGenerateReport: boolean;
  generateReportFailed?: boolean;
  generateReportComplete?: boolean;
  generateReportTooltip: string;
  // View Analysis
  onViewAnalysis?: () => void;
  hasAnalysisResults?: boolean;
  selectedTier: ModelTier;
  onTierChange: (tier: ModelTier) => void;
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

// NOTE: Accuracy tier options commented out for future use
// const TIER_OPTIONS: { id: ModelTier; label: string; fullName: string; icon: React.ReactNode; desc: string }[] = [
//   { id: "cost_optimized", label: "Eco", fullName: "Economy", icon: <Zap className="h-3.5 w-3.5" />, desc: "~R18/100 docs, 85% accuracy" },
//   { id: "balanced", label: "Bal", fullName: "Balanced", icon: <Scale className="h-3.5 w-3.5" />, desc: "~R25/100 docs, 90% accuracy" },
//   { id: "high_accuracy", label: "High", fullName: "High Accuracy", icon: <Target className="h-3.5 w-3.5" />, desc: "~R35/100 docs, 93% accuracy" },
//   { id: "maximum_accuracy", label: "Max", fullName: "Maximum", icon: <Crown className="h-3.5 w-3.5" />, desc: "~R50/100 docs, 95% accuracy" },
// ];

export const ControlBar: React.FC<ControlBarProps> = ({
  onClassifyDocs,
  isClassifying,
  classificationComplete,
  classificationFailed = false,
  onAddFolder,
  onRunReadability,
  isCheckingReadability,
  readabilityComplete,
  readabilityFailed = false,
  readyCount,
  failedCount,
  canRunReadability = true,
  needsReviewCount = 0,
  onRunEntityMapping,
  isRunningEntityMapping,
  entityMappingComplete,
  entityMappingFailed = false,
  canRunEntityMapping = false,
  entityCount = 0,
  onViewEntityMap,
  hasEntityMap,
  onAnalyzeDocuments,
  isAnalyzing,
  canAnalyze = false,
  analyzeComplete,
  analyzeFailed = false,
  onViewCheckpointC,
  isCreatingCheckpoint = false,
  hasCheckpointC,
  checkpointCFailed = false,
  checkpointCStatus,
  onGenerateReport,
  isGenerating,
  canGenerateReport,
  generateReportFailed = false,
  generateReportComplete = false,
  generateReportTooltip,
  onViewAnalysis,
  hasAnalysisResults = false,
  selectedTier,
  onTierChange,
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

  // Build pipeline state and callbacks for DDPipelineTimeline
  const pipelineState: DDPipelineState = {
    isClassifying,
    classificationComplete,
    classificationFailed,
    isCheckingReadability,
    readabilityComplete,
    readabilityFailed,
    canRunReadability,
    readyCount,
    isRunningEntityMapping,
    entityMappingComplete,
    entityMappingFailed,
    canRunEntityMapping,
    entityCount,
    hasEntityMap,
    isAnalyzing,
    analyzeComplete,
    analyzeFailed,
    canAnalyze,
    isCreatingCheckpoint,
    hasCheckpointC,
    checkpointCFailed,
    checkpointCStatus,
    isGenerating,
    canGenerateReport,
    generateReportFailed,
    generateReportComplete,
  };

  const pipelineCallbacks: DDPipelineCallbacks = {
    onClassifyDocs,
    onRunReadability,
    onRunEntityMapping,
    onAnalyzeDocuments,
    onViewCheckpointC,
    onGenerateReport,
  };

  const pipelineSteps = buildPipelineSteps(pipelineState, pipelineCallbacks);

  // Normal mode - Sequential Pipeline Timeline
  return (
    <div className="mb-4">
      <DDPipelineTimeline
        steps={pipelineSteps}
        onViewAnalysis={onViewAnalysis}
        hasAnalysisResults={hasAnalysisResults}
        className={cn(disabled && "opacity-50 pointer-events-none")}
      />

      {/* ============================================
       * NOTE: The following sections are commented out for future use.
       * They may be re-enabled when needed:
       * - GROUP 2: Accuracy Mode Selector (Eco, Bal, High, Max)
       * - GROUP 3: Restart button
       * ============================================ */}

      {/* GROUP 2: Accuracy Mode Selector (Segmented Control) - COMMENTED OUT
      <TooltipProvider delayDuration={300}>
        <div className="flex items-center gap-3 mt-3">
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
      </TooltipProvider>
      */}

      {/* GROUP 3: Restart (only shown when needed) - COMMENTED OUT
      {showRestart && (
        <div className="flex items-center gap-2 mt-3 justify-end">
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
        </div>
      )}
      */}
    </div>
  );
};

export default ControlBar;
