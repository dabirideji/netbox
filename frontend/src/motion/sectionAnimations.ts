/** Shared Motion presets for dashboard section cards and modals. */

import type { DashboardSectionId } from '../dashboardSections';
import { DASHBOARD_SECTION_IDS } from '../dashboardSections';

const EASE_OUT = [0.22, 1, 0.36, 1] as const;
const EASE_IN = [0.4, 0, 1, 1] as const;

/** Snappy spring — fast settle, no bounce. */
export const SPRING_SNAPPY = {
  type: 'spring' as const,
  stiffness: 460,
  damping: 38,
  mass: 0.72,
};

/** Slightly softer spring for page entrance. */
export const SPRING_ENTRANCE = {
  type: 'spring' as const,
  stiffness: 400,
  damping: 36,
  mass: 0.78,
};

export const SPRING_LAYOUT = {
  type: 'spring' as const,
  stiffness: 440,
  damping: 40,
  mass: 0.75,
};

export const sectionLayoutTransition = {
  layout: SPRING_LAYOUT,
};

export function sectionEntranceDelay(sectionId: DashboardSectionId): number {
  const index = DASHBOARD_SECTION_IDS.indexOf(sectionId);
  return (index >= 0 ? index : 0) * 0.028;
}

export const sectionCardEntranceInitial = {
  opacity: 0,
  y: 6,
};

export function sectionCardEntranceAnimate(sectionId: DashboardSectionId) {
  const delay = sectionEntranceDelay(sectionId);

  return {
    opacity: 1,
    y: 0,
    transition: {
      y: {
        ...SPRING_ENTRANCE,
        delay,
      },
      opacity: {
        duration: 0.2,
        delay,
        ease: EASE_OUT,
      },
    },
  };
}

export const sectionContentEnterInitial = {
  opacity: 0,
  height: 0,
};

export const sectionContentEnterAnimate = {
  opacity: 1,
  height: 'auto',
  transition: {
    height: SPRING_SNAPPY,
    opacity: {
      duration: 0.16,
      ease: EASE_OUT,
    },
  },
};

export const sectionContentExitAnimate = {
  opacity: 0,
  height: 0,
  transition: {
    height: SPRING_SNAPPY,
    opacity: {
      duration: 0.12,
      ease: EASE_IN,
    },
  },
};

export const sectionContentVisible = {
  opacity: 1,
  height: 'auto',
  transition: { duration: 0 },
};

export const modalBackdropInitial = { opacity: 0 };

export const modalBackdropAnimate = {
  opacity: 1,
  transition: { duration: 0.16, ease: EASE_OUT },
};

export const modalBackdropExit = {
  opacity: 0,
  transition: { duration: 0.12, ease: EASE_IN },
};

export const modalDialogInitial = {
  opacity: 0,
  y: 8,
  scale: 0.992,
};

export const modalDialogAnimate = {
  opacity: 1,
  y: 0,
  scale: 1,
  transition: {
    y: SPRING_SNAPPY,
    scale: SPRING_SNAPPY,
    opacity: { duration: 0.16, ease: EASE_OUT },
  },
};

export const modalDialogExit = {
  opacity: 0,
  y: 6,
  scale: 0.996,
  transition: {
    y: SPRING_SNAPPY,
    scale: { duration: 0.12, ease: EASE_IN },
    opacity: { duration: 0.12, ease: EASE_IN },
  },
};
