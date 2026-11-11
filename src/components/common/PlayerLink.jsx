import React from 'react';
import { Box } from '@mui/material';
import { Link } from 'react-router-dom';
import { colors } from '../../theme/hindsightDark';

// A player's name that opens his profile with the page's filters carried over (13 Nov 2026). One look everywhere: the
// name in its own colour with a dotted underline (phones have no hover, so the underline is the cue), lime on hover.
// Rules: never inside something that's already a control (a 19-0 card being picked, a row that expands); in games,
// only after the reveal; same tab, as every page keeps its state in the URL, so Back returns to it.

/** A season ("2016", or a cross-year "2016-17", July to June) as profile dates. */
export const seasonWindow = (season) => {
  const s = String(season);
  if (/^\d{4}-\d{2}$/.test(s)) {
    const y = Number(s.slice(0, 4));
    return { start: `${y}-07-01`, end: `${y + 1}-06-30` };
  }
  return { start: `${s}-01-01`, end: `${s}-12-31` };
};

/** The profile URL for a name and a window: {fmt, period ('recent'|'career'), start, end, scope ('strong'|'all')}. */
export const playerHref = (name, w = {}) => {
  const q = new URLSearchParams({ name });
  if (w.fmt && w.fmt !== 'T20') q.set('format', w.fmt);
  if (w.start) {
    q.set('start_date', w.start);
    if (w.end) q.set('end_date', w.end);
  } else if (w.period === 'career') {
    q.set('period', 'career');
  }
  if (w.scope && w.scope !== 'strong') q.set('scope', w.scope);
  return `/player?${q.toString()}`;
};

const PlayerLink = ({ name, win, children, sx }) => (
  // A new page opens at its top (the router keeps the scroll position of the page you left).
  <Box component={Link} to={playerHref(name, win)} onClick={(e) => { e.stopPropagation(); window.scrollTo(0, 0); }}
    // Vertical padding on an inline link widens the tap target to 32px without moving the line (13 Nov 2026 audit).
    sx={{ color: 'inherit', py: '7.5px', textDecorationLine: 'underline', textDecorationStyle: 'dotted', textDecorationColor: colors.textLo,
      textUnderlineOffset: '3px', '&:hover': { color: colors.accent, textDecorationColor: colors.accent },
      '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 }, ...sx }}>
    {children || name}
  </Box>
);

export default PlayerLink;
