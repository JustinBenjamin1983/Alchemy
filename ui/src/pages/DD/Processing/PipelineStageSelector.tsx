// File: ui/src/pages/DD/Processing/PipelineStageSelector.tsx
/**
 * Pipeline Stage Selector Component
 *
 * Displays the current pipeline progress and allows resuming from specific stages.
 * Shows a visual timeline of all stages with completion status.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Loader2,
  Play,
  Pause,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  Circle,
  Clock,
} from "lucide-react";
import {
  useGetPipelineProgress,
  useGetStageMetadata,
  useResumeFromStage,
  usePausePipeline,
  PipelineStage,
  PipelinePhase,
  StageMetadata,
} from "@/hooks/usePipelineProgress";

interface PipelineStageSelectorProps {
  ddId: string | null;
  onStageChange?: (stage: PipelineStage) => void;
}

// Phase colors and icons
const PHASE_COLORS: Record<PipelinePhase, string> = {
  pre_processing: "bg-blue-500",
  processing: "bg-orange-500",
  post_processing: "bg-green-500",
};

const PHASE_NAMES: Record<PipelinePhase, string> = {
  pre_processing: "Pre-Processing",
  processing: "Processing",
  post_processing: "Post-Processing",
};

export function PipelineStageSelector({
  ddId,
  onStageChange,
}: PipelineStageSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [confirmResumeStage, setConfirmResumeStage] = useState<StageMetadata | null>(null);
  const [expandedPhases, setExpandedPhases] = useState<Set<PipelinePhase>>(
    new Set(["pre_processing", "processing"])
  );

  const { data: progress, isLoading: progressLoading } = useGetPipelineProgress(ddId);
  const { data: metadata } = useGetStageMetadata();
  const resumeFromStage = useResumeFromStage();
  const pausePipeline = usePausePipeline();

  if (!ddId) return null;

  const handleResumeConfirm = async () => {
    if (!confirmResumeStage) return;

    try {
      await resumeFromStage.mutateAsync({
        ddId,
        stage: confirmResumeStage.id,
      });
      setConfirmResumeStage(null);
      onStageChange?.(confirmResumeStage.id);
    } catch (error) {
      console.error("Failed to resume from stage:", error);
    }
  };

  const handlePause = async () => {
    try {
      await pausePipeline.mutateAsync({ ddId });
    } catch (error) {
      console.error("Failed to pause pipeline:", error);
    }
  };

  const togglePhase = (phase: PipelinePhase) => {
    const newExpanded = new Set(expandedPhases);
    if (newExpanded.has(phase)) {
      newExpanded.delete(phase);
    } else {
      newExpanded.add(phase);
    }
    setExpandedPhases(newExpanded);
  };

  const getStageIcon = (stage: StageMetadata, isCompleted: boolean, isCurrent: boolean) => {
    if (isCompleted) {
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    }
    if (isCurrent) {
      return <Loader2 className="h-4 w-4 animate-spin text-blue-600" />;
    }
    if (stage.is_checkpoint) {
      return <Clock className="h-4 w-4 text-amber-500" />;
    }
    return <Circle className="h-4 w-4 text-gray-300" />;
  };

  // Group stages by phase
  const stagesByPhase = metadata?.stages.reduce((acc, stage) => {
    if (!acc[stage.phase]) {
      acc[stage.phase] = [];
    }
    acc[stage.phase].push(stage);
    return acc;
  }, {} as Record<PipelinePhase, StageMetadata[]>) || {};

  const completedStages = new Set(progress?.completed_stages || []);
  const currentStage = progress?.pipeline_stage;

  return (
    <div className="space-y-4">
      {/* Progress Summary Bar */}
      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Pipeline Progress</span>
            {progress?.status === "processing" && (
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                Processing
              </Badge>
            )}
            {progress?.status === "paused" && (
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                <Pause className="h-3 w-3 mr-1" />
                Paused
              </Badge>
            )}
            {progress?.status === "completed" && (
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                <Check className="h-3 w-3 mr-1" />
                Completed
              </Badge>
            )}
          </div>
          <span className="text-sm text-muted-foreground">
            {progress?.overall_progress || 0}%
          </span>
        </div>
        <Progress value={progress?.overall_progress || 0} className="h-2" />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-muted-foreground">
            Current: {progress?.current_stage_name || "Not started"}
          </span>
          <div className="flex gap-2">
            {progress?.status === "processing" && (
              <Button
                variant="outline"
                size="sm"
                onClick={handlePause}
                disabled={pausePipeline.isPending}
              >
                <Pause className="h-3 w-3 mr-1" />
                Pause
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsOpen(true)}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Resume from Stage
            </Button>
          </div>
        </div>
      </div>

      {/* Resume from Stage Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Resume from Stage</DialogTitle>
            <DialogDescription>
              Select a stage to resume processing from. Completed stages after your
              selection will be re-run.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {progressLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              (["pre_processing", "processing", "post_processing"] as PipelinePhase[]).map(
                (phase) => {
                  const stages = stagesByPhase[phase] || [];
                  if (stages.length === 0) return null;

                  return (
                    <Collapsible
                      key={phase}
                      open={expandedPhases.has(phase)}
                      onOpenChange={() => togglePhase(phase)}
                    >
                      <CollapsibleTrigger asChild>
                        <div
                          className={`flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-gray-50 ${PHASE_COLORS[phase]} bg-opacity-10`}
                        >
                          {expandedPhases.has(phase) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          <div
                            className={`w-2 h-2 rounded-full ${PHASE_COLORS[phase]}`}
                          />
                          <span className="font-medium">{PHASE_NAMES[phase]}</span>
                          <Badge variant="secondary" className="ml-auto">
                            {stages.filter((s) => completedStages.has(s.id)).length}/
                            {stages.length}
                          </Badge>
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="pl-6 space-y-1 mt-2">
                          {stages.map((stage) => {
                            const isCompleted = completedStages.has(stage.id);
                            const isCurrent = currentStage === stage.id;
                            const canResume = stage.can_resume_from;

                            return (
                              <div
                                key={stage.id}
                                className={`flex items-center gap-3 p-2 rounded transition-colors ${
                                  canResume
                                    ? "hover:bg-gray-100 cursor-pointer"
                                    : "opacity-60"
                                } ${isCurrent ? "bg-blue-50 border border-blue-200" : ""}`}
                                onClick={() =>
                                  canResume && setConfirmResumeStage(stage)
                                }
                              >
                                {getStageIcon(stage, isCompleted, isCurrent)}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span
                                      className={`text-sm ${
                                        isCompleted ? "text-green-700" : ""
                                      } ${isCurrent ? "font-medium text-blue-700" : ""}`}
                                    >
                                      {stage.name}
                                    </span>
                                    {stage.is_checkpoint && (
                                      <Badge
                                        variant="outline"
                                        className="text-xs bg-amber-50 text-amber-700 border-amber-200"
                                      >
                                        Checkpoint
                                      </Badge>
                                    )}
                                    {stage.model && (
                                      <Badge variant="secondary" className="text-xs">
                                        {stage.model}
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-xs text-muted-foreground truncate">
                                    {stage.description}
                                  </p>
                                </div>
                                {canResume && !isCurrent && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="opacity-0 group-hover:opacity-100 text-blue-600"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setConfirmResumeStage(stage);
                                    }}
                                  >
                                    <Play className="h-3 w-3" />
                                  </Button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  );
                }
              )
            )}
          </div>

          {progress?.last_error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded text-red-700">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="font-medium">Last Error:</p>
                <p className="text-red-600">{progress.last_error}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog */}
      <Dialog
        open={!!confirmResumeStage}
        onOpenChange={() => setConfirmResumeStage(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Resume from Stage</DialogTitle>
            <DialogDescription>
              Are you sure you want to resume from "{confirmResumeStage?.name}"?
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="bg-amber-50 border border-amber-200 rounded p-3 text-amber-800 text-sm">
              <p className="font-medium mb-1">Warning:</p>
              <p>
                All stages after "{confirmResumeStage?.name}" will be re-processed.
                This may take additional time and incur costs.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmResumeStage(null)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleResumeConfirm}
              disabled={resumeFromStage.isPending}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {resumeFromStage.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Resuming...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Resume from {confirmResumeStage?.name}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default PipelineStageSelector;
