/**
 * Pipeline Rings Visualization - Concentric Design
 *
 * Apple Watch-style concentric rings showing the 7-pass processing pipeline.
 * Rings progress from outside (Extract) to inside (Verify), each with its own color.
 * Center displays a green checkmark when all passes complete.
 */
import React, { useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ProcessingPass,
  ProcessingProgress,
  PASS_CONFIG,
  PASS_ORDER,
  RING_COLORS,
  STATUS_COLORS
} from './types';
import { useReducedMotion } from './hooks';

interface PipelineRingsProps {
  progress: ProcessingProgress | null;
  size?: number;
  className?: string;
}

interface RingConfig {
  pass: ProcessingPass;
  radius: number;
  color: string;
}

// Calculate ring configurations based on size
const calculateRings = (size: number): RingConfig[] => {
  const center = size / 2;
  const strokeWidth = 12;
  const gap = 6;
  const ringSpacing = strokeWidth + gap;
  const centerReserved = 45; // Space for center checkmark

  // Build rings from inside out, then reverse for outside-in order
  const rings: RingConfig[] = [];

  // PASS_ORDER is outside-to-inside, so we reverse it to calculate from center out
  const reversedOrder = [...PASS_ORDER].reverse();

  reversedOrder.forEach((pass, index) => {
    const radius = centerReserved + (index * ringSpacing);
    rings.push({
      pass,
      radius,
      color: RING_COLORS[pass],
    });
  });

  // Reverse back so we render outside-to-inside (Extract first, Verify last)
  return rings.reverse();
};

// Single concentric ring component
const ConcentricRing: React.FC<{
  pass: ProcessingPass;
  radius: number;
  color: string;
  progress: number;
  isActive: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  centerX: number;
  centerY: number;
  strokeWidth: number;
  reducedMotion: boolean;
}> = ({
  pass,
  radius,
  color,
  progress,
  isActive,
  isCompleted,
  isFailed,
  centerX,
  centerY,
  strokeWidth,
  reducedMotion,
}) => {
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (progress / 100) * circumference;

  // Determine the progress color
  const progressColor = isFailed
    ? STATUS_COLORS.failed
    : isCompleted
      ? color // Use ring's own color when complete
      : isActive
        ? color // Use ring's own color when active
        : STATUS_COLORS.default;

  // Background track opacity
  const trackOpacity = isCompleted ? 0.3 : 0.15;

  return (
    <g>
      {/* Background track */}
      <circle
        cx={centerX}
        cy={centerY}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        opacity={trackOpacity}
      />

      {/* Progress arc */}
      <motion.circle
        cx={centerX}
        cy={centerY}
        r={radius}
        fill="none"
        stroke={progressColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${centerX} ${centerY})`}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: dashOffset }}
        transition={reducedMotion ? { duration: 0 } : { duration: 0.5, ease: 'easeOut' }}
      />

      {/* Active pulse effect */}
      {isActive && !reducedMotion && (
        <motion.circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth + 4}
          opacity={0}
          animate={{
            opacity: [0, 0.3, 0],
            strokeWidth: [strokeWidth, strokeWidth + 8, strokeWidth],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
    </g>
  );
};

// Center completion indicator
const CenterIndicator: React.FC<{
  isAllCompleted: boolean;
  isFailed: boolean;
  isCancelled: boolean;
  isProcessing: boolean;
  centerX: number;
  centerY: number;
  reducedMotion: boolean;
}> = ({
  isAllCompleted,
  isFailed,
  isCancelled,
  isProcessing,
  centerX,
  centerY,
  reducedMotion,
}) => {
  const circleRadius = 32;

  if (isAllCompleted) {
    return (
      <motion.g
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        {/* Alchemy orange circle background */}
        <circle
          cx={centerX}
          cy={centerY}
          r={circleRadius}
          fill="#ff6b00"
        />
        {/* White checkmark */}
        <motion.path
          d={`M${centerX - 12} ${centerY + 2} l8 8 l16 -18`}
          stroke="white"
          strokeWidth={4}
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        />
      </motion.g>
    );
  }

  if (isFailed) {
    return (
      <motion.g
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        <circle
          cx={centerX}
          cy={centerY}
          r={circleRadius}
          fill={STATUS_COLORS.failed}
        />
        <path
          d={`M${centerX - 10} ${centerY - 10} l20 20 M${centerX + 10} ${centerY - 10} l-20 20`}
          stroke="white"
          strokeWidth={4}
          fill="none"
          strokeLinecap="round"
        />
      </motion.g>
    );
  }

  if (isCancelled) {
    return (
      <motion.g
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
      >
        <circle
          cx={centerX}
          cy={centerY}
          r={circleRadius}
          fill="#9ca3af"
        />
        <rect
          x={centerX - 10}
          y={centerY - 10}
          width={20}
          height={20}
          rx={3}
          fill="white"
        />
      </motion.g>
    );
  }

  if (isProcessing) {
    return (
      <g>
        {/* Subtle pulsing circle */}
        <motion.circle
          cx={centerX}
          cy={centerY}
          r={circleRadius - 8}
          fill="none"
          stroke={STATUS_COLORS.default}
          strokeWidth={2}
          animate={reducedMotion ? {} : {
            opacity: [0.3, 0.6, 0.3],
            r: [circleRadius - 10, circleRadius - 6, circleRadius - 10],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </g>
    );
  }

  // Idle/waiting state
  return (
    <circle
      cx={centerX}
      cy={centerY}
      r={circleRadius - 8}
      fill="none"
      stroke={STATUS_COLORS.default}
      strokeWidth={2}
      opacity={0.3}
    />
  );
};

// Main Pipeline Rings component - Concentric Design
export const PipelineRings: React.FC<PipelineRingsProps> = ({
  progress,
  size = 280,
  className = ''
}) => {
  const reducedMotion = useReducedMotion();
  const strokeWidth = 12;
  const centerX = size / 2;
  const centerY = size / 2;

  // Calculate ring configurations
  const rings = useMemo(() => calculateRings(size), [size]);

  const getPassProgress = useCallback((pass: ProcessingPass): number => {
    if (!progress) return 0;
    return progress.passProgress[pass]?.progress ?? 0;
  }, [progress]);

  const isPassActive = useCallback((pass: ProcessingPass): boolean => {
    if (!progress) return false;
    return progress.currentPass === pass && progress.status === 'processing';
  }, [progress]);

  const isPassCompleted = useCallback((pass: ProcessingPass): boolean => {
    if (!progress) return false;
    return progress.passProgress[pass]?.status === 'completed';
  }, [progress]);

  const isPassFailed = useCallback((pass: ProcessingPass): boolean => {
    if (!progress) return false;
    return progress.passProgress[pass]?.status === 'failed' ||
           (progress.status === 'failed' && progress.currentPass === pass);
  }, [progress]);

  // Overall status
  const isAllCompleted = progress?.status === 'completed';
  const isFailed = progress?.status === 'failed';
  const isCancelled = progress?.status === 'cancelled';
  const isProcessing = progress?.status === 'processing';

  // Current active pass info
  const currentPassConfig = progress?.currentPass ? PASS_CONFIG[progress.currentPass] : null;

  return (
    <div className={`flex flex-col items-center ${className}`}>
      {/* Concentric rings SVG */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="overflow-visible"
      >
        {/* Render rings from outside to inside */}
        {rings.map((ring) => (
          <ConcentricRing
            key={ring.pass}
            pass={ring.pass}
            radius={ring.radius}
            color={ring.color}
            progress={getPassProgress(ring.pass)}
            isActive={isPassActive(ring.pass)}
            isCompleted={isPassCompleted(ring.pass)}
            isFailed={isPassFailed(ring.pass)}
            centerX={centerX}
            centerY={centerY}
            strokeWidth={strokeWidth}
            reducedMotion={reducedMotion}
          />
        ))}

        {/* Center indicator */}
        <CenterIndicator
          isAllCompleted={isAllCompleted}
          isFailed={isFailed}
          isCancelled={isCancelled}
          isProcessing={isProcessing}
          centerX={centerX}
          centerY={centerY}
          reducedMotion={reducedMotion}
        />
      </svg>
    </div>
  );
};

export default PipelineRings;
