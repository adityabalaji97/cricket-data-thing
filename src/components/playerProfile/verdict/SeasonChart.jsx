import React from 'react';
import { Box, Tooltip } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import { ROLE_COLOURS, ROLE_NAMES, signed } from './verdictFormat';

const W = 343;
const LEFT = 40;
const RIGHT = 44;
const BAR = 8;
const GAP = 2;
const ROW_GAP = 9;

// Wins added by season: one thin bar per role from a zero line, the value at the bar's end. The all-rounder
// picture is the two roles side by side, season by season.
export const SeasonWinsChart = ({ roles, order }) => {
  const series = order.filter((r) => roles[r]).map((r) => ({ role: r, rows: roles[r].seasons || [] }));
  const years = [...new Set(series.flatMap((s) => s.rows.map((r) => r.year)))].sort();
  const max = Math.max(0.5, ...series.flatMap((s) => s.rows.map((r) => Math.abs(r.wpa || 0))));
  const dom = Math.ceil(max * 2) / 2;
  const rowH = series.length * BAR + (series.length - 1) * GAP;
  const H = years.length * (rowH + ROW_GAP) + 16;
  const x = (v) => LEFT + ((v + dom) / (2 * dom)) * (W - LEFT - RIGHT);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Wins added by season" style={{ display: 'block', overflow: 'visible' }}>
      {[-dom, 0, dom].map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1="0" y2={H - 14} stroke={t === 0 ? colors.textGhost : colors.borderStrong} strokeDasharray={t === 0 ? '' : '2 3'} />
          <text x={x(t)} y={H - 2} textAnchor="middle" fill={colors.textFaint} fontSize="9.5" fontFamily={fonts.mono}>
            {t === 0 ? '0' : signed(t, 1)}
          </text>
        </g>
      ))}
      {years.map((yr, i) => {
        const y0 = i * (rowH + ROW_GAP) + 2;
        return (
          <g key={yr}>
            <text x="0" y={y0 + rowH / 2 + 4} fill={colors.textMed} fontSize="12" fontFamily={fonts.display} fontWeight="600">{yr}</text>
            {series.map((s, j) => {
              const r = s.rows.find((row) => row.year === yr);
              if (!r || r.wpa === null || r.wpa === undefined) return null;
              const v = r.wpa;
              const y = y0 + j * (BAR + GAP);
              const x0 = Math.min(x(0), x(v));
              const w = Math.max(2, Math.abs(x(v) - x(0)));
              return (
                <Tooltip key={s.role} enterTouchDelay={0} placement="top"
                  title={`${yr} · ${ROLE_NAMES[s.role]}: ${signed(v)} wins added (${r.innings_count} innings, ${r.balls} balls)`}>
                  <g>
                    <rect x={x0} y={y} width={w} height={BAR} rx={Math.min(3, w / 2)} fill={ROLE_COLOURS[s.role]} />
                    <text x={v >= 0 ? x0 + w + 4 : x0 - 4} y={y + BAR - 0.5} textAnchor={v >= 0 ? 'start' : 'end'}
                      fill={colors.textMed} fontSize="10" fontFamily={fonts.body} style={{ fontVariantNumeric: 'tabular-nums' }}>
                      {signed(v)}
                    </text>
                    <rect x={LEFT} y={y - 3} width={W - LEFT - RIGHT} height={BAR + 6} fill="transparent" />
                  </g>
                </Tooltip>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
};

// ODIs have no wins added yet: the season slot shows the main role's rate by year against the peer median.
export const SeasonRateChart = ({ rows, metricKey, label, median }) => {
  const pts = (rows || []).filter((r) => r[metricKey] !== null && r[metricKey] !== undefined);
  if (!pts.length) return null;
  const vals = pts.map((r) => r[metricKey]);
  const lo = Math.floor(Math.min(median, ...vals) - 0.5);
  const hi = Math.ceil(Math.max(median, ...vals) + 0.3);
  const rowH = 17;
  const H = pts.length * rowH + 16;
  const x = (v) => LEFT + ((v - lo) / (hi - lo || 1)) * (W - LEFT - 70);
  const dp = metricKey === 'economy' ? 2 : 1;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${label} by year`} style={{ display: 'block', overflow: 'visible' }}>
      <line x1={x(median)} x2={x(median)} y1="0" y2={pts.length * rowH} stroke={colors.textLo} strokeDasharray="3 3" />
      <text x={x(median)} y={pts.length * rowH + 11} textAnchor="middle" fill={colors.textLo} fontSize="9.5" fontFamily={fonts.mono}>
        peer median {median.toFixed(dp)}
      </text>
      {pts.map((r, i) => {
        const y = i * rowH + 9;
        return (
          <g key={r.year}>
            <text x="0" y={y + 4} fill={colors.textMed} fontSize="12" fontFamily={fonts.display} fontWeight="600">{r.year}</text>
            <line x1={x(median)} x2={x(r[metricKey])} y1={y} y2={y} stroke={ROLE_COLOURS.bowl} strokeWidth="2" opacity="0.5" />
            <circle cx={x(r[metricKey])} cy={y} r="5" fill={ROLE_COLOURS.bowl} stroke={colors.bg} strokeWidth="2" />
            <text x={x(r[metricKey]) + 9} y={y + 4} fill={colors.textMed} fontSize="10.5" fontFamily={fonts.body}>
              {r[metricKey].toFixed(dp)}{r.balls < 120 ? `  (${r.balls} balls)` : ''}
            </text>
          </g>
        );
      })}
    </svg>
  );
};
