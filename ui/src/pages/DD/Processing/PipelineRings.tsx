/**
 * Pipeline Rings Visualization
 *
 * Animated concentric rings showing the 4-pass processing pipeline.
 * Each ring represents a pass: Extract, Analyze, Cross-Doc, Synthesize.
 *
 * Enhanced with:
 * - Orbiting particles along active ring path
 * - Pulse glow effect on active ring
 * - Completion checkmarks for finished passes
 * - Rotating gradient border effect
 */
import React, { useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ProcessingPass, ProcessingProgress, PASS_CONFIG } from './types';
import {
  ringPulseVariants,
  ringProgressVariants,
  particleVariants,
  reducedMotionVariants,
  SPRING_GENTLE,
  SPRING_BOUNCY
} from './animations';
import { useReducedMotion } from './hooks';

interface PipelineRingsProps {
  progress: ProcessingProgress | null;
  size?: number;
  className?: string;
}

interface PipelineRingProps {
  pass: ProcessingPass;
  radius: number;
  strokeWidth: number;
  progress: number;
  isActive: boolean;
  isCompleted: boolean;
  reducedMotion: boolean;
  centerX: number;
  centerY: number;
}

interface ParticleFlowProps {
  pass: ProcessingPass;
  radius: number;
  isActive: boolean;
  reducedMotion: boolean;
  centerX: number;
  centerY: number;
}

// Individual ring component
const PipelineRing: React.FC<PipelineRingProps> = ({
  pass,
  radius,
  strokeWidth,
  progress,
  isActive,
  isCompleted,
  reducedMotion,
  centerX,
  centerY
}) => {
  const config = PASS_CONFIG[pass];
  const circumference = 2 * Math.PI * radius;

  // Calculate the dash offset for progress
  const dashOffset = circumference - (progress / 100) * circumference;

  return (
    <g>
      {/* Background ring */}
      <circle
        cx={centerX}
        cy={centerY}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-gray-200 dark:text-gray-700"
        opacity={0.3}
      />

      {/* Progress ring */}
      <motion.circle
        cx={centerX}
        cy={centerY}
        r={radius}
        fill="none"
        stroke={config.color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${centerX} ${centerY})`}
        variants={reducedMotion ? reducedMotionVariants : ringProgressVariants}
        initial="initial"
        animate="animate"
        custom={progress}
        style={{
          filter: isActive ? `drop-shadow(0 0 8px ${config.color})` : 'none'
        }}
      />

      {/* Glow effect for active ring */}
      {isActive && !reducedMotion && (
        <motion.circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke={config.color}
          strokeWidth={strokeWidth + 4}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${centerX} ${centerY})`}
          opacity={0.3}
          variants={ringPulseVariants}
          initial="idle"
          animate="active"
        />
      )}

      {/* Completion indicator - full ring glow + checkmark position marker */}
      {isCompleted && (
        <>
          <motion.circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke={config.color}
            strokeWidth={2}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 0.3 }}
            transition={SPRING_GENTLE}
          />
          {/* Checkmark at the end of the ring */}
          <motion.g
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={SPRING_BOUNCY}
          >
            <circle
              cx={centerX + radius}
              cy={centerY}
              r={8}
              fill={config.color}
            />
            <path
              d={`M${centerX + radius - 3} ${centerY} l2 2 l4 -4`}
              stroke="white"
              strokeWidth={2}
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </motion.g>
        </>
      )}
    </g>
  );
};

// Orbiting particle component that follows circular path
const OrbitingParticle: React.FC<{
  radius: number;
  delay: number;
  duration: number;
  color: string;
  size: number;
  centerX: number;
  centerY: number;
}> = ({ radius, delay, duration, color, size, centerX, centerY }) => {
  return (
    <motion.circle
      cx={centerX + radius}
      cy={centerY}
      r={size}
      fill={color}
      initial={{ opacity: 0 }}
      animate={{
        opacity: [0.3, 1, 0.3],
      }}
      style={{
        transformOrigin: `${centerX}px ${centerY}px`,
      }}
      transition={{
        opacity: {
          duration: duration / 2,
          repeat: Infinity,
          ease: 'easeInOut',
          delay
        }
      }}
    >
      <animateTransform
        attributeName="transform"
        type="rotate"
        from={`0 ${centerX} ${centerY}`}
        to={`360 ${centerX} ${centerY}`}
        dur={`${duration}s`}
        repeatCount="indefinite"
        begin={`${delay}s`}
      />
    </motion.circle>
  );
};

// Particle flow animation between rings - Enhanced with orbiting particles
const ParticleFlow: React.FC<ParticleFlowProps> = ({
  pass,
  radius,
  isActive,
  reducedMotion,
  centerX,
  centerY
}) => {
  const config = PASS_CONFIG[pass];

  // Generate orbiting particles - 4 particles at different positions
  const particles = useMemo(() => {
    if (reducedMotion || !isActive) return [];

    return Array.from({ length: 4 }, (_, i) => ({
      id: `${pass}-orbit-${i}`,
      delay: i * 0.75, // Stagger start times
      size: 3 - i * 0.3, // Slightly smaller trailing particles
    }));
  }, [pass, isActive, reducedMotion]);

  if (!isActive || reducedMotion) return null;

  return (
    <g>
      {particles.map((particle) => (
        <OrbitingParticle
          key={particle.id}
          radius={radius}
          delay={particle.delay}
          duration={3} // 3 seconds for full orbit
          color={config.color}
          size={particle.size}
          centerX={centerX}
          centerY={centerY}
        />
      ))}
    </g>
  );
};

// Main Pipeline Rings component
export const PipelineRings: React.FC<PipelineRingsProps> = ({
  progress,
  size = 320,
  className = ''
}) => {
  const reducedMotion = useReducedMotion();

  const centerX = size / 2;
  const centerY = size / 2;

  // Calculate ring radii (outermost to innermost)
  const rings: { pass: ProcessingPass; radius: number; strokeWidth: number }[] = useMemo(() => [
    { pass: 'extract', radius: (size / 2) - 20, strokeWidth: 12 },
    { pass: 'analyze', radius: (size / 2) - 50, strokeWidth: 12 },
    { pass: 'crossdoc', radius: (size / 2) - 80, strokeWidth: 12 },
    { pass: 'synthesize', radius: (size / 2) - 110, strokeWidth: 12 }
  ], [size]);

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

  // Current pass info for center display
  const currentPassInfo = useMemo(() => {
    if (!progress || progress.status !== 'processing') return null;
    return PASS_CONFIG[progress.currentPass];
  }, [progress]);

  return (
    <div className={`relative ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="overflow-visible"
      >
        {/* Rings */}
        {rings.map(({ pass, radius, strokeWidth }) => (
          <React.Fragment key={pass}>
            <PipelineRing
              pass={pass}
              radius={radius}
              strokeWidth={strokeWidth}
              progress={getPassProgress(pass)}
              isActive={isPassActive(pass)}
              isCompleted={isPassCompleted(pass)}
              reducedMotion={reducedMotion}
              centerX={centerX}
              centerY={centerY}
            />
            <ParticleFlow
              pass={pass}
              radius={radius}
              isActive={isPassActive(pass)}
              reducedMotion={reducedMotion}
              centerX={centerX}
              centerY={centerY}
            />
          </React.Fragment>
        ))}
      </svg>

      {/* Center content */}
      <div
        className="absolute inset-0 flex items-center justify-center"
        style={{ pointerEvents: 'none' }}
      >
        <AnimatePresence mode="wait">
          {progress?.status === 'completed' ? (
            <motion.div
              key="completed"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={SPRING_GENTLE}
              className="flex flex-col items-center"
            >
              <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mb-2">
                <svg
                  className="w-8 h-8 text-emerald-600 dark:text-emerald-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                Complete
              </span>
            </motion.div>
          ) : currentPassInfo ? (
            <motion.div
              key={progress?.currentPass}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center text-center px-4"
            >
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center mb-2"
                style={{ backgroundColor: `${currentPassInfo.color}20` }}
              >
                <motion.div
                  animate={reducedMotion ? {} : { rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                >
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke={currentPassInfo.color}
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </motion.div>
              </div>
              <span
                className="text-sm font-semibold"
                style={{ color: currentPassInfo.color }}
              >
                {currentPassInfo.shortLabel}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-[120px]">
                {currentPassInfo.description}
              </span>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center"
            >
              <div className="w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-2">
                <svg
                  className="w-6 h-6 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Waiting
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Ring labels */}
      <div className="absolute inset-0 pointer-events-none">
        {rings.map(({ pass, radius }, index) => {
          const config = PASS_CONFIG[pass];
          const isActive = isPassActive(pass);
          const isCompleted = isPassCompleted(pass);

          // Position labels at top of each ring
          const labelY = centerY - radius - 16;

          return (
            <motion.div
              key={pass}
              className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap"
              style={{ top: labelY }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  isActive
                    ? 'text-white'
                    : isCompleted
                    ? 'text-white'
                    : 'text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800'
                }`}
                style={{
                  backgroundColor: isActive || isCompleted ? config.color : undefined
                }}
              >
                {config.shortLabel}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default PipelineRings;
