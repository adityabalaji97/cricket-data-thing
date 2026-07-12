export const qbColors = {
  bg: '#0a0c11',
  surface1: '#101319',
  surface2: '#14171e',
  surface3: '#161a22',
  input: '#0d1015',
  accent: '#b6f24a',
  accentHover: '#c8f56f',
  accentSoft: 'rgba(182,242,74,0.13)',
  textHi: '#f3f4f6',
  textMed: '#c3c8d0',
  textLo: '#9aa1ac',
  textFaint: '#6b7280',
  textGhost: '#4b5563',
  blue: '#5b8def',
  gold: '#f0b429',
  red: '#e5484d',
  purple: '#c99cf0',
  border: 'rgba(255,255,255,0.07)',
  borderStrong: 'rgba(255,255,255,0.12)',
};

export const qbFonts = {
  body: '"Barlow", sans-serif',
  display: '"Barlow Semi Condensed", sans-serif',
  mono: '"IBM Plex Mono", monospace',
};

export const qbCardSx = {
  bgcolor: qbColors.surface1,
  color: qbColors.textHi,
  border: `1px solid ${qbColors.border}`,
  borderRadius: '20px',
  boxShadow: 'none',
};

export const qbButtonSx = {
  bgcolor: qbColors.accent,
  color: qbColors.bg,
  borderRadius: '10px',
  fontFamily: qbFonts.mono,
  fontWeight: 700,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  '&:hover': { bgcolor: qbColors.accentHover },
  '&.Mui-disabled': {
    bgcolor: 'rgba(255,255,255,0.08)',
    color: qbColors.textFaint,
  },
};

export const qbGhostButtonSx = {
  color: qbColors.textMed,
  borderColor: qbColors.borderStrong,
  borderRadius: '10px',
  fontFamily: qbFonts.mono,
  fontSize: 11,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  '&:hover': {
    borderColor: 'rgba(182,242,74,0.4)',
    color: qbColors.accent,
    bgcolor: 'rgba(182,242,74,0.06)',
  },
};

