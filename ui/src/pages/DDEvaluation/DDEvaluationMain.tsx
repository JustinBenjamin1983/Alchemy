// pages/DDEvaluation/DDEvaluationMain.tsx
/**
 * DDEvaluationMain - Main page for DD Evaluation Testing System
 *
 * Features:
 * - 3 tabs: Rubrics, Run Evaluation, Results
 * - Create and manage evaluation rubrics
 * - Run evaluations against DD analysis runs
 * - View detailed scoring breakdowns
 */

import React, { useState } from "react";
import { Top } from "@/components/Top";
import { RubricList } from "./RubricList";
import { RubricViewer } from "./RubricViewer";
import { RubricUploader } from "./RubricUploader";
import { EvaluationRunner } from "./EvaluationRunner";
import { EvaluationResults } from "./EvaluationResults";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileCheck, Play, BarChart3, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

type TabValue = "rubrics" | "run" | "results";

interface DDEvaluationMainProps {
  embedded?: boolean;
}

export const DDEvaluationMain: React.FC<DDEvaluationMainProps> = ({ embedded = false }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabValue>("rubrics");
  const [selectedRubricId, setSelectedRubricId] = useState<string | null>(null);
  const [showRubricUploader, setShowRubricUploader] = useState(false);
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<string | null>(null);

  const handleSelectRubric = (rubricId: string) => {
    setSelectedRubricId(rubricId);
  };

  const handleCreateRubric = () => {
    setShowRubricUploader(true);
  };

  const handleRubricCreated = () => {
    setShowRubricUploader(false);
  };

  const handleEvaluationComplete = (evaluationId: string) => {
    setSelectedEvaluationId(evaluationId);
    setActiveTab("results");
  };

  const handleUseRubricForEvaluation = () => {
    setActiveTab("run");
  };

  return (
    <div className={embedded ? "" : "min-h-screen bg-gray-50 dark:bg-gray-900"}>
      {!embedded && <Top />}

      <div className={embedded ? "py-2" : "max-w-7xl mx-auto px-4 py-6"}>
        {/* Header - only show when not embedded */}
        {!embedded && (
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/activity")}
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  DD Evaluation Testing
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Evaluate DD report quality against known answer rubrics
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
          <TabsList className="grid w-full max-w-md grid-cols-3 mb-6">
            <TabsTrigger value="rubrics" className="flex items-center gap-2">
              <FileCheck className="w-4 h-4" />
              Rubrics
            </TabsTrigger>
            <TabsTrigger value="run" className="flex items-center gap-2">
              <Play className="w-4 h-4" />
              Run
            </TabsTrigger>
            <TabsTrigger value="results" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Results
            </TabsTrigger>
          </TabsList>

          {/* Rubrics Tab */}
          <TabsContent value="rubrics" className="space-y-6">
            {showRubricUploader ? (
              <RubricUploader
                onSuccess={handleRubricCreated}
                onCancel={() => setShowRubricUploader(false)}
              />
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Rubric List */}
                <div>
                  <RubricList
                    onSelectRubric={handleSelectRubric}
                    onCreateRubric={handleCreateRubric}
                    selectedRubricId={selectedRubricId}
                  />
                </div>

                {/* Rubric Viewer */}
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                  {selectedRubricId ? (
                    <>
                      <RubricViewer rubricId={selectedRubricId} />
                      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <Button onClick={handleUseRubricForEvaluation}>
                          <Play className="w-4 h-4 mr-2" />
                          Use This Rubric for Evaluation
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-64 text-gray-400">
                      Select a rubric to view details
                    </div>
                  )}
                </div>
              </div>
            )}
          </TabsContent>

          {/* Run Evaluation Tab */}
          <TabsContent value="run">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <EvaluationRunner
                onEvaluationComplete={handleEvaluationComplete}
                preSelectedRubricId={selectedRubricId}
              />
            </div>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <EvaluationResults evaluationId={selectedEvaluationId} />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default DDEvaluationMain;
