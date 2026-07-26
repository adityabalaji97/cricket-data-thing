/**
 * Query-builder theme tokens.
 *
 * These now live in src/theme/hindsightDark.js, which is the single source of truth for the dark
 * design system. This module stays as an alias so the seven components already importing the
 * `qb*` names keep working unchanged; new code should import from the theme directly.
 */

import {
  buttonSx,
  cardSx,
  colors,
  fonts,
  ghostButtonSx,
} from '../theme/hindsightDark';

export const qbColors = colors;
export const qbFonts = fonts;
export const qbCardSx = cardSx;
export const qbButtonSx = buttonSx;
export const qbGhostButtonSx = ghostButtonSx;
