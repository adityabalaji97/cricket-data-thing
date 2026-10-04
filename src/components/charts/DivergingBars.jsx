import React from 'react';
import { Box, Typography } from '@mui/material';
import { colors as hs, fonts } from '../../theme/hindsightDark';
import { DIVERGING, MIN_BALLS } from '../../theme/chartDefaults';

/**
 * Horizontal bars either side of zero, one row per item: label | bar | value | sample.
 *
 * Built for phones: no axes to rotate, labels never collide, every row carries its own sample
 * size, and rows under `minSample` are greyed out as small samples (CARTA "accurate"). One scale
 * for every row, symmetric around zero, so bar lengths compare honestly.
 *
 * rows: [{ key, label, group?, value, sample? }]. `group` prints a heading row when it changes
 * (e.g. Powerplay / Middle / Death above "v pace" / "v spin"). `span` fixes the scale (a value of
 * `span` fills half the width), so small differences stay small; by default the largest value does.
 */
const DivergingBars = ({
  rows,
  format = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`,
  sampleLabel = (n) => `${n}b`,
  minSample = MIN_BALLS,
  labelWidth = 72,
  ariaLabel,
  span,
}) => {
  const valid = rows.filter((r) => r.value != null && !Number.isNaN(Number(r.value)));
  if (!valid.length) return null;
  const max = Math.max(span || 0, ...valid.map((r) => Math.abs(Number(r.value))), 1e-9);
  let lastGroup = null;

  return (
    <Box role="list" aria-label={ariaLabel} sx={{ display: 'grid', gap: 0.5 }}>
      {valid.map((r) => {
        const v = Number(r.value);
        const small = r.sample != null && r.sample < minSample;
        const width = (Math.abs(v) / max) * 50;
        const heading = r.group && r.group !== lastGroup ? r.group : null;
        lastGroup = r.group || lastGroup;
        return (
          <React.Fragment key={r.key}>
            {heading && (
              <Typography sx={{ fontWeight: 600, fontSize: 13, color: hs.textHi, mt: 0.75 }}>{heading}</Typography>
            )}
            <Box
              role="listitem"
              aria-label={`${r.group ? `${r.group} ` : ''}${r.label}: ${format(v)}${r.sample != null ? `, ${sampleLabel(r.sample)}` : ''}${small ? ', small sample' : ''}`}
              sx={{ display: 'grid', gridTemplateColumns: `${labelWidth}px minmax(0, 1fr) 40px`, alignItems: 'center', gap: 1, minHeight: 26 }}
            >
              <Typography sx={{ fontSize: 13, color: hs.textMed, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {r.label}
              </Typography>
              <Box sx={{ position: 'relative', height: 18 }}>
                <Box sx={{ position: 'absolute', left: '50%', top: -3, bottom: -3, width: '1px', bgcolor: 'rgba(255,255,255,0.28)' }} />
                <Box
                  sx={{
                    position: 'absolute',
                    top: 2,
                    height: 14,
                    left: v >= 0 ? '50%' : `${50 - width}%`,
                    width: `${width}%`,
                    borderRadius: v >= 0 ? '0 3px 3px 0' : '3px 0 0 3px',
                    bgcolor: small ? 'rgba(255,255,255,0.18)' : v >= 0 ? DIVERGING.positive : DIVERGING.negative,
                  }}
                />
                <Typography
                  sx={{
                    position: 'absolute',
                    top: 0,
                    fontFamily: fonts.mono,
                    fontSize: 12,
                    lineHeight: '18px',
                    color: small ? hs.textFaint : hs.textHi,
                    ...(v >= 0
                      ? { left: `calc(${50 + width}% + 4px)` }
                      : { right: `calc(${50 + width}% + 4px)` }),
                    // Keep the value inside the track when the bar is at full length.
                    ...(width > 38 ? (v >= 0 ? { left: 'auto', right: 0 } : { right: 'auto', left: 0 }) : {}),
                  }}
                >
                  {format(v)}
                </Typography>
              </Box>
              <Typography sx={{ fontFamily: fonts.mono, fontSize: 11, color: hs.textFaint, textAlign: 'right' }}>
                {r.sample != null ? sampleLabel(r.sample) : ''}
              </Typography>
            </Box>
          </React.Fragment>
        );
      })}
    </Box>
  );
};

export default DivergingBars;
