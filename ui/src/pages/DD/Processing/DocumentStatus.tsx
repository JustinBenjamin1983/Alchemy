/**
 * Document Status Components
 *
 * Visual display of document processing status with shimmer effects.
 */
import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DocumentStatus, ProcessingPass, PASS_CONFIG } from './types';
import {
  shimmerVariants,
  statusIconVariants,
  progressBarVariants,
  staggerContainerVariants,
  staggerChildVariants,
  reducedMotionVariants
} from './animations';
import { useReducedMotion } from './hooks';

// Document type icons
const DOC_TYPE_ICONS: Record<string, React.ReactNode> = {
  constitutional: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
  governance: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  contract: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  financial: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  employment: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  ),
  regulatory: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  ),
  other: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
  )
};

// Status colors
const STATUS_COLORS = {
  queued: 'text-gray-400 dark:text-gray-500',
  processing: 'text-blue-500 dark:text-blue-400',
  completed: 'text-emerald-500 dark:text-emerald-400',
  error: 'text-red-500 dark:text-red-400'
};

// Processing shimmer component
interface ProcessingShimmerProps {
  className?: string;
}

export const ProcessingShimmer: React.FC<ProcessingShimmerProps> = ({ className = '' }) => {
  const reducedMotion = useReducedMotion();

  if (reducedMotion) {
    return (
      <div className={`bg-gray-200 dark:bg-gray-700 rounded ${className}`} />
    );
  }

  return (
    <motion.div
      className={`relative overflow-hidden rounded ${className}`}
      style={{
        background: 'linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%)',
        backgroundSize: '200% 100%'
      }}
      variants={shimmerVariants}
      animate="animate"
    />
  );
};

// Status icon component
interface StatusIconProps {
  status: DocumentStatus['status'];
  className?: string;
}

const StatusIcon: React.FC<StatusIconProps> = ({ status, className = '' }) => {
  const reducedMotion = useReducedMotion();

  const icon = useMemo(() => {
    switch (status) {
      case 'queued':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'processing':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        );
      case 'completed':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  }, [status]);

  return (
    <motion.div
      className={`${STATUS_COLORS[status]} ${className}`}
      variants={reducedMotion ? reducedMotionVariants : statusIconVariants}
      animate={status}
    >
      {icon}
    </motion.div>
  );
};

// Document card component - Enhanced with shimmer and severity badges
interface DocumentCardProps {
  document: DocumentStatus;
  index: number;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({ document, index }) => {
  const reducedMotion = useReducedMotion();
  const docIcon = DOC_TYPE_ICONS[document.docType] || DOC_TYPE_ICONS.other;
  const passConfig = document.currentPass ? PASS_CONFIG[document.currentPass] : null;

  // Truncate filename
  const displayName = useMemo(() => {
    if (document.filename.length > 35) {
      const ext = document.filename.split('.').pop() || '';
      const name = document.filename.slice(0, 30);
      return `${name}...${ext}`;
    }
    return document.filename;
  }, [document.filename]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25, delay: index * 0.05 }}
      className={`
        relative p-3 rounded-lg border transition-all overflow-hidden
        ${document.status === 'processing'
          ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
          : document.status === 'completed'
          ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800'
          : document.status === 'error'
          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700'}
      `}
    >
      {/* Shimmer effect for processing documents */}
      {document.status === 'processing' && !reducedMotion && (
        <motion.div
          className="absolute inset-0 -translate-x-full"
          animate={{ x: ['0%', '200%'] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
            width: '50%'
          }}
        />
      )}

      <div className="flex items-center gap-3 relative z-10">
        {/* Document type icon with status indicator */}
        <div className="relative">
          <div className={`
            p-2 rounded-lg
            ${document.status === 'processing'
              ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'
              : document.status === 'completed'
              ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400'
              : document.status === 'error'
              ? 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}
          `}>
            {docIcon}
          </div>
          {/* Completion checkmark overlay */}
          {document.status === 'completed' && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25 }}
              className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full flex items-center justify-center"
            >
              <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </motion.div>
          )}
          {/* Processing spinner overlay */}
          {document.status === 'processing' && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="absolute -top-1 -right-1 w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"
            />
          )}
        </div>

        {/* Document info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {displayName}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-1">
            {/* Document type badge */}
            <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">
              {document.docType}
            </span>

            {/* Current pass indicator */}
            {passConfig && document.status === 'processing' && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-xs px-1.5 py-0.5 rounded font-medium"
                style={{
                  backgroundColor: `${passConfig.color}20`,
                  color: passConfig.color
                }}
              >
                {passConfig.shortLabel}
              </motion.span>
            )}
          </div>
        </div>

        {/* Progress indicator for processing docs */}
        {document.status === 'processing' && document.progress !== undefined && (
          <div className="w-12 text-right">
            <motion.span
              key={document.progress}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-xs font-bold text-blue-600 dark:text-blue-400"
            >
              {document.progress}%
            </motion.span>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {document.status === 'processing' && document.progress !== undefined && (
        <div className="mt-2 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: passConfig?.color || '#3B82F6' }}
            initial={{ width: 0 }}
            animate={{ width: `${document.progress}%` }}
            transition={{ type: 'spring', stiffness: 50, damping: 20 }}
          />
        </div>
      )}

      {/* Error message */}
      {document.status === 'error' && document.error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-2 text-xs text-red-600 dark:text-red-400 truncate"
        >
          {document.error}
        </motion.div>
      )}
    </motion.div>
  );
};

// Document status grid
interface DocumentStatusGridProps {
  documents: DocumentStatus[];
  className?: string;
}

export const DocumentStatusGrid: React.FC<DocumentStatusGridProps> = ({
  documents,
  className = ''
}) => {
  const reducedMotion = useReducedMotion();

  // Sort: processing first, then queued, then completed, then error
  const sortedDocuments = useMemo(() => {
    const statusOrder = { processing: 0, queued: 1, completed: 2, error: 3 };
    return [...documents].sort((a, b) =>
      statusOrder[a.status] - statusOrder[b.status]
    );
  }, [documents]);

  // Count by status
  const statusCounts = useMemo(() => {
    return documents.reduce((acc, doc) => {
      acc[doc.status] = (acc[doc.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
  }, [documents]);

  if (documents.length === 0) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <svg
          className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No documents loaded
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Status summary */}
      <div className="flex items-center gap-4 mb-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Documents
        </h3>
        <div className="flex items-center gap-3 text-xs">
          {statusCounts.processing && (
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              {statusCounts.processing} processing
            </span>
          )}
          {statusCounts.completed && (
            <span className="text-emerald-600 dark:text-emerald-400">
              {statusCounts.completed} completed
            </span>
          )}
          {statusCounts.queued && (
            <span className="text-gray-500 dark:text-gray-400">
              {statusCounts.queued} queued
            </span>
          )}
          {statusCounts.error && (
            <span className="text-red-600 dark:text-red-400">
              {statusCounts.error} failed
            </span>
          )}
        </div>
      </div>

      {/* Document grid */}
      <motion.div
        variants={reducedMotion ? undefined : staggerContainerVariants}
        initial="initial"
        animate="animate"
        className="grid grid-cols-1 md:grid-cols-2 gap-3"
      >
        <AnimatePresence mode="popLayout">
          {sortedDocuments.map((doc, index) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              index={index}
            />
          ))}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default DocumentStatusGrid;
