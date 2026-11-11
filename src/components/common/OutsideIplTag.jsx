import React from 'react';
import { Box } from '@mui/material';

// A player whose numbers come from T20s outside the IPL (no IPL balls in the window: SMAT, SA20, T20Is...), shown as
// they are, unadjusted: league factors didn't predict IPL numbers any better than the IPL average (X4D_LEAGUE_FACTORS.md).
const OutsideIplTag = () => (
  <Box component="span" title="Numbers from T20s outside the IPL, unadjusted"
    sx={{ ml: 0.6, flexShrink: 0, px: '5px', borderRadius: '4px', border: '1px solid rgba(240,180,41,0.5)', color: '#f0b429',
      fontSize: 10.5, lineHeight: '16px', whiteSpace: 'nowrap' }}>non-IPL</Box>
);

export default OutsideIplTag;
