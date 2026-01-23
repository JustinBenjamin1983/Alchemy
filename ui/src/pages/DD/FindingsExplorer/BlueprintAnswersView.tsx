/**
 * BlueprintAnswersView - 3-Panel Layout for Blueprint Q&A
 *
 * Displays blueprint questions asked during DD analysis and Claude's answers.
 * - Left panel: Questions grouped by category
 * - Middle panel: Selected question's answer details
 * - Right panel: Source document information with View/Download buttons
 */

import React, { useState, useMemo } from 'react';

// Icons
const QuestionIcon = () => (
  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const DocumentIcon = () => (
  <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const EyeIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const FolderIcon = () => (
  <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

interface BlueprintQA {
  question: string;
  answer: string;
  finding_refs?: string[];
  source_document: string;
  folder_category?: string;
  document_id?: string;
}

interface BlueprintAnswersViewProps {
  blueprintQA: BlueprintQA[];
  onViewDocument?: (docId: string) => void;
  onDownloadDocument?: (docId: string) => void;
}

// Format folder category for display
const formatFolderCategory = (category?: string): string => {
  if (!category) return 'General';
  return category.replace(/_/g, ' ').replace(/^\d+/, '').trim() || 'General';
};

export const BlueprintAnswersView: React.FC<BlueprintAnswersViewProps> = ({
  blueprintQA,
  onViewDocument,
  onDownloadDocument
}) => {
  const [selectedQAIndex, setSelectedQAIndex] = useState<number | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Group Q&A by folder category
  const groupedQA = useMemo(() => {
    const groups: Record<string, BlueprintQA[]> = {};

    blueprintQA.forEach(qa => {
      const category = formatFolderCategory(qa.folder_category);
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(qa);
    });

    // Sort categories alphabetically
    return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]));
  }, [blueprintQA]);

  // Get currently selected Q&A
  const selectedQA = selectedQAIndex !== null ? blueprintQA[selectedQAIndex] : null;

  // Toggle category expansion
  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // Find global index of a Q&A item
  const findGlobalIndex = (category: string, localIndex: number): number => {
    let globalIndex = 0;
    for (const [cat, items] of groupedQA) {
      if (cat === category) {
        return globalIndex + localIndex;
      }
      globalIndex += items.length;
    }
    return -1;
  };

  // Expand all categories on initial load
  React.useEffect(() => {
    if (groupedQA.length > 0 && expandedCategories.size === 0) {
      setExpandedCategories(new Set(groupedQA.map(([cat]) => cat)));
    }
  }, [groupedQA]);

  if (blueprintQA.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600">
        <div className="text-center">
          <QuestionIcon />
          <p className="mt-2 text-gray-600 dark:text-gray-400">No blueprint Q&A data available</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Run an analysis to generate blueprint answers
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[600px] bg-white dark:bg-gray-900 rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
      {/* Left Panel: Questions grouped by category */}
      <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
        <div className="p-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <QuestionIcon />
            Blueprint Questions
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {blueprintQA.length} questions answered
          </p>
        </div>

        <div className="p-2">
          {groupedQA.map(([category, items]) => (
            <div key={category} className="mb-2">
              {/* Category header */}
              <button
                onClick={() => toggleCategory(category)}
                className="w-full flex items-center gap-2 px-2 py-2 text-left text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <span className={`transform transition-transform ${expandedCategories.has(category) ? 'rotate-90' : ''}`}>
                  <ChevronRightIcon />
                </span>
                <FolderIcon />
                <span>{category}</span>
                <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
                  {items.length}
                </span>
              </button>

              {/* Questions in category */}
              {expandedCategories.has(category) && (
                <div className="ml-6 mt-1 space-y-1">
                  {items.map((qa, idx) => {
                    const globalIdx = findGlobalIndex(category, idx);
                    const isSelected = selectedQAIndex === globalIdx;

                    return (
                      <button
                        key={idx}
                        onClick={() => setSelectedQAIndex(globalIdx)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          isSelected
                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                            : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        <p className="line-clamp-2">{qa.question}</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">
                          {qa.source_document}
                        </p>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Middle Panel: Answer details */}
      <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
        <div className="p-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            Answer
          </h3>
        </div>

        {selectedQA ? (
          <div className="p-4">
            {/* Question */}
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Question
              </label>
              <p className="mt-1 text-gray-900 dark:text-gray-100 font-medium">
                {selectedQA.question}
              </p>
            </div>

            {/* Answer */}
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Answer
              </label>
              <div className="mt-1 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                  {selectedQA.answer}
                </p>
              </div>
            </div>

            {/* Related findings */}
            {selectedQA.finding_refs && selectedQA.finding_refs.length > 0 && (
              <div>
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Related Findings
                </label>
                <div className="mt-1 flex flex-wrap gap-2">
                  {selectedQA.finding_refs.map((ref, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded"
                    >
                      {ref}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <p>Select a question to view the answer</p>
          </div>
        )}
      </div>

      {/* Right Panel: Source document */}
      <div className="w-1/3 overflow-y-auto">
        <div className="p-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <DocumentIcon />
            Source Document
          </h3>
        </div>

        {selectedQA ? (
          <div className="p-4">
            {/* Document info */}
            <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <p className="font-medium text-gray-900 dark:text-gray-100">
                {selectedQA.source_document}
              </p>
              {selectedQA.folder_category && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1">
                  <FolderIcon />
                  {formatFolderCategory(selectedQA.folder_category)}
                </p>
              )}
            </div>

            {/* Action buttons */}
            {selectedQA.document_id && (
              <div className="space-y-2">
                {onViewDocument && (
                  <button
                    onClick={() => onViewDocument(selectedQA.document_id!)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    <EyeIcon />
                    View Document
                  </button>
                )}
                {onDownloadDocument && (
                  <button
                    onClick={() => onDownloadDocument(selectedQA.document_id!)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg border border-gray-300 dark:border-gray-600 transition-colors"
                  >
                    <DownloadIcon />
                    Download Original
                  </button>
                )}
              </div>
            )}

            {!selectedQA.document_id && (
              <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                Document reference not available
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <p>Select a question to view source</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BlueprintAnswersView;
