/**
 * FindingDetail - Right panel showing full finding details
 *
 * Displays:
 * - Source document and page reference
 * - Original evidence/text
 * - AI analysis and chain of thought
 * - Recommendations
 * - Human Review section (status, notes, implications)
 * - AI chat input for follow-up questions
 */

import React, { useState } from 'react';
import {
  FindingDetailProps,
  SEVERITY_CONFIG,
  ReviewStatus,
  HumanReview,
  FindingSeverity,
  SEVERITY_ORDER
} from './types';

// Simple document icon
const DocumentIcon = () => (
  <svg className="w-8 h-8 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

// Check icon for confirmed status
const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

// X icon for dismissed status
const XIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

// Clock icon for pending status
const ClockIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

// Refresh icon for reclassified
const RefreshIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

// Brain icon for AI reasoning
const BrainIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

// External link icon for View Source
const ExternalLinkIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
);

interface ExtendedFindingDetailProps extends FindingDetailProps {
  humanReview?: HumanReview;
  onUpdateReview?: (review: Partial<HumanReview>) => void;
  showReviewSection?: boolean;
  onViewDocument?: (docId: string, pageNumber?: number) => void;
}

const REVIEW_STATUS_CONFIG: Record<ReviewStatus, { label: string; icon: React.ReactNode; color: string; bgColor: string }> = {
  pending: { label: 'Pending Review', icon: <ClockIcon />, color: 'text-gray-600 dark:text-gray-400', bgColor: 'bg-gray-100 dark:bg-gray-700' },
  confirmed: { label: 'Confirmed', icon: <CheckIcon />, color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-100 dark:bg-green-900/30' },
  dismissed: { label: 'Dismissed', icon: <XIcon />, color: 'text-red-600 dark:text-red-400', bgColor: 'bg-red-100 dark:bg-red-900/30' },
  reclassified: { label: 'Reclassified', icon: <RefreshIcon />, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-100 dark:bg-blue-900/30' }
};

export const FindingDetail: React.FC<ExtendedFindingDetailProps> = ({
  finding,
  onAskQuestion,
  humanReview,
  onUpdateReview,
  showReviewSection = true,
  onViewDocument
}) => {
  const [question, setQuestion] = useState('');
  const [isAskingQuestion, setIsAskingQuestion] = useState(false);
  const [localReview, setLocalReview] = useState<Partial<HumanReview>>(humanReview || { status: 'pending' });
  const [isEditingNotes, setIsEditingNotes] = useState(false);

  if (!finding) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <DocumentIcon />
          <div className="text-sm text-gray-400 dark:text-gray-500 mt-3">
            Select a finding to view details
          </div>
        </div>
      </div>
    );
  }

  const config = SEVERITY_CONFIG[finding.severity];

  const handleAskQuestion = () => {
    if (!question.trim() || !onAskQuestion) return;
    setIsAskingQuestion(true);
    onAskQuestion(question);
    setQuestion('');
    // In real implementation, this would wait for response
    setTimeout(() => setIsAskingQuestion(false), 1000);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-gray-300 dark:border-gray-600 bg-gradient-to-r from-slate-100 to-gray-100 dark:from-gray-800 dark:to-gray-800">
        <div className="flex items-start gap-3">
          <span className={`px-2 py-1 text-xs font-medium rounded ${config.bgColor} ${config.color}`}>
            {config.label}
          </span>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {finding.title}
            </h2>
            <div className="flex items-center gap-2 mt-1 text-sm text-gray-500 dark:text-gray-400">
              <span>{finding.document_name}</span>
              {finding.actual_page_number && (
                <>
                  <span className="text-gray-300 dark:text-gray-600">•</span>
                  <span className="font-medium text-blue-600 dark:text-blue-400">Page {finding.actual_page_number}</span>
                </>
              )}
              {finding.clause_reference && (
                <>
                  <span className="text-gray-300 dark:text-gray-600">•</span>
                  <span className="font-medium text-purple-600 dark:text-purple-400">{finding.clause_reference}</span>
                </>
              )}
              {finding.page_reference && !finding.clause_reference && (
                <>
                  <span className="text-gray-300 dark:text-gray-600">•</span>
                  <span>{finding.page_reference}</span>
                </>
              )}
              {/* View Source Button */}
              {finding.document_id && onViewDocument && (
                <button
                  onClick={() => onViewDocument(finding.document_id, finding.actual_page_number)}
                  className="ml-2 flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                  title={`View document${finding.actual_page_number ? ` at page ${finding.actual_page_number}` : ''}`}
                >
                  <ExternalLinkIcon />
                  View Source
                </button>
              )}
            </div>
          </div>
        </div>
        {finding.category && (
          <div className="mt-2">
            <span className="inline-block px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
              {finding.category}
            </span>
          </div>
        )}
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Source Evidence */}
        {finding.source_text && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              Source Evidence
            </h3>
            <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-700 dark:text-gray-300 italic leading-relaxed">
                "{finding.source_text}"
              </p>
            </div>
          </section>
        )}

        {/* Analysis */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            Analysis
          </h3>
          <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
            {finding.analysis}
          </div>
        </section>

        {/* Financial Exposure with Calculation */}
        {finding.financial_exposure && finding.financial_exposure.amount && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              Financial Exposure
            </h3>
            <div className="p-3 bg-amber-50 dark:bg-amber-900/10 rounded-lg border border-amber-100 dark:border-amber-900/30">
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-lg font-bold text-amber-700 dark:text-amber-400">
                  {finding.financial_exposure.currency} {finding.financial_exposure.amount.toLocaleString()}
                </span>
                {finding.deal_impact && (
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                    finding.deal_impact === 'deal_blocker'
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                      : finding.deal_impact === 'condition_precedent'
                      ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
                      : finding.deal_impact === 'price_chip'
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                  }`}>
                    {finding.deal_impact.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
              {finding.financial_exposure.calculation && (
                <div className="mt-2 pt-2 border-t border-amber-100 dark:border-amber-800/30">
                  <div className="text-xs text-amber-600 dark:text-amber-400 font-medium mb-1">
                    Calculation:
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 font-mono bg-white dark:bg-gray-800 p-2 rounded">
                    {finding.financial_exposure.calculation}
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Chain of Thought - Prominently displayed */}
        {finding.chain_of_thought && (
          <section>
            <h3 className="flex items-center gap-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              <BrainIcon />
              AI Reasoning (Chain of Thought)
            </h3>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-100 dark:border-blue-900/30">
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                {finding.chain_of_thought}
              </p>
              {finding.confidence_score !== undefined && (
                <div className="mt-2 pt-2 border-t border-blue-100 dark:border-blue-800/30">
                  <span className="text-xs text-blue-600 dark:text-blue-400">
                    AI Confidence: {Math.round(finding.confidence_score * 100)}%
                  </span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Recommendation */}
        {finding.recommendation && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              Recommendation
            </h3>
            <div className="p-3 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-100 dark:border-green-900/30">
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {finding.recommendation}
              </p>
            </div>
          </section>
        )}

        {/* Metadata */}
        <section className="pt-4 border-t border-gray-100 dark:border-gray-800">
          <div className="grid grid-cols-2 gap-4 text-sm">
            {finding.exposure_amount !== undefined && finding.exposure_amount > 0 && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Exposure:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  ${finding.exposure_amount.toLocaleString()}
                </span>
              </div>
            )}
            {finding.confidence_score !== undefined && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Confidence:</span>
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  {Math.round(finding.confidence_score * 100)}%
                </span>
              </div>
            )}
          </div>
        </section>

        {/* Human Review Section */}
        {showReviewSection && (
          <section className="pt-4 border-t border-gray-100 dark:border-gray-800">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
              Human Review
            </h3>

            {/* Review Status Buttons */}
            <div className="flex flex-wrap gap-2 mb-4">
              {(['pending', 'confirmed', 'dismissed', 'reclassified'] as ReviewStatus[]).map((status) => {
                const statusConfig = REVIEW_STATUS_CONFIG[status];
                const isSelected = localReview.status === status;
                return (
                  <button
                    key={status}
                    onClick={() => {
                      const newReview = { ...localReview, status };
                      setLocalReview(newReview);
                      onUpdateReview?.(newReview);
                    }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                      isSelected
                        ? `${statusConfig.bgColor} ${statusConfig.color} border-current`
                        : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    {statusConfig.icon}
                    {statusConfig.label}
                  </button>
                );
              })}
            </div>

            {/* Reclassify Severity (shown when reclassified is selected) */}
            {localReview.status === 'reclassified' && (
              <div className="mb-4">
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                  Reclassify to:
                </label>
                <div className="flex flex-wrap gap-2">
                  {SEVERITY_ORDER.filter(s => s !== finding.severity).map((severity) => {
                    const sevConfig = SEVERITY_CONFIG[severity];
                    const isSelected = localReview.reclassified_severity === severity;
                    return (
                      <button
                        key={severity}
                        onClick={() => {
                          const newReview = { ...localReview, reclassified_severity: severity };
                          setLocalReview(newReview);
                          onUpdateReview?.(newReview);
                        }}
                        className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                          isSelected
                            ? `${sevConfig.bgColor} ${sevConfig.color}`
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                      >
                        {sevConfig.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Reviewer Notes */}
            <div className="mb-4">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                Reviewer Notes
              </label>
              <textarea
                value={localReview.reviewer_notes || ''}
                onChange={(e) => setLocalReview({ ...localReview, reviewer_notes: e.target.value })}
                onBlur={() => onUpdateReview?.(localReview)}
                placeholder="Add notes about this finding..."
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Negotiation Implications */}
            <div className="mb-4">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                Negotiation Implications
              </label>
              <textarea
                value={localReview.negotiation_implications || ''}
                onChange={(e) => setLocalReview({ ...localReview, negotiation_implications: e.target.value })}
                onBlur={() => onUpdateReview?.(localReview)}
                placeholder="How does this affect deal negotiations..."
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Client-Specific Notes */}
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                Client-Specific Notes
              </label>
              <textarea
                value={localReview.client_specific_notes || ''}
                onChange={(e) => setLocalReview({ ...localReview, client_specific_notes: e.target.value })}
                onBlur={() => onUpdateReview?.(localReview)}
                placeholder="Client context or special considerations..."
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              />
            </div>
          </section>
        )}
      </div>

      {/* AI Chat Input */}
      {onAskQuestion && (
        <div className="flex-shrink-0 p-4 border-t border-gray-300 dark:border-gray-600 bg-gradient-to-r from-slate-100 to-gray-100 dark:from-gray-800 dark:to-gray-800">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
              placeholder="Ask a follow-up question about this finding..."
              className="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isAskingQuestion}
            />
            <button
              onClick={handleAskQuestion}
              disabled={!question.trim() || isAskingQuestion}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isAskingQuestion ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Asking...
                </span>
              ) : (
                'Ask'
              )}
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Ask Claude to explain, elaborate, or investigate further
          </p>
        </div>
      )}
    </div>
  );
};
