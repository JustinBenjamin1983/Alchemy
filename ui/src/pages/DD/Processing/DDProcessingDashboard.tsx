/**
 * DD Processing Dashboard
 *
 * Main dashboard component for visualizing the DD processing pipeline in real-time.
 * Features:
 * - Animated pipeline rings showing 4-pass progress
 * - Live findings feed via SSE
 * - Document status grid
 * - Risk summary counters
 * - Cost tracking
 */
import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import { ProcessingProgress, RiskSummary, PASS_CONFIG, ProcessingPass } from './types';
import {
  useProcessingProgress,
  useLiveFindings,
  useElapsedTime,
  useAnimatedCurrency,
  useReducedMotion
} from './hooks';
import { PipelineRings } from './PipelineRings';
import { LiveFindingsFeed, RiskSummaryCounters } from './FindingsFeed';
import { DocumentStatusGrid } from './DocumentStatus';
import { celebrationVariants, SPRING_GENTLE } from './animations';

interface DDProcessingDashboardProps {
  ddId?: string;
}

export const DDProcessingDashboard: React.FC<DDProcessingDashboardProps> = ({ ddId: propDdId }) => {
  const params = useParams<{ ddId: string }>();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();

  const ddId = propDdId || params.ddId || '';

  // Fetch processing progress
  const { progress, isLoading, error } = useProcessingProgress(ddId, 2000);

  // Live findings via SSE
  const { findings, isConnected } = useLiveFindings(ddId);

  // Elapsed time
  const elapsedTime = useElapsedTime(progress?.startedAt || null);

  // Animated cost display
  const animatedCost = useAnimatedCurrency(progress?.estimatedCostUsd ?? 0);

  // Risk summary from progress
  const riskSummary: RiskSummary = useMemo(() => ({
    critical: progress?.findingCounts.critical ?? 0,
    high: progress?.findingCounts.high ?? 0,
    medium: progress?.findingCounts.medium ?? 0,
    low: progress?.findingCounts.low ?? 0,
    dealBlockers: progress?.findingCounts.dealBlockers ?? 0,
    conditionsPrecedent: progress?.findingCounts.conditionsPrecedent ?? 0,
    totalExposure: 0, // Would come from findings
    currency: 'ZAR'
  }), [progress]);

  // Overall progress percentage
  const overallProgress = useMemo(() => {
    if (!progress) return 0;
    const passes = Object.values(progress.passProgress);
    const total = passes.reduce((sum, p) => sum + p.progress, 0);
    return Math.round(total / 4);
  }, [progress]);

  // Handle navigation back
  const handleBack = () => {
    navigate(`/dd/${ddId}`);
  };

  // Handle view results
  const handleViewResults = () => {
    navigate(`/dd/${ddId}/findings`);
  };

  if (!ddId) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-500 dark:text-gray-400">No DD ID provided</p>
      </div>
    );
  }

  if (isLoading && !progress) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <motion.div
            animate={reducedMotion ? {} : { rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-4"
          />
          <p className="text-gray-500 dark:text-gray-400">Loading processing status...</p>
        </div>
      </div>
    );
  }

  if (error && !progress) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md">
          <svg
            className="w-16 h-16 text-red-400 mx-auto mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Unable to load processing status
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={handleBack}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Enhanced Header with project info */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={handleBack}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                {/* Project name - prominent */}
                <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {progress?.ddId ? `Project ${ddId.slice(0, 8)}` : 'DD Processing'}
                </h1>
                {/* Transaction type & doc count - secondary info */}
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <span className="font-medium">
                    {progress?.status === 'completed'
                      ? 'Analysis Complete'
                      : progress?.status === 'failed'
                      ? 'Processing Failed'
                      : progress?.currentPass
                        ? PASS_CONFIG[progress.currentPass].label
                        : 'Initializing...'}
                  </span>
                  {progress?.totalDocuments && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600">|</span>
                      <span>{progress.totalDocuments} documents</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection status with better styling */}
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700">
                <motion.span
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-green-500' : 'bg-gray-400'
                  }`}
                  animate={isConnected ? {
                    scale: [1, 1.2, 1],
                    opacity: [1, 0.7, 1]
                  } : {}}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                  {isConnected ? 'Connected' : 'Polling'}
                </span>
              </div>

              {/* Time estimate with elapsed */}
              <div className="flex items-center gap-2 text-sm">
                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="font-mono text-gray-700 dark:text-gray-300">{elapsedTime}</span>
                {progress?.estimatedCompletion && progress.status === 'processing' && (
                  <span className="text-gray-400 dark:text-gray-500 text-xs">
                    ~{Math.ceil((progress.estimatedCompletion.getTime() - Date.now()) / 60000)} min remaining
                  </span>
                )}
              </div>

              {/* Overall progress bar - enhanced */}
              <div className="flex items-center gap-3">
                <div className="w-32 h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{
                      background: progress?.status === 'completed'
                        ? '#10B981'
                        : progress?.status === 'failed'
                        ? '#EF4444'
                        : 'linear-gradient(90deg, #3B82F6, #8B5CF6)'
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${overallProgress}%` }}
                    transition={{ type: 'spring', stiffness: 50, damping: 20 }}
                  />
                </div>
                <span className="text-sm font-bold text-gray-700 dark:text-gray-300 min-w-[3ch]">
                  {overallProgress}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Pipeline visualization */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                Processing Pipeline
              </h2>

              {/* Pipeline rings */}
              <div className="flex justify-center">
                <PipelineRings progress={progress} size={280} />
              </div>

              {/* Pass details - Enhanced with current document indicator */}
              <div className="mt-6 space-y-3">
                {(['extract', 'analyze', 'crossdoc', 'synthesize'] as const).map((pass) => {
                  const config = PASS_CONFIG[pass];
                  const passProgress = progress?.passProgress[pass];
                  const isActive = progress?.currentPass === pass && progress?.status === 'processing';
                  const isCompleted = passProgress?.status === 'completed';

                  // Get currently processing document name from progress
                  const currentDocName = isActive && progress?.currentDocumentName
                    ? progress.currentDocumentName
                    : null;

                  return (
                    <motion.div
                      key={pass}
                      layout
                      className={`
                        relative p-3 rounded-lg transition-colors overflow-hidden
                        ${isActive
                          ? 'bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-200 dark:ring-blue-800'
                          : isCompleted
                          ? 'bg-emerald-50 dark:bg-emerald-900/20'
                          : 'bg-gray-50 dark:bg-gray-800/50'}
                      `}
                    >
                      {/* Active indicator glow */}
                      {isActive && !reducedMotion && (
                        <motion.div
                          className="absolute inset-0 rounded-lg"
                          animate={{
                            boxShadow: [
                              `0 0 0 0 ${config.color}00`,
                              `0 0 15px 2px ${config.color}20`,
                              `0 0 0 0 ${config.color}00`,
                            ]
                          }}
                          transition={{ duration: 2, repeat: Infinity }}
                        />
                      )}

                      <div className="flex items-center justify-between relative z-10">
                        <div className="flex items-center gap-3">
                          {/* Status indicator */}
                          {isCompleted ? (
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="w-5 h-5 rounded-full flex items-center justify-center"
                              style={{ backgroundColor: config.color }}
                            >
                              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            </motion.div>
                          ) : isActive ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                              className="w-5 h-5 rounded-full border-2 border-t-transparent"
                              style={{ borderColor: config.color, borderTopColor: 'transparent' }}
                            />
                          ) : (
                            <div
                              className="w-3 h-3 rounded-full opacity-40"
                              style={{ backgroundColor: config.color }}
                            />
                          )}
                          <div>
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              {config.label}
                            </span>
                            {/* Show current document being processed */}
                            {currentDocName && (
                              <motion.p
                                initial={{ opacity: 0, y: -5 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="text-xs text-blue-600 dark:text-blue-400 truncate max-w-[180px]"
                              >
                                {currentDocName}
                              </motion.p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {passProgress && passProgress.totalItems > 0 && (
                            <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                              {passProgress.itemsProcessed}/{passProgress.totalItems}
                            </span>
                          )}
                          <span
                            className="text-sm font-bold min-w-[3ch] text-right"
                            style={{ color: config.color }}
                          >
                            {passProgress?.progress ?? 0}%
                          </span>
                        </div>
                      </div>

                      {/* Progress bar for active pass */}
                      {isActive && passProgress && (
                        <div className="mt-2 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <motion.div
                            className="h-full rounded-full"
                            style={{ backgroundColor: config.color }}
                            initial={{ width: 0 }}
                            animate={{ width: `${passProgress.progress}%` }}
                            transition={{ type: 'spring', stiffness: 50, damping: 20 }}
                          />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>

              {/* Cost tracking */}
              <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Est. Cost</span>
                  <span className="font-mono text-gray-700 dark:text-gray-300">
                    {animatedCost}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm mt-2">
                  <span className="text-gray-500 dark:text-gray-400">Tokens</span>
                  <span className="font-mono text-gray-700 dark:text-gray-300">
                    {((progress?.totalInputTokens ?? 0) + (progress?.totalOutputTokens ?? 0)).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right column - Findings and documents */}
          <div className="lg:col-span-2 space-y-6">
            {/* Risk summary */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                Risk Summary
              </h2>
              <RiskSummaryCounters summary={riskSummary} />
            </div>

            {/* Live findings */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
              <LiveFindingsFeed findings={findings} maxVisible={5} />
            </div>

            {/* Document status */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
              <DocumentStatusGrid documents={progress?.documents ?? []} />
            </div>
          </div>
        </div>

        {/* Completion celebration */}
        <AnimatePresence>
          {progress?.status === 'completed' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={handleViewResults}
            >
              <motion.div
                variants={celebrationVariants}
                initial="initial"
                animate="animate"
                className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center"
                onClick={(e) => e.stopPropagation()}
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, ...SPRING_GENTLE }}
                  className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center mx-auto mb-4"
                >
                  <svg
                    className="w-10 h-10 text-emerald-600 dark:text-emerald-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </motion.div>

                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                  Analysis Complete!
                </h2>

                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  Found {progress.findingCounts.total} findings across {progress.totalDocuments} documents
                </p>

                <div className="flex items-center justify-center gap-4 mb-6 text-sm">
                  {progress.findingCounts.dealBlockers > 0 && (
                    <span className="text-red-600 dark:text-red-400 font-semibold">
                      {progress.findingCounts.dealBlockers} Deal Blockers
                    </span>
                  )}
                  {progress.findingCounts.conditionsPrecedent > 0 && (
                    <span className="text-violet-600 dark:text-violet-400 font-semibold">
                      {progress.findingCounts.conditionsPrecedent} CPs
                    </span>
                  )}
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={handleBack}
                    className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  >
                    Back to DD
                  </button>
                  <button
                    onClick={handleViewResults}
                    className="flex-1 px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    View Results
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error state */}
        {progress?.status === 'failed' && (
          <div className="mt-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-red-100 dark:bg-red-900/50 rounded-full flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-5 h-5 text-red-600 dark:text-red-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-1">
                  Processing Failed
                </h3>
                <p className="text-red-700 dark:text-red-300 mb-3">
                  {progress.lastError || 'An unknown error occurred during processing.'}
                </p>
                {progress.retryCount > 0 && (
                  <p className="text-sm text-red-600 dark:text-red-400 mb-3">
                    Attempted {progress.retryCount} retries
                  </p>
                )}
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Retry Processing
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default DDProcessingDashboard;
