// pages/DDEvaluation/ScoreCard.tsx
/**
 * ScoreCard - Reusable component for displaying category scores
 *
 * Shows score as X/Y with progress bar and color coding based on percentage.
 */

import React from "react";

interface ScoreCardProps {
  title: string;
  score: number;
  maxScore: number;
  icon?: string;
  description?: string;
  className?: string;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({
  title,
  score,
  maxScore,
  icon,
  description,
  className = "",
}) => {
  const percentage = maxScore > 0 ? (score / maxScore) * 100 : 0;

  const getScoreColor = (pct: number) => {
    if (pct >= 90) return "text-green-600 dark:text-green-400";
    if (pct >= 75) return "text-blue-600 dark:text-blue-400";
    if (pct >= 60) return "text-yellow-600 dark:text-yellow-400";
    if (pct >= 45) return "text-orange-600 dark:text-orange-400";
    return "text-red-600 dark:text-red-400";
  };

  const getProgressColor = (pct: number) => {
    if (pct >= 90) return "bg-green-500";
    if (pct >= 75) return "bg-blue-500";
    if (pct >= 60) return "bg-yellow-500";
    if (pct >= 45) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon && <span className="text-lg">{icon}</span>}
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {title}
          </h3>
        </div>
        <div className={`text-lg font-bold ${getScoreColor(percentage)}`}>
          {score}/{maxScore}
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getProgressColor(percentage)} transition-all duration-300`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {/* Percentage */}
      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right">
        {percentage.toFixed(0)}%
      </div>

      {description && (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {description}
        </p>
      )}
    </div>
  );
};

export default ScoreCard;
