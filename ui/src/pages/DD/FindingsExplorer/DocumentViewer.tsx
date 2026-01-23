/**
 * DocumentViewer - In-app PDF viewer with page navigation
 *
 * Features:
 * - PDF viewing via react-pdf
 * - Page navigation (jump to specific page)
 * - Zoom controls
 * - Search/text highlighting for evidence quotes
 * - Full-screen mode
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Custom styles for text highlighting
const highlightStyles = `
  .evidence-highlight {
    background-color: rgba(250, 204, 21, 0.5) !important;
    border-radius: 2px;
    padding: 1px 2px;
    box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.3);
    animation: pulse-highlight 2s ease-in-out infinite;
  }
  @keyframes pulse-highlight {
    0%, 100% { background-color: rgba(250, 204, 21, 0.5); }
    50% { background-color: rgba(250, 204, 21, 0.7); }
  }
`;

// Configure PDF.js worker - use unpkg for latest versions
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

interface DocumentViewerProps {
  documentUrl: string | null;
  documentName: string;
  initialPage?: number;
  evidenceQuote?: string;
  clauseReference?: string;  // e.g., "Clause 15.2.1", "Section 4(a)"
  onClose: () => void;
}

// Icons
const CloseIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const ZoomInIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
  </svg>
);

const ZoomOutIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
  </svg>
);

const ChevronLeftIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const FullscreenIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentUrl,
  documentName,
  initialPage = 1,
  evidenceQuote,
  clauseReference,
  onClose
}) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [hasScrolledToHighlight, setHasScrolledToHighlight] = useState<boolean>(false);
  const [pdfData, setPdfData] = useState<Uint8Array | null>(null);
  const pageContainerRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Fetch PDF as ArrayBuffer for better error handling
  useEffect(() => {
    if (!documentUrl) return;

    const fetchPdf = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(documentUrl);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && !contentType.includes('pdf')) {
          console.warn('Response content-type:', contentType);
        }

        const arrayBuffer = await response.arrayBuffer();

        // Convert to Uint8Array to prevent "detached ArrayBuffer" errors
        // PDF.js transfers ArrayBuffers to workers, detaching them on re-render
        const uint8Array = new Uint8Array(arrayBuffer);

        // Verify it starts with PDF magic bytes
        const pdfHeader = String.fromCharCode(...uint8Array.slice(0, 5));
        if (!pdfHeader.startsWith('%PDF')) {
          console.error('Invalid PDF header:', pdfHeader);
          throw new Error('Response is not a valid PDF file');
        }

        setPdfData(uint8Array);
      } catch (err) {
        console.error('Error fetching PDF:', err);
        setError(err instanceof Error ? err.message : 'Failed to load PDF');
        setIsLoading(false);
      }
    };

    fetchPdf();
  }, [documentUrl]);

  // Prepare search terms for highlighting - improved fuzzy matching
  const searchTerms = useMemo(() => {
    const terms: string[] = [];

    // Add clause reference as a search term (if provided)
    if (clauseReference) {
      // Normalize clause reference (e.g., "Clause 15.2" -> ["clause 15.2", "15.2"])
      const normalizedClause = clauseReference.toLowerCase().trim();
      terms.push(normalizedClause);
      // Also extract just the number part (e.g., "15.2.1")
      const numberMatch = clauseReference.match(/[\d.]+/);
      if (numberMatch) {
        terms.push(numberMatch[0]);
      }
    }

    if (evidenceQuote) {
      // Strategy 1: Break into phrases (split on punctuation)
      const phrases = evidenceQuote
        .split(/[,;.!?\n]+/)
        .map(term => term.trim().toLowerCase())
        .filter(term => term.length >= 6); // Lowered threshold for better matching
      terms.push(...phrases);

      // Strategy 2: Extract significant multi-word chunks (3-5 consecutive words)
      const words = evidenceQuote.toLowerCase().split(/\s+/).filter(w => w.length > 3);
      for (let i = 0; i < words.length - 2; i++) {
        const chunk = words.slice(i, i + 3).join(' ');
        if (chunk.length >= 12) {
          terms.push(chunk);
        }
      }
    }

    // Remove duplicates
    return [...new Set(terms)];
  }, [evidenceQuote, clauseReference]);

  // Highlight matching text in the text layer after render
  const highlightMatchingText = useCallback(() => {
    if (!pageContainerRef.current || searchTerms.length === 0) return;

    // Find the text layer
    const textLayer = pageContainerRef.current.querySelector('.react-pdf__Page__textContent');
    if (!textLayer) return;

    // Get all text spans
    const spans = textLayer.querySelectorAll('span');
    let firstHighlightedSpan: Element | null = null;

    spans.forEach(span => {
      const text = span.textContent?.toLowerCase() || '';
      // Check if any search term is found in this span
      for (const term of searchTerms) {
        // Fuzzy match: check if the text contains any significant portion of the term
        // or if the term contains the text (handles split words across spans)
        if (text.includes(term) || (text.length > 4 && term.includes(text))) {
          span.classList.add('evidence-highlight');
          if (!firstHighlightedSpan) {
            firstHighlightedSpan = span;
          }
          break;
        }
      }
    });

    // Auto-scroll to first highlighted element
    if (firstHighlightedSpan && scrollContainerRef.current && !hasScrolledToHighlight) {
      setTimeout(() => {
        firstHighlightedSpan?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setHasScrolledToHighlight(true);
      }, 300); // Small delay to ensure rendering is complete
    }
  }, [searchTerms, hasScrolledToHighlight]);

  // Reset scroll flag when page changes
  useEffect(() => {
    setHasScrolledToHighlight(false);
  }, [pageNumber]);

  // Jump to initial page when it changes
  useEffect(() => {
    if (initialPage && initialPage > 0) {
      setPageNumber(initialPage);
    }
  }, [initialPage]);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
    // Ensure we don't exceed total pages
    if (pageNumber > numPages) {
      setPageNumber(numPages);
    }
  }, [pageNumber]);

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('Error loading PDF:', error);
    setError('Failed to load document. The file may be corrupted or unavailable.');
    setIsLoading(false);
  }, []);

  const goToPrevPage = () => {
    setPageNumber(prev => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setPageNumber(prev => Math.min(numPages, prev + 1));
  };

  const handlePageInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 1 && value <= numPages) {
      setPageNumber(value);
    }
  };

  const zoomIn = () => {
    setScale(prev => Math.min(2.5, prev + 0.25));
  };

  const zoomOut = () => {
    setScale(prev => Math.max(0.5, prev - 0.25));
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleDownload = () => {
    if (documentUrl) {
      window.open(documentUrl, '_blank');
    }
  };

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        goToPrevPage();
      } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
        goToNextPage();
      } else if (e.key === 'Escape') {
        if (isFullscreen) {
          setIsFullscreen(false);
        } else {
          onClose();
        }
      } else if (e.key === '+' || e.key === '=') {
        zoomIn();
      } else if (e.key === '-') {
        zoomOut();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [numPages, isFullscreen, onClose]);

  if (!documentUrl) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100 dark:bg-gray-800">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <p>No document selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col bg-gray-100 dark:bg-gray-900 ${isFullscreen ? 'fixed inset-0 z-50' : 'h-full'}`}>
      {/* Inject highlight styles */}
      <style dangerouslySetInnerHTML={{ __html: highlightStyles }} />

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-xs" title={documentName}>
            {documentName}
          </h3>
          {clauseReference && (
            <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded font-medium">
              {clauseReference}
            </span>
          )}
          {initialPage && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
              Page {initialPage}
            </span>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
            <button
              onClick={zoomOut}
              disabled={scale <= 0.5}
              className="p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50"
              title="Zoom out"
            >
              <ZoomOutIcon />
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-300 w-12 text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={zoomIn}
              disabled={scale >= 2.5}
              className="p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50"
              title="Zoom in"
            >
              <ZoomInIcon />
            </button>
          </div>

          {/* Page navigation */}
          <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
            <button
              onClick={goToPrevPage}
              disabled={pageNumber <= 1}
              className="p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50"
              title="Previous page"
            >
              <ChevronLeftIcon />
            </button>
            <div className="flex items-center gap-1 text-sm">
              <input
                type="number"
                min={1}
                max={numPages}
                value={pageNumber}
                onChange={handlePageInput}
                className="w-12 px-1 py-0.5 text-center bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-gray-900 dark:text-gray-100"
              />
              <span className="text-gray-600 dark:text-gray-300">/ {numPages}</span>
            </div>
            <button
              onClick={goToNextPage}
              disabled={pageNumber >= numPages}
              className="p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50"
              title="Next page"
            >
              <ChevronRightIcon />
            </button>
          </div>

          {/* Action buttons */}
          <button
            onClick={toggleFullscreen}
            className="p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            <FullscreenIcon />
          </button>

          <button
            onClick={handleDownload}
            className="p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Download document"
          >
            <DownloadIcon />
          </button>

          <button
            onClick={onClose}
            className="p-2 text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Close viewer"
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      {/* Evidence quote highlight hint */}
      {evidenceQuote && (
        <div className="px-4 py-2 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <span className="text-yellow-600 dark:text-yellow-400 font-medium text-sm">Evidence:</span>
            <p className="text-sm text-yellow-800 dark:text-yellow-200 italic truncate">
              "{evidenceQuote.slice(0, 150)}{evidenceQuote.length > 150 ? '...' : ''}"
            </p>
          </div>
        </div>
      )}

      {/* Document content */}
      <div ref={scrollContainerRef} className="flex-1 overflow-auto flex justify-center p-4">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-red-500 dark:text-red-400">
              <p className="font-medium">Error loading document</p>
              <p className="text-sm mt-1">{error}</p>
              <button
                onClick={handleDownload}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Open in new tab
              </button>
            </div>
          </div>
        )}

        {pdfData && (
          <div ref={pageContainerRef}>
          <Document
            file={{ data: new Uint8Array(pdfData) }}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={null}
            className="shadow-xl"
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
              className="bg-white"
              onRenderTextLayerSuccess={highlightMatchingText}
            />
          </Document>
        </div>
        )}
      </div>

      {/* Footer with keyboard shortcuts */}
      <div className="px-4 py-1 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
        <span className="mr-4">Arrow keys: Navigate pages</span>
        <span className="mr-4">+/-: Zoom</span>
        <span>Esc: Close</span>
      </div>
    </div>
  );
};

export default DocumentViewer;
