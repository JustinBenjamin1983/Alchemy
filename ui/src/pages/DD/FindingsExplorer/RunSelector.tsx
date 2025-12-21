/**
 * RunSelector - Dropdown for selecting analysis runs
 */

import React, { useState, useRef, useEffect } from 'react';
import { RunSelectorProps, RunInfo } from './types';

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Simple pencil icon
const EditIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
  </svg>
);

// Simple chevron icon
const ChevronIcon = ({ isOpen }: { isOpen: boolean }) => (
  <svg
    className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

interface ExtendedRunSelectorProps extends RunSelectorProps {
  onEditRun?: (runId: string) => void;
}

export const RunSelector: React.FC<ExtendedRunSelectorProps> = ({
  runs,
  selectedRunId,
  onSelect,
  onEditRun
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedRun = runs.find(r => r.id === selectedRunId);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (runId: string) => {
    onSelect(runId);
    setIsOpen(false);
  };

  const handleEdit = (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    onEditRun?.(runId);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Selected Run Display / Trigger - Compact */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between px-2.5 py-1.5 text-left bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-md hover:border-gray-300 dark:hover:border-gray-500 transition-colors"
      >
        {selectedRun ? (
          <div className="flex items-center gap-2 flex-nowrap">
            {/* Run name */}
            <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
              Run #{selectedRun.run_number}
            </span>

            <span className="text-gray-300 dark:text-gray-600 flex-shrink-0">|</span>

            {/* Status */}
            <span className={`text-xs flex-shrink-0 ${
              selectedRun.status === 'completed' ? 'text-green-600 dark:text-green-400' :
              selectedRun.status === 'failed' ? 'text-red-600 dark:text-red-400' :
              'text-blue-600 dark:text-blue-400'
            }`}>
              {selectedRun.status}
            </span>

            <span className="text-gray-300 dark:text-gray-600 flex-shrink-0">|</span>

            {/* Date */}
            <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
              {formatDate(selectedRun.created_at)}
            </span>

            <span className="text-gray-300 dark:text-gray-600 flex-shrink-0">|</span>

            {/* Findings count */}
            <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
              {selectedRun.critical_findings} critical / {selectedRun.total_findings} total
            </span>
          </div>
        ) : (
          <span className="text-xs text-gray-500 dark:text-gray-400">Select a run...</span>
        )}

        <ChevronIcon isOpen={isOpen} />
      </button>

      {/* Dropdown Menu - Compact */}
      {isOpen && (
        <div className="absolute z-50 mt-1 min-w-max bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-md shadow-lg overflow-hidden">
          <div className="max-h-64 overflow-y-auto">
            {runs.length === 0 ? (
              <div className="px-3 py-2 text-center text-gray-500 dark:text-gray-400 text-xs">
                No analysis runs available
              </div>
            ) : (
              runs.map((run) => (
                <button
                  key={run.id}
                  onClick={() => handleSelect(run.id)}
                  className={`w-full px-2.5 py-1.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                    run.id === selectedRunId ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
                      Run #{run.run_number}
                    </span>
                    <span className="text-gray-300 dark:text-gray-600">|</span>
                    <span className={`text-xs ${
                      run.status === 'completed' ? 'text-green-600 dark:text-green-400' :
                      run.status === 'failed' ? 'text-red-600 dark:text-red-400' :
                      'text-blue-600 dark:text-blue-400'
                    }`}>
                      {run.status}
                    </span>
                    <span className="text-gray-300 dark:text-gray-600">|</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDate(run.created_at)}
                    </span>
                    <span className="text-gray-300 dark:text-gray-600">|</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {run.critical_findings} critical / {run.total_findings} findings
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
