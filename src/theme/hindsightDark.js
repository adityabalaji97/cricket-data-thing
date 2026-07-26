/**
 * The Hindsight dark design system — the single source of truth for its tokens.
 *
 * These values previously existed three times over: in components/queryBuilderTheme.js, as local
 * `C` and `fonts` consts inside LandingPage.jsx, and as raw hex literals throughout
 * scorecard/matchScorecard.css. Three copies of the same palette drift, and one already had:
 * the hairline border was rgba(255,255,255,0.07) in the query builder and 0.06 on the landing
 * page. This file resolves that to 0.07 and is now the only place a token is defined.
 *
 * Token names follow the query-builder set, because those were already the most systematic and
 * are used across seven components. LandingPage maps its shorter names onto these.
 */

export const colors = {
  // Surfaces, darkest to lightest
  bg: '#0a0c11',
  inset: '#070a0e',
  surface1: '#101319',
  surface2: '#14171e',
  surface3: '#161a22',
  input: '#0d1015',

  // Lime accent
  accent: '#b6f24a',
  accentHover: '#c8f56f',
  accentSoft: 'rgba(182,242,74,0.13)',

  // Text, brightest to faintest
  textHi: '#f3f4f6',
  textMed: '#c3c8d0',
  textLo: '#9aa1ac',
  textFaint: '#6b7280',
  textGhost: '#4b5563',

  // Semantic
  blue: '#5b8def',
  gold: '#f0b429',
  red: '#e5484d',
  purple: '#c99cf0',

  border: 'rgba(255,255,255,0.07)',
  borderStrong: 'rgba(255,255,255,0.12)',
};

export const fonts = {
  body: '"Barlow", sans-serif',
  display: '"Barlow Semi Condensed", sans-serif',
  mono: '"IBM Plex Mono", monospace',
};

export const cardSx = {
  bgcolor: colors.surface1,
  color: colors.textHi,
  border: `1px solid ${colors.border}`,
  borderRadius: '20px',
  boxShadow: 'none',
};

export const buttonSx = {
  bgcolor: colors.accent,
  color: colors.bg,
  borderRadius: '10px',
  fontFamily: fonts.mono,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  '&:hover': { bgcolor: colors.accentHover },
  '&.Mui-disabled': {
    bgcolor: 'rgba(255,255,255,0.08)',
    color: colors.textFaint,
  },
};

export const ghostButtonSx = {
  color: colors.textMed,
  borderColor: colors.borderStrong,
  borderRadius: '10px',
  fontFamily: fonts.mono,
  fontSize: 11,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  '&:hover': {
    borderColor: 'rgba(182,242,74,0.4)',
    color: colors.accent,
    bgcolor: 'rgba(182,242,74,0.06)',
  },
};

/**
 * The same tokens as CSS custom properties, for stylesheets that cannot import JS.
 * Applied to :root by src/index.js so matchScorecard.css can use var(--hs-*).
 */
export const cssVariables = {
  '--hs-bg': colors.bg,
  '--hs-inset': colors.inset,
  '--hs-surface-1': colors.surface1,
  '--hs-surface-2': colors.surface2,
  '--hs-surface-3': colors.surface3,
  '--hs-input': colors.input,
  '--hs-accent': colors.accent,
  '--hs-accent-hover': colors.accentHover,
  '--hs-accent-soft': colors.accentSoft,
  '--hs-text-hi': colors.textHi,
  '--hs-text-med': colors.textMed,
  '--hs-text-lo': colors.textLo,
  '--hs-text-faint': colors.textFaint,
  '--hs-text-ghost': colors.textGhost,
  '--hs-blue': colors.blue,
  '--hs-gold': colors.gold,
  '--hs-red': colors.red,
  '--hs-purple': colors.purple,
  '--hs-border': colors.border,
  '--hs-border-strong': colors.borderStrong,
  '--hs-font-body': fonts.body,
  '--hs-font-display': fonts.display,
  '--hs-font-mono': fonts.mono,
};

const hindsightDark = { colors, fonts, cardSx, buttonSx, ghostButtonSx, cssVariables };

export default hindsightDark;
