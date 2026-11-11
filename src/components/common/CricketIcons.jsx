import React from 'react';
import { SvgIcon } from '@mui/material';

// Cricket marks in the app's icon style (Material Rounded, 24-unit grid, currentColor), for where Material has no
// glyph: a bat, a ball, a wicketkeeper's glove. Used inline like the overseas plane (OverseasMark). 13 Nov 2026.
// Each takes the usual SvgIcon props (sx, fontSize) and names itself for screen readers.

export const BatIcon = (props) => (
  <SvgIcon titleAccess="Batting" {...props}>
    <g transform="rotate(45 12 12)">
      <rect x="10.9" y="1.5" width="2.2" height="6.5" rx="1.1" />
      <rect x="8.6" y="8" width="6.8" height="14.5" rx="2.4" />
    </g>
  </SvgIcon>
);

export const BallIcon = (props) => (
  <SvgIcon titleAccess="Bowling" {...props}>
    <path fillRule="evenodd"
      d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 3.6q2.6 8.4 0 16.8l1.2.4q2.6-8.6 0-17.6zm3.6-.4q2.6 9 0 17.6l1.2-.4q2.6-8.4 0-16.8z" />
  </SvgIcon>
);

export const GloveIcon = (props) => (
  <SvgIcon titleAccess="Wicketkeeper" {...props}>
    <path d="M7.5 21.5v-6.2L4.6 12a1.4 1.4 0 0 1 2.05-1.9L8 11.4V5.2a1.3 1.3 0 0 1 2.6 0v4.6h.6V3.8a1.3 1.3 0 0 1 2.6 0v6h.6V4.8a1.3 1.3 0 0 1 2.6 0v5.6h.6V6.9a1.3 1.3 0 0 1 2.6 0v8.1c0 3.6-2.9 6.5-6.5 6.5H7.5z" />
  </SvgIcon>
);
