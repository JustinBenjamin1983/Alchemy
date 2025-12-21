/**
 * FindingsList - Middle panel showing findings grouped by severity
 *
 * Features:
 * - Search/filter findings
 * - Keyboard navigation (arrow keys)
 * - Multi-select for export
 * - Actions menu per finding
 */

import React, { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import {
  FindingsListProps,
  Finding,
  FindingSeverity,
  SEVERITY_CONFIG,
  SEVERITY_ORDER,
  DDCategory,
  DD_CATEGORY_CONFIG,
  getDDCategoryForFinding
} from './types';

// Search icon
const SearchIcon = () => (
  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

// More actions icon (three dots)
const MoreIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
  </svg>
);

interface ExtendedFindingsListProps extends FindingsListProps {
  onMarkResolved?: (findingId: string) => void;
  onFlagForReview?: (findingId: string) => void;
  onViewDocument?: (findingId: string, documentId: string) => void;
  selectedForExport?: Set<string>;
  onToggleExportSelection?: (findingId: string) => void;
  // Filters
  filterCategory?: DDCategory | null;
  filterSeverity?: FindingSeverity | null;
}

interface SeverityGroupProps {
  severity: FindingSeverity;
  findings: Finding[];
  selectedFindingId: string | null;
  onFindingSelect: (id: string) => void;
  isExpanded: boolean;
  onToggle: () => void;
  onMarkResolved?: (findingId: string) => void;
  onFlagForReview?: (findingId: string) => void;
  onViewDocument?: (findingId: string, documentId: string) => void;
  selectedForExport?: Set<string>;
  onToggleExportSelection?: (findingId: string) => void;
  focusedFindingId?: string | null;
}

// Actions dropdown for a finding
const FindingActions: React.FC<{
  finding: Finding;
  onMarkResolved?: (id: string) => void;
  onFlagForReview?: (id: string) => void;
  onViewDocument?: (id: string, docId: string) => void;
}> = ({ finding, onMarkResolved, onFlagForReview, onViewDocument }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <MoreIcon />
      </button>
      {isOpen && (
        <div className="absolute right-0 top-6 z-50 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg overflow-hidden">
          {onMarkResolved && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMarkResolved(finding.id);
                setIsOpen(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
            >
              Mark as resolved
            </button>
          )}
          {onFlagForReview && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFlagForReview(finding.id);
                setIsOpen(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
            >
              Flag for review
            </button>
          )}
          {onViewDocument && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewDocument(finding.id, finding.document_id);
                setIsOpen(false);
              }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
            >
              View source document
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const SeverityGroup: React.FC<SeverityGroupProps> = ({
  severity,
  findings,
  selectedFindingId,
  onFindingSelect,
  isExpanded,
  onToggle,
  onMarkResolved,
  onFlagForReview,
  onViewDocument,
  selectedForExport,
  onToggleExportSelection,
  focusedFindingId
}) => {
  const config = SEVERITY_CONFIG[severity];

  if (findings.length === 0) return null;

  return (
    <div className="border-b border-gray-100 dark:border-gray-800 last:border-b-0">
      {/* Group Header */}
      <button
        onClick={onToggle}
        className={`w-full px-3 py-2 flex items-center justify-between ${config.bgColor} hover:opacity-90 transition-opacity`}
      >
        <div className="flex items-center gap-2">
          <span className={`text-sm ${config.color}`}>{config.icon}</span>
          <span className={`text-sm font-medium ${config.color}`}>
            {config.label}
          </span>
          <span className={`text-xs ${config.color} opacity-70`}>
            ({findings.length})
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Findings in Group */}
      {isExpanded && (
        <div>
          {findings.map((finding) => (
            <div
              key={finding.id}
              className={`group flex items-start gap-2 px-3 py-2 border-l-2 transition-colors cursor-pointer ${
                selectedFindingId === finding.id
                  ? `${config.borderColor} bg-gray-50 dark:bg-gray-800/50`
                  : focusedFindingId === finding.id
                  ? 'border-blue-300 bg-blue-50/50 dark:bg-blue-900/20'
                  : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/30'
              }`}
              onClick={() => onFindingSelect(finding.id)}
              data-finding-id={finding.id}
            >
              {/* Checkbox for export selection */}
              {onToggleExportSelection && (
                <input
                  type="checkbox"
                  checked={selectedForExport?.has(finding.id) || false}
                  onChange={(e) => {
                    e.stopPropagation();
                    onToggleExportSelection(finding.id);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
              )}

              <span className={`text-xs mt-0.5 ${config.color}`}>{config.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
                  {finding.title}
                </div>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span className="truncate max-w-[120px]" title={finding.document_name}>
                    {finding.document_name}
                  </span>
                  {finding.page_reference && (
                    <>
                      <span>•</span>
                      <span>{finding.page_reference}</span>
                    </>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-1 flex-wrap">
                  {/* DD Category badge */}
                  {finding.category && (() => {
                    const ddCat = getDDCategoryForFinding(finding.category);
                    const config = DD_CATEGORY_CONFIG[ddCat];
                    return (
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 text-xs rounded ${config.bgColor} ${config.color}`}
                      >
                        {config.label}
                      </span>
                    );
                  })()}
                  {/* Gap reason badge */}
                  {finding.severity === 'gap' && finding.gap_reason && (
                    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs rounded ${
                      finding.gap_reason === 'documents_not_provided'
                        ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                        : finding.gap_reason === 'information_not_found'
                        ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                        : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
                    }`}>
                      {finding.gap_reason === 'documents_not_provided' && '📁 Docs needed'}
                      {finding.gap_reason === 'information_not_found' && '🔍 Info missing'}
                      {finding.gap_reason === 'inconclusive' && '❓ Needs review'}
                    </span>
                  )}
                  {/* Cross-document badge */}
                  {finding.is_cross_document && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded">
                      <span className="text-[10px]">🔗</span>
                      Cross-doc
                    </span>
                  )}
                </div>
              </div>

              {/* Actions menu */}
              {(onMarkResolved || onFlagForReview || onViewDocument) && (
                <FindingActions
                  finding={finding}
                  onMarkResolved={onMarkResolved}
                  onFlagForReview={onFlagForReview}
                  onViewDocument={onViewDocument}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const FindingsList: React.FC<ExtendedFindingsListProps> = ({
  findings,
  selectedFindingId,
  onFindingSelect,
  filterDocId,
  onMarkResolved,
  onFlagForReview,
  onViewDocument,
  selectedForExport,
  onToggleExportSelection,
  filterCategory,
  filterSeverity
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [focusedFindingId, setFocusedFindingId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Track which severity groups are expanded - start collapsed
  const [expandedGroups, setExpandedGroups] = useState<Set<FindingSeverity>>(
    new Set()
  );

  // Filter findings by document, folder category, severity, and search query
  const filteredFindings = useMemo(() => {
    let result = findings;

    if (filterDocId) {
      result = result.filter(f => f.document_id === filterDocId);
    }

    // Filter by DD category (matches finding category against DD category keywords)
    if (filterCategory) {
      result = result.filter(f => getDDCategoryForFinding(f.category) === filterCategory);
    }

    // Filter by severity
    if (filterSeverity) {
      result = result.filter(f => f.severity === filterSeverity);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(f =>
        f.title.toLowerCase().includes(query) ||
        f.document_name.toLowerCase().includes(query) ||
        f.category?.toLowerCase().includes(query) ||
        f.analysis?.toLowerCase().includes(query) ||
        f.folder_category?.toLowerCase().includes(query)
      );
    }

    return result;
  }, [findings, filterDocId, filterCategory, filterSeverity, searchQuery]);

  // Flat list of all visible findings for keyboard navigation
  const flatFindings = useMemo(() => {
    const result: Finding[] = [];
    SEVERITY_ORDER.forEach(severity => {
      if (expandedGroups.has(severity)) {
        result.push(...filteredFindings.filter(f => f.severity === severity));
      }
    });
    return result;
  }, [filteredFindings, expandedGroups]);

  // Group findings by severity
  const groupedFindings = useMemo(() => {
    const groups: Record<FindingSeverity, Finding[]> = {
      critical: [],
      high: [],
      medium: [],
      low: [],
      positive: [],
      gap: []
    };

    filteredFindings.forEach(finding => {
      if (groups[finding.severity]) {
        groups[finding.severity].push(finding);
      }
    });

    return groups;
  }, [filteredFindings]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (flatFindings.length === 0) return;

    const currentIndex = focusedFindingId
      ? flatFindings.findIndex(f => f.id === focusedFindingId)
      : -1;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const nextIndex = currentIndex < flatFindings.length - 1 ? currentIndex + 1 : 0;
      setFocusedFindingId(flatFindings[nextIndex].id);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const prevIndex = currentIndex > 0 ? currentIndex - 1 : flatFindings.length - 1;
      setFocusedFindingId(flatFindings[prevIndex].id);
    } else if (e.key === 'Enter' && focusedFindingId) {
      e.preventDefault();
      onFindingSelect(focusedFindingId);
    }
  }, [flatFindings, focusedFindingId, onFindingSelect]);

  // Set up keyboard listeners
  useEffect(() => {
    const container = listRef.current;
    if (!container) return;

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Scroll focused item into view
  useEffect(() => {
    if (focusedFindingId && listRef.current) {
      const element = listRef.current.querySelector(`[data-finding-id="${focusedFindingId}"]`);
      element?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [focusedFindingId]);

  const toggleGroup = (severity: FindingSeverity) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(severity)) {
        next.delete(severity);
      } else {
        next.add(severity);
      }
      return next;
    });
  };

  const totalCount = filteredFindings.length;

  return (
    <div className="flex flex-col h-full" ref={listRef} tabIndex={0}>
      {/* Header */}
      <div className="flex-shrink-0 px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Findings
          </h3>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {totalCount} {filterDocId ? 'filtered' : 'total'}
          </span>
        </div>
        {/* Search input */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
            <SearchIcon />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search findings..."
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Findings List */}
      <div className="flex-1 overflow-y-auto flex flex-col">
        {totalCount === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-sm text-gray-400 dark:text-gray-500">
                {searchQuery ? 'No matching findings' : 'No findings'}
              </div>
              <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                {searchQuery
                  ? 'Try a different search term'
                  : filterDocId
                    ? 'No issues found in this document'
                    : 'Run analysis to discover findings'}
              </div>
            </div>
          </div>
        ) : (
          SEVERITY_ORDER.map(severity => (
            <SeverityGroup
              key={severity}
              severity={severity}
              findings={groupedFindings[severity]}
              selectedFindingId={selectedFindingId}
              onFindingSelect={onFindingSelect}
              isExpanded={expandedGroups.has(severity)}
              onToggle={() => toggleGroup(severity)}
              onMarkResolved={onMarkResolved}
              onFlagForReview={onFlagForReview}
              onViewDocument={onViewDocument}
              selectedForExport={selectedForExport}
              onToggleExportSelection={onToggleExportSelection}
              focusedFindingId={focusedFindingId}
            />
          ))
        )}
      </div>
    </div>
  );
};
