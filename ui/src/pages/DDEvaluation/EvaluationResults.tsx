// pages/DDEvaluation/EvaluationResults.tsx
/**
 * EvaluationResults - Display detailed scoring breakdown for an evaluation
 */

import React from "react";
import { useGetEvaluation, CategoryScore, ScoringItem } from "@/hooks/useGetEvaluation";
import { useGetEvaluations } from "@/hooks/useGetEvaluations";
import { ScoreCard } from "./ScoreCard";
import { Loader2, CheckCircle, XCircle, Clock, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react";

interface EvaluationResultsProps {
  evaluationId: string | null;
}

const PERFORMANCE_BAND_CONFIG: Record<
  string,
  { color: string; bgColor: string; icon: React.ReactNode; description: string }
> = {
  EXCELLENT: {
    color: "text-green-600 dark:text-green-400",
    bgColor: "bg-green-100 dark:bg-green-900/30",
    icon: <CheckCircle className="w-6 h-6" />,
    description: "Outstanding detection of critical issues",
  },
  GOOD: {
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
    icon: <TrendingUp className="w-6 h-6" />,
    description: "Solid performance with minor gaps",
  },
  ADEQUATE: {
    color: "text-yellow-600 dark:text-yellow-400",
    bgColor: "bg-yellow-100 dark:bg-yellow-900/30",
    icon: <AlertTriangle className="w-6 h-6" />,
    description: "Acceptable but needs improvement",
  },
  BELOW_EXPECTATIONS: {
    color: "text-orange-600 dark:text-orange-400",
    bgColor: "bg-orange-100 dark:bg-orange-900/30",
    icon: <TrendingDown className="w-6 h-6" />,
    description: "Significant issues missed",
  },
  FAILURE: {
    color: "text-red-600 dark:text-red-400",
    bgColor: "bg-red-100 dark:bg-red-900/30",
    icon: <XCircle className="w-6 h-6" />,
    description: "Critical failures in detection",
  },
};

export const EvaluationResults: React.FC<EvaluationResultsProps> = ({
  evaluationId,
}) => {
  const { data: evaluation, isLoading, error } = useGetEvaluation(evaluationId);
  const { data: allEvaluations } = useGetEvaluations();

  if (!evaluationId) {
    return (
      <div className="space-y-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Evaluation Results
        </h2>
        <RecentEvaluationsList evaluations={allEvaluations?.evaluations || []} />
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
        Error loading evaluation: {error.message}
      </div>
    );
  }

  if (!evaluation) {
    return (
      <div className="text-center py-12 text-gray-500">Evaluation not found</div>
    );
  }

  if (evaluation.status === "pending" || evaluation.status === "evaluating") {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-12 h-12 animate-spin text-blue-500 mb-4" />
        <p className="text-gray-600 dark:text-gray-400">
          Evaluation in progress...
        </p>
      </div>
    );
  }

  if (evaluation.status === "failed") {
    return (
      <div className="text-center py-12">
        <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600 font-medium">Evaluation Failed</p>
        <p className="text-sm text-gray-500 mt-2">{evaluation.error_message}</p>
      </div>
    );
  }

  const bandConfig = evaluation.performance_band
    ? PERFORMANCE_BAND_CONFIG[evaluation.performance_band]
    : null;

  const scores = evaluation.scores;

  return (
    <div className="space-y-6">
      {/* Header with overall score */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Evaluation Results
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {evaluation.rubric_name} • {evaluation.run_name}
          </p>
          {evaluation.dd_name && (
            <p className="text-xs text-gray-400">Project: {evaluation.dd_name}</p>
          )}
        </div>

        {/* Performance Band Badge */}
        {bandConfig && evaluation.performance_band && (
          <div
            className={`px-4 py-2 rounded-lg ${bandConfig.bgColor} ${bandConfig.color}`}
          >
            <div className="flex items-center gap-2">
              {bandConfig.icon}
              <div>
                <div className="font-bold text-lg">{evaluation.performance_band}</div>
                <div className="text-xs opacity-80">{bandConfig.description}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Overall Score */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:col-span-2">
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
            <div className="text-center">
              <div className="text-5xl font-bold text-gray-900 dark:text-gray-100">
                {evaluation.total_score}
                <span className="text-2xl text-gray-400">
                  /{evaluation.rubric_total_points || 200}
                </span>
              </div>
              <div className="text-2xl font-medium text-gray-600 dark:text-gray-400 mt-2">
                {evaluation.percentage?.toFixed(1)}%
              </div>
              <div className="w-full h-4 bg-gray-200 dark:bg-gray-700 rounded-full mt-4 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    (evaluation.percentage || 0) >= 90
                      ? "bg-green-500"
                      : (evaluation.percentage || 0) >= 75
                      ? "bg-blue-500"
                      : (evaluation.percentage || 0) >= 60
                      ? "bg-yellow-500"
                      : (evaluation.percentage || 0) >= 45
                      ? "bg-orange-500"
                      : "bg-red-500"
                  }`}
                  style={{ width: `${Math.min(evaluation.percentage || 0, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider">
            Performance Thresholds
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between text-green-600">
              <span>Excellent</span>
              <span>90%+</span>
            </div>
            <div className="flex justify-between text-blue-600">
              <span>Good</span>
              <span>75-89%</span>
            </div>
            <div className="flex justify-between text-yellow-600">
              <span>Adequate</span>
              <span>60-74%</span>
            </div>
            <div className="flex justify-between text-orange-600">
              <span>Below Expectations</span>
              <span>45-59%</span>
            </div>
            <div className="flex justify-between text-red-600">
              <span>Failure</span>
              <span>&lt;45%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Scores */}
      {scores && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scores.critical_red_flags && (
            <ScoreCard
              title="Critical Red Flags"
              score={scores.critical_red_flags.score}
              maxScore={scores.critical_red_flags.max}
              icon="🚨"
            />
          )}
          {scores.amber_flags && (
            <ScoreCard
              title="Amber Flags"
              score={scores.amber_flags.score}
              maxScore={scores.amber_flags.max}
              icon="⚠️"
            />
          )}
          {scores.cross_document_connections && (
            <ScoreCard
              title="Cross-Document"
              score={scores.cross_document_connections.score}
              maxScore={scores.cross_document_connections.max}
              icon="🔗"
            />
          )}
          {scores.intelligent_questions && (
            <ScoreCard
              title="Intelligent Questions"
              score={scores.intelligent_questions.score}
              maxScore={scores.intelligent_questions.max}
              icon="❓"
            />
          )}
          {scores.missing_documents && (
            <ScoreCard
              title="Missing Docs Flagged"
              score={scores.missing_documents.score}
              maxScore={scores.missing_documents.max}
              icon="📁"
            />
          )}
          {scores.overall_quality && (
            <ScoreCard
              title="Overall Quality"
              score={scores.overall_quality.score}
              maxScore={scores.overall_quality.max}
              icon="⭐"
            />
          )}
        </div>
      )}

      {/* Detailed Breakdown */}
      {scores && (
        <div className="space-y-6">
          {/* Critical Red Flags Detail */}
          {scores.critical_red_flags && (
            <CategoryDetail
              title="Critical Red Flags"
              icon="🚨"
              category={scores.critical_red_flags}
              foundColor="text-green-600"
              missedColor="text-red-600"
            />
          )}

          {/* Amber Flags Detail */}
          {scores.amber_flags && (
            <CategoryDetail
              title="Amber Flags"
              icon="⚠️"
              category={scores.amber_flags}
              foundColor="text-green-600"
              missedColor="text-red-600"
            />
          )}

          {/* Cross-Document Detail */}
          {scores.cross_document_connections && (
            <CategoryDetail
              title="Cross-Document Connections"
              icon="🔗"
              category={scores.cross_document_connections}
              foundColor="text-green-600"
              missedColor="text-red-600"
            />
          )}

          {/* Summary */}
          {scores.summary && (
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
              <h3 className="text-base font-semibold mb-4">Summary</h3>

              {scores.summary.key_strengths && scores.summary.key_strengths.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-green-600 mb-2">
                    Key Strengths
                  </h4>
                  <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    {scores.summary.key_strengths.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {scores.summary.key_gaps && scores.summary.key_gaps.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-red-600 mb-2">Key Gaps</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    {scores.summary.key_gaps.map((g, i) => (
                      <li key={i}>{g}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="text-xs text-gray-400 flex items-center gap-4">
        <span>Model: {evaluation.evaluation_model}</span>
        {evaluation.completed_at && (
          <span>
            Completed: {new Date(evaluation.completed_at).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
};

interface CategoryDetailProps {
  title: string;
  icon: string;
  category: CategoryScore;
  foundColor: string;
  missedColor: string;
}

const CategoryDetail: React.FC<CategoryDetailProps> = ({
  title,
  icon,
  category,
  foundColor,
  missedColor,
}) => {
  const found = category.found || [];
  const missed = category.missed || [];

  if (found.length === 0 && missed.length === 0) return null;

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <div className="bg-gray-50 dark:bg-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <div className="text-sm font-medium">
          {category.score}/{category.max}
        </div>
      </div>

      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {/* Found Items */}
        {found.map((item, i) => (
          <div key={`found-${i}`} className="px-4 py-3 flex items-start gap-3">
            <CheckCircle className={`w-4 h-4 mt-0.5 ${foundColor} flex-shrink-0`} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {item.rubric_item}
              </div>
              {item.matched_finding && (
                <div className="text-xs text-gray-500 mt-1">
                  Matched: {item.matched_finding}
                </div>
              )}
              {item.notes && (
                <div className="text-xs text-gray-400 mt-1 italic">{item.notes}</div>
              )}
            </div>
            <div className={`text-sm font-medium ${foundColor}`}>
              +{item.score}
            </div>
          </div>
        ))}

        {/* Missed Items */}
        {missed.map((item, i) => (
          <div
            key={`missed-${i}`}
            className="px-4 py-3 flex items-start gap-3 bg-red-50/50 dark:bg-red-900/10"
          >
            <XCircle className={`w-4 h-4 mt-0.5 ${missedColor} flex-shrink-0`} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {item.rubric_item}
              </div>
              {item.notes && (
                <div className="text-xs text-gray-500 mt-1">{item.notes}</div>
              )}
            </div>
            <div className="text-sm font-medium text-gray-400">0/{item.max}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface RecentEvaluationsListProps {
  evaluations: any[];
}

const RecentEvaluationsList: React.FC<RecentEvaluationsListProps> = ({
  evaluations,
}) => {
  if (evaluations.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No evaluations yet.</p>
        <p className="text-sm mt-2">Run an evaluation to see results here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Recent Evaluations
      </h3>
      <div className="space-y-2">
        {evaluations.slice(0, 10).map((evaluation) => {
          const bandConfig = evaluation.performance_band
            ? PERFORMANCE_BAND_CONFIG[evaluation.performance_band]
            : null;

          return (
            <div
              key={evaluation.id}
              className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {evaluation.rubric_name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {evaluation.dd_name} • {evaluation.run_name}
                  </div>
                </div>
                <div className="text-right">
                  {evaluation.status === "completed" ? (
                    <>
                      <div
                        className={`text-lg font-bold ${bandConfig?.color || "text-gray-600"}`}
                      >
                        {evaluation.percentage?.toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">
                        {evaluation.total_score} pts
                      </div>
                    </>
                  ) : (
                    <span
                      className={`text-sm ${
                        evaluation.status === "failed"
                          ? "text-red-500"
                          : "text-gray-500"
                      }`}
                    >
                      {evaluation.status}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EvaluationResults;
