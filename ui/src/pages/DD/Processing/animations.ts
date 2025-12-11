/**
 * DD Processing Dashboard Animations
 *
 * Framer Motion animation configurations for smooth, premium UI/UX.
 */
import { Variants, Transition } from 'framer-motion';

// Spring configurations for different feel
export const SPRING_GENTLE: Transition = {
  type: 'spring',
  stiffness: 120,
  damping: 20
};

export const SPRING_BOUNCY: Transition = {
  type: 'spring',
  stiffness: 200,
  damping: 15
};

export const SPRING_SNAPPY: Transition = {
  type: 'spring',
  stiffness: 300,
  damping: 25
};

// Easing curves
export const EASE_OUT_EXPO = [0.16, 1, 0.3, 1];
export const EASE_OUT_QUART = [0.25, 1, 0.5, 1];
export const EASE_IN_OUT_CUBIC = [0.65, 0, 0.35, 1];

// Ring pulse animation
export const ringPulseVariants: Variants = {
  idle: {
    scale: 1,
    opacity: 0.3,
    filter: 'blur(0px)'
  },
  active: {
    scale: [1, 1.05, 1],
    opacity: [0.5, 0.8, 0.5],
    filter: ['blur(0px)', 'blur(2px)', 'blur(0px)'],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  },
  completed: {
    scale: 1,
    opacity: 1,
    filter: 'blur(0px)',
    transition: SPRING_GENTLE
  }
};

// Ring progress arc animation
export const ringProgressVariants: Variants = {
  initial: {
    pathLength: 0,
    opacity: 0
  },
  animate: (progress: number) => ({
    pathLength: progress / 100,
    opacity: 1,
    transition: {
      pathLength: {
        type: 'spring',
        stiffness: 50,
        damping: 20
      },
      opacity: { duration: 0.3 }
    }
  })
};

// Particle flow animation
export const particleVariants: Variants = {
  initial: {
    opacity: 0,
    scale: 0
  },
  animate: {
    opacity: [0, 0.8, 0],
    scale: [0.5, 1, 0.3],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'linear'
    }
  }
};

// Finding card entrance animation
export const findingCardVariants: Variants = {
  initial: {
    opacity: 0,
    x: 50,
    scale: 0.9
  },
  animate: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: {
      ...SPRING_BOUNCY,
      opacity: { duration: 0.3 }
    }
  },
  exit: {
    opacity: 0,
    x: -20,
    scale: 0.95,
    transition: {
      duration: 0.2
    }
  }
};

// Severity badge pulse for critical/high
export const severityPulseVariants: Variants = {
  critical: {
    scale: [1, 1.1, 1],
    boxShadow: [
      '0 0 0 0 rgba(239, 68, 68, 0.4)',
      '0 0 0 8px rgba(239, 68, 68, 0)',
      '0 0 0 0 rgba(239, 68, 68, 0)'
    ],
    transition: {
      duration: 1.5,
      repeat: 3,
      ease: 'easeOut'
    }
  },
  high: {
    scale: [1, 1.05, 1],
    boxShadow: [
      '0 0 0 0 rgba(249, 115, 22, 0.3)',
      '0 0 0 6px rgba(249, 115, 22, 0)',
      '0 0 0 0 rgba(249, 115, 22, 0)'
    ],
    transition: {
      duration: 1.5,
      repeat: 2,
      ease: 'easeOut'
    }
  },
  normal: {
    scale: 1,
    boxShadow: 'none'
  }
};

// Document card processing shimmer
export const shimmerVariants: Variants = {
  animate: {
    backgroundPosition: ['200% 0', '-200% 0'],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear'
    }
  }
};

// Counter increment animation
export const counterVariants: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: SPRING_SNAPPY
  },
  bump: {
    scale: [1, 1.2, 1],
    transition: {
      duration: 0.3,
      ease: EASE_OUT_EXPO
    }
  }
};

// Stagger children animations
export const staggerContainerVariants: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1
    }
  }
};

export const staggerChildVariants: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: SPRING_GENTLE
  }
};

// Pass transition animation
export const passTransitionVariants: Variants = {
  initial: {
    opacity: 0,
    scale: 0.8,
    rotateY: -30
  },
  animate: {
    opacity: 1,
    scale: 1,
    rotateY: 0,
    transition: {
      ...SPRING_BOUNCY,
      opacity: { duration: 0.4 }
    }
  },
  exit: {
    opacity: 0,
    scale: 1.1,
    rotateY: 30,
    transition: {
      duration: 0.3,
      ease: EASE_OUT_QUART
    }
  }
};

// Document status icon animations
export const statusIconVariants: Variants = {
  queued: {
    opacity: 0.5,
    scale: 1
  },
  processing: {
    opacity: 1,
    scale: [1, 1.1, 1],
    rotate: [0, 360],
    transition: {
      scale: {
        duration: 0.8,
        repeat: Infinity,
        ease: 'easeInOut'
      },
      rotate: {
        duration: 2,
        repeat: Infinity,
        ease: 'linear'
      }
    }
  },
  completed: {
    opacity: 1,
    scale: [0.8, 1.2, 1],
    transition: SPRING_BOUNCY
  },
  error: {
    opacity: 1,
    scale: 1,
    x: [0, -3, 3, -3, 3, 0],
    transition: {
      x: {
        duration: 0.4,
        ease: 'easeInOut'
      }
    }
  }
};

// Progress bar fill animation
export const progressBarVariants: Variants = {
  initial: { scaleX: 0 },
  animate: (progress: number) => ({
    scaleX: progress / 100,
    transition: {
      type: 'spring',
      stiffness: 100,
      damping: 20
    }
  })
};

// Glow effect for active elements
export const glowVariants: Variants = {
  inactive: {
    boxShadow: '0 0 0 0 rgba(59, 130, 246, 0)'
  },
  active: {
    boxShadow: [
      '0 0 20px 0 rgba(59, 130, 246, 0.3)',
      '0 0 40px 10px rgba(59, 130, 246, 0.1)',
      '0 0 20px 0 rgba(59, 130, 246, 0.3)'
    ],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  }
};

// Cost ticker animation
export const tickerVariants: Variants = {
  initial: { opacity: 0, y: -10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2 }
  },
  exit: {
    opacity: 0,
    y: 10,
    transition: { duration: 0.1 }
  }
};

// Completion celebration animation
export const celebrationVariants: Variants = {
  initial: { scale: 0, rotate: -180 },
  animate: {
    scale: 1,
    rotate: 0,
    transition: {
      type: 'spring',
      stiffness: 200,
      damping: 15
    }
  }
};

// Reduced motion alternatives (for accessibility)
export const reducedMotionVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.1 } }
};
