import React from 'react';
import { Box, Tooltip } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import { formatMetric, ordinal } from './verdictFormat';

const W = 343;
const H = 14;

// Every peer as a faint tick (the peer distribution as quantiles, so ticks crowd where players crowd), the median
// as a taller tick, and the player as a lime dot. Better is always to the right: lower-is-better metrics flip.
const PeerStrip = ({ metric }) => {
  const q = metric.quantiles || [];
  if (!q.length) return null;
  const at = (f) => q[Math.min(q.length - 1, Math.max(0, Math.round(f * (q.length - 1))))];
  const lo = Math.min(at(0.02), metric.value);
  const hi = Math.max(at(0.98), metric.value);
  const span = hi - lo || 1;
  const x = (v) => {
    const t = (Math.min(hi, Math.max(lo, v)) - lo) / span;
    return 5 + (metric.lower_is_better ? 1 - t : t) * (W - 10);
  };
  const top = metric.rank <= Math.max(3, Math.round(metric.n * 0.1));
  const shown = formatMetric(metric.key, metric.value);
  const tip = `${metric.label}: ${shown}. ${ordinal(metric.rank)} of ${metric.n}; median ${formatMetric(metric.key, metric.median)}.`
    + `${metric.lower_is_better ? ' Lower is better;' : ''} better to the right.`;

  return (
    <Tooltip title={tip} placement="top" enterTouchDelay={0}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, fontSize: 13 }}>
          <Box component="span" sx={{ color: colors.textMed, flex: 1 }}>{metric.label}</Box>
          <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 600, fontSize: 15, color: colors.textHi, fontVariantNumeric: 'tabular-nums' }}>
            {shown}
          </Box>
          <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 10.5, minWidth: 78, textAlign: 'right', color: top ? colors.accent : colors.textLo, fontVariantNumeric: 'tabular-nums' }}>
            {ordinal(metric.rank)} of {metric.n}
          </Box>
        </Box>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" aria-hidden="true">
          <rect x="0" y="6" width={W} height="2" rx="1" fill={colors.surface2} />
          {q.map((v, i) => (
            <rect key={i} x={x(v) - 0.5} y="3" width="1" height="8" fill={colors.textGhost} opacity="0.8" />
          ))}
          <rect x={x(metric.median) - 0.75} y="0" width="1.5" height={H} fill={colors.textLo} />
          <circle cx={x(metric.value)} cy="7" r="5" fill={colors.accent} stroke={colors.bg} strokeWidth="2" />
        </svg>
      </Box>
    </Tooltip>
  );
};

export const StripAxisCue = () => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', fontFamily: fonts.mono, fontSize: 9.5, color: colors.textFaint, letterSpacing: '0.06em' }}>
    <span>← worse</span><span>│ median</span><span>better →</span>
  </Box>
);

export default PeerStrip;
