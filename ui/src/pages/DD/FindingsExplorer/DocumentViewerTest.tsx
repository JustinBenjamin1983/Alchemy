/**
 * DocumentViewerTest - Test page for the DocumentViewer component
 *
 * Access via: Add route to your router or import directly for testing
 */

import React, { useState } from 'react';
import { DocumentViewer } from './DocumentViewer';

// Sample public PDF for testing (Mozilla PDF.js sample)
const SAMPLE_PDF_URL = 'https://raw.githubusercontent.com/nickmancol/pdf-sample-files/main/lorem-ipsum.pdf';

export const DocumentViewerTest: React.FC = () => {
  const [showViewer, setShowViewer] = useState(false);
  const [config, setConfig] = useState({
    documentUrl: SAMPLE_PDF_URL,
    documentName: 'Sample Document.pdf',
    initialPage: 1,
    clauseReference: 'Clause 15.2.1',
    evidenceQuote: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit'
  });

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          DocumentViewer Test Page
        </h1>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 space-y-4">
          {/* Document URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Document URL
            </label>
            <input
              type="text"
              value={config.documentUrl}
              onChange={(e) => setConfig({ ...config, documentUrl: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
              placeholder="https://example.com/document.pdf"
            />
            <p className="mt-1 text-xs text-gray-500">
              Enter a PDF URL or use the sample PDF
            </p>
          </div>

          {/* Document Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Document Name
            </label>
            <input
              type="text"
              value={config.documentName}
              onChange={(e) => setConfig({ ...config, documentName: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
            />
          </div>

          {/* Initial Page */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Initial Page
            </label>
            <input
              type="number"
              min={1}
              value={config.initialPage}
              onChange={(e) => setConfig({ ...config, initialPage: parseInt(e.target.value) || 1 })}
              className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
            />
          </div>

          {/* Clause Reference */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Clause Reference
            </label>
            <input
              type="text"
              value={config.clauseReference}
              onChange={(e) => setConfig({ ...config, clauseReference: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
              placeholder="e.g., Clause 15.2.1, Section 4(a)"
            />
          </div>

          {/* Evidence Quote */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Evidence Quote (for highlighting)
            </label>
            <textarea
              value={config.evidenceQuote}
              onChange={(e) => setConfig({ ...config, evidenceQuote: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
              placeholder="Text to highlight in the document..."
            />
          </div>

          {/* Launch Button */}
          <div className="pt-4">
            <button
              onClick={() => setShowViewer(true)}
              className="w-full px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Open Document Viewer
            </button>
          </div>

          {/* Quick Test Buttons */}
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Quick Tests:</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => {
                  setConfig({
                    documentUrl: SAMPLE_PDF_URL,
                    documentName: 'Lorem Ipsum Sample.pdf',
                    initialPage: 1,
                    clauseReference: 'Section 1.1',
                    evidenceQuote: 'Lorem ipsum dolor sit amet'
                  });
                  setShowViewer(true);
                }}
                className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Sample PDF with Highlight
              </button>
              <button
                onClick={() => {
                  setConfig({
                    documentUrl: SAMPLE_PDF_URL,
                    documentName: 'Test Navigation.pdf',
                    initialPage: 2,
                    clauseReference: '',
                    evidenceQuote: ''
                  });
                  setShowViewer(true);
                }}
                className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Page 2 (No Highlight)
              </button>
            </div>
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <h3 className="font-medium text-blue-800 dark:text-blue-300 mb-2">Testing Features:</h3>
          <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1">
            <li>- Page navigation: Arrow keys, +/- for zoom</li>
            <li>- Clause reference badge in header (purple)</li>
            <li>- Page number badge in header (blue)</li>
            <li>- Evidence quote banner (yellow)</li>
            <li>- Text highlighting with auto-scroll</li>
            <li>- Fullscreen mode, Download button</li>
            <li>- Press Escape to close</li>
          </ul>
        </div>
      </div>

      {/* Document Viewer Modal */}
      {showViewer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-[90vw] h-[90vh] bg-white dark:bg-gray-900 rounded-xl shadow-2xl overflow-hidden">
            <DocumentViewer
              documentUrl={config.documentUrl}
              documentName={config.documentName}
              initialPage={config.initialPage}
              clauseReference={config.clauseReference || undefined}
              evidenceQuote={config.evidenceQuote || undefined}
              onClose={() => setShowViewer(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentViewerTest;
