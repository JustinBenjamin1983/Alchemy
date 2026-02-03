/**
 * FindingsExplorer - Main Three-Panel Layout
 *
 * Professional interface for exploring DD findings with:
 * - Run selector dropdown at top
 * - Left: Document Navigator (collapsible)
 * - Middle: Findings List (grouped by severity)
 * - Right: Finding Detail (collapsible)
 * - Bottom: Stats bar with severity legend
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { RunSelector } from './RunSelector';
import { DocumentNavigator } from './DocumentNavigator';
import { FindingsList } from './FindingsList';
import { FindingDetail } from './FindingDetail';
import { CompletenessCheck } from './CompletenessCheck';
import { AIChatPanel } from './AIChatPanel';
import { SynthesisView } from './SynthesisView';
import { BlueprintAnswersView } from './BlueprintAnswersView';
import { FinancialAnalysisView } from './FinancialAnalysisView';
import { DocumentViewer } from './DocumentViewer';
import { ReportVersionManager } from '../ReportVersionManager';
import {
  Finding,
  DocumentWithFindings,
  RunInfo,
  SEVERITY_ORDER,
  SEVERITY_CONFIG,
  FindingSeverity,
  HumanReview,
  ChatMessage,
  CompletenessCheckData,
  MissingItemStatus,
  DDCategory,
  DD_CATEGORY_CONFIG,
  DD_CATEGORY_ORDER,
  getDDCategoryForFinding
} from './types';

// Collapse/expand icons
const CollapseLeftIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
  </svg>
);

const ExpandLeftIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
  </svg>
);

const CollapseRightIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 5l7 7-7 7m-8-14l7 7-7 7" />
  </svg>
);

const ExpandRightIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
  </svg>
);

// Spinner icon for loading states
const SpinnerIcon = () => (
  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
  </svg>
);

// File/document icon for reports
const FileTextIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

// Download icon
const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

// Chevron down icon for dropdowns
const ChevronDownIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

// Copy icon
const CopyIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

// Check icon for copy confirmation
const CheckIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

// Clipboard check icon for completeness
const ClipboardCheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
);

// List icon for findings
const ListIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
  </svg>
);

// Document icon for empty state
const DocumentIcon = () => (
  <svg className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

type ActiveTab =
  | 'findings'
  | 'completeness'
  | 'blueprint_answers'
  | 'financial_analysis'
  | 'executive_summary'
  | 'deal_assessment'
  | 'financial_exposures'
  | 'deal_blockers'
  | 'conditions_precedent'
  | 'warranties'
  | 'indemnities'
  | 'recommendations';

// Import SynthesisData type
import { SynthesisData } from '@/hooks/useAnalysisRuns';

interface FindingsExplorerProps {
  ddId: string;
  runs: RunInfo[];
  selectedRunId: string | null;
  onRunSelect: (runId: string) => void;
  findings: Finding[];
  isLoading?: boolean;
  onAskQuestion?: (findingId: string, question: string) => void;
  onExportFindings?: (findingIds: string[]) => void;
  onViewDocument?: (findingId: string, documentId: string) => void;
  // Human Review
  findingReviews?: Record<string, HumanReview>;
  onUpdateFindingReview?: (findingId: string, review: Partial<HumanReview>) => void;
  // AI Chat
  chatMessages?: ChatMessage[];
  onSendChatMessage?: (message: string, context?: { findingId?: string; documentId?: string }) => void;
  isChatLoading?: boolean;
  // Completeness Check
  completenessData?: CompletenessCheckData;
  onUpdateDocumentStatus?: (docId: string, status: MissingItemStatus, note?: string) => void;
  onUpdateQuestionStatus?: (questionId: string, status: MissingItemStatus, note?: string) => void;
  onGenerateRequestLetter?: () => void;
  onRefreshCompletenessAssessment?: () => void;
  isCompletenessLoading?: boolean;
  // Report Generation
  onDownloadReport?: (type: 'preliminary' | 'final') => void;
  reportTypeLoading?: 'preliminary' | 'final' | null;
  // Synthesis Data
  synthesisData?: SynthesisData | null;
  // All analyzed documents from the run
  analyzedDocuments?: { id: string; name: string }[];
  // Document Actions (for left panel)
  onOpenDocumentInTab?: (docId: string) => void;
  onDownloadDocument?: (docId: string) => void;
}

export const FindingsExplorer: React.FC<FindingsExplorerProps> = ({
  ddId,
  runs,
  selectedRunId,
  onRunSelect,
  findings,
  isLoading = false,
  onAskQuestion,
  onExportFindings,
  onViewDocument,
  // Human Review
  findingReviews = {},
  onUpdateFindingReview,
  // AI Chat
  chatMessages = [],
  onSendChatMessage,
  isChatLoading = false,
  // Completeness Check
  completenessData,
  onUpdateDocumentStatus,
  onUpdateQuestionStatus,
  onGenerateRequestLetter,
  onRefreshCompletenessAssessment,
  isCompletenessLoading = false,
  // Report Generation
  onDownloadReport,
  reportTypeLoading = null,
  // Synthesis Data
  synthesisData,
  // All analyzed documents from the run
  analyzedDocuments = [],
  // Document Actions (for left panel)
  onOpenDocumentInTab,
  onDownloadDocument
}) => {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);
  const [selectedForExport, setSelectedForExport] = useState<Set<string>>(new Set());
  const [showLegend, setShowLegend] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>('findings');
  const [chatExpanded, setChatExpanded] = useState(false);

  // Document Viewer state
  const [documentViewerState, setDocumentViewerState] = useState<{
    docUrl: string;
    docName: string;
    pageNumber?: number;
    evidenceQuote?: string;
    clauseReference?: string;
  } | null>(null);
  const [isLoadingDocViewer, setIsLoadingDocViewer] = useState(false);

  // Filter state
  const [filterCategory, setFilterCategory] = useState<DDCategory | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<FindingSeverity | null>(null);

  // Copy state
  const [copySuccess, setCopySuccess] = useState(false);
  const contentPanelRef = useRef<HTMLDivElement>(null);

  // Resizable panel state
  const STORAGE_KEY = 'findings-explorer-panel-sizes';
  const MIN_LEFT_WIDTH = 150;
  const MAX_LEFT_WIDTH = 400;
  const MIN_RIGHT_WIDTH = 200;
  const MAX_RIGHT_WIDTH = 600;
  const MIN_CONTAINER_HEIGHT = 300;
  const DEFAULT_LEFT_WIDTH = 224; // 14rem = 224px
  const DEFAULT_RIGHT_WIDTH = 384; // 24rem = 384px
  const DEFAULT_CONTAINER_HEIGHT = 700;

  const [leftPanelWidth, setLeftPanelWidth] = useState(DEFAULT_LEFT_WIDTH);
  const [rightPanelWidth, setRightPanelWidth] = useState(DEFAULT_RIGHT_WIDTH);
  const [containerHeight, setContainerHeight] = useState(DEFAULT_CONTAINER_HEIGHT);
  const [isResizing, setIsResizing] = useState<'left' | 'right' | 'bottom' | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load saved sizes from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const sizes = JSON.parse(saved);
        if (sizes.leftWidth) setLeftPanelWidth(sizes.leftWidth);
        if (sizes.rightWidth) setRightPanelWidth(sizes.rightWidth);
        if (sizes.containerHeight) setContainerHeight(sizes.containerHeight);
      }
    } catch (e) {
      console.warn('Failed to load panel sizes from localStorage');
    }
  }, []);

  // Save sizes to localStorage when they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        leftWidth: leftPanelWidth,
        rightWidth: rightPanelWidth,
        containerHeight: containerHeight
      }));
    } catch (e) {
      console.warn('Failed to save panel sizes to localStorage');
    }
  }, [leftPanelWidth, rightPanelWidth, containerHeight]);

  // Handle mouse move during resize
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();

      if (isResizing === 'left') {
        const newWidth = e.clientX - containerRect.left;
        setLeftPanelWidth(Math.min(MAX_LEFT_WIDTH, Math.max(MIN_LEFT_WIDTH, newWidth)));
      } else if (isResizing === 'right') {
        const newWidth = containerRect.right - e.clientX;
        setRightPanelWidth(Math.min(MAX_RIGHT_WIDTH, Math.max(MIN_RIGHT_WIDTH, newWidth)));
      } else if (isResizing === 'bottom') {
        const newHeight = e.clientY - containerRect.top;
        setContainerHeight(Math.max(MIN_CONTAINER_HEIGHT, newHeight));
      }
    };

    const handleMouseUp = () => {
      setIsResizing(null);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = isResizing === 'bottom' ? 'ns-resize' : 'ew-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Start resize handlers
  const startLeftResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing('left');
  }, []);

  const startRightResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing('right');
  }, []);

  const startBottomResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing('bottom');
  }, []);

  // Get selected run info
  const selectedRun = useMemo(() =>
    runs.find(r => r.id === selectedRunId) || null,
    [runs, selectedRunId]
  );

  // Compute documents with finding counts - includes ALL analyzed documents
  const documents = useMemo((): DocumentWithFindings[] => {
    const docMap = new Map<string, DocumentWithFindings>();

    // First, initialize with all analyzed documents from the run
    analyzedDocuments.forEach(doc => {
      if (!doc.id) return;
      docMap.set(doc.id, {
        id: doc.id,
        name: doc.name,
        file_type: 'pdf',
        findings_count: 0,
        critical_count: 0,
        high_count: 0,
        medium_count: 0,
        low_count: 0,
        positive_count: 0,
        gap_count: 0
      });
    });

    // Then augment with finding counts
    findings.forEach(f => {
      // Skip findings without a valid document_id (e.g., gap findings, cross-document findings)
      if (!f.document_id) return;

      // If doc not in map (edge case), add it
      if (!docMap.has(f.document_id)) {
        docMap.set(f.document_id, {
          id: f.document_id,
          name: f.document_name,
          file_type: 'pdf',
          findings_count: 0,
          critical_count: 0,
          high_count: 0,
          medium_count: 0,
          low_count: 0,
          positive_count: 0,
          gap_count: 0
        });
      }

      const doc = docMap.get(f.document_id)!;
      doc.findings_count++;

      switch (f.severity) {
        case 'critical': doc.critical_count++; break;
        case 'high': doc.high_count++; break;
        case 'medium': doc.medium_count++; break;
        case 'low': doc.low_count++; break;
        case 'positive': doc.positive_count++; break;
        case 'gap': doc.gap_count++; break;
      }
    });

    return Array.from(docMap.values()).sort((a, b) => {
      // Documents with findings first, sorted by severity
      if (b.critical_count !== a.critical_count) return b.critical_count - a.critical_count;
      if (b.high_count !== a.high_count) return b.high_count - a.high_count;
      if (b.findings_count !== a.findings_count) return b.findings_count - a.findings_count;
      // Then alphabetically by name
      return a.name.localeCompare(b.name);
    });
  }, [findings, analyzedDocuments]);

  // Get selected finding
  const selectedFinding = useMemo(() =>
    findings.find(f => f.id === selectedFindingId) || null,
    [findings, selectedFindingId]
  );

  // Summary stats
  const stats = useMemo(() => {
    const bySeverity: Record<FindingSeverity, number> = {
      critical: 0, high: 0, medium: 0, low: 0, positive: 0, gap: 0
    };

    findings.forEach(f => {
      if (bySeverity[f.severity] !== undefined) {
        bySeverity[f.severity]++;
      }
    });

    return {
      total: findings.length,
      bySeverity,
      documentsWithFindings: documents.length
    };
  }, [findings, documents]);

  // Get available severities from findings
  const availableSeverities = useMemo(() => {
    const severities = new Set<FindingSeverity>();
    findings.forEach(f => {
      if (f.severity) {
        severities.add(f.severity);
      }
    });
    return SEVERITY_ORDER.filter(sev => severities.has(sev));
  }, [findings]);

  // Handle run selection change
  const handleRunSelect = (runId: string) => {
    setSelectedDocId(null);
    setSelectedFindingId(null);
    setSelectedForExport(new Set());
    onRunSelect(runId);
  };

  // Handle document filter
  const handleDocumentSelect = (docId: string | null) => {
    setSelectedDocId(docId);
    setSelectedFindingId(null);
  };

  // Handle finding selection
  const handleFindingSelect = (findingId: string) => {
    setSelectedFindingId(findingId);
    // Auto-expand right panel when selecting a finding
    if (rightPanelCollapsed) {
      setRightPanelCollapsed(false);
    }
  };

  // Toggle export selection
  const handleToggleExportSelection = useCallback((findingId: string) => {
    setSelectedForExport(prev => {
      const next = new Set(prev);
      if (next.has(findingId)) {
        next.delete(findingId);
      } else {
        next.add(findingId);
      }
      return next;
    });
  }, []);

  // Export selected findings
  const handleExportSelected = () => {
    if (onExportFindings && selectedForExport.size > 0) {
      onExportFindings(Array.from(selectedForExport));
    }
  };

  // Select all visible findings for export
  const handleSelectAllForExport = () => {
    const visibleIds = findings
      .filter(f => !selectedDocId || f.document_id === selectedDocId)
      .map(f => f.id);
    setSelectedForExport(new Set(visibleIds));
  };

  // Clear export selection
  const handleClearExportSelection = () => {
    setSelectedForExport(new Set());
  };

  // Open document in viewer with optional page number, evidence quote, and clause reference
  const handleViewDocumentSource = useCallback(async (
    docId: string,
    pageNumber?: number,
    evidenceQuote?: string,
    clauseReference?: string
  ) => {
    if (!docId) return;

    // Find the document name - check both document_id and converted_doc_id
    // (docId might be a converted PDF id)
    let doc = documents.find(d => d.id === docId);
    if (!doc) {
      // Check if this is a converted doc ID - look in findings
      const finding = findings.find(f => f.converted_doc_id === docId);
      if (finding) {
        doc = documents.find(d => d.id === finding.document_id);
      }
    }
    const docName = doc?.name || 'Document';

    setIsLoadingDocViewer(true);

    try {
      // Fetch the document URL from the API
      const response = await fetch(`/api/link?doc_id=${docId}&is_dd=true`);
      if (!response.ok) {
        throw new Error('Failed to fetch document URL');
      }
      const data = await response.json();

      // For local files, construct absolute URL
      const docUrl = data.local
        ? `${window.location.origin}${data.url}`
        : data.url;

      setDocumentViewerState({
        docUrl,
        docName,
        pageNumber,
        evidenceQuote,
        clauseReference
      });
    } catch (error) {
      console.error('Error loading document for viewer:', error);
      // Fallback: try opening in new tab
      if (onOpenDocumentInTab) {
        onOpenDocumentInTab(docId);
      }
    } finally {
      setIsLoadingDocViewer(false);
    }
  }, [documents, findings, onOpenDocumentInTab]);

  // Close document viewer
  const handleCloseDocumentViewer = useCallback(() => {
    setDocumentViewerState(null);
  }, []);

  // Copy content to clipboard - copies exactly what's visible in the panel
  const handleCopyContent = useCallback(() => {
    if (!contentPanelRef.current) return;

    const content = contentPanelRef.current.innerText || contentPanelRef.current.textContent || '';

    navigator.clipboard.writeText(content).then(() => {
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    });
  }, []);

  // Empty state when no run selected
  if (!selectedRunId || !selectedRun) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-300 dark:border-gray-600 shadow-xl p-8 h-full flex items-center justify-center">
        <div className="text-center">
          <DocumentIcon />
          <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mt-4 mb-2">
            No Analysis Run Selected
          </h3>
          <p className="text-gray-400 dark:text-gray-500 text-sm">
            Select an analysis run from the dropdown to view findings
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-300 dark:border-gray-600 shadow-xl p-8 h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-400 dark:text-gray-500 text-sm">Loading findings...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex flex-col bg-white dark:bg-gray-900 rounded-xl border border-gray-300 dark:border-gray-600 shadow-xl relative mb-24 overflow-hidden"
      style={{ minHeight: containerHeight }}
    >
      {/* Top Bar - Compact with Run Selector, Filters, and Actions */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Run Selector */}
            <RunSelector
              runs={runs}
              selectedRunId={selectedRunId}
              onSelect={handleRunSelect}
            />

            {/* Analysis View Dropdown */}
            <select
              value={activeTab}
              onChange={(e) => setActiveTab(e.target.value as ActiveTab)}
              className="h-8 px-2.5 text-xs font-medium bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <optgroup label="Analysis">
                <option value="findings">Findings</option>
                <option value="completeness">Completeness Check</option>
                {synthesisData?.blueprint_qa && synthesisData.blueprint_qa.length > 0 && (
                  <option value="blueprint_answers">Blueprint Answers</option>
                )}
                {synthesisData?.financial_analysis && Object.keys(synthesisData.financial_analysis).length > 0 && (
                  <option value="financial_analysis">Financial Analysis</option>
                )}
              </optgroup>
              {synthesisData && (
                <optgroup label="Synthesis Report">
                  <option value="executive_summary">Executive Summary</option>
                  <option value="deal_assessment">Deal Assessment</option>
                  <option value="financial_exposures">Financial Exposures</option>
                  <option value="deal_blockers">Deal Blockers</option>
                  <option value="conditions_precedent">Conditions Precedent</option>
                  <option value="warranties">Warranties</option>
                  <option value="indemnities">Indemnities</option>
                  <option value="recommendations">Recommendations</option>
                </optgroup>
              )}
            </select>

            {/* Category Filter - show when on findings tab */}
            {activeTab === 'findings' && (
              <select
                value={filterCategory || ''}
                onChange={(e) => setFilterCategory((e.target.value as DDCategory) || null)}
                className="h-8 px-2.5 text-xs bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All Categories</option>
                {DD_CATEGORY_ORDER.map(cat => (
                  <option key={cat} value={cat}>
                    {DD_CATEGORY_CONFIG[cat].label}
                  </option>
                ))}
              </select>
            )}

            {/* Severity Filter - only show when on findings tab */}
            {activeTab === 'findings' && (
              <select
                value={filterSeverity || ''}
                onChange={(e) => setFilterSeverity(e.target.value as FindingSeverity || null)}
                className="h-8 px-2.5 text-xs bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All Severities</option>
                {availableSeverities.map(sev => (
                  <option key={sev} value={sev}>
                    {SEVERITY_CONFIG[sev].label}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Right side actions */}
          <div className="flex items-center gap-2">
            {/* Export controls */}
            {onExportFindings && activeTab === 'findings' && (
              <div className="flex items-center gap-2">
                {selectedForExport.size > 0 && (
                  <>
                    <span className="text-xs text-gray-500">
                      {selectedForExport.size} selected
                    </span>
                    <button
                      onClick={handleClearExportSelection}
                      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-all duration-200 hover:scale-105"
                    >
                      Clear
                    </button>
                    <button
                      onClick={handleExportSelected}
                      className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all duration-200 hover:scale-105 hover:shadow-md"
                    >
                      <DownloadIcon />
                      Export
                    </button>
                  </>
                )}
                {selectedForExport.size === 0 && (
                  <button
                    onClick={handleSelectAllForExport}
                    className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-all duration-200 hover:scale-105"
                  >
                    Select all
                  </button>
                )}
              </div>
            )}

            {/* Report Download Buttons - Chevron Style */}
            {onDownloadReport && (
              <div className="flex items-center pl-3 border-l border-gray-200 dark:border-slate-600">
                {/* Preliminary Report Button (Orange with chevron pointing right INTO Final) */}
                <button
                  onClick={() => onDownloadReport('preliminary')}
                  disabled={reportTypeLoading !== null}
                  className={`
                    h-8 flex items-center gap-1.5 pl-3 pr-2 text-xs font-medium
                    transition-all duration-200 ease-in-out relative z-10
                    ${reportTypeLoading === 'preliminary'
                      ? 'bg-[#ff6b00] text-white cursor-wait'
                      : reportTypeLoading !== null
                      ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                      : 'bg-[#ff6b00] text-white hover:bg-[#e55f00] hover:shadow-md active:bg-[#cc5500]'
                    }
                  `}
                  style={{
                    clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 0 100%)',
                    borderRadius: '4px 0 0 4px',
                    paddingRight: '14px'
                  }}
                  title="Download preliminary report (Word document)"
                >
                  {reportTypeLoading === 'preliminary' ? <SpinnerIcon /> : <FileTextIcon />}
                  {reportTypeLoading === 'preliminary' ? 'Generating...' : 'Preliminary'}
                </button>
                {/* Final Report Button (White/Grey, with notch for orange chevron to fit into) */}
                <button
                  onClick={() => onDownloadReport('final')}
                  disabled={reportTypeLoading !== null}
                  className={`
                    h-8 flex items-center gap-1.5 pl-4 pr-3 text-xs font-medium
                    transition-all duration-200 ease-in-out relative -ml-2
                    ${reportTypeLoading === 'final'
                      ? 'bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-200 cursor-wait'
                      : reportTypeLoading !== null
                      ? 'bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                      : 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-slate-600 hover:shadow-md'
                    }
                  `}
                  style={{
                    clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%, 12px 50%)',
                    borderRadius: '0 4px 4px 0'
                  }}
                  title="Download final report with all findings (Word document)"
                >
                  {reportTypeLoading === 'final' ? <SpinnerIcon /> : <DownloadIcon />}
                  {reportTypeLoading === 'final' ? 'Generating...' : 'Final Report'}
                </button>
              </div>
            )}

            {/* Version Manager removed from header for cleaner UI - can be accessed via Analysis page settings if needed */}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-0">
        {activeTab === 'findings' ? (
          /* Three-Panel Layout for Findings */
          <div className="flex-1 flex min-h-0">
            {/* Left Panel - Document Navigator */}
            <div
              className="flex-shrink-0 border-r border-gray-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 relative"
              style={{ width: leftPanelCollapsed ? 40 : leftPanelWidth }}
            >
              <div className="h-full flex flex-col">
                {/* Collapse button */}
                <button
                  onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
                  className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 transition-all duration-200 hover:scale-105 flex items-center gap-2"
                  title={leftPanelCollapsed ? 'Expand documents panel' : 'Collapse documents panel'}
                >
                  {leftPanelCollapsed ? <ExpandLeftIcon /> : <CollapseLeftIcon />}
                  {!leftPanelCollapsed && (
                    <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">Documents</span>
                  )}
                </button>
                {/* Content */}
                {!leftPanelCollapsed && (
                  <div className="flex-1 overflow-y-auto">
                    <DocumentNavigator
                      documents={documents}
                      selectedDocId={selectedDocId}
                      onDocumentSelect={handleDocumentSelect}
                      onViewDocument={onOpenDocumentInTab}
                      onDownloadDocument={onDownloadDocument}
                    />
                  </div>
                )}
              </div>
              {/* Left panel resize handle */}
              {!leftPanelCollapsed && (
                <div
                  onMouseDown={startLeftResize}
                  className="absolute top-0 right-0 w-1 h-full cursor-ew-resize hover:bg-blue-500/50 active:bg-blue-500 transition-colors z-10"
                  title="Drag to resize"
                />
              )}
            </div>

            {/* Middle Panel - Findings List */}
            <div ref={contentPanelRef} className="flex-1 min-w-0 overflow-hidden relative">
              <FindingsList
                findings={findings}
                selectedFindingId={selectedFindingId}
                onFindingSelect={handleFindingSelect}
                filterDocId={selectedDocId}
                filterCategory={filterCategory}
                filterSeverity={filterSeverity}
                onViewDocument={onViewDocument}
                selectedForExport={onExportFindings ? selectedForExport : undefined}
                onToggleExportSelection={onExportFindings ? handleToggleExportSelection : undefined}
              />
            </div>

            {/* Right Panel - Finding Detail */}
            <div
              className="flex-shrink-0 border-l border-gray-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 relative"
              style={{ width: rightPanelCollapsed ? 40 : rightPanelWidth }}
            >
              {/* Right panel resize handle */}
              {!rightPanelCollapsed && (
                <div
                  onMouseDown={startRightResize}
                  className="absolute top-0 left-0 w-1 h-full cursor-ew-resize hover:bg-blue-500/50 active:bg-blue-500 transition-colors z-10"
                  title="Drag to resize"
                />
              )}
              <div className="h-full flex flex-col">
                {/* Collapse button */}
                <button
                  onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
                  className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 transition-all duration-200 hover:scale-105"
                  title={rightPanelCollapsed ? 'Expand details panel' : 'Collapse details panel'}
                >
                  {rightPanelCollapsed ? <ExpandRightIcon /> : <CollapseRightIcon />}
                </button>
                {/* Content */}
                {!rightPanelCollapsed && (
                  <div className="flex-1 overflow-y-auto">
                    <FindingDetail
                      finding={selectedFinding}
                      onAskQuestion={onAskQuestion ? (question) => onAskQuestion(selectedFinding?.id || '', question) : undefined}
                      humanReview={selectedFinding ? findingReviews[selectedFinding.id] : undefined}
                      onUpdateReview={selectedFinding && onUpdateFindingReview
                        ? (review) => onUpdateFindingReview(selectedFinding.id, review)
                        : undefined
                      }
                      showReviewSection={!!onUpdateFindingReview}
                      onViewDocument={(docId, pageNumber) => {
                        // docId here might be the converted_doc_id if a converted PDF exists
                        handleViewDocumentSource(
                          docId,
                          pageNumber,
                          selectedFinding?.evidence_quote,
                          selectedFinding?.clause_reference
                        );
                      }}
                      onOpenOriginal={onOpenDocumentInTab}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : activeTab === 'completeness' ? (
          /* Completeness Check View */
          <div ref={contentPanelRef} className="flex-1 overflow-hidden p-4">
            {completenessData ? (
              <CompletenessCheck
                data={completenessData}
                onUpdateDocumentStatus={onUpdateDocumentStatus || (() => {})}
                onUpdateQuestionStatus={onUpdateQuestionStatus || (() => {})}
                onGenerateRequestLetter={onGenerateRequestLetter || (() => {})}
                onRefreshAssessment={onRefreshCompletenessAssessment || (() => {})}
                isLoading={isCompletenessLoading}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <ClipboardCheckIcon />
                  <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mt-4 mb-2">
                    Completeness Check Not Available
                  </h3>
                  <p className="text-gray-400 dark:text-gray-500 text-sm">
                    Run the completeness assessment to see missing documents and unanswered questions
                  </p>
                  {onRefreshCompletenessAssessment && (
                    <button
                      onClick={onRefreshCompletenessAssessment}
                      className="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all duration-200 hover:scale-105 hover:shadow-md"
                    >
                      Run Assessment
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : activeTab === 'blueprint_answers' ? (
          /* Blueprint Answers View - 3-Panel Layout */
          <div ref={contentPanelRef} className="flex-1 overflow-auto p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Blueprint Answers
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Questions from the DD blueprint and Claude's answers based on document analysis
              </p>
            </div>
            <BlueprintAnswersView
              blueprintQA={synthesisData?.blueprint_qa || []}
              onViewDocument={(docId) => onOpenDocumentInTab?.(docId)}
              onDownloadDocument={(docId) => onOpenDocumentInTab?.(docId)}
            />
          </div>
        ) : activeTab === 'financial_analysis' ? (
          /* Financial Analysis View */
          <div ref={contentPanelRef} className="flex-1 overflow-auto p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Financial Analysis
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Comprehensive financial overview based on DD financial documents
              </p>
            </div>
            {synthesisData ? (
              <FinancialAnalysisView synthesisData={synthesisData} />
            ) : (
              <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600">
                <p className="text-gray-400 dark:text-gray-500">No financial analysis available</p>
              </div>
            )}
          </div>
        ) : (
          /* Synthesis Views */
          <div ref={contentPanelRef} className="flex-1 overflow-auto p-6">
            {synthesisData ? (
              <SynthesisView
                activeTab={activeTab}
                synthesisData={synthesisData}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <DocumentIcon />
                  <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mt-4 mb-2">
                    Analysis Summary Not Available
                  </h3>
                  <p className="text-gray-400 dark:text-gray-500 text-sm">
                    Run the DD analysis to generate the executive summary and recommendations
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* AI Chat Panel - Always visible at bottom */}
        {onSendChatMessage && (
          <AIChatPanel
            ddId={ddId}
            runId={selectedRunId}
            selectedFinding={selectedFinding}
            messages={chatMessages}
            onSendMessage={onSendChatMessage}
            isLoading={isChatLoading}
            isExpanded={chatExpanded}
            onToggleExpand={() => setChatExpanded(!chatExpanded)}
          />
        )}
      </div>

      {/* Bottom Stats Bar with Severity Legend */}
      <div className="flex-shrink-0 px-4 py-2.5 border-t border-gray-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span>{stats.total} findings</span>
            <span className="text-gray-300 dark:text-slate-600">|</span>
            <span>
              {stats.documentsWithFindings} with findings
              {selectedRun && selectedRun.documents_processed > stats.documentsWithFindings && (
                <span className="text-gray-400"> / {selectedRun.documents_processed} analyzed</span>
              )}
            </span>
          </div>

          {/* Severity counts with legend toggle */}
          <div className="relative flex items-center gap-3">
            {SEVERITY_ORDER.map(severity => {
              const config = SEVERITY_CONFIG[severity];
              const count = stats.bySeverity[severity];
              if (count === 0 && !showLegend) return null;
              return (
                <span
                  key={severity}
                  className="flex items-center gap-1 cursor-default"
                  title={config.label}
                >
                  <span className={`w-2 h-2 rounded-full ${
                    severity === 'critical' ? 'bg-red-500' :
                    severity === 'high' ? 'bg-orange-500' :
                    severity === 'medium' ? 'bg-yellow-500' :
                    severity === 'low' ? 'bg-blue-500' :
                    severity === 'positive' ? 'bg-green-500' :
                    'bg-gray-400'
                  }`} />
                  {showLegend && <span className="text-gray-400">{config.label}:</span>}
                  <span>{count}</span>
                </span>
              );
            })}
            <button
              onClick={() => setShowLegend(!showLegend)}
              className="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs transition-all duration-200 hover:scale-105"
            >
              {showLegend ? 'Hide labels' : 'Show labels'}
            </button>
          </div>
        </div>
      </div>

      {/* Bottom resize handle */}
      <div
        onMouseDown={startBottomResize}
        className="absolute bottom-0 left-0 right-0 h-1 cursor-ns-resize hover:bg-blue-500/50 active:bg-blue-500 transition-colors z-10"
        title="Drag to resize height"
      />

      {/* Document Viewer Modal */}
      {documentViewerState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-[90vw] h-[90vh] bg-white dark:bg-gray-900 rounded-xl shadow-2xl overflow-hidden">
            <DocumentViewer
              documentUrl={documentViewerState.docUrl}
              documentName={documentViewerState.docName}
              initialPage={documentViewerState.pageNumber}
              evidenceQuote={documentViewerState.evidenceQuote}
              clauseReference={documentViewerState.clauseReference}
              onClose={handleCloseDocumentViewer}
            />
          </div>
        </div>
      )}

      {/* Loading overlay for document viewer */}
      {isLoadingDocViewer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-2xl flex items-center gap-3">
            <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
            <span className="text-gray-700 dark:text-gray-300">Loading document...</span>
          </div>
        </div>
      )}
    </div>
  );
};
