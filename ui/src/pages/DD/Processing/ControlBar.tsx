/**
 * ControlBar - Unified action bar for DD Console
 *
 * Clean horizontal toolbar with three logical groups:
 * 1. Document Prep (Classify, Readability, Entity Map, Analyse)
 * 2. Accuracy Mode (segmented control)
 * 3. Primary Action (Generate Report)
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
  Network,
  Eye,
  FileSearch,
  FileText,
  ClipboardCheck,
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
  classificationComplete: boolean;
  onAddFolder: () => void;
  onRunReadability: () => void;
  isCheckingReadability: boolean;
  readabilityComplete: boolean;
  readyCount: number;
  failedCount: number;
  // Checkpoint A blocking condition
  canRunReadability?: boolean;
  needsReviewCount?: number;
  // Entity Mapping
  onRunEntityMapping: () => void;
  isRunningEntityMapping: boolean;
  entityMappingComplete: boolean;
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
  // Checkpoint C (post-analysis validation)
  onViewCheckpointC: () => void;
  isCreatingCheckpoint?: boolean;
  hasCheckpointC: boolean;
  checkpointCStatus?: 'awaiting_user_input' | 'completed' | 'skipped';
  // Generate Report (Pass 3-7)
  onGenerateReport: () => void;
  isGenerating: boolean;
  canGenerateReport: boolean;
  generateReportTooltip: string;
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

const TIER_OPTIONS: { id: ModelTier; label: string; fullName: string; icon: React.ReactNode; desc: string }[] = [
  { id: "cost_optimized", label: "Eco", fullName: "Economy", icon: <Zap className="h-3.5 w-3.5" />, desc: "~R18/100 docs, 85% accuracy" },
  { id: "balanced", label: "Bal", fullName: "Balanced", icon: <Scale className="h-3.5 w-3.5" />, desc: "~R25/100 docs, 90% accuracy" },
  { id: "high_accuracy", label: "High", fullName: "High Accuracy", icon: <Target className="h-3.5 w-3.5" />, desc: "~R35/100 docs, 93% accuracy" },
  { id: "maximum_accuracy", label: "Max", fullName: "Maximum", icon: <Crown className="h-3.5 w-3.5" />, desc: "~R50/100 docs, 95% accuracy" },
];

export const ControlBar: React.FC<ControlBarProps> = ({
  onClassifyDocs,
  isClassifying,
  classificationComplete,
  onAddFolder,
  onRunReadability,
  isCheckingReadability,
  readabilityComplete,
  readyCount,
  failedCount,
  canRunReadability = true,
  needsReviewCount = 0,
  onRunEntityMapping,
  isRunningEntityMapping,
  entityMappingComplete,
  canRunEntityMapping = false,
  entityCount = 0,
  onViewEntityMap,
  hasEntityMap,
  onAnalyzeDocuments,
  isAnalyzing,
  canAnalyze = false,
  analyzeComplete,
  onViewCheckpointC,
  isCreatingCheckpoint = false,
  hasCheckpointC,
  checkpointCStatus,
  onGenerateReport,
  isGenerating,
  canGenerateReport,
  generateReportTooltip,
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
                  className={cn(
                    "h-9 w-36 text-sm font-medium gap-2 transition-all duration-200",
                    classificationComplete && !isClassifying
                      ? "border-green-700 bg-green-50 text-green-700 hover:bg-green-100 hover:scale-105 hover:shadow-md"
                      : "border-gray-300 bg-white hover:bg-gray-50 hover:scale-105 hover:shadow-md"
                  )}
                >
                  {isClassifying ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : classificationComplete ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <FolderCog className="h-4 w-4 text-purple-500" />
                  )}
                  {classificationComplete ? "Classified" : "Classify Files"}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2">
                {classificationComplete ? (
                  <p className="text-sm text-white">Classification complete. Click to re-run AI classification.</p>
                ) : (
                  <p className="text-sm text-white">Run AI classification on all documents</p>
                )}
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onRunReadability}
                    disabled={disabled || isCheckingReadability || !canRunReadability}
                    className={cn(
                      "h-9 w-32 text-sm font-medium border-gray-300 bg-white hover:bg-gray-50 gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md",
                      readabilityComplete && failedCount === 0 && canRunReadability && "border-green-700 bg-green-50 text-green-700 hover:bg-green-100",
                      !canRunReadability && "border-amber-300 bg-amber-50 text-amber-700"
                    )}
                  >
                    {isCheckingReadability ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : !canRunReadability ? (
                      <span className="h-4 w-4 text-amber-500 text-xs font-bold">{needsReviewCount}</span>
                    ) : readabilityComplete && failedCount === 0 ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <ScanText className="h-4 w-4 text-blue-500" />
                    )}
                    Readability
                    {readabilityComplete && canRunReadability && (
                      <span className={cn(
                        "text-xs font-semibold",
                        failedCount > 0 ? "text-amber-600" : "text-green-700"
                      )}>
                        {readyCount}{failedCount > 0 && `/${failedCount}`}
                      </span>
                    )}
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2 max-w-xs">
                {!canRunReadability ? (
                  <div>
                    <p className="text-sm font-semibold text-amber-300">Classification Required</p>
                    <p className="text-sm text-white">{needsReviewCount} document{needsReviewCount !== 1 ? 's' : ''} in "Needs Review" must be assigned to folders before running readability check.</p>
                  </div>
                ) : (
                  <p className="text-sm text-white">Click to check document readability before performing a DD run</p>
                )}
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onRunEntityMapping}
                    disabled={disabled || isRunningEntityMapping || !canRunEntityMapping}
                    className={cn(
                      "h-9 w-36 text-sm font-medium border-gray-300 bg-white hover:bg-gray-50 gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md",
                      entityMappingComplete && canRunEntityMapping && "border-green-700 bg-green-50 text-green-700 hover:bg-green-100",
                      !canRunEntityMapping && "border-gray-200 bg-gray-50 text-gray-400"
                    )}
                  >
                    {isRunningEntityMapping ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : entityMappingComplete ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Network className="h-4 w-4 text-indigo-500" />
                    )}
                    Entity Map
                    {entityMappingComplete && entityCount > 0 && (
                      <span className="text-xs font-semibold text-green-700">
                        {entityCount}
                      </span>
                    )}
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2 max-w-xs">
                {!canRunEntityMapping ? (
                  <div>
                    <p className="text-sm font-semibold text-gray-300">Readability Required</p>
                    <p className="text-sm text-white">Complete readability check before running entity mapping.</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-white">Map entities across documents to identify relationships with the target company.</p>
                    <p className="text-sm text-indigo-300 mt-1">Identifies subsidiaries, counterparties, and related parties.</p>
                  </div>
                )}
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onViewEntityMap}
                    disabled={disabled || !hasEntityMap}
                    className={cn(
                      "h-9 w-40 text-sm font-medium border-gray-300 bg-white hover:bg-gray-50 gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md",
                      hasEntityMap && "border-indigo-400 bg-indigo-50 text-indigo-700 hover:bg-indigo-100",
                      !hasEntityMap && "border-gray-200 bg-gray-50 text-gray-400"
                    )}
                  >
                    <Eye className={cn("h-4 w-4", hasEntityMap ? "text-indigo-500" : "text-gray-400")} />
                    View Entity Map
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2 max-w-xs">
                {!hasEntityMap ? (
                  <div>
                    <p className="text-sm font-semibold text-gray-300">No Entity Map</p>
                    <p className="text-sm text-white">Run entity mapping first to generate the corporate organogram.</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-white">View the entity map showing corporate structure and relationships.</p>
                  </div>
                )}
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onAnalyzeDocuments}
                    disabled={disabled || isAnalyzing || !canAnalyze || analyzeComplete}
                    className={cn(
                      "h-9 w-28 text-sm font-medium gap-2 transition-all duration-200",
                      analyzeComplete
                        ? "border-green-700 bg-green-50 text-green-700 disabled:opacity-100 disabled:border-green-700 disabled:bg-green-50 disabled:text-green-700"
                        : canAnalyze
                          ? "border-gray-300 bg-white hover:bg-gray-50 hover:scale-105 hover:shadow-md"
                          : "border-gray-200 bg-gray-50 text-gray-400"
                    )}
                  >
                    {isAnalyzing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : analyzeComplete ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <FileSearch className={cn("h-4 w-4", canAnalyze ? "text-cyan-500" : "text-gray-400")} />
                    )}
                    Analyse
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2 max-w-xs">
                {analyzeComplete ? (
                  <div>
                    <p className="text-sm font-semibold text-green-400">Analysis Complete</p>
                    <p className="text-sm text-white">Document extraction and analysis finished. Click Reset to run again.</p>
                  </div>
                ) : !canAnalyze ? (
                  <div>
                    <p className="text-sm font-semibold text-gray-300">Entity Map Required</p>
                    <p className="text-sm text-white">Complete entity mapping and validate Checkpoint B before running analysis.</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-white">Extract and analyse document content.</p>
                    <p className="text-sm text-cyan-300 mt-1">Runs Pass 1 (Extraction) and Pass 2 (Analysis), then presents Checkpoint C for validation.</p>
                  </div>
                )}
              </TooltipContent>
            </Tooltip>

            {/* Checkpoint C Button - shows after analysis is complete */}
            {analyzeComplete && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onViewCheckpointC}
                    disabled={disabled || isCreatingCheckpoint}
                    className={cn(
                      "h-9 w-32 text-sm font-medium gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md",
                      checkpointCStatus === 'awaiting_user_input'
                        ? "border-amber-500 bg-amber-50 text-amber-700 hover:bg-amber-100"
                        : hasCheckpointC
                          ? "border-green-700 bg-green-50 text-green-700 hover:bg-green-100"
                          : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                    )}
                  >
                    {isCreatingCheckpoint ? (
                      <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
                    ) : checkpointCStatus === 'awaiting_user_input' ? (
                      <ClipboardCheck className="h-4 w-4 text-amber-600" />
                    ) : hasCheckpointC ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <ClipboardCheck className="h-4 w-4 text-gray-500" />
                    )}
                    {isCreatingCheckpoint ? "Creating..." : "Checkpoint C"}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2 max-w-xs">
                  {checkpointCStatus === 'awaiting_user_input' ? (
                    <div>
                      <p className="text-sm font-semibold text-amber-300">Validation Required</p>
                      <p className="text-sm text-white">Review AI findings and confirm understanding before generating report.</p>
                    </div>
                  ) : hasCheckpointC ? (
                    <div>
                      <p className="text-sm font-semibold text-green-400">Validation Complete</p>
                      <p className="text-sm text-white">Click to review the validated checkpoint data.</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-semibold text-gray-300">No Checkpoint Data</p>
                      <p className="text-sm text-white">Checkpoint C data not yet available from analysis.</p>
                    </div>
                  )}
                </TooltipContent>
              </Tooltip>
            )}

            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onGenerateReport}
                    disabled={disabled || !canGenerateReport || isGenerating}
                    className={cn(
                      "h-9 w-36 text-sm font-medium border-gray-300 bg-white hover:bg-gray-50 gap-2 transition-all duration-200 hover:scale-105 hover:shadow-md",
                      canGenerateReport && !isGenerating && "border-orange-400 bg-orange-50 text-orange-700 hover:bg-orange-100",
                      !canGenerateReport && "border-gray-200 bg-gray-50 text-gray-400"
                    )}
                  >
                    {isGenerating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <FileText className={cn("h-4 w-4", canGenerateReport ? "text-orange-500" : "text-gray-400")} />
                    )}
                    Generate Report
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-alchemyPrimaryNavyBlue border-alchemyPrimaryNavyBlue px-3 py-2 max-w-xs">
                {!canGenerateReport ? (
                  <div>
                    <p className="text-sm font-semibold text-gray-300">Analysis Required</p>
                    <p className="text-sm text-white">{generateReportTooltip}</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-white">Generate the Due Diligence report.</p>
                    <p className="text-sm text-orange-300 mt-1">Runs Pass 3-7: Cross-document analysis, synthesis, and report generation.</p>
                  </div>
                )}
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

          {/* GROUP 3: Restart (only shown when needed) */}
          {showRestart && (
            <>
            {/* Visual Divider - hidden on mobile */}
            <div className="hidden lg:block w-px h-8 bg-gray-300 dark:bg-gray-600" />
            <div className="flex items-center gap-2 w-full lg:w-auto justify-end">
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
            </>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
};

export default ControlBar;
