import React from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../../theme/hindsightDark';
import { fmt } from '../../../story/postVisuals';
import { FRAME, alpha, back, clamp, countUp, easeOut, fitSize, progress, u } from '../motion';
import { At } from '../ReelFrame';

/** Type at canvas sizes in the site's faces: display (Barlow Semi Condensed), body (Barlow), mono (IBM Plex Mono). */
export const type = {
  display: (px, weight = 700) => ({ fontFamily: fonts.display, fontWeight: weight, fontSize: u(px), lineHeight: 0.92, textTransform: 'uppercase' }),
  body: (px, weight = 600) => ({ fontFamily: fonts.body, fontWeight: weight, fontSize: u(px), lineHeight: 1.2 }),
  mono: (px, weight = 600) => ({ fontFamily: fonts.mono, fontWeight: weight, fontSize: u(px), lineHeight: 1.2, fontVariantNumeric: 'tabular-nums' }),
};

/** Canvas-px helpers for scenes. */
export { At };

/** An element entering over `dur` from `a`: opacity and a rise of `dy` canvas px. */
export const enter = (t, a, { dur = 0.4, dy = 50, dx = 0, overshoot = false } = {}) => {
  const p = progress(t, a, dur);
  const e = overshoot ? back(p) : easeOut(p);
  return { opacity: clamp(p * 2), transform: `translate(${u((1 - e) * dx)}px, ${u((1 - e) * dy)}px)` };
};

/** A popped badge: scale from 0.6 with overshoot, from the left edge. */
export const pop = (t, a, origin = 'left center') => {
  const p = progress(t, a, 0.45);
  return { opacity: clamp(p * 4), transform: `scale(${0.6 + 0.4 * back(p)})`, transformOrigin: origin };
};

/** A number counting up in the card's own format; `from` lets a count start part way (frame 0 is never a bare 0). */
export const Count = ({ value, format = 'dec1', t, a, dur = 0.8, from = 0, suffix = '', done = '' }) => {
  const p = progress(t, a, dur);
  const v = from + countUp(value - from, p, format === 'int' || /0$/.test(format) ? 0 : format.endsWith('2') ? 2 : 1);
  return <>{fmt(v, format)}{suffix}{p >= 1 ? done : ''}</>;
};

/** The kicker over a scene: mono caps in the lower text tier, shrunk to fit one line (validateReel flags long ones). */
export const Kicker = ({ children }) => (
  <At x={FRAME.kicker.x} y={FRAME.kicker.y} w={FRAME.kicker.w} sx={{ ...type.mono(fitSize(children, FRAME.kicker.w, 30, 'mono', 0.14)), letterSpacing: '0.14em', textTransform: 'uppercase', color: colors.textLo, whiteSpace: 'nowrap' }}>
    {children}
  </At>
);

/** The scope line at the foot of a picture. */
export const Scope = ({ children, y = 1400, sx }) => (
  <At x={64} y={y} w={876} sx={{ ...type.mono(28, 500), color: colors.textLo, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', ...sx }}>
    {children}
  </At>
);

/**
 * A deck-style player card (the SMAT round-2 Reel's card): the team's fill, ink by the palette's ink rule, a trim
 * along the bottom, and the cards' lime "best" ring around it when `apex`.
 */
export const PlayerCard = ({ tone, first, last, corner, rank, value, detail, apex, sizes = {} }) => (
  <Box sx={{ position: 'relative', borderRadius: `${u(16)}px`, boxSizing: 'border-box', p: `${u(26)}px ${u(30)}px ${u(22)}px`,
    display: 'flex', flexDirection: 'column', gap: `${u(10)}px`, bgcolor: tone.fill, color: tone.ink, borderBottom: `${u(14)}px solid ${tone.trim}`,
    boxShadow: apex ? `0 0 0 ${u(8)}px ${colors.bg}, 0 0 0 ${u(16)}px ${colors.accent}` : 'none' }}>
    {(rank != null || corner) && (
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <Box sx={type.display(64)}>{rank}</Box>
        <Box sx={{ ...type.mono(32), opacity: 0.85 }}>{corner}</Box>
      </Box>
    )}
    <Box>
      {first && <Box sx={{ ...type.display(sizes.first || 46, 600), opacity: 0.8 }}>{first}</Box>}
      <Box sx={{ ...type.display(sizes.last || 200), whiteSpace: 'nowrap' }}>{last}</Box>
    </Box>
    {value != null && <Box sx={{ ...type.mono(sizes.value || 170), lineHeight: 1 }}>{value}</Box>}
    {detail && <Box sx={{ ...type.mono(sizes.detail || 50, 500), opacity: 0.88 }}>{detail}</Box>}
  </Box>
);

/** Split a name into first part and surname for the card's two lines. */
export const splitName = (name) => {
  const parts = String(name || '').split(/\s+/).filter(Boolean);
  if (parts.length < 2) return { first: '', last: name || '' };
  return { first: parts.slice(0, -1).join(' '), last: parts[parts.length - 1] };
};

/** The Reel-only kinds' lime ring (inset), breathing with `pulse` (0..1, motion.ringPulse) while its item is read. */
export const ringBox = (k, colour = colors.accent, pulse = 0) => (k > 0 ? { boxShadow: `inset 0 0 0 ${u(6 + Math.round(6 * pulse))}px ${alpha(colour, k)}` } : {});
