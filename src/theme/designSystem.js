import { colors as hsColors } from './hindsightDark';

/**
 * Design System - Cricket Data Thing
 *
 * Single source of truth for design tokens and theme configuration.
 * - Import tokens from this module instead of hardcoding values.
 * - Use the MUI theme from src/theme for consistent component styling.
 *
 * World-class design tokens inspired by Stripe, Linear, and Vercel.
 */

// Spacing scale (4px base unit)
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
  section: 40,
};

// Color palette
//
// Dark-mode values. These keys were a light palette (neutral[0] white cards, neutral[900] near-
// black text, sky-blue primary) and ~40 components index them directly in sx, which bypasses the
// MUI theme — so after the app went dark they rendered as white islands. Rather than edit ~200
// call sites, each key now holds its dark-design equivalent from hindsightDark:
//   neutral 0-100  -> surfaces (cards, subtle fills)      neutral 200-300 -> hairlines/borders
//   neutral 400-950 -> text, faint to brightest            primary -> the lime accent scale
//   success/warning/error 50 -> translucent tints; 500-700 -> hues readable on dark
// So `backgroundColor: neutral[0]` is still "card surface" and `color: neutral[900]` is still
// "strongest text"; only the rendering flipped. New code should prefer theme palette tokens
// (background.paper, text.primary, divider) or hindsightDark `colors` directly.
export const colors = {
  primary: {
    50: 'rgba(182,242,74,0.10)',
    100: 'rgba(182,242,74,0.16)',
    200: 'rgba(182,242,74,0.28)',
    300: '#8fc93a',
    400: '#a6e043',
    500: hsColors.accent,
    600: hsColors.accent,
    700: hsColors.accentHover,
    800: '#d6f79a',
    900: '#e6fbc2',
  },

  success: {
    50: 'rgba(74,222,128,0.12)',
    100: 'rgba(74,222,128,0.20)',
    500: '#22c55e',
    600: '#4ade80',
    700: '#86efac',
    900: '#dcfce7',
  },

  warning: {
    50: 'rgba(240,180,41,0.12)',
    100: 'rgba(240,180,41,0.20)',
    500: hsColors.gold,
    600: '#f5c451',
    700: '#fcd34d',
    900: '#fef3c7',
  },

  error: {
    50: 'rgba(229,72,77,0.12)',
    100: 'rgba(229,72,77,0.20)',
    500: '#ef4444',
    600: '#f87171',
    700: '#fca5a5',
    900: '#fee2e2',
  },

  neutral: {
    0: hsColors.surface1,
    50: hsColors.surface2,
    100: hsColors.surface3,
    200: '#252a33',
    300: '#2f3540',
    // Faintest *readable* text (~3.2:1 on cards). textGhost sat at 2.5:1 and ~20 call sites use
    // this step for real captions (ball counts, labels), not just decoration.
    400: '#5f6672',
    500: hsColors.textFaint,
    600: hsColors.textLo,
    700: hsColors.textMed,
    800: '#e2e5ea',
    900: hsColors.textHi,
    950: '#ffffff',
  },

  // Data visualization (saturated hues read fine on dark surfaces)
  chart: {
    blue: '#3b82f6',
    indigo: '#6366f1',
    purple: '#a855f7',
    pink: '#ec4899',
    red: '#ef4444',
    orange: '#f97316',
    yellow: '#eab308',
    green: '#22c55e',
    teal: '#14b8a6',
    cyan: '#06b6d4',
  },
};

// Typography scale
export const typography = {
  fontFamily: {
    sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
  },

  fontSize: {
    xs: '0.75rem',      // 12px
    sm: '0.875rem',     // 14px
    base: '1rem',       // 16px
    lg: '1.125rem',     // 18px
    xl: '1.25rem',      // 20px
    '2xl': '1.5rem',    // 24px
    '3xl': '1.875rem',  // 30px
    '4xl': '2.25rem',   // 36px
    '5xl': '3rem',      // 48px
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.75,
  },
};

// Typography usage guide mapped to MUI variants
export const typographyUsage = {
  h1: {
    label: 'H1',
    muiVariant: 'h1',
    fontSize: typography.fontSize['4xl'],
    fontWeight: typography.fontWeight.bold,
    lineHeight: typography.lineHeight.tight,
  },
  h2: {
    label: 'H2',
    muiVariant: 'h2',
    fontSize: typography.fontSize['3xl'],
    fontWeight: typography.fontWeight.bold,
    lineHeight: typography.lineHeight.tight,
  },
  h3: {
    label: 'H3',
    muiVariant: 'h3',
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.tight,
  },
  body: {
    label: 'Body',
    muiVariant: 'body1',
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.normal,
    lineHeight: typography.lineHeight.normal,
  },
  caption: {
    label: 'Caption',
    muiVariant: 'caption',
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.normal,
    lineHeight: typography.lineHeight.normal,
  },
};

// Border radius scale
export const borderRadius = {
  none: 0,
  sm: 4,
  base: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
};

// Shadow system (elevation)
export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
};

// Transitions
export const transitions = {
  fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  base: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  bounce: '500ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
};

// Breakpoints
export const breakpoints = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  xxl: 1536,
};

// Z-index scale
export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  modal: 30,
  popover: 40,
  tooltip: 50,
};

// Component-specific tokens
export const components = {
  card: {
    padding: {
      mobile: spacing.base,
      desktop: spacing.lg,
    },
    borderRadius: borderRadius.base,
    background: colors.neutral[0],
    border: `1px solid ${colors.neutral[200]}`,
    shadow: shadows.sm,
    hover: {
      shadow: shadows.base,
      borderColor: colors.neutral[300],
    },
  },

  section: {
    spacing: {
      mobile: spacing.lg,
      desktop: spacing.xl,
    },
  },

  filter: {
    height: {
      mobile: 40,
      desktop: 36,
    },
    borderRadius: borderRadius.base,
    padding: `${spacing.sm}px ${spacing.md}px`,
  },

  button: {
    height: {
      small: 32,
      medium: 40,
      large: 48,
    },
    borderRadius: borderRadius.base,
    padding: {
      small: `${spacing.xs}px ${spacing.md}px`,
      medium: `${spacing.sm}px ${spacing.base}px`,
      large: `${spacing.md}px ${spacing.lg}px`,
    },
  },
};

// Export a theme object for MUI
export const muiTheme = {
  palette: {
    primary: {
      main: colors.primary[600],
      light: colors.primary[400],
      dark: colors.primary[700],
    },
    secondary: {
      main: colors.neutral[700],
      light: colors.neutral[500],
      dark: colors.neutral[900],
    },
    success: {
      main: colors.success[600],
    },
    warning: {
      main: colors.warning[600],
    },
    error: {
      main: colors.error[600],
    },
    background: {
      default: colors.neutral[50],
      paper: colors.neutral[0],
    },
    text: {
      primary: colors.neutral[900],
      secondary: colors.neutral[600],
      disabled: colors.neutral[400],
    },
  },

  typography: {
    fontFamily: typography.fontFamily.sans,
    fontSize: 16,
    h1: {
      fontSize: typography.fontSize['4xl'],
      fontWeight: typography.fontWeight.bold,
      lineHeight: typography.lineHeight.tight,
    },
    h2: {
      fontSize: typography.fontSize['3xl'],
      fontWeight: typography.fontWeight.bold,
      lineHeight: typography.lineHeight.tight,
    },
    h3: {
      fontSize: typography.fontSize['2xl'],
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.tight,
    },
    h4: {
      fontSize: typography.fontSize.xl,
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.normal,
    },
    h5: {
      fontSize: typography.fontSize.lg,
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.normal,
    },
    h6: {
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      lineHeight: typography.lineHeight.normal,
    },
    body1: {
      fontSize: typography.fontSize.base,
      lineHeight: typography.lineHeight.normal,
    },
    body2: {
      fontSize: typography.fontSize.sm,
      lineHeight: typography.lineHeight.normal,
    },
    caption: {
      fontSize: typography.fontSize.xs,
      lineHeight: typography.lineHeight.normal,
    },
  },

  shape: {
    borderRadius: borderRadius.base,
  },

  shadows: [
    shadows.none,
    shadows.sm,
    shadows.base,
    shadows.md,
    shadows.lg,
    shadows.xl,
    ...Array(19).fill(shadows.xl), // Fill remaining shadow levels
  ],

  transitions: {
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195,
    },
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
    },
  },
};

export default {
  spacing,
  colors,
  typography,
  typographyUsage,
  borderRadius,
  shadows,
  transitions,
  breakpoints,
  zIndex,
  components,
  muiTheme,
};
