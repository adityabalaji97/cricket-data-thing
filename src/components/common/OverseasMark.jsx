import React from 'react';
import { Box } from '@mui/material';
import FlightRounded from '@mui/icons-material/FlightRounded';
import { colors } from '../../theme/hindsightDark';

// An overseas player: a small plane after the name, as the IPL marks them in its own scorecards (12 Nov 2026).
// Screen readers hear "overseas".
const OverseasMark = ({ size = 14, sx }) => (
  <Box component="span" role="img" aria-label="overseas" title="Overseas player"
    sx={{ display: 'inline-flex', alignItems: 'center', flexShrink: 0, ml: 0.5, color: colors.textMed, ...sx }}>
    <FlightRounded sx={{ fontSize: size, transform: 'rotate(45deg)' }} />
  </Box>
);

export default OverseasMark;
