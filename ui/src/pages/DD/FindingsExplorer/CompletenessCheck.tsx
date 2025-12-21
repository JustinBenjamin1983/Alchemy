/**
 * CompletenessCheck - Panel showing missing documents and unanswered questions
 *
 * Features:
 * - Missing documents list (vs Blueprint)
 * - Unanswered questions list
 * - AI importance assessment for each item
 * - Completeness score
 * - Actions: Request from client, Mark as N/A, Add note
 */

import React, { useState, useMemo } from 'react';
import {
  CompletenessCheckData,
  MissingDocument,
  UnansweredQuestion,
  MissingItemStatus,
  ImportanceLevel,
  IMPORTANCE_CONFIG,
  IMPORTANCE_ORDER
} from './types';

// Icons
const DocumentIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const QuestionIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ClockIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const XCircleIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const MailIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const ChevronDownIcon = ({ isOpen }: { isOpen: boolean }) => (
  <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const BrainIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

interface CompletenessCheckProps {
  data: CompletenessCheckData;
  onUpdateDocumentStatus: (docId: string, status: MissingItemStatus, note?: string) => void;
  onUpdateQuestionStatus: (questionId: string, status: MissingItemStatus, note?: string) => void;
  onGenerateRequestLetter: () => void;
  onRefreshAssessment: () => void;
  isLoading?: boolean;
}

const STATUS_CONFIG: Record<MissingItemStatus, { label: string; icon: React.ReactNode; color: string; bgColor: string }> = {
  outstanding: { label: 'Outstanding', icon: <ClockIcon />, color: 'text-orange-600 dark:text-orange-400', bgColor: 'bg-orange-100 dark:bg-orange-900/30' },
  requested: { label: 'Requested', icon: <MailIcon />, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-100 dark:bg-blue-900/30' },
  not_applicable: { label: 'N/A', icon: <XCircleIcon />, color: 'text-gray-600 dark:text-gray-400', bgColor: 'bg-gray-100 dark:bg-gray-700' },
  received: { label: 'Received', icon: <CheckCircleIcon />, color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-100 dark:bg-green-900/30' }
};

// Progress Ring Component
const ProgressRing: React.FC<{ percentage: number; size?: number }> = ({ percentage, size = 80 }) => {
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const getColor = () => {
    if (percentage >= 80) return 'text-green-500';
    if (percentage >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        {/* Background circle */}
        <circle
          className="text-gray-200 dark:text-gray-700"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* Progress circle */}
        <circle
          className={getColor()}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{percentage}%</span>
      </div>
    </div>
  );
};

// Missing Document Item
const MissingDocumentItem: React.FC<{
  doc: MissingDocument;
  onUpdateStatus: (status: MissingItemStatus, note?: string) => void;
}> = ({ doc, onUpdateStatus }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [note, setNote] = useState(doc.note || '');
  const importanceConfig = IMPORTANCE_CONFIG[doc.importance];
  const statusConfig = STATUS_CONFIG[doc.status];

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`flex-shrink-0 ${importanceConfig.color}`}>
            <DocumentIcon />
          </span>
          <div className="min-w-0 text-left">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {doc.document_type}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {doc.description}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${importanceConfig.bgColor} ${importanceConfig.color}`}>
            {importanceConfig.label}
          </span>
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${statusConfig.bgColor} ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
          <ChevronDownIcon isOpen={isExpanded} />
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
          {/* AI Rationale */}
          <div className="mb-3">
            <div className="flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
              <BrainIcon />
              AI Assessment
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              {doc.ai_rationale}
            </p>
          </div>

          {doc.blueprint_reference && (
            <div className="mb-3 text-xs text-gray-500 dark:text-gray-400">
              Blueprint: {doc.blueprint_reference}
            </div>
          )}

          {/* Status Actions */}
          <div className="flex flex-wrap gap-2 mb-3">
            {(['outstanding', 'requested', 'not_applicable', 'received'] as MissingItemStatus[]).map((status) => {
              const config = STATUS_CONFIG[status];
              const isSelected = doc.status === status;
              return (
                <button
                  key={status}
                  onClick={() => onUpdateStatus(status)}
                  className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
                    isSelected
                      ? `${config.bgColor} ${config.color}`
                      : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600'
                  }`}
                >
                  {config.icon}
                  {config.label}
                </button>
              );
            })}
          </div>

          {/* Note */}
          <div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onBlur={() => note !== doc.note && onUpdateStatus(doc.status, note)}
              placeholder="Add a note..."
              rows={2}
              className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>
        </div>
      )}
    </div>
  );
};

// Unanswered Question Item
const UnansweredQuestionItem: React.FC<{
  question: UnansweredQuestion;
  onUpdateStatus: (status: MissingItemStatus, note?: string) => void;
}> = ({ question, onUpdateStatus }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [note, setNote] = useState(question.note || '');
  const importanceConfig = IMPORTANCE_CONFIG[question.importance];
  const statusConfig = STATUS_CONFIG[question.status];

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`flex-shrink-0 ${importanceConfig.color}`}>
            <QuestionIcon />
          </span>
          <div className="min-w-0 text-left">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
              {question.question}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {question.category}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${importanceConfig.bgColor} ${importanceConfig.color}`}>
            {importanceConfig.label}
          </span>
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${statusConfig.bgColor} ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
          <ChevronDownIcon isOpen={isExpanded} />
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
          {/* AI Rationale */}
          <div className="mb-3">
            <div className="flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
              <BrainIcon />
              AI Assessment
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              {question.ai_rationale}
            </p>
          </div>

          {question.related_documents && question.related_documents.length > 0 && (
            <div className="mb-3 text-xs text-gray-500 dark:text-gray-400">
              Related docs: {question.related_documents.join(', ')}
            </div>
          )}

          {/* Status Actions */}
          <div className="flex flex-wrap gap-2 mb-3">
            {(['outstanding', 'requested', 'not_applicable', 'received'] as MissingItemStatus[]).map((status) => {
              const config = STATUS_CONFIG[status];
              const isSelected = question.status === status;
              return (
                <button
                  key={status}
                  onClick={() => onUpdateStatus(status)}
                  className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
                    isSelected
                      ? `${config.bgColor} ${config.color}`
                      : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600'
                  }`}
                >
                  {config.icon}
                  {config.label}
                </button>
              );
            })}
          </div>

          {/* Note */}
          <div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onBlur={() => note !== question.note && onUpdateStatus(question.status, note)}
              placeholder="Add a note..."
              rows={2}
              className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export const CompletenessCheck: React.FC<CompletenessCheckProps> = ({
  data,
  onUpdateDocumentStatus,
  onUpdateQuestionStatus,
  onGenerateRequestLetter,
  onRefreshAssessment,
  isLoading = false
}) => {
  const [activeTab, setActiveTab] = useState<'documents' | 'questions'>('documents');

  // Group items by importance
  const groupedDocuments = useMemo(() => {
    const groups: Record<ImportanceLevel, MissingDocument[]> = {
      critical: [],
      high: [],
      medium: [],
      low: []
    };
    data.missing_documents.forEach(doc => {
      if (doc.status !== 'received' && doc.status !== 'not_applicable') {
        groups[doc.importance].push(doc);
      }
    });
    return groups;
  }, [data.missing_documents]);

  const groupedQuestions = useMemo(() => {
    const groups: Record<ImportanceLevel, UnansweredQuestion[]> = {
      critical: [],
      high: [],
      medium: [],
      low: []
    };
    data.unanswered_questions.forEach(q => {
      if (q.status !== 'received' && q.status !== 'not_applicable') {
        groups[q.importance].push(q);
      }
    });
    return groups;
  }, [data.unanswered_questions]);

  const outstandingDocsCount = data.missing_documents.filter(d => d.status === 'outstanding').length;
  const outstandingQuestionsCount = data.unanswered_questions.filter(q => q.status === 'outstanding').length;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header with Completeness Score */}
      <div className="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Completeness Check
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {data.documents_received} of {data.documents_expected} documents received
            </p>
          </div>
          <div className="flex items-center gap-4">
            <ProgressRing percentage={data.completeness_score} />
            <div className="flex flex-col gap-2">
              <button
                onClick={onRefreshAssessment}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors disabled:opacity-50"
              >
                {isLoading ? (
                  <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <BrainIcon />
                )}
                Re-assess
              </button>
              <button
                onClick={onGenerateRequestLetter}
                disabled={outstandingDocsCount === 0 && outstandingQuestionsCount === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <MailIcon />
                Generate Request
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex-shrink-0 flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('documents')}
          className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'documents'
              ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50/50 dark:bg-blue-900/10'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'
          }`}
        >
          <span className="flex items-center justify-center gap-2">
            <DocumentIcon />
            Missing Documents
            {outstandingDocsCount > 0 && (
              <span className="px-1.5 py-0.5 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded">
                {outstandingDocsCount}
              </span>
            )}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('questions')}
          className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'questions'
              ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50/50 dark:bg-blue-900/10'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'
          }`}
        >
          <span className="flex items-center justify-center gap-2">
            <QuestionIcon />
            Unanswered Questions
            {outstandingQuestionsCount > 0 && (
              <span className="px-1.5 py-0.5 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded">
                {outstandingQuestionsCount}
              </span>
            )}
          </span>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'documents' ? (
          <div className="space-y-4">
            {IMPORTANCE_ORDER.map(importance => {
              const docs = groupedDocuments[importance];
              if (docs.length === 0) return null;
              const config = IMPORTANCE_CONFIG[importance];
              return (
                <div key={importance}>
                  <h3 className={`text-xs font-semibold ${config.color} uppercase tracking-wider mb-2`}>
                    {config.label} ({docs.length})
                  </h3>
                  <div className="space-y-2">
                    {docs.map(doc => (
                      <MissingDocumentItem
                        key={doc.id}
                        doc={doc}
                        onUpdateStatus={(status, note) => onUpdateDocumentStatus(doc.id, status, note)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
            {Object.values(groupedDocuments).every(g => g.length === 0) && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircleIcon />
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  All required documents have been received or marked as N/A
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {IMPORTANCE_ORDER.map(importance => {
              const questions = groupedQuestions[importance];
              if (questions.length === 0) return null;
              const config = IMPORTANCE_CONFIG[importance];
              return (
                <div key={importance}>
                  <h3 className={`text-xs font-semibold ${config.color} uppercase tracking-wider mb-2`}>
                    {config.label} ({questions.length})
                  </h3>
                  <div className="space-y-2">
                    {questions.map(q => (
                      <UnansweredQuestionItem
                        key={q.id}
                        question={q}
                        onUpdateStatus={(status, note) => onUpdateQuestionStatus(q.id, status, note)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
            {Object.values(groupedQuestions).every(g => g.length === 0) && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircleIcon />
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  All questions have been answered or marked as N/A
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="flex-shrink-0 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span>{data.documents_received}/{data.documents_expected} documents</span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>{data.questions_answered}/{data.questions_total} questions answered</span>
          </div>
          {data.last_checked_at && (
            <span>Last assessed: {new Date(data.last_checked_at).toLocaleString('en-GB', {
              day: 'numeric',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit'
            })}</span>
          )}
        </div>
      </div>
    </div>
  );
};
