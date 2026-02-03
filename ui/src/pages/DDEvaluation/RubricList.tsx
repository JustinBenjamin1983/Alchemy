// pages/DDEvaluation/RubricList.tsx
/**
 * RubricList - Card grid displaying available evaluation rubrics
 */

import React from "react";
import { useGetEvalRubrics, EvalRubricSummary } from "@/hooks/useGetEvalRubrics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, FileText, Plus } from "lucide-react";

interface RubricListProps {
  onSelectRubric: (rubricId: string) => void;
  onCreateRubric: () => void;
  selectedRubricId?: string | null;
}

export const RubricList: React.FC<RubricListProps> = ({
  onSelectRubric,
  onCreateRubric,
  selectedRubricId,
}) => {
  const { data, isLoading, error } = useGetEvalRubrics();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-500">
        Error loading rubrics: {error.message}
      </div>
    );
  }

  const rubrics = data?.rubrics || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Evaluation Rubrics
        </h2>
        <Button onClick={onCreateRubric} size="sm">
          <Plus className="w-4 h-4 mr-1" />
          Create Rubric
        </Button>
      </div>

      {rubrics.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No rubrics created yet.</p>
          <p className="text-sm mt-2">Create a rubric to start evaluating DD reports.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rubrics.map((rubric) => (
            <RubricCard
              key={rubric.id}
              rubric={rubric}
              isSelected={selectedRubricId === rubric.id}
              onClick={() => onSelectRubric(rubric.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface RubricCardProps {
  rubric: EvalRubricSummary;
  isSelected: boolean;
  onClick: () => void;
}

const RubricCard: React.FC<RubricCardProps> = ({ rubric, isSelected, onClick }) => {
  const { summary } = rubric;

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md ${
        isSelected
          ? "ring-2 ring-blue-500 border-blue-500"
          : "hover:border-gray-300 dark:hover:border-gray-600"
      }`}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <span className="text-xl">📋</span>
          {rubric.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {rubric.description && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
            {rubric.description}
          </p>
        )}

        <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex justify-between">
            <span>Critical Red Flags:</span>
            <span className="font-medium text-red-600 dark:text-red-400">
              {summary.critical_red_flags_count}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Amber Flags:</span>
            <span className="font-medium text-amber-600 dark:text-amber-400">
              {summary.amber_flags_count}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Cross-Doc Connections:</span>
            <span className="font-medium text-indigo-600 dark:text-indigo-400">
              {summary.cross_document_connections_count}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Missing Doc Categories:</span>
            <span className="font-medium">{summary.missing_documents_count}</span>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Total Points:</span>
            <span className="font-bold text-gray-900 dark:text-gray-100">
              {rubric.total_points}
            </span>
          </div>
        </div>

        {rubric.created_at && (
          <div className="mt-2 text-xs text-gray-400">
            Created {new Date(rubric.created_at).toLocaleDateString()}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RubricList;
