/**
 * Live Findings Feed Components
 *
 * Real-time display of findings as they're discovered during processing.
 */
import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LiveFinding, RiskSummary, PASS_CONFIG } from './types';
import {
  findingCardVariants,
  severityPulseVariants,
  counterVariants,
  staggerContainerVariants,
  staggerChildVariants,
  reducedMotionVariants,
  SPRING_BOUNCY
} from './animations';
import { useReducedMotion, useAnimatedNumber } from './hooks';

// Severity color mapping
const SEVERITY_COLORS: Record<LiveFinding['severity'], {
  bg: string;
  text: string;
  border: string;
  badge: string;
}> = {
  critical: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    text: 'text-red-800 dark:text-red-200',
    border: 'border-red-200 dark:border-red-800',
    badge: 'bg-red-500 text-white'
  },
  high: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    text: 'text-orange-800 dark:text-orange-200',
    border: 'border-orange-200 dark:border-orange-800',
    badge: 'bg-orange-500 text-white'
  },
  medium: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    text: 'text-yellow-800 dark:text-yellow-200',
    border: 'border-yellow-200 dark:border-yellow-800',
    badge: 'bg-yellow-500 text-white'
  },
  low: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    text: 'text-blue-800 dark:text-blue-200',
    border: 'border-blue-200 dark:border-blue-800',
    badge: 'bg-blue-500 text-white'
  },
  info: {
    bg: 'bg-gray-50 dark:bg-gray-800/50',
    text: 'text-gray-700 dark:text-gray-300',
    border: 'border-gray-200 dark:border-gray-700',
    badge: 'bg-gray-500 text-white'
  }
};

// Deal impact labels
const DEAL_IMPACT_LABELS: Record<LiveFinding['dealImpact'], string> = {
  deal_blocker: 'Deal Blocker',
  condition_precedent: 'Condition Precedent',
  price_chip: 'Price Chip',
  warranty_indemnity: 'Warranty/Indemnity',
  post_closing: 'Post-Closing',
  noted: 'Noted'
};

interface FindingCardProps {
  finding: LiveFinding;
  index: number;
}

const FindingCard: React.FC<FindingCardProps> = ({ finding, index }) => {
  const reducedMotion = useReducedMotion();
  const colors = SEVERITY_COLORS[finding.severity];
  const passConfig = PASS_CONFIG[finding.pass];

  const isCritical = finding.severity === 'critical';
  const isHigh = finding.severity === 'high';
  const isPulsingBadge = isCritical || isHigh;

  // Format timestamp
  const timeAgo = useMemo(() => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - finding.timestamp.getTime()) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  }, [finding.timestamp]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -50, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={`
        relative p-4 rounded-lg border-l-4 ${colors.bg} ${colors.border}
        shadow-sm hover:shadow-md transition-shadow
      `}
      style={{ borderLeftColor: passConfig.color }}
    >
      {/* Critical finding pulse effect */}
      {isCritical && index === 0 && !reducedMotion && (
        <motion.div
          className="absolute inset-0 rounded-lg pointer-events-none"
          initial={{ boxShadow: '0 0 0 0 rgba(220, 38, 38, 0)' }}
          animate={{
            boxShadow: [
              '0 0 0 0 rgba(220, 38, 38, 0)',
              '0 0 20px 4px rgba(220, 38, 38, 0.4)',
              '0 0 0 0 rgba(220, 38, 38, 0)',
            ]
          }}
          transition={{ duration: 0.6, times: [0, 0.5, 1], repeat: 2 }}
        />
      )}
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Severity badge */}
          <motion.span
            variants={isPulsingBadge && !reducedMotion ? severityPulseVariants : undefined}
            animate={isPulsingBadge ? finding.severity : 'normal'}
            className={`
              px-2 py-0.5 text-xs font-semibold rounded-full uppercase
              ${colors.badge}
            `}
          >
            {finding.severity}
          </motion.span>

          {/* Deal impact */}
          <span className={`text-xs font-medium ${colors.text}`}>
            {DEAL_IMPACT_LABELS[finding.dealImpact]}
          </span>
        </div>

        {/* Timestamp */}
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {timeAgo}
        </span>
      </div>

      {/* Description */}
      <p className={`text-sm ${colors.text} mb-2 line-clamp-2`}>
        {finding.description}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {/* Source document */}
          <span className="text-gray-500 dark:text-gray-400 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {finding.sourceDocument.length > 30
              ? `${finding.sourceDocument.slice(0, 27)}...`
              : finding.sourceDocument}
          </span>
        </div>

        {/* Pass indicator */}
        <span
          className="px-1.5 py-0.5 rounded text-xs font-medium"
          style={{
            backgroundColor: `${passConfig.color}20`,
            color: passConfig.color
          }}
        >
          Pass {(['extract', 'analyze', 'crossdoc', 'synthesize'].indexOf(finding.pass) + 1)}
        </span>
      </div>

      {/* Financial exposure if present */}
      {finding.financialExposure && (
        <div className="mt-2 pt-2 border-t border-dashed border-gray-200 dark:border-gray-700">
          <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
            Exposure: {' '}
            <span className="text-red-600 dark:text-red-400">
              {new Intl.NumberFormat('en-ZA', {
                style: 'currency',
                currency: finding.financialExposure.currency
              }).format(finding.financialExposure.amount)}
            </span>
          </span>
        </div>
      )}

      {/* New finding indicator */}
      {index === 0 && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-2 -right-2 w-4 h-4 bg-blue-500 rounded-full"
        >
          <motion.div
            className="absolute inset-0 bg-blue-500 rounded-full"
            animate={reducedMotion ? {} : {
              scale: [1, 1.5, 1],
              opacity: [1, 0, 1]
            }}
            transition={{ duration: 1, repeat: 2 }}
          />
        </motion.div>
      )}
    </motion.div>
  );
};

interface LiveFindingsFeedProps {
  findings: LiveFinding[];
  maxVisible?: number;
  className?: string;
}

export const LiveFindingsFeed: React.FC<LiveFindingsFeedProps> = ({
  findings,
  maxVisible = 10,
  className = ''
}) => {
  const reducedMotion = useReducedMotion();
  const visibleFindings = findings.slice(0, maxVisible);

  if (findings.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center py-12 ${className}`}>
        <motion.div
          animate={reducedMotion ? {} : { y: [0, -5, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <svg
            className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
        </motion.div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Waiting for findings...
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          Findings will appear here as they're discovered
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Live Findings
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {findings.length} found
        </span>
      </div>

      <motion.div
        variants={reducedMotion ? undefined : staggerContainerVariants}
        initial="initial"
        animate="animate"
        className="space-y-3"
      >
        <AnimatePresence mode="popLayout">
          {visibleFindings.map((finding, index) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              index={index}
            />
          ))}
        </AnimatePresence>
      </motion.div>

      {findings.length > maxVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-2"
        >
          <span className="text-xs text-gray-500 dark:text-gray-400">
            +{findings.length - maxVisible} more findings
          </span>
        </motion.div>
      )}
    </div>
  );
};

interface RiskCounterProps {
  label: string;
  value: number;
  color: string;
  bgColor?: string;
  icon?: React.ReactNode;
  pulse?: boolean;
}

const RiskCounter: React.FC<RiskCounterProps> = ({ label, value, color, bgColor, icon, pulse }) => {
  const reducedMotion = useReducedMotion();
  const animatedValue = useAnimatedNumber(value, reducedMotion ? 0 : 300);

  return (
    <motion.div
      variants={reducedMotion ? reducedMotionVariants : staggerChildVariants}
      className="relative flex flex-col items-center p-3 rounded-lg shadow-sm overflow-hidden"
      style={{ backgroundColor: bgColor || 'white' }}
    >
      {/* Pulse effect for non-zero critical values */}
      {pulse && value > 0 && !reducedMotion && (
        <motion.div
          className="absolute inset-0 rounded-lg"
          animate={{
            boxShadow: [
              `inset 0 0 0 0 ${color}00`,
              `inset 0 0 20px 2px ${color}30`,
              `inset 0 0 0 0 ${color}00`,
            ]
          }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
      <div className="flex items-center gap-1.5 mb-1 relative z-10">
        {icon}
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <AnimatePresence mode="popLayout">
        <motion.span
          key={value}
          initial={{ y: 20, opacity: 0, scale: 0.8 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          exit={{ y: -20, opacity: 0, scale: 0.8 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="text-2xl font-bold relative z-10"
          style={{ color }}
        >
          {animatedValue}
        </motion.span>
      </AnimatePresence>
    </motion.div>
  );
};

interface RiskSummaryCountersProps {
  summary: RiskSummary;
  className?: string;
}

export const RiskSummaryCounters: React.FC<RiskSummaryCountersProps> = ({
  summary,
  className = ''
}) => {
  const reducedMotion = useReducedMotion();

  return (
    <motion.div
      variants={reducedMotion ? undefined : staggerContainerVariants}
      initial="initial"
      animate="animate"
      className={`grid grid-cols-2 md:grid-cols-4 gap-3 ${className}`}
    >
      <RiskCounter
        label="Critical"
        value={summary.critical}
        color="#DC2626"
        bgColor={summary.critical > 0 ? '#FEF2F2' : '#FFFFFF'}
        pulse={true}
        icon={
          <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        }
      />
      <RiskCounter
        label="High"
        value={summary.high}
        color="#EA580C"
        bgColor={summary.high > 0 ? '#FFF7ED' : '#FFFFFF'}
        icon={
          <svg className="w-4 h-4 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        }
      />
      <RiskCounter
        label="Deal Blockers"
        value={summary.dealBlockers}
        color="#B91C1C"
        bgColor={summary.dealBlockers > 0 ? '#FEE2E2' : '#FFFFFF'}
        pulse={true}
        icon={
          <svg className="w-4 h-4 text-red-700" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
          </svg>
        }
      />
      <RiskCounter
        label="Conditions Precedent"
        value={summary.conditionsPrecedent}
        color="#7C3AED"
        bgColor={summary.conditionsPrecedent > 0 ? '#F5F3FF' : '#FFFFFF'}
        icon={
          <svg className="w-4 h-4 text-violet-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        }
      />
    </motion.div>
  );
};

export default LiveFindingsFeed;
