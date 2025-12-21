/**
 * DocumentNavigator - Left panel showing documents with finding counts
 *
 * Features:
 * - Document list with finding counts
 * - Hover tooltip with document details
 * - View document in new tab
 * - Download document
 */

import React, { useState } from 'react';
import { DocumentNavigatorProps, DocumentWithFindings } from './types';

// Simple file icon component
const FileIcon = () => (
  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
  </svg>
);

// External link icon for viewing in new tab
const ExternalLinkIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
);

// Download icon
const DownloadIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

// Tooltip component for document preview
const DocumentTooltip: React.FC<{
  doc: DocumentWithFindings;
  visible: boolean;
}> = ({ doc, visible }) => {
  if (!visible) return null;

  return (
    <div className="absolute left-full top-0 ml-2 z-50 w-56 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg pointer-events-none">
      <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2 break-words">
        {doc.name}
      </div>
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-gray-400">Type:</span>
          <span className="text-gray-700 dark:text-gray-300 uppercase">{doc.file_type}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-gray-400">Total findings:</span>
          <span className="text-gray-700 dark:text-gray-300">{doc.findings_count}</span>
        </div>
        {doc.critical_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Critical:</span>
            <span className="text-red-600 dark:text-red-400 font-medium">{doc.critical_count}</span>
          </div>
        )}
        {doc.high_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">High:</span>
            <span className="text-orange-600 dark:text-orange-400 font-medium">{doc.high_count}</span>
          </div>
        )}
        {doc.medium_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Medium:</span>
            <span className="text-yellow-600 dark:text-yellow-400 font-medium">{doc.medium_count}</span>
          </div>
        )}
        {doc.low_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Low:</span>
            <span className="text-blue-600 dark:text-blue-400 font-medium">{doc.low_count}</span>
          </div>
        )}
        {doc.positive_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Positive:</span>
            <span className="text-green-600 dark:text-green-400 font-medium">{doc.positive_count}</span>
          </div>
        )}
        {doc.gap_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Gaps:</span>
            <span className="text-gray-600 dark:text-gray-400">{doc.gap_count}</span>
          </div>
        )}
      </div>
      {doc.findings_count === 0 && (
        <div className="mt-2 text-xs text-green-600 dark:text-green-400">
          No issues found in this document
        </div>
      )}
    </div>
  );
};

const DocumentItem: React.FC<{
  doc: DocumentWithFindings;
  isSelected: boolean;
  onSelect: () => void;
  onViewDocument?: (docId: string) => void;
  onDownloadDocument?: (docId: string) => void;
}> = ({ doc, isSelected, onSelect, onViewDocument, onDownloadDocument }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const hasIssues = doc.critical_count > 0 || doc.high_count > 0;

  return (
    <div
      className="relative group"
      onMouseEnter={() => { setShowTooltip(true); setShowActions(true); }}
      onMouseLeave={() => { setShowTooltip(false); setShowActions(false); }}
    >
      <button
        onClick={onSelect}
        className={`w-full px-3 py-2.5 text-left transition-all ${
          isSelected
            ? 'bg-white dark:bg-gray-800 border-l-3 border-blue-500 shadow-sm'
            : 'hover:bg-gray-100 dark:hover:bg-gray-800/50 border-l-3 border-transparent hover:border-gray-300'
        }`}
      >
        <div className="flex items-start gap-2">
          <span className="flex-shrink-0 mt-0.5"><FileIcon /></span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate pr-12">
              {doc.name}
            </div>
            <div className="flex items-center gap-2 mt-1">
              {/* Finding count badges */}
              {doc.critical_count > 0 && (
                <span className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded">
                  {doc.critical_count}
                </span>
              )}
              {doc.high_count > 0 && (
                <span className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 rounded">
                  {doc.high_count}
                </span>
              )}
              {doc.medium_count > 0 && (
                <span className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
                  {doc.medium_count}
                </span>
              )}
              {!hasIssues && doc.findings_count > 0 && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {doc.findings_count} findings
                </span>
              )}
              {doc.findings_count === 0 && (
                <span className="text-xs text-green-600 dark:text-green-400">
                  Clear
                </span>
              )}
            </div>
          </div>
        </div>
      </button>

      {/* Action buttons - show on hover */}
      {(onViewDocument || onDownloadDocument) && showActions && (
        <div className="absolute top-2 right-2 flex items-center gap-1">
          {onViewDocument && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewDocument(doc.id);
              }}
              className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              title="View document in new tab"
            >
              <ExternalLinkIcon />
            </button>
          )}
          {onDownloadDocument && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDownloadDocument(doc.id);
              }}
              className="p-1 rounded hover:bg-green-100 dark:hover:bg-green-900/30 text-gray-500 hover:text-green-600 dark:text-gray-400 dark:hover:text-green-400 transition-colors"
              title="Download document"
            >
              <DownloadIcon />
            </button>
          )}
        </div>
      )}

      <DocumentTooltip doc={doc} visible={showTooltip && !showActions} />
    </div>
  );
};

export const DocumentNavigator: React.FC<DocumentNavigatorProps> = ({
  documents,
  selectedDocId,
  onDocumentSelect,
  onViewDocument,
  onDownloadDocument
}) => {
  const totalFindings = documents.reduce((sum, d) => sum + d.findings_count, 0);
  const totalCritical = documents.reduce((sum, d) => sum + d.critical_count, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2.5 border-b border-gray-300 dark:border-gray-600 bg-gradient-to-r from-slate-100 to-gray-100 dark:from-gray-800 dark:to-gray-800">
        <h3 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
          Documents
        </h3>
      </div>

      {/* All Documents option */}
      <button
        onClick={() => onDocumentSelect(null)}
        className={`w-full px-3 py-2.5 text-left border-b border-gray-200 dark:border-gray-700 transition-all ${
          selectedDocId === null
            ? 'bg-white dark:bg-gray-800 border-l-3 border-blue-500 shadow-sm'
            : 'hover:bg-gray-100 dark:hover:bg-gray-800/50 border-l-3 border-transparent hover:border-gray-300'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            All Documents
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {totalFindings}
          </span>
        </div>
        {totalCritical > 0 && (
          <div className="mt-1">
            <span className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded">
              {totalCritical} critical
            </span>
          </div>
        )}
      </button>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto flex flex-col">
        {documents.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-400 dark:text-gray-500 text-sm">
              No documents analysed
            </div>
          </div>
        ) : (
          documents.map((doc) => (
            <DocumentItem
              key={doc.id}
              doc={doc}
              isSelected={selectedDocId === doc.id}
              onSelect={() => onDocumentSelect(doc.id)}
              onViewDocument={onViewDocument}
              onDownloadDocument={onDownloadDocument}
            />
          ))
        )}
      </div>
    </div>
  );
};
