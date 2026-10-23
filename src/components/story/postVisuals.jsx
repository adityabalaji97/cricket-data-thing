import React from 'react';
import { Box, Typography } from '@mui/material';
import { SERIES } from '../../theme/chartDefaults';
import { colors, fonts } from '../../theme/hindsightDark';
import { getTeamColor, readableOnDark } from '../../utils/teamColors';
import { InningsClue } from '../games/GuessInningsGame';

/**
 * Visuals for Instagram post cards (services/ig_posts): one question answered from several angles. Same contract as
 * the match-preview visuals in visuals.jsx: ({ payload, teams }) => element, drawn for a phone-sized 4:5 card (the
 * /ig/:id/:n slide renders it at 432x540 and screenshots at 2.5x, so 12px text lands at 30px). visuals.jsx looks
 * here for any visual it doesn't have; this module imports nothing from it (no import cycle).
 *
 * Every number drawn here arrives in the payload already computed by the backend; the components only format.
 */

const mono = { fontFamily: fonts.mono, fontSize: 12 };

/** Number formats named by the backend (services/ig_posts/angles.py FORMATS). */
export const fmt = (value, kind = 'dec1') => {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  const v = Number(value);
  // No sign on a value that rounds to zero ("0.0", not "−0.0").
  const sign = (s) => (Number(s) === 0 ? '' : v > 0 ? '+' : v < 0 ? '−' : '') + s;
  switch (kind) {
    case 'int': return Math.round(v).toLocaleString('en-US');
    case 'pct1': return `${v.toFixed(1)}%`;
    case 'pct0': return `${Math.round(v)}%`;
    case 'dec2': return v.toFixed(2);
    case 'signed0': return sign(Math.abs(v).toFixed(0));
    case 'signed1': return sign(Math.abs(v).toFixed(1));
    case 'signed2': return sign(Math.abs(v).toFixed(2));
    default: return v.toFixed(1);
  }
};

export const surname = (name) => {
  const parts = String(name || '').split(/\s+/).filter(Boolean);
  if (parts.length < 2) return name;
  // Keep particles with the surname: "de Villiers", "ul Haq".
  const i = parts.findIndex((p, k) => k > 0 && /^(de|du|van|von|der|ul|al|da|di)$/i.test(p));
  return i > 0 ? parts.slice(i).join(' ') : parts[parts.length - 1];
};

const teamColour = (team, fallback) => {
  const c = team ? getTeamColor(team) : null;
  const r = c && /^#[0-9a-f]{6}$/i.test(c) ? readableOnDark(c) : null;
  return r && /^#[0-9a-f]{6}$/i.test(r) ? r : fallback;
};

const Legend = ({ items }) => (
  <Box data-legend sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mt: 1 }}>
    {items.map(([label, color]) => (
      <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
        <Box sx={color === 'ring' ? { width: 10, height: 10, borderRadius: '3px', border: `2px solid ${colors.textHi}`, boxSizing: 'border-box' }
          : { width: 10, height: 10, borderRadius: '3px', bgcolor: color }} />
        <Typography sx={{ fontSize: 12, color: colors.textMed }}>{label}</Typography>
      </Box>
    ))}
  </Box>
);

/**
 * The split verdict: top entities x metrics, each cell shaded by its percentile in the whole field (brighter = better),
 * the leader of each metric ringed, then the verdict line ("Gill leads overall; Head is fastest...").
 * payload: {metrics:[{key,label,format}], rows:[{name, values:{k:v}, pct:{k:0..100}, leader:[k...], highlight}], verdict}
 */
const Scorecard = ({ payload }) => {
  const { metrics, rows } = payload;
  const cols = `${payload.label_width || 92}px repeat(${metrics.length}, 1fr)`; // label_width: long row labels
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.5 }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: cols, gap: '4px', alignItems: 'end' }}>
        <span />
        {metrics.map((m) => (
          <Typography key={m.key} sx={{ fontSize: 11, color: colors.textLo, textAlign: 'center', lineHeight: 1.15 }}>{m.label}</Typography>
        ))}
      </Box>
      {rows.map((r) => (
        <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: cols, gap: '4px', alignItems: 'center' }}>
          <Typography noWrap sx={{ fontSize: 13, color: r.highlight ? colors.accent : colors.textHi, fontWeight: r.highlight ? 600 : 400 }}>
            {r.short || surname(r.name)}
          </Typography>
          {metrics.map((m) => {
            const pct = r.pct?.[m.key];
            const lead = (r.leader || []).includes(m.key);
            return (
              <Box key={m.key} sx={{
                height: 30, borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                bgcolor: pct == null ? colors.surface2 : `rgba(182,242,74,${(0.08 + 0.62 * (pct / 100)).toFixed(2)})`,
                border: lead ? `2px solid ${colors.textHi}` : '2px solid transparent',
              }}>
                <Typography sx={{ ...mono, fontSize: 12, color: pct != null && pct > 70 ? colors.bg : colors.textHi, fontWeight: lead ? 700 : 500 }}>
                  {fmt(r.values?.[m.key], m.format)}
                </Typography>
              </Box>
            );
          })}
        </Box>
      ))}
      {payload.verdict && (
        <Typography sx={{ fontSize: 14, color: colors.textHi, mt: 1, lineHeight: 1.35 }}>{payload.verdict}</Typography>
      )}
      <Legend items={[['Brighter: better in the field', colors.accent], ['Ring: leads the column', 'ring']]} />
    </Box>
  );
};

/** A robust axis range: the points' range after dropping values beyond 1.5 IQRs of the middle half (outliers sit on the edge). */
const robustRange = (vals) => {
  const v = [...vals].sort((a, b) => a - b);
  const q = (p) => v[Math.min(v.length - 1, Math.max(0, Math.round(p * (v.length - 1))))];
  const iqr = q(0.75) - q(0.25);
  const lo = Math.max(v[0], q(0.25) - 1.5 * iqr); const hi = Math.min(v[v.length - 1], q(0.75) + 1.5 * iqr);
  const d = (hi - lo) * 0.08 || 1;
  return [lo - d, hi + d];
};

/**
 * Numbered markers that don't sit on each other or on the `avoid` points (the named dots and their labels): each, best
 * first, takes the nearest free spot around its dot (a short line leads back to the dot when it had to move).
 */
const spreadMarkers = (pts, sx, sy, [xmin, xmax, ymin, ymax], avoid = []) => {
  const placed = [];
  const clear = (x, y) => placed.every(([px, py]) => Math.hypot(px - x, py - y) >= 19)
    && avoid.every(([ax, ay]) => Math.hypot(ax - x, ay - y) >= 13);
  const offsets = [[0, 0]];
  for (let r = 16; r <= 48; r += 16) {
    for (let k = 0; k < 8; k++) offsets.push([Math.round(r * Math.cos((k * Math.PI) / 4)), Math.round(r * Math.sin((k * Math.PI) / 4))]);
  }
  return pts.map((p) => {
    const dx = sx(p.x); const dy = sy(p.y);
    const spot = offsets.map(([ox, oy]) => [dx + ox, dy + oy])
      .find(([x, y]) => x >= xmin && x <= xmax && y >= ymin && y <= ymax && clear(x, y))
      || [dx, dy];
    placed.push(spot);
    return { name: p.name, dx, dy, mx: spot[0], my: spot[1], moved: spot[0] !== dx || spot[1] !== dy };
  });
};

/**
 * Two metrics across the field. The subject in lime; the field dims or brightens with an optional third metric; the
 * region that beats the subject on both is shaded. The labelled leaders are numbered on the chart and named in a key
 * below, so names never pile up in the busy corner.
 * payload: {x:{label,format,higher_better}, y:{...}, z?:{label}, points:[{name, short, x, y, zp?, highlight?, label?}], box}
 * Several highlighted points are all named in lime; the box is drawn only for a single subject.
 */
const ScatterPlus = ({ payload }) => {
  const { points, x: X, y: Y, z: Z } = payload;
  const W = 300; const H = 214; const L = 8; const R = 8; const T = 18; const B = 184;
  // Robust to the field's outliers, but always wide enough for the named and numbered players (never pinned to an edge).
  const subjects = points.filter((p) => p.highlight);
  const named = points.filter((p) => p.highlight || p.label);
  const reach = ([a, b], vals, all) => {
    const d = (b - a) * 0.06;
    const lo = Math.min(a, ...vals.map((v) => v - d));
    // A measure that can't go below zero (a percentage of balls) starts at 0, never at "-1%".
    return [Math.min(...all) >= 0 ? Math.max(0, lo) : lo, Math.max(b, ...vals.map((v) => v + d))];
  };
  const [x0, x1] = reach(robustRange(points.map((p) => p.x)), named.map((p) => p.x), points.map((p) => p.x));
  const [y0, y1] = reach(robustRange(points.map((p) => p.y)), named.map((p) => p.y), points.map((p) => p.y));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  // A lower-is-better axis runs backwards, so better is always up and to the right.
  const fx = X.higher_better === false; const fy = Y.higher_better === false;
  const tx = (v) => (fx ? (x1 - v) / (x1 - x0) : (v - x0) / (x1 - x0));
  const ty = (v) => (fy ? (y1 - v) / (y1 - y0) : (v - y0) / (y1 - y0));
  const sx = (v) => clamp(L + tx(v) * (W - L - R), L + 3, W - R - 3);
  const sy = (v) => clamp(B - ty(v) * (B - T), T + 3, B - 3);
  const subject = subjects.length === 1 ? subjects[0] : null; // the 'beats him on both' box needs one subject
  const better = (p, axis, ref) => (payload[axis].higher_better === false ? p[axis] < ref[axis] : p[axis] > ref[axis]);
  const boxX = subject ? [sx(subject.x), W - R] : null;
  const boxY = subject ? [T, sy(subject.y)] : null;
  const keyed = points.filter((p) => p.label && !p.highlight).sort((a, b) => a.label - b.label); // label: rank, best first
  // A named dot's label: beside it, to the left near the right edge, below it at the top of the plot (clear of the axis title).
  const tag = (p) => {
    const left = sx(p.x) > (W - R) * 0.65;
    return { x: left ? sx(p.x) - 11 : sx(p.x) + 11, y: sy(p.y) < T + 20 ? sy(p.y) + 4.5 : sy(p.y) - 8, left, text: p.short || surname(p.name) };
  };
  const avoid = subjects.flatMap((p) => {
    const t = tag(p); const w = t.text.length * 7;
    const xs = []; for (let d = 0; d <= w; d += 8) xs.push([t.left ? t.x - d : t.x + d, t.y - 4]);
    return [[sx(p.x), sy(p.y)], ...xs];
  });
  const markers = spreadMarkers(keyed, sx, sy, [L + 8, W - R - 8, T + 8, B - 8], avoid);
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${Y.label} against ${X.label}`} sx={{ width: '100%' }}>
        <text x={L} y={10} style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{`↑ ${Y.label}${Y.higher_better === false ? ' (lower is better)' : ''}`}</text>
        {subject && payload.box && (
          <rect x={boxX[0]} y={boxY[0]} width={boxX[1] - boxX[0]} height={boxY[1] - boxY[0]} fill={colors.accent} fillOpacity="0.07" />
        )}
        <rect x={L} y={T} width={W - L - R} height={B - T} fill="none" stroke={colors.border} />
        {/* Zero lines for signed measures (runs above average and the like), so the quadrants mean something. */}
        {x0 < 0 && x1 > 0 && <line x1={sx(0)} y1={T} x2={sx(0)} y2={B} stroke={colors.borderStrong} strokeDasharray="3 3" />}
        {y0 < 0 && y1 > 0 && <line x1={L} y1={sy(0)} x2={W - R} y2={sy(0)} stroke={colors.borderStrong} strokeDasharray="3 3" />}
        {points.filter((p) => !p.highlight && !p.label).map((p) => {
          const op = Z && p.zp != null ? 0.18 + 0.8 * (p.zp / 100) : 0.55;
          const inBox = subject && better(p, 'x', subject) && better(p, 'y', subject);
          return <circle key={p.name} cx={sx(p.x)} cy={sy(p.y)} r="3.5" fill={Z ? colors.accent : '#7c8aa5'} fillOpacity={op}
            stroke={inBox ? colors.textHi : 'none'} strokeWidth="1" />;
        })}
        {/* Leader lines first, so none runs over another player's marker. */}
        {markers.filter((m) => m.moved).map((m) => (
          <g key={`${m.name}-leader`}>
            <line x1={m.dx} y1={m.dy} x2={m.mx} y2={m.my} stroke={colors.textMed} strokeWidth="0.8" />
            <circle cx={m.dx} cy={m.dy} r="2.5" fill={colors.textHi} />
          </g>
        ))}
        {markers.map((m, i) => (
          <g key={m.name}>
            <circle cx={m.mx} cy={m.my} r="7.5" fill={colors.textHi} stroke={colors.bg} strokeWidth="1.5" />
            <text x={m.mx} y={m.my + 3.5} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 10, fontWeight: 700, fill: colors.bg }}>{i + 1}</text>
          </g>
        ))}
        {subjects.map((s) => (
          <g key={s.name}>
            <circle cx={sx(s.x)} cy={sy(s.y)} r="7" fill={colors.accent} stroke={colors.bg} strokeWidth="2" />
            <text x={tag(s).x} y={tag(s).y} textAnchor={tag(s).left ? 'end' : 'start'}
              style={{ fontFamily: fonts.body, fontSize: 13, fontWeight: 600, fill: colors.accent }}>
              {tag(s).text}
            </text>
          </g>
        ))}
        <text x={L} y={H - 16} style={{ ...mono, fill: colors.textFaint }}>{fmt(fx ? x1 : x0, X.format)}</text>
        <text x={W - R} y={H - 16} textAnchor="end" style={{ ...mono, fill: colors.textFaint }}>{fmt(fx ? x0 : x1, X.format)}</text>
        <text x={(L + W - R) / 2} y={H - 2} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: colors.textLo }}>
          {`${X.label}${fx ? ' (lower is better)' : ''} →`}
        </text>
      </Box>
      {keyed.length > 0 && (
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 1.5, rowGap: 0.25, mt: 0.75 }}>
          {keyed.map((p, i) => (
            <Typography key={p.name} noWrap sx={{ fontSize: 12, color: colors.textHi }}>
              <Box component="span" sx={{ fontWeight: 700, color: colors.textMed, mr: 0.5 }}>{i + 1}</Box>{p.short || surname(p.name)}
            </Typography>
          ))}
        </Box>
      )}
      {Z && (
        <Legend items={[[`Brighter: higher ${Z.label}`, colors.accent]]} />
      )}
    </Box>
  );
};

/**
 * One metric, ranked; the subject in lime, others in their team colour (or slate). Signed metrics draw from zero.
 * payload: {metric:{label, format, signed}, rows:[{name, value, team?, highlight?, detail?}], label_width?}
 * (label_width: px for the name column when the detail lines are long; 110 by default)
 */
const MetricBars = ({ payload }) => {
  const { rows, metric } = payload;
  const signed = metric.signed || rows.some((r) => r.value < 0);
  const max = Math.max(...rows.map((r) => Math.abs(r.value)), 1e-9);
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.7 }}>
      {rows.map((r) => {
        const width = (100 * Math.abs(r.value)) / max / (signed ? 2 : 1);
        const color = r.highlight ? colors.accent : teamColour(r.team, '#5b6b85');
        return (
          <Box key={`${r.name}-${r.detail || ''}`} sx={{ display: 'grid', gridTemplateColumns: `${payload.label_width || 110}px 1fr 58px`, gap: 1, alignItems: 'center' }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography noWrap sx={{ fontSize: 13, color: r.highlight ? colors.accent : colors.textHi, fontWeight: r.highlight ? 600 : 400 }}>{r.name}</Typography>
              {r.detail && <Typography noWrap sx={{ fontSize: 11, color: colors.textLo, lineHeight: 1.25 }}>{r.detail}</Typography>}
            </Box>
            <Box sx={{ position: 'relative', height: 14 }}>
              {signed && <Box sx={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: '1px', bgcolor: colors.borderStrong }} />}
              <Box sx={{
                position: 'absolute', top: 2, height: 10, borderRadius: '4px', bgcolor: color,
                left: signed ? (r.value >= 0 ? '50%' : `${50 - width}%`) : 0, width: `${Math.max(2, width)}%`,
              }} />
            </Box>
            <Typography sx={{ ...mono, fontSize: 13, color: colors.textMed, textAlign: 'right' }}>{fmt(r.value, metric.format)}</Typography>
          </Box>
        );
      })}
      {payload.legend && <Legend items={payload.legend.map((t) => [t, teamColour(t, '#5b6b85')])} />}
    </Box>
  );
};

/**
 * Shares that add up to 100% per row (how often each opener goes big, is middling, costs the team): one stacked bar a
 * row, the first group in the accent colour, the last in red, each segment's share written on it when it fits.
 * payload: {groups:[{key, label}], rows:[{name, detail?, segments:[{key, value}]}], format}
 */
export const SHARE_COLOURS = [colors.accent, '#5b6b85', '#e66767'];
const ShareBars = ({ payload }) => {
  const { groups, rows } = payload;
  const colour = (k) => SHARE_COLOURS[Math.max(0, groups.findIndex((g) => g.key === k))] || '#5b6b85';
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.1 }}>
      {rows.map((r) => (
        <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: '96px 1fr', gap: 1, alignItems: 'center' }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography noWrap sx={{ fontSize: 13, color: colors.textHi, fontWeight: 600 }}>{r.name}</Typography>
            {r.detail && <Typography noWrap sx={{ fontSize: 11, color: colors.textLo, lineHeight: 1.25 }}>{r.detail}</Typography>}
          </Box>
          <Box sx={{ display: 'flex', height: 26, gap: '2px' }}>
            {r.segments.map((seg) => (
              <Box key={seg.key} sx={{ width: `${seg.value}%`, bgcolor: colour(seg.key), borderRadius: '4px', display: 'flex',
                alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                {seg.value >= 9 && (
                  <Typography sx={{ ...mono, fontSize: 12, fontWeight: 700, color: colors.bg }}>{fmt(seg.value, payload.format || 'pct0')}</Typography>
                )}
              </Box>
            ))}
          </Box>
        </Box>
      ))}
      <Legend items={groups.map((g) => [g.label, colour(g.key)])} />
    </Box>
  );
};

/**
 * Cumulative runs or wickets against balls (or innings) for the fastest few to a milestone, the milestone dashed.
 * payload: {unit:'balls'|'innings', target, measure, series:[{name, points:[[x, y]], reached_at, highlight}]}
 */
// Surnames shared by many players read as full names ("Zaheer Khan", not "Khan").
const SHARED_SURNAMES = /^(Khan|Singh|Kumar|Sharma|Yadav|Patel|Ahmed|Ali|Hasan|Rahman|Malik|Iqbal|Hussain|Shah)$/;
const raceName = (name) => {
  const s = surname(name);
  return SHARED_SURNAMES.test(s) ? name : s;
};

const RaceLines = ({ payload }) => {
  // The finish line, not the race: a dot where each reached the target (the fastest first), a dashed line at the
  // fastest, and a bar for how much longer the others took. The running totals overlapped into one tangle; the
  // answer is the finishing order and the gaps, so that's what's drawn. Dots on a range axis (not bars from zero):
  // the gaps are a fifth of the totals, which bars from zero would hide.
  const rows = [...payload.series].sort((a, b) => a.reached_at - b.reached_at);
  const anyMarked = rows.some((r) => r.highlight);
  const best = rows[0].reached_at;
  const worst = rows[rows.length - 1].reached_at;
  const pad = Math.max((worst - best) * 0.12, 1);
  const lo = best - pad; const hi = worst + pad;
  const W = 300; const rowH = 42; const T = 22; const L = 104; const R = 56;
  const H = T + rows.length * rowH + 8;
  const sx = (v) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  const n = (v) => Math.round(v).toLocaleString('en-US');
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label={`${payload.unit} to ${payload.target} ${payload.measure}: ${rows.map((r) => `${r.name} ${r.reached_at}`).join(', ')}`}
        sx={{ width: '100%' }}>
        <line x1={sx(best)} x2={sx(best)} y1={T - 8} y2={H - 6} stroke={colors.textFaint} strokeDasharray="3 4" />
        <text x={sx(best)} y={T - 11} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>fastest</text>
        {rows.map((r, i) => {
          const y = T + i * rowH + rowH / 2;
          const mine = anyMarked ? r.highlight : r.reached_at === best;  // no subject marked: the record holder(s)
          const ink = mine ? colors.accent : colors.textHi;
          return (
            <g key={r.name}>
              <text x={0} y={y + 5} style={{ fontFamily: fonts.body, fontSize: 14, fontWeight: mine ? 700 : 400, fill: mine ? colors.accent : colors.textHi }}>
                {raceName(r.name)}
              </text>
              <line x1={L} x2={W - R} y1={y} y2={y} stroke={colors.border} strokeWidth="1" />
              {r.reached_at > best && (
                <rect x={sx(best)} y={y - 3} width={Math.max(1, sx(r.reached_at) - sx(best))} height="6" rx="3"
                  fill={mine ? 'rgba(182,242,74,.35)' : 'rgba(255,255,255,.14)'} />
              )}
              <circle cx={sx(r.reached_at)} cy={y} r={mine ? 6 : 5} fill={mine ? colors.accent : '#8a96ad'}
                stroke={colors.bg} strokeWidth="2" />
              <text x={W} y={y + 5} textAnchor="end" style={{ ...mono, fontSize: 13, fill: ink }}>
                {i === 0 ? n(r.reached_at) : r.reached_at === best ? 'level' : `+${n(r.reached_at - best)}`}
              </text>
            </g>
          );
        })}
      </Box>
      <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 0.5 }}>
        {`${payload.unit === 'innings' ? 'Innings' : 'Balls'} to ${payload.target.toLocaleString('en-US')} ${payload.measure}`}
      </Typography>
    </Box>
  );
};

/**
 * Effects with 95% confidence intervals against no effect (a hypothesis-lab result).
 * payload: {effects:[{label, estimate, lo, hi, call}], unit, better:'left'|'right'|null}
 */
const Forest = ({ payload }) => {
  const W = 300; const rowH = 46; const H = payload.effects.length * rowH + 30; const L = 10; const R = 10;
  const span = Math.max(...payload.effects.flatMap((e) => [Math.abs(e.lo), Math.abs(e.hi), Math.abs(e.estimate)]), 1e-9) * 1.1;
  const sx = (v) => L + ((v + span) / (2 * span)) * (W - L - R);
  const callColour = (c) => ({ 'Supported': colors.accent, 'Not supported': colors.red, 'Inconclusive': colors.textLo })[c] || colors.textMed;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Effects with 95% confidence intervals" sx={{ width: '100%' }}>
        <line x1={sx(0)} x2={sx(0)} y1="0" y2={H - 24} stroke={colors.textFaint} strokeDasharray="3 3" />
        {payload.effects.map((e, i) => {
          const y = i * rowH + 30;
          // A test is coloured by whether its interval leaves out "no effect" (clear), else by its verdict word.
          const c = e.clear === true ? colors.accent : e.clear === false ? colors.textLo : callColour(e.call);
          return (
            <g key={e.label}>
              <text x={L} y={y - 12} style={{ fontFamily: fonts.body, fontSize: 12, fill: colors.textHi }}>{e.label}</text>
              <line x1={sx(e.lo)} x2={sx(e.hi)} y1={y} y2={y} stroke={c} strokeWidth="2.5" strokeLinecap="round" />
              <circle cx={sx(e.estimate)} cy={y} r="5" fill={c} />

            </g>
          );
        })}
        <text x={sx(0)} y={H - 6} textAnchor="middle" style={{ ...mono, fill: colors.textLo }}>no effect</text>
        <text x={L} y={H - 6} style={{ ...mono, fill: colors.textFaint }}>{fmt(-span, 'signed1')}</text>
        <text x={W - R} y={H - 6} textAnchor="end" style={{ ...mono, fill: colors.textFaint }}>{fmt(span, 'signed1')}</text>
      </Box>
      <Legend items={[['Clear effect', colors.accent], ["Data can't tell", colors.textFaint]]} />
    </Box>
  );
};

/**
 * One metric across ordered buckets, with 95% intervals where known.
 * payload: {metric:{label, format}, buckets:[{label, value, lo?, hi?, n}], baseline?}
 */
const BucketBars = ({ payload }) => {
  const W = 300; const H = 210; const L = 10; const R = 10; const T = 18; const B = 168;
  const vals = payload.buckets.flatMap((b) => [b.value, b.lo ?? b.value, b.hi ?? b.value, 0]);
  const lo = Math.min(...vals); const hi = Math.max(...vals);
  const sy = (v) => B - ((v - lo) / (hi - lo || 1)) * (B - T);
  const bw = (W - L - R) / payload.buckets.length;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={payload.metric.label} sx={{ width: '100%' }}>
        <line x1={L} x2={W - R} y1={sy(0)} y2={sy(0)} stroke={colors.borderStrong} />
        {payload.buckets.map((b, i) => {
          const x = L + i * bw + bw * 0.2; const w = bw * 0.6;
          const top = Math.min(sy(b.value), sy(0)); const h = Math.abs(sy(b.value) - sy(0));
          return (
            <g key={b.label}>
              <rect x={x} y={top} width={w} height={Math.max(1, h)} rx="3" fill={b.value >= 0 ? SERIES[0] : '#e66767'} />
              {b.lo != null && (
                <line x1={x + w / 2} x2={x + w / 2} y1={sy(b.lo)} y2={sy(b.hi)} stroke={colors.textHi} strokeWidth="1.5" />
              )}
              {/* Positive values sit above their bar; negative ones just above the zero line, clear of the bucket labels. */}
              <text x={x + w / 2} y={b.value >= 0 ? top - 6 : sy(0) - 6} textAnchor="middle" style={{ ...mono, fill: colors.textHi }}>
                {fmt(b.value, payload.metric.format)}
              </text>
              <text x={x + w / 2} y={B + 16} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 12, fill: colors.textMed }}>{b.label}</text>
              {b.n != null && <text x={x + w / 2} y={B + 32} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{`n=${b.n}`}</text>}
            </g>
          );
        })}
      </Box>
      <Typography sx={{ fontSize: 12, color: colors.textLo }}>{payload.metric.label}</Typography>
    </Box>
  );
};

/**
 * Two values per row (before/after, v pace/v spin): a dumbbell.
 * payload: {series:[a, b], format, rows:[{label, a, b, highlight?}], values?, full_labels?} (full_labels: row labels as
 * given, not shortened to a surname)
 */
const PairDumbbell = ({ payload }) => {
  const W = 300; const rowH = 30; const H = payload.rows.length * rowH + 26; const L = payload.values ? 130 : 104; const R = payload.values ? 70 : 44;
  const vals = payload.rows.flatMap((r) => [r.a, r.b]);
  const lo = Math.min(...vals); const hi = Math.max(...vals); const pad = (hi - lo) * 0.1 || 1;
  const sx = (v) => L + ((v - lo + pad) / (hi - lo + 2 * pad)) * (W - L - R);
  const [ca, cb] = [SERIES[0], SERIES[1]];
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={payload.series.join(' against ')} sx={{ width: '100%' }}>
        {payload.rows.map((r, i) => {
          const y = i * rowH + 16;
          return (
            <g key={r.label}>
              <text x="0" y={y + 4} style={{ fontFamily: fonts.body, fontSize: 12, fill: r.highlight ? colors.accent : colors.textHi }}>{payload.full_labels ? r.label : surname(r.label)}</text>
              <line x1={sx(r.a)} x2={sx(r.b)} y1={y} y2={y} stroke={colors.borderStrong} strokeWidth="3" />
              <circle cx={sx(r.a)} cy={y} r="5" fill={ca} />
              <circle cx={sx(r.b)} cy={y} r="5" fill={cb} />
              {payload.values && (
                <>
                  <text x={sx(Math.min(r.a, r.b)) - 8} y={y + 4} textAnchor="end" style={{ ...mono, fontSize: 10, fill: r.a <= r.b ? ca : cb }}>{fmt(Math.min(r.a, r.b), payload.format)}</text>
                  <text x={sx(Math.max(r.a, r.b)) + 8} y={y + 4} style={{ ...mono, fontSize: 10, fill: r.a <= r.b ? cb : ca }}>{fmt(Math.max(r.a, r.b), payload.format)}</text>
                </>
              )}
              <text x={W} y={y + 4} textAnchor="end" style={{ ...mono, fontSize: 11, fill: colors.textMed }}>{fmt(r.b - r.a, payload.format === 'int' ? 'signed0' : 'signed1')}</text>
            </g>
          );
        })}
      </Box>
      <Legend items={[[payload.series[0], ca], [payload.series[1], cb]]} />
    </Box>
  );
};

/**
 * "Whose innings is this?": the Guess the Innings game's own clue card and wagon wheel.
 * payload: the game's puzzle question (runs, balls, strike_rate, fours, sixes, bat_hand, season, deliveries[{x, y, runs}])
 */
/**
 * "The deeper cut" (services/ig_posts/deep_cut.py): the player against the average player, split by split. Two bars a
 * row, the player's in the accent colour (brighter on the split the sentence is about), the field's in grey; a field of
 * 0 (runs above average) is drawn as the zero line only.
 * payload: {metric:{label, format, signed}, series:[player, field], rows:[{label, subject, field, highlight?}]}
 */
const DeepCompare = ({ payload }) => {
  const { metric, rows, series } = payload;
  const signed = metric.signed;
  const vals = rows.flatMap((r) => [r.subject, r.field ?? 0, 0]);
  const lo = Math.min(...vals); const hi = Math.max(...vals);
  const span = hi - lo || 1;
  const pos = (v) => ((v - lo) / span) * 100; // % across the bar track
  const zero = pos(0);
  const bar = (v, color, h) => (
    <Box sx={{ position: 'relative', height: h }}>
      <Box sx={{ position: 'absolute', top: 0, bottom: 0, borderRadius: '3px', bgcolor: color,
        left: `${Math.min(zero, pos(v))}%`, width: `${Math.max(0.8, Math.abs(pos(v) - zero))}%` }} />
    </Box>
  );
  const showField = !signed || rows.some((r) => r.field);
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: rows.length > 3 ? 1 : 1.5 }}>
      {rows.map((r) => (
        <Box key={r.label}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 0.5 }}>
            <Typography sx={{ fontSize: 14, fontWeight: r.highlight ? 700 : 500, color: r.highlight ? colors.textHi : colors.textMed }}>{r.label}</Typography>
            <Typography sx={{ ...mono, fontSize: 13, color: r.highlight ? colors.accent : colors.textHi }}>
              {fmt(r.subject, metric.format)}
              {showField && <Box component="span" sx={{ color: colors.textLo }}>{`  v ${fmt(r.field, metric.format)}`}</Box>}
            </Typography>
          </Box>
          {bar(r.subject, r.highlight ? colors.accent : 'rgba(182,242,74,.45)', 12)}
          {showField && <Box sx={{ mt: '3px' }}>{bar(r.field ?? 0, colors.borderStrong, 6)}</Box>}
        </Box>
      ))}
      <Legend items={showField ? [[series[0], colors.accent], [series[1], colors.borderStrong]] : [[series[0], colors.accent]]} />
      <Typography sx={{ fontSize: 12, color: colors.textLo, mt: -0.5 }}>{metric.label}</Typography>
    </Box>
  );
};

/**
 * One innings of the match page's Impact scorecard (services/ig_posts/match.innings_scorecards): batting in order with
 * runs (balls), strike rate and Impact (* = not out), then the bowling as the match page shows it: figures, wickets,
 * Impact. Impact is green when it helped the player's side, red when it hurt; no Impact column when the match has none.
 * payload: {batting_team, bowling_team, accent, bowl_accent, has_impact,
 *           batting:[{name, runs, balls, sr, impact, not_out}], bowling:[{name, figures, wickets, impact}]}
 */
const InningsScorecard = ({ payload }) => {
  const { batting, bowling, has_impact: hasImpact } = payload;
  // A full innings is up to 11 batters and 8 bowlers: rows tighten as they add up, so the card never scrolls.
  const dense = batting.length + bowling.length > 14;
  const fs = dense ? 11.5 : 12.5;
  const impactCell = (v) => (
    <Typography sx={{ ...mono, fontSize: fs - 0.5, lineHeight: 1.3, textAlign: 'right', color: v == null ? colors.textLo : v >= 0 ? colors.accent : colors.red }}>
      {v == null ? '' : fmt(v, 'signed1')}
    </Typography>
  );
  const batCols = hasImpact ? '1fr 64px 36px 46px' : '1fr 64px 36px';
  const bowlCols = hasImpact ? '1fr 64px 36px 46px' : '1fr 64px 36px';
  const head = (labels, cols, color) => (
    <Box sx={{ display: 'grid', gridTemplateColumns: cols, gap: '6px', pb: '3px', borderBottom: `1px solid ${colors.border}` }}>
      {labels.map((l, i) => (
        <Typography key={l} sx={{ fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', color: i === 0 ? color : colors.textLo,
          textAlign: i === 0 ? 'left' : 'right', fontWeight: i === 0 ? 700 : 400 }}>{l}</Typography>
      ))}
    </Box>
  );
  const row = { display: 'grid', gap: '6px', alignItems: 'baseline', py: dense ? 0 : '1.5px' };
  const name = { fontSize: fs, lineHeight: 1.3, color: colors.textHi, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };
  const num = { ...mono, fontSize: fs - 0.5, lineHeight: 1.3, color: colors.textMed, textAlign: 'right' };
  const batColour = payload.accent || colors.accent;
  const bowlColour = payload.bowl_accent || colors.textMed;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: dense ? 0.75 : 1 }}>
      <Box>
        {head([`${payload.batting_team} batting${payload.overs ? ` · ${payload.overs} ov` : ''}`, 'R (B)', 'SR', ...(hasImpact ? ['Impact'] : [])], batCols, batColour)}
        {batting.map((r) => (
          <Box key={r.name} sx={{ ...row, gridTemplateColumns: batCols }}>
            <Typography sx={name}>{r.name}{r.not_out ? '*' : ''}</Typography>
            <Typography sx={{ ...num, color: colors.textHi }}>{r.runs} ({r.balls})</Typography>
            <Typography sx={num}>{r.sr != null ? Math.round(r.sr) : ''}</Typography>
            {hasImpact && impactCell(r.impact)}
          </Box>
        ))}
      </Box>
      <Box>
        {head([`${payload.bowling_team} bowling`, 'O-M-R', 'W', ...(hasImpact ? ['Impact'] : [])], bowlCols, bowlColour)}
        {bowling.map((r) => (
          <Box key={r.name} sx={{ ...row, gridTemplateColumns: bowlCols }}>
            <Typography sx={name}>{r.name}</Typography>
            <Typography sx={num}>{r.figures}</Typography>
            <Typography sx={{ ...num, color: colors.textHi }}>{r.wickets}</Typography>
            {hasImpact && impactCell(r.impact)}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

const InningsWagon = ({ payload }) => (
  // The game's clue card already holds its wheel and run legend; zoomed a little so the whole card fits a 4:5 slide.
  <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', zoom: 0.84 }}>
    <InningsClue puzzle={payload} />
  </Box>
);

/**
 * One side's win probability through a chase, ball by ball (services/ig_posts/recap_special.wp_line): the line in the
 * side's colour, a 50% guide, and the overs that moved it most shaded and numbered, each named below with who did it
 * (the over and the batters, not the bowler). Each ball's tooltip: ball, score, chance.
 * payload: {team, label, start, points:[{wp, label, score, over}], bands:[{i0, i1, over, from, to, text}], upto?}
 * upto: draw the line only to that many points, on the whole chase's axis, with the chance at that ball beside the
 * dot (a replay: the same chart drawn a little further on each slide). Bands past it aren't drawn.
 */
export const WinProbLine = ({ payload }) => {
  const { points } = payload;
  const W = 300; const H = 200; const L = 30; const R = 10; const T = 16; const B = 176;
  const n = points.length;
  const shown = Math.min(n, payload.upto || n);
  const bands = (payload.bands || []).filter((b) => b.i1 < shown);
  const sx = (i) => L + ((i + 1) / n) * (W - L - R); // x 0 is the start of the innings (payload.start)
  const sy = (v) => B - (v / 100) * (B - T);
  const line = `M${L},${sy(payload.start)} ` + points.slice(0, shown).map((p, i) => `L${sx(i).toFixed(1)},${sy(p.wp).toFixed(1)}`).join(' ');
  const colour = teamColour(payload.team, colors.accent);
  const overTicks = [];
  points.forEach((p, i) => {
    if (i && p.over !== points[i - 1].over && (p.over % 5 === 0)) overTicks.push([i, p.over]);
  });
  const last = points[shown - 1];
  // The replay's chance label: right of the dot (left of it near the end), on the side the line didn't come from.
  const nowRight = sx(shown - 1) < W - 60;
  const falling = points[Math.max(0, shown - 6)].wp >= last.wp;
  const nowY = falling ? sy(last.wp) + 18 : sy(last.wp) - 8;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.75 }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={`${payload.label}: ${Math.round(payload.start)}% at the start of the chase, ${Math.round(last.wp)}% at the end; ${bands.map((b) => `over ${b.over} ${b.from}% to ${b.to}%`).join(', ')}`}>
        {[0, 50, 100].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke={v === 50 ? colors.borderStrong : colors.border}
              strokeDasharray={v === 50 ? '4 4' : undefined} />
            <text x={L - 6} y={sy(v) + 4} textAnchor="end" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{`${v}%`}</text>
          </g>
        ))}
        {bands.map((b) => (
          <g key={b.over}>
            <rect x={sx(b.i0 - 1)} y={T} width={Math.max(3, sx(b.i1) - sx(b.i0 - 1))} height={B - T} fill={colors.textHi} fillOpacity="0.09" />
            <text x={(sx(b.i0 - 1) + sx(b.i1)) / 2} y={T - 4} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textHi, fontWeight: 700 }}>{b.over}</text>
          </g>
        ))}
        <path d={line} fill="none" stroke={colour} strokeWidth="2" strokeLinejoin="round" />
        <circle cx={sx(shown - 1)} cy={sy(last.wp)} r="4" fill={colour} stroke={colors.bg} strokeWidth="2" />
        {shown < n && (
          <text x={sx(shown - 1) + (nowRight ? 8 : -8)} y={Math.min(B + 14, nowY)} textAnchor={nowRight ? 'start' : 'end'}
            style={{ ...mono, fontSize: 14, fontWeight: 700, fill: colors.textHi }}>{`${Math.round(last.wp)}%`}</text>
        )}
        {points.slice(0, shown).map((p, i) => (
          <rect key={i} x={sx(i - 1)} y={T} width={Math.max(1, sx(i) - sx(i - 1))} height={B - T} fill="transparent">
            <title>{`${p.label} · ${p.score} · ${Math.round(p.wp)}%`}</title>
          </rect>
        ))}
        {overTicks.map(([i, o]) => (
          <text key={o} x={sx(i - 1)} y={H - 6} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{`${o} ov`}</text>
        ))}
      </Box>
      {bands.map((b) => (
        <Box key={b.over} sx={{ display: 'grid', gridTemplateColumns: '22px 1fr auto', gap: 1, alignItems: 'baseline' }}>
          <Typography sx={{ ...mono, fontSize: 12, fontWeight: 700, color: colors.textHi }}>{b.over}</Typography>
          <Typography sx={{ fontSize: 12.5, color: colors.textMed, lineHeight: 1.3 }}>{b.text.replace(/^Over \d+: /, '')}</Typography>
          <Typography sx={{ ...mono, fontSize: 12, color: colors.textHi, whiteSpace: 'nowrap' }}>{`${b.from}% → ${b.to}%`}</Typography>
        </Box>
      ))}
    </Box>
  );
};

/**
 * Where an innings went (wagon_x / wagon_y, centred on 150,150, as on the site's wheels: down the ground is down,
 * a right-hander's leg side to the right). Boundaries reach the rope; other shots are scaled within the inner ring.
 * Sixes gold, fours in the accent, the rest grey. Highlighted shots are drawn thick with their label at the rope and
 * the rest fade, so the wheel can tell one moment of an innings.
 * payload: {shots:[{x, y, runs, highlight?, label?}], left_handed?, compact?}
 */
export const ShotWheel = ({ payload }) => {
  const size = 300; const c = size / 2; const rope = size * (payload.compact ? 0.46 : 0.38);
  const shots = (payload.shots || []).filter((d) => d.runs > 0 && d.x != null && (d.x !== 150 || d.y !== 150));
  const far = Math.max(1, ...shots.filter((d) => d.runs < 4).map((d) => Math.hypot(d.x - 150, d.y - 150)));
  const focus = shots.some((d) => d.highlight);
  const ink = (runs) => (runs >= 6 ? colors.gold : runs >= 4 ? colors.accent : '#8b95a7');
  const end = (d, k) => {
    const dx = d.x - 150; const dy = d.y - 150; const dist = Math.hypot(dx, dy) || 1;
    const r = (d.runs >= 4 ? rope : (dist / far) * rope * 0.72) * k;
    return [c + (dx / dist) * r, c + (dy / dist) * r];
  };
  const order = [...shots].sort((a, b) => Number(!!a.highlight) - Number(!!b.highlight)); // highlights on top
  const [offX, legX] = payload.left_handed ? [size - 4, 4] : [4, size - 4];
  return (
    <Box sx={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${size} ${size}`} role="img" sx={{ width: '100%', maxHeight: '100%' }}
        aria-label={`Wagon wheel: ${shots.length} scoring shots${focus ? `; ${shots.filter((d) => d.highlight).map((d) => d.label).join(', ')}` : ''}`}>
        <circle cx={c} cy={c} r={rope} fill="#12301c" stroke="rgba(255,255,255,0.25)" />
        <circle cx={c} cy={c} r={rope * 0.55} fill="none" stroke="rgba(255,255,255,0.12)" strokeDasharray="3 4" />
        <rect x={c - 5} y={c - 16} width={10} height={32} rx={2} fill="#c9b27c" opacity={0.7} />
        {!payload.compact && (
          <>
            <text x={offX} y={14} textAnchor={payload.left_handed ? 'end' : 'start'} style={{ ...mono, fontSize: 10, fill: colors.textLo }}>OFF SIDE</text>
            <text x={legX} y={14} textAnchor={payload.left_handed ? 'start' : 'end'} style={{ ...mono, fontSize: 10, fill: colors.textLo }}>LEG SIDE</text>
          </>
        )}
        {order.map((d, i) => {
          const [x2, y2] = end(d, 1);
          const dim = focus && !d.highlight;
          return (
            <g key={i}>
              <line x1={c} y1={c} x2={x2} y2={y2} stroke={ink(d.runs)} strokeWidth={d.highlight ? 3.2 : d.runs >= 4 ? 2 : 1.3}
                strokeLinecap="round" opacity={dim ? 0.28 : 0.95} />
              {d.highlight && <circle cx={x2} cy={y2} r="4" fill={ink(d.runs)} stroke={colors.bg} strokeWidth="1.5" />}
            </g>
          );
        })}
        {order.filter((d) => d.highlight && d.label).map((d, i) => {
          // Beyond the rope, kept inside the frame: a label that would run off the side sits above or below its dot.
          let [lx, ly] = end(d, 1.17);
          const wide = String(d.label).length * 7.5;
          let anchor = lx < c - 10 ? 'end' : lx > c + 10 ? 'start' : 'middle';
          if (anchor === 'start' && lx + wide > size - 2) { [lx, ly] = end(d, 1); lx = Math.min(lx, size - 2); ly -= 14; anchor = 'end'; }
          if (anchor === 'end' && lx - wide < 2) { [lx, ly] = end(d, 1); lx = Math.max(lx, 2); ly -= 14; anchor = 'start'; }
          return (
            <text key={`l${i}`} x={lx} y={ly + 4} textAnchor={anchor}
              style={{ ...mono, fontSize: 11.5, fontWeight: 700, fill: colors.textHi }}>{d.label}</text>
          );
        })}
      </Box>
    </Box>
  );
};

/**
 * One over, ball by ball (a replay): the side's chance after each delivery as a stepped line, the chance above each
 * ball and what happened below it (W, 6nb, wd, 3b...), the highlighted ball in the accent, wickets in red.
 * payload: {team, start, balls:[{tag, wp, highlight?, wicket?}]}
 */
const BallSteps = ({ payload }) => {
  const { balls } = payload;
  const W = 300; const H = 190; const L = 30; const R = 8; const T = 22; const B = 150;
  const n = balls.length;
  const col = (W - L - R) / n;
  const sx = (i) => L + col * (i + 0.5);
  const sy = (v) => B - (v / 100) * (B - T);
  const colour = teamColour(payload.team, colors.accent);
  let d = `M${L},${sy(payload.start)}`;
  balls.forEach((b, i) => { d += ` H${(L + col * i).toFixed(1)} V${sy(b.wp).toFixed(1)}`; });
  d += ` H${W - R}`;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={`Ball by ball: ${balls.map((b) => `${b.tag} ${Math.round(b.wp)}%`).join(', ')}`}>
        {[0, 50, 100].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke={v === 50 ? colors.borderStrong : colors.border}
              strokeDasharray={v === 50 ? '4 4' : undefined} />
            <text x={L - 6} y={sy(v) + 4} textAnchor="end" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{`${v}%`}</text>
          </g>
        ))}
        <path d={d} fill="none" stroke={colour} strokeWidth="2" strokeLinejoin="round" />
        {balls.map((b, i) => {
          const hi = b.highlight; const ink = b.wicket ? colors.red : hi ? colors.accent : colors.textHi;
          const y = sy(b.wp); const above = y > T + 14;
          return (
            <g key={i}>
              <circle cx={sx(i)} cy={y} r={hi ? 4.5 : 3} fill={hi ? colors.accent : colour} stroke={colors.bg} strokeWidth="1.5" />
              <text x={sx(i)} y={above ? y - 8 : y + 15} textAnchor="middle"
                style={{ ...mono, fontSize: 9.5, fontWeight: hi ? 700 : 400, fill: hi ? colors.accent : colors.textMed }}>{`${Math.round(b.wp)}%`}</text>
              <rect x={sx(i) - col / 2 + 2} y={B + 10} width={col - 4} height={22} rx={4}
                fill={b.wicket ? 'rgba(229,72,77,.16)' : hi ? 'rgba(182,242,74,.16)' : colors.surface2} />
              <text x={sx(i)} y={B + 25} textAnchor="middle" style={{ ...mono, fontSize: 10.5, fontWeight: 700, fill: ink }}>{b.tag}</text>
            </g>
          );
        })}
      </Box>
    </Box>
  );
};

/**
 * A side's bowling, over by over (services/ig_posts/captains_call.plan_card): one row per bowler, one chip per over
 * they bowled with its runs, pace and spin in the first two series colours, the over in question ringed, and how many
 * overs each still had left before it.
 * payload: {team, mark, overs, rows:[{name, kind:'pace'|'spin'|'other', cells:[{o, runs}], left}]}
 */
const BowlingPlan = ({ payload }) => {
  const { rows, mark } = payload;
  const kindColour = { pace: SERIES[0], spin: SERIES[1], other: '#5b6b85' };
  const cols = '74px repeat(20, 1fr) 30px';
  const head = (o) => (o === 1 || o % 5 === 0 || o === mark ? o : '');
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '5px' }}
      role="img" aria-label={`${payload.team} bowling by over; over ${mark} marked; ${rows.map((r) => `${r.name} ${r.cells.length} overs, ${r.left} left`).join('; ')}`}>
      <Box sx={{ display: 'grid', gridTemplateColumns: cols, gap: '2px', alignItems: 'end' }}>
        <span />
        {Array.from({ length: 20 }, (_, i) => (
          <Typography key={i} sx={{ ...mono, fontSize: 9.5, textAlign: 'center', color: i + 1 === mark ? colors.textHi : colors.textLo, fontWeight: i + 1 === mark ? 700 : 400 }}>{head(i + 1)}</Typography>
        ))}
        <Typography sx={{ fontSize: 9.5, color: colors.textLo, textAlign: 'right', lineHeight: 1.1 }}>left</Typography>
      </Box>
      {rows.map((r) => {
        const at = Object.fromEntries(r.cells.map((c) => [c.o, c.runs]));
        return (
          <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: cols, gap: '2px', alignItems: 'center' }}>
            <Typography noWrap sx={{ fontSize: 12, color: colors.textHi }}>{r.short || raceName(r.name)}</Typography>
            {Array.from({ length: 20 }, (_, i) => {
              const o = i + 1; const runs = at[o]; const isMark = o === mark;
              return (
                <Box key={o} title={runs != null ? `Over ${o}: ${runs} runs` : undefined} sx={{
                  height: 24, borderRadius: '3px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  bgcolor: runs != null ? kindColour[r.kind] : (isMark ? 'rgba(255,255,255,0.06)' : colors.surface2),
                  outline: isMark && runs != null ? `2px solid ${colors.textHi}` : 'none', outlineOffset: '1px',
                }}>
                  {runs != null && <Typography sx={{ ...mono, fontSize: 9.5, color: '#fff', fontWeight: 600, lineHeight: 1 }}>{runs}</Typography>}
                </Box>
              );
            })}
            <Typography sx={{ ...mono, fontSize: 12, textAlign: 'right', color: r.left ? colors.textHi : colors.textLo }}>{r.left}</Typography>
          </Box>
        );
      })}
      <Legend items={[['Pace', kindColour.pace], ['Spin', kindColour.spin]]} />
      <Typography sx={{ fontSize: 11.5, color: colors.textLo, mt: -0.25 }}>Runs in each over</Typography>
    </Box>
  );
};

/**
 * "How it was won": the match page's recap card (services/match_recap.build_recap), headline and bullets as the site
 * shows them (services/ig_posts/recap_series.how_it_was_won).
 * payload: {headline, bullets:[string]}
 */
const RecapText = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
    <Typography sx={{ fontSize: 19, fontWeight: 700, color: colors.textHi, lineHeight: 1.25 }}>{payload.headline}</Typography>
    {payload.bullets.map((b) => (
      <Box key={b} sx={{ display: 'grid', gridTemplateColumns: '10px 1fr', gap: 1, alignItems: 'baseline' }}>
        <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: colors.accent, transform: 'translateY(-2px)' }} />
        <Typography sx={{ fontSize: 14.5, color: colors.textMed, lineHeight: 1.4 }}>{b}</Typography>
      </Box>
    ))}
  </Box>
);

/**
 * Both innings' scores at the end of every over (the match page's momentum worm), wickets as dots, the over the chase
 * was last level or ahead marked (services/ig_posts/recap_series.score_race).
 * payload: {series:[{team, values:[runs], wickets:[count]}], mark}
 */
const ScoreRace = ({ payload }) => {
  const { series, mark } = payload;
  const W = 300; const H = 180; const L = 30; const R = 40; const T = 12; const B = 152;
  const top = Math.max(...series.flatMap((s) => s.values), 1);
  const sx = (o) => L + (o / 20) * (W - L - R);
  const sy = (v) => B - (v / top) * (B - T);
  const tones = series.map((s, i) => teamColour(s.team, SERIES[i]));
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={series.map((s) => `${s.team}: ${s.values[mark - 1]} after ${mark} overs, ${s.values[s.values.length - 1]} at the end`).join('; ')}>
        {[0, 100, 200].filter((v) => v <= top).map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke={colors.border} />
            <text x={L - 6} y={sy(v) + 4} textAnchor="end" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{v}</text>
          </g>
        ))}
        {mark && (
          <g>
            <rect x={sx(mark)} y={T} width={sx(20) - sx(mark)} height={B - T} fill={colors.textHi} fillOpacity="0.07" />
            <line x1={sx(mark)} x2={sx(mark)} y1={T} y2={B} stroke={colors.textLo} strokeDasharray="3 4" />
          </g>
        )}
        {series.map((s, i) => {
          const d = `M${sx(0)},${sy(0)} ` + s.values.map((v, o) => `L${sx(o + 1).toFixed(1)},${sy(v).toFixed(1)}`).join(' ');
          const last = s.values.length;
          return (
            <g key={s.team}>
              <path d={d} fill="none" stroke={tones[i]} strokeWidth="2.2" strokeLinejoin="round" />
              {s.values.map((v, o) => (s.wickets[o] > (o ? s.wickets[o - 1] : 0) ? (
                <circle key={o} cx={sx(o + 1)} cy={sy(v)} r="3.2" fill={colors.bg} stroke={tones[i]} strokeWidth="1.6" />
              ) : null))}
              <text x={sx(last) + 4} y={sy(s.values[last - 1]) + (i ? 12 : -4)} style={{ ...mono, fontSize: 12, fill: tones[i], fontWeight: 700 }}>
                {s.values[last - 1]}
              </text>
            </g>
          );
        })}
        {[5, 10, 15, 20].map((o) => (
          <text key={o} x={sx(o)} y={H - 10} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{`${o} ov`}</text>
        ))}
      </Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto auto', columnGap: 1.5, rowGap: 0.25, mt: 0.5 }}>
        <span />
        <Typography sx={{ ...mono, fontSize: 11, color: colors.textLo, textAlign: 'right' }}>{`after ${mark}`}</Typography>
        <Typography sx={{ ...mono, fontSize: 11, color: colors.textLo, textAlign: 'right' }}>{`last ${series[0].values.length - mark}`}</Typography>
        {series.map((s, i) => {
          const n = s.values.length;
          return (
            <React.Fragment key={s.team}>
              <Typography sx={{ fontSize: 13, color: tones[i], fontWeight: 600 }}>{s.team}</Typography>
              <Typography sx={{ ...mono, fontSize: 13, color: colors.textHi, textAlign: 'right' }}>{`${s.values[mark - 1]}/${s.wickets[mark - 1]}`}</Typography>
              <Typography sx={{ ...mono, fontSize: 13, color: colors.textHi, textAlign: 'right' }}>
                {`${s.values[n - 1] - s.values[mark - 1]}/${s.wickets[n - 1] - s.wickets[mark - 1]}`}
              </Typography>
            </React.Fragment>
          );
        })}
      </Box>
    </Box>
  );
};

/**
 * A pitch map of one batter against one kind of bowling: every line-and-length cell shaded by a measure, from the
 * bowler's end (the batter at the top, full balls nearest him, short balls nearest the bowler). Off side is on the
 * left for a right-hander and on the right for a left-hander, so the picture matches a broadcast pitch map.
 * Cells better for the batter than `mid` are lime, better for the bowler red, deeper with the gap; cells under
 * `min_balls` stay blank. Highlighted cells are outlined.
 * payload: {hand:'RHB'|'LHB', lines:[...], lengths:[...], metric:{label, format, higher_better, mid},
 *           min_balls, cells:[{line, length, value, balls, outs?, highlight?}], show_outs?, legend?:[better, worse]}
 * One number per cell; wickets under it only with show_outs (when the claim is about dismissals).
 */
const PITCH_LINES = { WIDE_OUTSIDE_OFFSTUMP: 'Wide off', OUTSIDE_OFFSTUMP: 'Off', ON_THE_STUMPS: 'Stumps', DOWN_LEG: 'Leg', WIDE_DOWN_LEG: 'Wide leg' };
const PITCH_LENGTHS = { YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };
const PitchMap = ({ payload }) => {
  const { metric, cells, min_balls: minBalls = 10 } = payload;
  const lines = payload.hand === 'LHB' ? [...payload.lines].reverse() : payload.lines;
  const lengths = payload.lengths;
  const L = 92; const T = 20; const cw = (300 - L - 6) / lines.length; const ch = 54; const H = T + lengths.length * ch + 34;
  const at = (line, length) => cells.find((c) => c.line === line && c.length === length);
  const shown = cells.filter((c) => c.balls >= minBalls);
  const span = Math.max(...shown.map((c) => Math.abs(c.value - metric.mid)), 1e-9);
  const good = (v) => (metric.higher_better === false ? v < metric.mid : v > metric.mid);
  // Three shades a side, not a smooth ramp: a smooth ramp passes through shades where neither light nor dark text
  // reaches 4.5:1. These steps were checked against the dark pitch (lowest 5.8:1 with the ink below) and for colour
  // blindness (lime v red at least 10 OKLab ΔE under deuteranopia).
  const step = (v) => { const r = Math.abs(v - metric.mid) / span; return r < 0.2 ? -1 : r < 0.5 ? 0 : r < 0.8 ? 1 : 2; };
  const SHADE = { good: [0.18, 0.32, 0.85], bad: [0.25, 0.45, 0.7] };
  const paint = (v) => {
    const k = step(v);
    if (k < 0) return { fill: colors.textMed, opacity: 0.1, ink: colors.textHi };
    const g = good(v);
    return { fill: g ? colors.accent : colors.red, opacity: (g ? SHADE.good : SHADE.bad)[k], ink: g && k === 2 ? colors.bg : colors.textHi };
  };
  const offLeft = payload.hand !== 'LHB';
  const stumpsX = L + (lines.indexOf('ON_THE_STUMPS') + 0.5) * cw;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 300 ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={`${metric.label} by line and length: ${shown.map((c) => `${PITCH_LENGTHS[c.length]} ${PITCH_LINES[c.line]} ${fmt(c.value, metric.format)}`).join('; ')}`}>
        <rect x={L - 4} y={T - 6} width={300 - L} height={lengths.length * ch + 10} rx="10" fill={colors.surface2} />
        <line x1={L - 4} x2={296} y1={T - 1} y2={T - 1} stroke={colors.borderStrong} strokeWidth="1.5" />
        {lines.indexOf('ON_THE_STUMPS') >= 0 && [-5, 0, 5].map((dx) => (
          <rect key={dx} x={stumpsX + dx - 1.2} y={2} width="2.4" height={T - 6} rx="1" fill={colors.textMed} />
        ))}
        {lengths.map((len, i) => (
          <text key={len} x={L - 9} y={T + i * ch + ch / 2 + 4} textAnchor="end" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textHi }}>
            {PITCH_LENGTHS[len] || len}
          </text>
        ))}
        {lengths.map((len, i) => lines.map((line, j) => {
          const c = at(line, len); const x = L + j * cw; const y = T + i * ch;
          const ok = c && c.balls >= minBalls;
          const p = ok ? paint(c.value) : null;
          return (
            <g key={`${len}-${line}`}>
              <rect x={x + 1.5} y={y + 1.5} width={cw - 3} height={ch - 3} rx="6"
                fill={ok ? p.fill : 'none'} fillOpacity={ok ? p.opacity : 0}
                stroke={ok && c.highlight ? colors.textHi : colors.border} strokeWidth={ok && c.highlight ? 2.5 : 1}>
                {ok && <title>{`${PITCH_LENGTHS[len]}, ${PITCH_LINES[line]}: ${fmt(c.value, metric.format)} (${c.balls} balls)`}</title>}
              </rect>
              {ok ? (
                <>
                  <text x={x + cw / 2} y={y + ch / 2 + (payload.show_outs && c.outs ? 0 : 5)} textAnchor="middle" style={{ ...mono, fontSize: 15, fontWeight: 700, fill: p.ink }}>{fmt(c.value, metric.format)}</text>
                  <text x={x + cw / 2} y={y + ch / 2 + 12} textAnchor="middle" style={{ ...mono, fontSize: 8, fill: p.ink }}>
                    {payload.show_outs && c.outs ? `${c.outs} ${c.outs === 1 ? 'wicket' : 'wickets'}` : ''}
                  </text>
                </>
              ) : (
                <text x={x + cw / 2} y={y + ch / 2 + 4} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textGhost }}>–</text>
              )}
            </g>
          );
        }))}
        {lines.map((line, j) => (
          <text key={line} x={L + (j + 0.5) * cw} y={T + lengths.length * ch + 15} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{PITCH_LINES[line] || line}</text>
        ))}
        <text x={L} y={H - 4} style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{offLeft ? '← off side' : '← leg side'}</text>
        <text x={296} y={H - 4} textAnchor="end" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{offLeft ? 'leg side →' : 'off side →'}</text>
      </Box>
      <Legend items={[[payload.legend?.[0] || `Better than his ${fmt(metric.mid, metric.format)}`, colors.accent],
        [payload.legend?.[1] || 'Worse', colors.red]]} />
    </Box>
  );
};

/**
 * A few measures over an ordered axis (ball of the innings, season): one line each, the highlighted one in lime and
 * the rest in the series colours, each named at its end with its last value. An optional shaded span marks a period
 * (the Impact Player era) and dots can be called out with their value.
 * payload: {x:{label, ticks:[x...]}, y:{label, format}, series:[{name, points:[{x, y}], highlight?, dashed?}],
 *           span?:{from, to, label}, callouts?:[{series, x, place?:'below'|'above-left'}]}
 */
const MetricLines = ({ payload }) => {
  const { series, x: X, y: Y, span, callouts = [] } = payload;
  const W = 300; const H = 210; const L = 30; const R = 66; const T = 18; const B = 182;
  const xs = series.flatMap((s) => s.points.map((p) => p.x)); const ys = series.flatMap((s) => s.points.map((p) => p.y));
  const xa = Math.min(...xs); const xb = Math.max(...xs);
  const top = Math.max(...ys) * 1.08;
  const sx = (v) => L + ((v - xa) / (xb - xa || 1)) * (W - L - R);
  const sy = (v) => B - (v / top) * (B - T);
  const step = [1, 2, 5, 10, 20, 25, 50].find((s) => top / s <= 4) || 100;
  const grid = []; for (let v = 0; v <= top; v += step) grid.push(v);
  const others = SERIES.filter((c) => c !== colors.accent);
  let k = 0;
  const tone = series.map((s) => (s.highlight ? colors.accent : others[k++ % others.length]));
  // End labels: spread so they never overlap, in the order the lines finish.
  const ends = series.map((s, i) => ({ i, y: sy(s.points[s.points.length - 1].y) })).sort((a, b) => a.y - b.y);
  ends.forEach((e, j) => { if (j && e.y - ends[j - 1].y < 26) e.y = ends[j - 1].y + 26; });
  const endY = Object.fromEntries(ends.map((e) => [e.i, e.y]));
  const last = (s) => s.points[s.points.length - 1];
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={series.map((s) => `${s.name}: ${fmt(s.points[0].y, Y.format)} at ${X.label} ${s.points[0].x}, ${fmt(last(s).y, Y.format)} at ${last(s).x}`).join('; ')}>
        <text x={0} y={10} style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{`↑ ${Y.label}`}</text>
        {span && (
          <g>
            <rect x={sx(span.from)} y={T} width={sx(span.to) - sx(span.from)} height={B - T} fill={colors.textHi} fillOpacity="0.07" />
            <text x={(sx(span.from) + sx(span.to)) / 2} y={B - 8} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textMed }}>{span.label}</text>
          </g>
        )}
        {grid.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke={v ? colors.border : colors.borderStrong} />
            <text x={L - 6} y={sy(v) + 4} textAnchor="end" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{fmt(v, Y.format === 'pct1' ? 'pct0' : Y.format)}</text>
          </g>
        ))}
        {series.map((s, i) => (
          <g key={s.name}>
            <path d={s.points.map((p, j) => `${j ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ')} fill="none"
              stroke={tone[i]} strokeWidth={s.highlight ? 2.6 : 2} strokeDasharray={s.dashed ? '5 4' : undefined} strokeLinejoin="round" />
            <circle cx={sx(last(s).x)} cy={sy(last(s).y)} r="3.5" fill={tone[i]} stroke={colors.bg} strokeWidth="1.5" />
            <text x={W - R + 6} y={endY[i] - 2} style={{ ...mono, fontSize: 12, fontWeight: 700, fill: tone[i] }}>{fmt(last(s).y, Y.format)}</text>
            <text x={W - R + 6} y={endY[i] + 10} style={{ fontFamily: fonts.body, fontSize: 10.5, fill: colors.textMed }}>{s.name}</text>
          </g>
        ))}
        {callouts.map((c) => {
          const i = series.findIndex((s) => s.name === c.series); const p = i >= 0 && series[i].points.find((q) => q.x === c.x);
          if (!p) return null;
          return (
            <g key={`${c.series}-${c.x}`}>
              <circle cx={sx(p.x)} cy={sy(p.y)} r="4" fill={tone[i]} stroke={colors.bg} strokeWidth="1.5" />
              <text x={c.place === 'above-left' ? sx(p.x) - 6 : sx(p.x) + 6} y={c.place === 'above-left' ? sy(p.y) - 10 : sy(p.y) + 14}
                textAnchor={c.place === 'above-left' ? 'end' : 'start'} style={{ ...mono, fontSize: 12, fontWeight: 700, fill: tone[i] }}>{fmt(p.y, Y.format)}</text>
            </g>
          );
        })}
        {X.ticks.map((t) => (
          <text key={t} x={sx(t)} y={B + 14} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textLo }}>{t}</text>
        ))}
        <text x={(L + W - R) / 2} y={H - 2} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{`${X.label} →`}</text>
      </Box>
    </Box>
  );
};

/**
 * Keep / try (services/preview_cards/series.series_keep_try): per side, up to two things to keep and two to try, each
 * with its evidence under it. Options, not verdicts; the side's name in its team colour.
 * payload: {sides:[{team, keep:[{text, detail}], try:[{text, detail}]}], team1, team2}
 */
const KeepTry = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 2 }}>
    {payload.sides.map((side) => (
      <Box key={side.team}>
        <Typography sx={{ fontFamily: fonts.display, fontSize: 17, fontWeight: 700, color: teamColour(side.team, colors.textHi), mb: 0.75 }}>
          {side.team}
        </Typography>
        {[['Keep', side.keep, colors.accent], ['Try', side.try, colors.textHi]].map(([word, items, ink]) => items.map((it) => (
          <Box key={`${word}-${it.text}`} sx={{ display: 'grid', gridTemplateColumns: '40px 1fr', columnGap: 1, mb: 0.75 }}>
            <Typography sx={{ ...mono, fontSize: 11, fontWeight: 700, color: ink, letterSpacing: '0.06em', pt: '3px' }}>{word.toUpperCase()}</Typography>
            <Box>
              <Typography sx={{ fontSize: 14.5, color: colors.textHi, lineHeight: 1.3 }}>{it.text}</Typography>
              <Typography sx={{ fontSize: 12, color: colors.textLo, lineHeight: 1.35 }}>{it.detail}</Typography>
            </Box>
          </Box>
        )))}
      </Box>
    ))}
  </Box>
);

export const POST_VISUALS = {
  recap_text: RecapText,
  score_race: ScoreRace,
  deep_compare: DeepCompare,
  innings_scorecard: InningsScorecard,
  innings_wagon: InningsWagon,
  scorecard: Scorecard,
  scatter_plus: ScatterPlus,
  metric_bars: MetricBars,
  share_bars: ShareBars,
  race_lines: RaceLines,
  win_prob_line: WinProbLine,
  shot_wheel: ShotWheel,
  ball_steps: BallSteps,
  forest: Forest,
  bucket_bars: BucketBars,
  bowling_plan: BowlingPlan,
  pair_dumbbell: PairDumbbell,
  pitch_map: PitchMap,
  metric_lines: MetricLines,
  keep_try: KeepTry,
};
