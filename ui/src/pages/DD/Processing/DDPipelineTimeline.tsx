/**
 * DDPipelineTimeline - Sequential chevron-flow timeline for DD processing
 *
 * Clean interlocking chevron design showing:
 * - Pre-Processing: Classify, Readability, Entity Map, View Entities
 * - Analysis: Extract & Assess
 * - Validation: Checkpoint C
 * - Synthesis: Synthesise Report
 */
import React, { useState } from "react";
import {
  Loader2,
  FolderCog,
  ScanText,
  Network,
  FileSearch,
  ClipboardCheck,
  FileText,
  Check,
  Lock,
  BarChart3,
  ChevronRight,
  X,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

// ============================================
// Re-run Warning Messages
// ============================================

const getFailureExplanation = (stepId: string): { title: string; cause: string; action: string } => {
  switch (stepId) {
    case 'classify':
      return {
        title: 'Classification Failed',
        cause: 'The AI could not sort your documents into folders. This may be due to unrecognised file formats or a temporary connection issue.',
        action: 'Click to try again. If the problem persists, check that your documents are standard PDF, Word, or Excel files.',
      };
    case 'readability':
      return {
        title: 'Readability Check Failed',
        cause: 'Some documents could not be converted to searchable format. This often happens with scanned images or password-protected files.',
        action: 'Click to retry. You may need to re-scan poor quality documents or unlock protected files.',
      };
    case 'entity-map':
      return {
        title: 'Entity Mapping Failed',
        cause: 'The AI could not identify the parties in your documents. This may happen if documents are heavily formatted or contain unusual text layouts.',
        action: 'Click to try again. If it fails repeatedly, ensure documents are searchable PDFs.',
      };
    case 'analyze':
      return {
        title: 'Document Analysis Failed',
        cause: 'The AI encountered an error while extracting data or assessing risks. This could be due to API limits, malformed document content, or a temporary outage.',
        action: 'Click to retry the analysis. If it continues to fail, try reducing the number of documents or contact support.',
      };
    case 'checkpoint-c':
      return {
        title: 'Checkpoint Creation Failed',
        cause: 'The validation checkpoint could not be generated. This may be due to missing analysis data or a database error.',
        action: 'Click to retry. If the issue persists, try re-running the Extract & Assess step first.',
      };
    case 'generate-report':
      return {
        title: 'Report Synthesis Failed',
        cause: 'The AI could not generate your final report. This is often caused by incomplete validation data or an API timeout during the multi-step synthesis process.',
        action: 'Click to try again. Ensure Checkpoint C is completed. For large document sets, this may take multiple attempts.',
      };
    default:
      return {
        title: 'Step Failed',
        cause: 'An unexpected error occurred during processing.',
        action: 'Click to retry. If the problem persists, please contact support.',
      };
  }
};

const getRerunWarning = (stepId: string): { title: string; description: string; impact: string } => {
  switch (stepId) {
    case 'classify':
      return {
        title: 'Re-run Classification?',
        description: 'This will re-classify all documents in the data room using AI.',
        impact: 'Documents may be moved to different category folders. Any manual folder assignments will be overwritten.',
      };
    case 'readability':
      return {
        title: 'Re-run Readability Check?',
        description: 'This will re-process all documents to validate formats and convert to searchable PDFs.',
        impact: 'Previously converted documents will be re-processed. This may take some time depending on the number of documents.',
      };
    case 'entity-map':
      return {
        title: 'Re-run Entity Mapping?',
        description: 'This will re-scan all documents to identify parties and rebuild the entity relationship map.',
        impact: 'The existing entity map will be replaced. Any manual entity edits or relationship corrections will be lost.',
      };
    case 'analyze':
      return {
        title: 'Re-run Document Analysis?',
        description: 'This will re-extract key data points and re-assess legal risks across all documents.',
        impact: 'All existing analysis findings will be replaced. Checkpoint C validation will need to be completed again before generating a new report.',
      };
    case 'checkpoint-c':
      return {
        title: 'Re-open Checkpoint C?',
        description: 'This will open the validation checkpoint for review.',
        impact: 'You can review and update your validation responses. The report may need to be regenerated if changes are made.',
      };
    case 'generate-report':
      return {
        title: 'Re-generate Report?',
        description: 'This will synthesise a new DD report from the current analysis findings.',
        impact: 'The existing report will be replaced with a newly generated version based on current data.',
      };
    default:
      return {
        title: 'Re-run Step?',
        description: 'This will re-run the selected processing step.',
        impact: 'Previous results from this step may be overwritten.',
      };
  }
};

// ============================================
// Types
// ============================================

export type StepState = 'completed' | 'active' | 'available' | 'locked' | 'optional' | 'failed';

export interface PipelineStep {
  id: string;
  label: string;
  state: StepState;
  count?: number;
  tooltip: string;
  phase: string;
  icon: React.ReactNode;
  activeIcon?: React.ReactNode;
  onClick?: () => void;
}

interface DDPipelineTimelineProps {
  steps: PipelineStep[];
  onStepClick?: (stepId: string) => void;
  onViewAnalysis?: () => void;
  hasAnalysisResults?: boolean;
  className?: string;
}

// ============================================
// Helper Functions
// ============================================

const getStateStyles = (state: StepState): string => {
  switch (state) {
    case 'completed':
      return "bg-emerald-200 border-2 border-emerald-600 text-emerald-700 cursor-pointer hover:bg-emerald-300";
    case 'active':
      return "bg-amber-200 border-2 border-amber-500 text-amber-700";
    case 'available':
      return "bg-amber-200 border-2 border-amber-500 text-amber-700 cursor-pointer hover:bg-amber-300";
    case 'failed':
      return "bg-red-200 border-2 border-red-600 text-red-700 cursor-pointer hover:bg-red-300";
    case 'optional':
      return "bg-slate-200 border-2 border-slate-400 text-slate-600 cursor-pointer hover:bg-slate-300";
    case 'locked':
      return "bg-slate-200 border-2 border-slate-300 text-slate-400 cursor-not-allowed";
    default:
      return "bg-slate-200 border-2 border-slate-400 text-slate-600";
  }
};

const getIcon = (step: PipelineStep): React.ReactNode => {
  if (step.state === 'active' && step.activeIcon) {
    return step.activeIcon;
  }

  switch (step.state) {
    case 'completed':
      return <Check className="h-5 w-5" />;
    case 'active':
      return <Loader2 className="h-5 w-5 animate-spin" />;
    case 'failed':
      return <X className="h-5 w-5" />;
    case 'locked':
      return <Lock className="h-4 w-4" />;
    default:
      return step.icon;
  }
};

// ============================================
// Main Component
// ============================================

export const DDPipelineTimeline: React.FC<DDPipelineTimelineProps> = ({
  steps,
  onStepClick,
  onViewAnalysis,
  hasAnalysisResults = false,
  className,
}) => {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);
  const [isAnalysisHovered, setIsAnalysisHovered] = useState(false);
  const [pendingRerunStep, setPendingRerunStep] = useState<PipelineStep | null>(null);

  const handleStepClick = (step: PipelineStep) => {
    if (step.state === 'completed') {
      // Show confirmation dialog for completed steps
      setPendingRerunStep(step);
    } else if (step.state === 'available' || step.state === 'optional' || step.state === 'failed') {
      // Allow clicking on available, optional, or failed steps
      step.onClick?.();
      onStepClick?.(step.id);
    }
  };

  const handleConfirmRerun = () => {
    if (pendingRerunStep) {
      pendingRerunStep.onClick?.();
      onStepClick?.(pendingRerunStep.id);
      setPendingRerunStep(null);
    }
  };

  const handleCancelRerun = () => {
    setPendingRerunStep(null);
  };

  const rerunWarning = pendingRerunStep ? getRerunWarning(pendingRerunStep.id) : null;

  return (
    <TooltipProvider delayDuration={200}>
      <div className={cn(
        "bg-slate-900 rounded-xl p-4 shadow-lg",
        className
      )}>
        {/* Chevron Steps Row - Full Width */}
        <div className="flex items-center">
          {steps.map((step, index) => {
            const isHovered = hoveredStep === step.id;
            const isClickable = step.state === 'available' || step.state === 'optional' || step.state === 'completed' || step.state === 'failed';

            return (
              <Tooltip key={step.id}>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      "relative flex items-center justify-center gap-2 py-2.5 transition-all duration-150 flex-1",
                      getStateStyles(step.state),
                      isHovered && isClickable && "brightness-110"
                    )}
                    style={{
                      clipPath: index === 0
                        ? 'polygon(0 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 0 100%)'
                        : 'polygon(0 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 0 100%, 12px 50%)',
                      paddingLeft: index === 0 ? '14px' : '22px',
                      paddingRight: '20px',
                      marginLeft: index === 0 ? '0' : '-8px',
                      zIndex: steps.length - index + 1,
                    }}
                    onMouseEnter={() => setHoveredStep(step.id)}
                    onMouseLeave={() => setHoveredStep(null)}
                    onClick={() => handleStepClick(step)}
                  >
                    {/* Icon */}
                    <span className="flex-shrink-0">
                      {getIcon(step)}
                    </span>

                    {/* Label */}
                    <span className="font-semibold text-base whitespace-nowrap">
                      {step.label}
                    </span>

                    {/* Count badge */}
                    {step.count !== undefined && step.count > 0 && (
                      <span className="text-sm opacity-70 ml-0.5">
                        ({step.count})
                      </span>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent
                  side="bottom"
                  className={cn(
                    "border px-3 py-2 shadow-xl",
                    step.state === 'failed'
                      ? "bg-red-900 border-red-700 max-w-sm"
                      : "bg-slate-800 border-slate-700 max-w-xs"
                  )}
                >
                  {step.state === 'failed' ? (
                    <>
                      <p className="text-sm font-semibold text-red-200">
                        {getFailureExplanation(step.id).title}
                      </p>
                      <p className="text-xs text-red-100 mt-1.5">
                        {getFailureExplanation(step.id).cause}
                      </p>
                      <p className="text-xs text-amber-300 mt-2 font-medium">
                        {getFailureExplanation(step.id).action}
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-sm text-white">
                        {step.tooltip}
                      </p>
                      {step.state === 'locked' && (
                        <p className="text-xs text-amber-400 mt-1">
                          Complete previous steps first
                        </p>
                      )}
                    </>
                  )}
                </TooltipContent>
              </Tooltip>
            );
          })}

          {/* View Analysis Button - Always at the end */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={onViewAnalysis}
                disabled={!hasAnalysisResults}
                onMouseEnter={() => setIsAnalysisHovered(true)}
                onMouseLeave={() => setIsAnalysisHovered(false)}
                className={cn(
                  "relative flex items-center justify-center gap-2 py-2.5 px-4 transition-all duration-150 flex-shrink-0",
                  hasAnalysisResults
                    ? "bg-amber-500 border-2 border-amber-600 text-white cursor-pointer hover:bg-amber-400"
                    : "bg-white border-2 border-slate-300 text-slate-400 cursor-not-allowed",
                  isAnalysisHovered && hasAnalysisResults && "brightness-110"
                )}
                style={{
                  clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%, 12px 50%)',
                  paddingLeft: '22px',
                  marginLeft: '-8px',
                  zIndex: 0,
                }}
              >
                <BarChart3 className="h-5 w-5" />
                <span className="font-semibold text-base whitespace-nowrap">
                  View Analysis
                </span>
                <ChevronRight className="h-6 w-6 ml-1" />
              </button>
            </TooltipTrigger>
            <TooltipContent
              side="bottom"
              className="bg-slate-800 border-slate-700 px-3 py-2 max-w-xs shadow-xl"
            >
              <p className="text-sm text-white">
                {hasAnalysisResults
                  ? "View detailed analysis results, findings, and risk assessments"
                  : "Complete document analysis to view results"}
              </p>
            </TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Re-run Confirmation Dialog */}
      <AlertDialog open={!!pendingRerunStep} onOpenChange={(open) => !open && handleCancelRerun()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{rerunWarning?.title}</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>{rerunWarning?.description}</p>
                <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                  <p className="text-amber-800 text-sm font-medium">Impact:</p>
                  <p className="text-amber-700 text-sm mt-1">{rerunWarning?.impact}</p>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelRerun}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmRerun}
              className="bg-amber-600 hover:bg-amber-700"
            >
              Yes, Re-run
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </TooltipProvider>
  );
};

// ============================================
// Step Builder Helper
// ============================================

export interface DDPipelineState {
  // Classification
  isClassifying: boolean;
  classificationComplete: boolean;
  classificationFailed?: boolean;
  // Readability
  isCheckingReadability: boolean;
  readabilityComplete: boolean;
  readabilityFailed?: boolean;
  canRunReadability: boolean;
  readyCount: number;
  // Entity Mapping
  isRunningEntityMapping: boolean;
  entityMappingComplete: boolean;
  entityMappingFailed?: boolean;
  canRunEntityMapping: boolean;
  entityCount: number;
  hasEntityMap: boolean;
  // Analysis
  isAnalyzing: boolean;
  analyzeComplete: boolean;
  analyzeFailed?: boolean;
  canAnalyze: boolean;
  // Checkpoint C
  isCreatingCheckpoint: boolean;
  hasCheckpointC: boolean;
  checkpointCFailed?: boolean;
  checkpointCStatus?: 'awaiting_user_input' | 'completed' | 'skipped';
  // Generate Report
  isGenerating: boolean;
  canGenerateReport: boolean;
  generateReportFailed?: boolean;
  generateReportComplete?: boolean;  // True when synthesis has completed successfully
}

export interface DDPipelineCallbacks {
  onClassifyDocs: () => void;
  onRunReadability: () => void;
  onRunEntityMapping: () => void;
  onAnalyzeDocuments: () => void;
  onViewCheckpointC: () => void;
  onGenerateReport: () => void;
}

export function buildPipelineSteps(
  state: DDPipelineState,
  callbacks: DDPipelineCallbacks
): PipelineStep[] {
  const steps: PipelineStep[] = [];

  // Determine states for each step
  // Note: Check completion BEFORE failure - if step completed successfully, show green
  const getClassifyState = (): StepState => {
    if (state.isClassifying) return 'active';
    if (state.classificationComplete) return 'completed';
    if (state.classificationFailed) return 'failed';
    return 'available';
  };

  const getReadabilityState = (): StepState => {
    if (state.isCheckingReadability) return 'active';
    if (state.readabilityComplete) return 'completed';
    if (state.readabilityFailed) return 'failed';
    if (!state.canRunReadability) return 'locked';
    if (state.classificationComplete) return 'available';
    return 'locked';
  };

  const getEntityMapState = (): StepState => {
    if (state.isRunningEntityMapping) return 'active';
    if (state.entityMappingComplete) return 'completed';
    if (state.entityMappingFailed) return 'failed';
    if (!state.canRunEntityMapping) return 'locked';
    if (state.readabilityComplete) return 'available';
    return 'locked';
  };

  const getAnalyzeState = (): StepState => {
    if (state.isAnalyzing) return 'active';
    if (state.analyzeComplete) return 'completed';
    if (state.analyzeFailed) return 'failed';
    if (!state.canAnalyze) return 'locked';
    return 'available';
  };

  const getCheckpointCState = (): StepState => {
    if (state.isCreatingCheckpoint) return 'active';
    if (state.checkpointCStatus === 'completed' || state.checkpointCStatus === 'skipped') return 'completed';
    if (state.checkpointCFailed) return 'failed';
    if (state.checkpointCStatus === 'awaiting_user_input') return 'available';
    if (!state.analyzeComplete) return 'locked';
    if (state.hasCheckpointC) return 'available';
    return 'locked';
  };

  const getGenerateReportState = (): StepState => {
    if (state.isGenerating) return 'active';
    if (state.generateReportComplete) return 'completed';  // Green when synthesis done
    if (state.generateReportFailed) return 'failed';
    if (!state.canGenerateReport) return 'locked';
    return 'available';
  };

  // Pre-Processing Phase
  steps.push({
    id: 'classify',
    label: 'Classify',
    state: getClassifyState(),
    count: state.classificationComplete ? undefined : undefined,
    tooltip: 'Automatically sort documents into category folders using AI classification',
    phase: 'Pre-Processing',
    icon: <FolderCog className="h-5 w-5" />,
    onClick: callbacks.onClassifyDocs,
  });

  steps.push({
    id: 'readability',
    label: 'Readability',
    state: getReadabilityState(),
    count: state.readabilityComplete ? state.readyCount : undefined,
    tooltip: 'Validate document formats and convert to searchable PDF for analysis',
    phase: 'Pre-Processing',
    icon: <ScanText className="h-5 w-5" />,
    onClick: callbacks.onRunReadability,
  });

  steps.push({
    id: 'entity-map',
    label: 'Entity Map',
    state: getEntityMapState(),
    count: state.entityMappingComplete ? state.entityCount : undefined,
    tooltip: 'Identify all parties mentioned in documents and map relationships to target company',
    phase: 'Pre-Processing',
    icon: <Network className="h-5 w-5" />,
    onClick: callbacks.onRunEntityMapping,
  });

  // Analysis Phase
  steps.push({
    id: 'analyze',
    label: 'Extract & Assess',
    state: getAnalyzeState(),
    tooltip: 'Extract key data points and identify legal risks across all documents (Pass 1-2)',
    phase: 'Analysis',
    icon: <FileSearch className="h-5 w-5" />,
    onClick: callbacks.onAnalyzeDocuments,
  });

  // Validation Phase
  steps.push({
    id: 'checkpoint-c',
    label: 'Checkpoint C',
    state: getCheckpointCState(),
    tooltip: 'Review AI findings and confirm understanding before final report synthesis',
    phase: 'Validation',
    icon: <ClipboardCheck className="h-5 w-5" />,
    onClick: callbacks.onViewCheckpointC,
  });

  // Synthesis Phase
  steps.push({
    id: 'generate-report',
    label: 'Synthesise Report',
    state: getGenerateReportState(),
    tooltip: 'Cross-reference findings, calculate exposures, and generate final DD report (Pass 3-7)',
    phase: 'Synthesis',
    icon: <FileText className="h-5 w-5" />,
    onClick: callbacks.onGenerateReport,
  });

  return steps;
}

export default DDPipelineTimeline;
