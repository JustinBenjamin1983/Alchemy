// pages/DDEvaluation/EvaluationRunner.tsx
/**
 * EvaluationRunner - Select rubric + DD run and execute evaluation
 */

import React, { useState, useEffect } from "react";
import { useGetEvalRubrics } from "@/hooks/useGetEvalRubrics";
import { useGetDDListing } from "@/hooks/useGetDDListing";
import { useMutateRunEvaluation } from "@/hooks/useMutateRunEvaluation";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Loader2, Play, CheckCircle, AlertTriangle } from "lucide-react";
import { useAxiosWithAuth } from "@/hooks/useAxiosWithAuth";

interface EvaluationRunnerProps {
  onEvaluationComplete: (evaluationId: string) => void;
  preSelectedRubricId?: string | null;
}

interface AnalysisRun {
  run_id: string;
  name: string;
  status: string;
  findings_total: number;
  created_at: string;
}

export const EvaluationRunner: React.FC<EvaluationRunnerProps> = ({
  onEvaluationComplete,
  preSelectedRubricId,
}) => {
  const [selectedRubricId, setSelectedRubricId] = useState<string>(preSelectedRubricId || "");
  const [selectedDDId, setSelectedDDId] = useState<string>("");
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  const axios = useAxiosWithAuth();
  const { data: rubricsData, isLoading: loadingRubrics } = useGetEvalRubrics();
  const { data: ddsData, isLoading: loadingDDs } = useGetDDListing("involves_me");
  const runEvaluation = useMutateRunEvaluation();

  // Update selected rubric when preselected changes
  useEffect(() => {
    if (preSelectedRubricId) {
      setSelectedRubricId(preSelectedRubricId);
    }
  }, [preSelectedRubricId]);

  // Fetch runs when DD is selected
  useEffect(() => {
    if (!selectedDDId) {
      setRuns([]);
      setSelectedRunId("");
      return;
    }

    const fetchRuns = async () => {
      setLoadingRuns(true);
      try {
        const { data } = await axios({
          url: `/dd-analysis-run-list?dd_id=${selectedDDId}`,
          method: "GET",
        });
        setRuns(data.runs || []);
      } catch (err) {
        console.error("Error fetching runs:", err);
        setRuns([]);
      } finally {
        setLoadingRuns(false);
      }
    };

    fetchRuns();
  }, [selectedDDId]);

  const completedRuns = runs.filter((r) => r.status === "completed");

  const handleRunEvaluation = async () => {
    if (!selectedRubricId || !selectedRunId) return;

    try {
      const result = await runEvaluation.mutateAsync({
        rubric_id: selectedRubricId,
        run_id: selectedRunId,
      });

      if (result.id) {
        onEvaluationComplete(result.id);
      }
    } catch (err) {
      // Error handled by mutation
    }
  };

  const selectedRubric = rubricsData?.rubrics?.find((r) => r.id === selectedRubricId);
  const selectedDD = ddsData?.due_diligences?.find((d: any) => d.id === selectedDDId);
  const selectedRun = runs.find((r) => r.run_id === selectedRunId);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Run Evaluation
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Selection */}
        <div className="space-y-4">
          {/* Rubric Selection */}
          <div className="space-y-2">
            <Label>Select Rubric</Label>
            <Select value={selectedRubricId} onValueChange={setSelectedRubricId}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a rubric..." />
              </SelectTrigger>
              <SelectContent>
                {loadingRubrics ? (
                  <div className="p-2 text-sm text-gray-500">Loading...</div>
                ) : (
                  rubricsData?.rubrics?.map((rubric) => (
                    <SelectItem key={rubric.id} value={rubric.id}>
                      {rubric.name} ({rubric.total_points} pts)
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          {/* DD Selection */}
          <div className="space-y-2">
            <Label>Select Due Diligence Project</Label>
            <Select value={selectedDDId} onValueChange={setSelectedDDId}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a project..." />
              </SelectTrigger>
              <SelectContent>
                {loadingDDs ? (
                  <div className="p-2 text-sm text-gray-500">Loading...</div>
                ) : (
                  ddsData?.due_diligences?.map((dd: any) => (
                    <SelectItem key={dd.id} value={dd.id}>
                      {dd.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Run Selection */}
          <div className="space-y-2">
            <Label>Select Analysis Run</Label>
            <Select
              value={selectedRunId}
              onValueChange={setSelectedRunId}
              disabled={!selectedDDId || loadingRuns}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    loadingRuns
                      ? "Loading runs..."
                      : !selectedDDId
                      ? "Select a project first"
                      : completedRuns.length === 0
                      ? "No completed runs available"
                      : "Choose a run..."
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {completedRuns.map((run) => (
                  <SelectItem key={run.run_id} value={run.run_id}>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-3 h-3 text-green-500" />
                      <span>{run.name}</span>
                      <span className="text-xs text-gray-400">
                        ({run.findings_total} findings)
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedDDId && !loadingRuns && completedRuns.length === 0 && runs.length > 0 && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {runs.length} run(s) found but none are completed
              </p>
            )}
          </div>

          {/* Run Button */}
          <Button
            onClick={handleRunEvaluation}
            disabled={!selectedRubricId || !selectedRunId || runEvaluation.isPending}
            className="w-full mt-4"
            size="lg"
          >
            {runEvaluation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Running Evaluation...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Run Evaluation
              </>
            )}
          </Button>

          {runEvaluation.isPending && (
            <p className="text-xs text-gray-500 text-center">
              This may take a minute. Claude Opus is comparing findings against the rubric...
            </p>
          )}
        </div>

        {/* Right: Selection Summary */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Evaluation Summary
          </h3>

          {/* Selected Rubric Info */}
          {selectedRubric ? (
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                📋 {selectedRubric.name}
              </div>
              <div className="mt-1 text-xs text-gray-500 grid grid-cols-2 gap-1">
                <span>Total Points: {selectedRubric.total_points}</span>
                <span>
                  Critical: {selectedRubric.summary.critical_red_flags_count}
                </span>
                <span>Amber: {selectedRubric.summary.amber_flags_count}</span>
                <span>
                  Cross-Doc: {selectedRubric.summary.cross_document_connections_count}
                </span>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-dashed border-gray-300 dark:border-gray-600 text-sm text-gray-400 text-center">
              No rubric selected
            </div>
          )}

          {/* Selected DD Info */}
          {selectedDD ? (
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                📁 {selectedDD.name}
              </div>
            </div>
          ) : (
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-dashed border-gray-300 dark:border-gray-600 text-sm text-gray-400 text-center">
              No project selected
            </div>
          )}

          {/* Selected Run Info */}
          {selectedRun ? (
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                {selectedRun.name}
              </div>
              <div className="mt-1 text-xs text-gray-500">
                {selectedRun.findings_total} findings •{" "}
                {new Date(selectedRun.created_at).toLocaleDateString()}
              </div>
            </div>
          ) : (
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-dashed border-gray-300 dark:border-gray-600 text-sm text-gray-400 text-center">
              No run selected
            </div>
          )}

          {/* Ready indicator */}
          {selectedRubricId && selectedRunId && (
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800 text-sm text-green-700 dark:text-green-400 text-center">
              Ready to evaluate
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EvaluationRunner;
