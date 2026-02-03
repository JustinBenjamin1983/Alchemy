// pages/DDEvaluation/RubricViewer.tsx
/**
 * RubricViewer - Displays full rubric details with expected findings
 */

import React from "react";
import { useGetEvalRubric, RubricItem } from "@/hooks/useGetEvalRubric";
import { Loader2, AlertTriangle, AlertCircle, Link2, HelpCircle, FileQuestion, Star } from "lucide-react";

interface RubricViewerProps {
  rubricId: string | null;
}

export const RubricViewer: React.FC<RubricViewerProps> = ({ rubricId }) => {
  const { data: rubric, isLoading, error } = useGetEvalRubric(rubricId);

  if (!rubricId) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-400">
        Select a rubric to view details
      </div>
    );
  }

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
        Error loading rubric: {error.message}
      </div>
    );
  }

  if (!rubric) {
    return (
      <div className="text-center py-12 text-gray-500">
        Rubric not found
      </div>
    );
  }

  const { rubric_data } = rubric;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          {rubric.name}
        </h2>
        {rubric.description && (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {rubric.description}
          </p>
        )}
        <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
          <span>Total Points: <strong>{rubric.total_points}</strong></span>
          {rubric.dd_name && <span>Linked to: <strong>{rubric.dd_name}</strong></span>}
        </div>
      </div>

      {/* Critical Red Flags */}
      {rubric_data.critical_red_flags && rubric_data.critical_red_flags.length > 0 && (
        <RubricSection
          title="Critical Red Flags"
          icon={<AlertTriangle className="w-5 h-5 text-red-500" />}
          items={rubric_data.critical_red_flags}
          pointsPerItem={10}
          bgColor="bg-red-50 dark:bg-red-900/20"
          borderColor="border-red-200 dark:border-red-800"
        />
      )}

      {/* Amber Flags */}
      {rubric_data.amber_flags && rubric_data.amber_flags.length > 0 && (
        <RubricSection
          title="Amber Flags"
          icon={<AlertCircle className="w-5 h-5 text-amber-500" />}
          items={rubric_data.amber_flags}
          pointsPerItem={5}
          bgColor="bg-amber-50 dark:bg-amber-900/20"
          borderColor="border-amber-200 dark:border-amber-800"
        />
      )}

      {/* Cross-Document Connections */}
      {rubric_data.cross_document_connections && rubric_data.cross_document_connections.length > 0 && (
        <RubricSection
          title="Cross-Document Connections"
          icon={<Link2 className="w-5 h-5 text-indigo-500" />}
          items={rubric_data.cross_document_connections}
          pointsPerItem={5}
          bgColor="bg-indigo-50 dark:bg-indigo-900/20"
          borderColor="border-indigo-200 dark:border-indigo-800"
        />
      )}

      {/* Intelligent Questions */}
      {rubric_data.intelligent_questions && (
        <div className="rounded-lg border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20 p-4">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="w-5 h-5 text-purple-500" />
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Intelligent Questions
            </h3>
            <span className="ml-auto text-sm font-medium text-purple-600 dark:text-purple-400">
              {rubric_data.intelligent_questions.points || 15} pts
            </span>
          </div>
          {rubric_data.intelligent_questions.criteria && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {rubric_data.intelligent_questions.criteria}
            </p>
          )}
        </div>
      )}

      {/* Missing Documents */}
      {rubric_data.missing_documents && rubric_data.missing_documents.length > 0 && (
        <RubricSection
          title="Missing Documents to Flag"
          icon={<FileQuestion className="w-5 h-5 text-gray-500" />}
          items={rubric_data.missing_documents}
          pointsPerItem={1}
          bgColor="bg-gray-50 dark:bg-gray-800"
          borderColor="border-gray-200 dark:border-gray-700"
        />
      )}

      {/* Overall Quality */}
      {rubric_data.overall_quality && (
        <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-5 h-5 text-blue-500" />
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Overall Quality
            </h3>
            <span className="ml-auto text-sm font-medium text-blue-600 dark:text-blue-400">
              {rubric_data.overall_quality.points || 5} pts
            </span>
          </div>
          {rubric_data.overall_quality.criteria && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {rubric_data.overall_quality.criteria}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

interface RubricSectionProps {
  title: string;
  icon: React.ReactNode;
  items: RubricItem[];
  pointsPerItem: number;
  bgColor: string;
  borderColor: string;
}

const RubricSection: React.FC<RubricSectionProps> = ({
  title,
  icon,
  items,
  pointsPerItem,
  bgColor,
  borderColor,
}) => {
  const totalPoints = items.reduce((sum, item) => sum + (item.points || pointsPerItem), 0);

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-4`}>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          ({items.length} items)
        </span>
        <span className="ml-auto text-sm font-medium">
          {totalPoints} pts
        </span>
      </div>

      <div className="space-y-2">
        {items.map((item, index) => (
          <div
            key={index}
            className="flex items-start gap-3 py-2 px-3 bg-white/50 dark:bg-gray-800/50 rounded"
          >
            <span className="text-xs font-mono text-gray-400 mt-0.5">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {item.name}
              </div>
              {item.description && (
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {item.description}
                </div>
              )}
              {item.expected_finding && (
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
                  Expected: {item.expected_finding}
                </div>
              )}
            </div>
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              {item.points || pointsPerItem} pts
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RubricViewer;
