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

// Vertical 3-dots menu icon
const MoreVerticalIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
  </svg>
);

// Tooltip component for document preview
const DocumentTooltip: React.FC<{
  doc: DocumentWithFindings;
  visible: boolean;
}> = ({ doc, visible }) => {
  if (!visible) return null;

  return (
    <div className="absolute left-full top-0 ml-2 z-50 w-56 p-3 bg-white dark:bg-slate-200 border border-gray-200 dark:border-slate-400 rounded-lg shadow-lg pointer-events-none">
      <div className="text-sm font-medium text-gray-900 dark:text-slate-800 mb-2 break-words">
        {doc.name}
      </div>
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-slate-600">Type:</span>
          <span className="text-gray-700 dark:text-slate-700 uppercase">{doc.file_type}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-slate-600">Total findings:</span>
          <span className="text-gray-700 dark:text-slate-700">{doc.findings_count}</span>
        </div>
        {doc.critical_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-slate-600">Critical:</span>
            <span className="text-red-600 dark:text-red-400 font-medium">{doc.critical_count}</span>
          </div>
        )}
        {doc.high_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-slate-600">High:</span>
            <span className="text-orange-600 dark:text-orange-400 font-medium">{doc.high_count}</span>
          </div>
        )}
        {doc.medium_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-slate-600">Medium:</span>
            <span className="text-yellow-600 dark:text-yellow-400 font-medium">{doc.medium_count}</span>
          </div>
        )}
        {doc.low_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-slate-600">Low:</span>
            <span className="text-blue-600 dark:text-blue-400 font-medium">{doc.low_count}</span>
          </div>
        )}
        {doc.positive_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-slate-600">Positive:</span>
            <span className="text-green-600 dark:text-green-400 font-medium">{doc.positive_count}</span>
          </div>
        )}
        {doc.gap_count > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-slate-600">Gaps:</span>
            <span className="text-gray-600 dark:text-slate-600">{doc.gap_count}</span>
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
  const [showMenu, setShowMenu] = useState(false);
  const hasIssues = doc.critical_count > 0 || doc.high_count > 0;

  return (
    <div
      className="relative group"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => { setShowTooltip(false); setShowMenu(false); }}
    >
      <button
        onClick={onSelect}
        className={`w-full px-3 py-2.5 text-left transition-all ${
          isSelected
            ? 'bg-white dark:bg-slate-200 border-l-3 border-blue-500 shadow-sm'
            : 'hover:bg-gray-100 dark:hover:bg-slate-200 border-l-3 border-transparent hover:border-gray-300'
        }`}
      >
        <div className="flex items-start gap-2">
          <span className="flex-shrink-0 mt-0.5"><FileIcon /></span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 dark:text-slate-800 truncate pr-6">
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
                <span className="text-xs text-gray-500 dark:text-slate-600">
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

      {/* 3-dots menu button */}
      {(onViewDocument || onDownloadDocument) && (
        <div className="absolute top-2 right-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-slate-300 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-all duration-200 hover:scale-110"
            title="Document options"
          >
            <MoreVerticalIcon />
          </button>

          {/* Dropdown menu */}
          {showMenu && (
            <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-slate-200 border border-gray-200 dark:border-slate-400 rounded-lg shadow-lg z-50 py-1">
              {onViewDocument && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewDocument(doc.id);
                    setShowMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-slate-700 hover:bg-blue-50 dark:hover:bg-slate-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2 transition-all duration-200"
                >
                  <ExternalLinkIcon />
                  View
                </button>
              )}
              {onDownloadDocument && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDownloadDocument(doc.id);
                    setShowMenu(false);
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-slate-700 hover:bg-green-50 dark:hover:bg-slate-300 hover:text-green-600 dark:hover:text-green-400 flex items-center gap-2 transition-all duration-200"
                >
                  <DownloadIcon />
                  Download
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <DocumentTooltip doc={doc} visible={showTooltip && !showMenu} />
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
      {/* All Documents option */}
      <button
        onClick={() => onDocumentSelect(null)}
        className={`w-full px-3 py-2.5 text-left border-b border-gray-200 dark:border-slate-400 transition-all ${
          selectedDocId === null
            ? 'bg-white dark:bg-slate-200 border-l-3 border-blue-500 shadow-sm'
            : 'hover:bg-gray-100 dark:hover:bg-slate-200 border-l-3 border-transparent hover:border-gray-300'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900 dark:text-slate-800">
            All Documents
          </span>
          <span className="text-xs text-gray-500 dark:text-slate-600">
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
            <div className="text-center text-gray-400 dark:text-slate-500 text-sm">
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
