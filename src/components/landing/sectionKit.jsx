import React from 'react';
import { Box, Typography } from '@mui/material';
import { colors as dark, fonts } from '../../theme/hindsightDark';

// The landing page's section pieces (kicker, header, chip and mono styles), shared with /connect so that page doesn't
// import the whole landing page (landing plan L6). Tokens as LandingPage names them.
const C = {
  bg: dark.bg,
  surface: dark.surface1,
  muted: dark.input,
  inset: dark.inset,
  hairline: dark.border,
  hairlineStrong: dark.borderStrong,
  hi: dark.textHi,
  mid: dark.textMed,
  soft: dark.textLo,
  low: dark.textFaint,
  lime: dark.accent,
  limeHover: dark.accentHover,
};
export { C as kitColors };

export const sectionTitleSx = {
  color: C.hi,
  fontFamily: fonts.display,
  fontWeight: 700,
  fontSize: { xs: 20, md: 25 },
  lineHeight: 1.05,
};

export const Kicker = ({ children, color = C.lime }) => (
  <Typography
    sx={{
      color,
      fontFamily: fonts.mono,
      fontSize: 12,
      letterSpacing: '0.16em',
      textTransform: 'uppercase',
      fontWeight: 600,
      mb: 0.75,
    }}
  >
    {children}
  </Typography>
);

export const SectionHeader = ({ kicker, kickerColor, title, subtitle, action }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 2, mb: 1.75 }}>
    <Box sx={{ minWidth: 0 }}>
      <Kicker color={kickerColor}>{kicker}</Kicker>
      <Typography sx={sectionTitleSx}>{title}</Typography>
      {subtitle && (
        <Typography sx={{ color: C.soft, mt: 0.6, fontFamily: fonts.body, fontSize: { xs: 13, md: 14 } }}>
          {subtitle}
        </Typography>
      )}
    </Box>
    {action}
  </Box>
);

export const chipSx = {
  color: C.mid,
  bgcolor: C.muted,
  px: 0.8,
  py: 0.45,
  borderRadius: 1,
  fontFamily: fonts.mono,
  fontSize: 12,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  maxWidth: '62%',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

export const monoSx = {
  fontFamily: fonts.mono,
  fontSize: 12,
  letterSpacing: '0.04em',
  whiteSpace: 'nowrap',
};
