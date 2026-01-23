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
  SEVERITY_ORDER,
  ActionCategory,
  MaterialityClassification
} from './types';

// Action Category configuration
const ACTION_CATEGORY_CONFIG: Record<ActionCategory, { label: string; color: string; bgColor: string; icon: string }> = {
  terminal: { label: 'Deal Blocker', color: 'text-red-700 dark:text-red-400', bgColor: 'bg-red-100 dark:bg-red-900/30', icon: '🛑' },
  valuation: { label: 'Valuation Impact', color: 'text-amber-700 dark:text-amber-400', bgColor: 'bg-amber-100 dark:bg-amber-900/30', icon: '📊' },
  indemnity: { label: 'Indemnity Required', color: 'text-orange-700 dark:text-orange-400', bgColor: 'bg-orange-100 dark:bg-orange-900/30', icon: '🔒' },
  warranty: { label: 'Warranty Coverage', color: 'text-blue-700 dark:text-blue-400', bgColor: 'bg-blue-100 dark:bg-blue-900/30', icon: '📋' },
  information: { label: 'More Info Needed', color: 'text-purple-700 dark:text-purple-400', bgColor: 'bg-purple-100 dark:bg-purple-900/30', icon: '❓' },
  condition_precedent: { label: 'Condition Precedent', color: 'text-indigo-700 dark:text-indigo-400', bgColor: 'bg-indigo-100 dark:bg-indigo-900/30', icon: '⏳' }
};

// Materiality classification configuration
const MATERIALITY_CONFIG: Record<MaterialityClassification, { label: string; color: string; bgColor: string; barColor: string }> = {
  material: { label: 'Material', color: 'text-red-700 dark:text-red-400', bgColor: 'bg-red-100 dark:bg-red-900/30', barColor: 'bg-red-500' },
  potentially_material: { label: 'Potentially Material', color: 'text-orange-700 dark:text-orange-400', bgColor: 'bg-orange-100 dark:bg-orange-900/30', barColor: 'bg-orange-500' },
  likely_immaterial: { label: 'Likely Immaterial', color: 'text-green-700 dark:text-green-400', bgColor: 'bg-green-100 dark:bg-green-900/30', barColor: 'bg-green-500' },
  unquantified: { label: 'Unquantified', color: 'text-gray-700 dark:text-gray-400', bgColor: 'bg-gray-100 dark:bg-gray-700', barColor: 'bg-gray-500' }
};

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

// Download/Open icon for View Original
const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

// Scale/Balance icon for statutory references
const ScaleIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
  </svg>
);

// Chevron icon for collapsible sections
const ChevronIcon = ({ isOpen }: { isOpen: boolean }) => (
  <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

// Target icon for resolution
const TargetIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

interface ExtendedFindingDetailProps extends FindingDetailProps {
  humanReview?: HumanReview;
  onUpdateReview?: (review: Partial<HumanReview>) => void;
  showReviewSection?: boolean;
  onViewDocument?: (docId: string, pageNumber?: number) => void;
  onOpenOriginal?: (docId: string) => void;
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
  onViewDocument,
  onOpenOriginal
}) => {
  const [question, setQuestion] = useState('');
  const [isAskingQuestion, setIsAskingQuestion] = useState(false);
  const [localReview, setLocalReview] = useState<Partial<HumanReview>>(humanReview || { status: 'pending' });
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const [isResolutionExpanded, setIsResolutionExpanded] = useState(false);

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
      {/* Header - Document Info & Actions */}
      <div className="flex-shrink-0 p-4 border-b border-gray-300 dark:border-gray-600 bg-gradient-to-r from-slate-100 to-gray-100 dark:from-gray-800 dark:to-gray-800">
        {/* Document Name Row */}
        <div className="flex items-center gap-2 mb-3">
          {finding.document_type && (
            <span className="flex-shrink-0 w-10 h-6 flex items-center justify-center bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-[10px] uppercase font-bold tracking-wide">
              {finding.document_type}
            </span>
          )}
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" title={finding.document_name}>
            {finding.document_name}
          </span>
        </div>

        {/* Action Buttons Row */}
        <div className="flex flex-wrap gap-2">
          {/* View Section Button - For PDFs or documents with converted PDF */}
          {finding.document_id && onViewDocument && (finding.document_type === 'pdf' || finding.converted_doc_id) && (
            <button
              onClick={() => {
                const docIdToView = finding.converted_doc_id || finding.document_id;
                onViewDocument(docIdToView, finding.actual_page_number);
              }}
              className="flex-1 min-w-[120px] flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              title={`View ${finding.clause_reference || 'section'} in document viewer`}
            >
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span>View Section</span>
            </button>
          )}
          {/* View Document Button - For all documents */}
          {finding.document_id && onOpenOriginal && (
            <button
              onClick={() => onOpenOriginal(finding.document_id)}
              className="flex-1 min-w-[120px] flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
              title={`Download original ${finding.document_type?.toUpperCase() || ''} file`}
            >
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>View Document</span>
            </button>
          )}
        </div>
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

        {/* Action Category & Materiality Row */}
        {(finding.action_category || finding.materiality) && (
          <section className="flex flex-wrap gap-3">
            {/* Action Category Badge */}
            {finding.action_category && ACTION_CATEGORY_CONFIG[finding.action_category] && (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${ACTION_CATEGORY_CONFIG[finding.action_category].bgColor}`}>
                <span className="text-lg">{ACTION_CATEGORY_CONFIG[finding.action_category].icon}</span>
                <div>
                  <div className={`text-sm font-medium ${ACTION_CATEGORY_CONFIG[finding.action_category].color}`}>
                    {ACTION_CATEGORY_CONFIG[finding.action_category].label}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Action Required</div>
                </div>
              </div>
            )}

            {/* Materiality Badge */}
            {finding.materiality?.classification && MATERIALITY_CONFIG[finding.materiality.classification] && (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${MATERIALITY_CONFIG[finding.materiality.classification].bgColor}`}>
                <div className={`w-3 h-3 rounded-full ${MATERIALITY_CONFIG[finding.materiality.classification].barColor}`}></div>
                <div>
                  <div className={`text-sm font-medium ${MATERIALITY_CONFIG[finding.materiality.classification].color}`}>
                    {MATERIALITY_CONFIG[finding.materiality.classification].label}
                  </div>
                  {finding.materiality.ratio_to_deal !== undefined && (
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {(finding.materiality.ratio_to_deal * 100).toFixed(1)}% of deal value
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Resolution Path - Collapsible */}
        {finding.resolution_path && (
          <section>
            <button
              onClick={() => setIsResolutionExpanded(!isResolutionExpanded)}
              className="w-full flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <div className="flex items-center gap-2">
                <TargetIcon />
                <span>Resolution Path</span>
              </div>
              <ChevronIcon isOpen={isResolutionExpanded} />
            </button>
            {isResolutionExpanded && (
              <div className="p-3 bg-indigo-50 dark:bg-indigo-900/10 rounded-lg border border-indigo-100 dark:border-indigo-900/30 space-y-3">
                {/* Mechanism */}
                {finding.resolution_path.mechanism && (
                  <div>
                    <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mb-1">Mechanism</div>
                    <div className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                      {finding.resolution_path.mechanism.replace(/_/g, ' ')}
                    </div>
                  </div>
                )}
                {/* Description */}
                {finding.resolution_path.description && (
                  <div>
                    <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mb-1">Description</div>
                    <div className="text-sm text-gray-700 dark:text-gray-300">
                      {finding.resolution_path.description}
                    </div>
                  </div>
                )}
                {/* Responsible Party & Timeline */}
                <div className="flex flex-wrap gap-4">
                  {finding.resolution_path.responsible_party && (
                    <div>
                      <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mb-1">Responsible Party</div>
                      <div className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                        {finding.resolution_path.responsible_party.replace(/_/g, ' ')}
                      </div>
                    </div>
                  )}
                  {finding.resolution_path.timeline && (
                    <div>
                      <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mb-1">Timeline</div>
                      <div className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                        {finding.resolution_path.timeline.replace(/_/g, ' ')}
                      </div>
                    </div>
                  )}
                </div>
                {/* Estimated Cost */}
                {finding.resolution_path.estimated_cost !== undefined && finding.resolution_path.estimated_cost > 0 && (
                  <div>
                    <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mb-1">Estimated Cost to Resolve</div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        R{finding.resolution_path.estimated_cost.toLocaleString()}
                      </span>
                      {finding.resolution_path.cost_confidence !== undefined && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          ({Math.round(finding.resolution_path.cost_confidence * 100)}% confidence)
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* Confidence Score - Enhanced Display */}
        {finding.confidence && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              AI Confidence Assessment
            </h3>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 space-y-3">
              {/* Overall Confidence Bar */}
              {finding.confidence.overall !== undefined && (
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-gray-600 dark:text-gray-400">Overall Confidence</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {Math.round(finding.confidence.overall * 100)}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        finding.confidence.overall >= 0.7
                          ? 'bg-green-500'
                          : finding.confidence.overall >= 0.5
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${finding.confidence.overall * 100}%` }}
                    />
                  </div>
                </div>
              )}
              {/* Sub-confidence scores */}
              <div className="grid grid-cols-3 gap-2 text-center">
                {finding.confidence.finding_exists !== undefined && (
                  <div className="p-2 bg-white dark:bg-gray-800 rounded">
                    <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {Math.round(finding.confidence.finding_exists * 100)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Exists</div>
                  </div>
                )}
                {finding.confidence.severity_correct !== undefined && (
                  <div className="p-2 bg-white dark:bg-gray-800 rounded">
                    <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {Math.round(finding.confidence.severity_correct * 100)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Severity</div>
                  </div>
                )}
                {finding.confidence.financial_amount_correct !== undefined && (
                  <div className="p-2 bg-white dark:bg-gray-800 rounded">
                    <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {Math.round(finding.confidence.financial_amount_correct * 100)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Amount</div>
                  </div>
                )}
              </div>
              {/* Confidence Basis */}
              {finding.confidence.basis && (
                <div className="pt-2 border-t border-slate-200 dark:border-slate-600">
                  <div className="text-xs text-gray-500 dark:text-gray-400 italic">
                    {finding.confidence.basis}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Statutory Reference */}
        {finding.statutory_reference && (
          <section>
            <h3 className="flex items-center gap-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              <ScaleIcon />
              Statutory Reference
            </h3>
            <div className="p-3 bg-purple-50 dark:bg-purple-900/10 rounded-lg border border-purple-100 dark:border-purple-900/30">
              {/* Act and Section */}
              <div className="flex flex-wrap gap-2 mb-2">
                {finding.statutory_reference.act && (
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
                    {finding.statutory_reference.act}
                  </span>
                )}
                {finding.statutory_reference.section && (
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
                    {finding.statutory_reference.section}
                  </span>
                )}
              </div>
              {/* Provision */}
              {finding.statutory_reference.provision && (
                <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                  {finding.statutory_reference.provision}
                </div>
              )}
              {/* Consequence */}
              {finding.statutory_reference.consequence && (
                <div className="mt-2 pt-2 border-t border-purple-100 dark:border-purple-800/30">
                  <div className="text-xs text-purple-600 dark:text-purple-400 font-medium mb-1">
                    Consequence of Non-Compliance
                  </div>
                  <div className="text-sm text-red-700 dark:text-red-400">
                    {finding.statutory_reference.consequence}
                  </div>
                </div>
              )}
              {/* Regulatory Body */}
              {finding.statutory_reference.regulatory_body && (
                <div className="mt-2 pt-2 border-t border-purple-100 dark:border-purple-800/30">
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Regulatory Body: <span className="font-medium text-gray-700 dark:text-gray-300">{finding.statutory_reference.regulatory_body}</span>
                  </div>
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
