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
  <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mt: 1 }}>
    {items.map(([label, color]) => (
      <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
        <Box sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: color }} />
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
  const cols = `92px repeat(${metrics.length}, 1fr)`;
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
      <Typography sx={{ fontSize: 11, color: colors.textLo, mt: 0.25 }}>
        {payload.method || 'Shade: percentile in the whole field (brighter is better). Ring: leads that column.'}
      </Typography>
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
 * Numbered markers that don't sit on each other: each, best first, takes the nearest free spot around its dot (a short
 * line leads back to the dot when it had to move).
 */
const spreadMarkers = (pts, sx, sy, [xmin, xmax, ymin, ymax]) => {
  const placed = [];
  const offsets = [[0, 0]];
  for (let r = 16; r <= 48; r += 16) {
    for (let k = 0; k < 8; k++) offsets.push([Math.round(r * Math.cos((k * Math.PI) / 4)), Math.round(r * Math.sin((k * Math.PI) / 4))]);
  }
  return pts.map((p) => {
    const dx = sx(p.x); const dy = sy(p.y);
    const spot = offsets.map(([ox, oy]) => [dx + ox, dy + oy])
      .find(([x, y]) => x >= xmin && x <= xmax && y >= ymin && y <= ymax && placed.every(([px, py]) => Math.hypot(px - x, py - y) >= 16))
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
 */
const ScatterPlus = ({ payload }) => {
  const { points, x: X, y: Y, z: Z } = payload;
  const W = 300; const H = 214; const L = 8; const R = 8; const T = 18; const B = 184;
  const [x0, x1] = robustRange(points.map((p) => p.x)); const [y0, y1] = robustRange(points.map((p) => p.y));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  // A lower-is-better axis runs backwards, so better is always up and to the right.
  const fx = X.higher_better === false; const fy = Y.higher_better === false;
  const tx = (v) => (fx ? (x1 - v) / (x1 - x0) : (v - x0) / (x1 - x0));
  const ty = (v) => (fy ? (y1 - v) / (y1 - y0) : (v - y0) / (y1 - y0));
  const sx = (v) => clamp(L + tx(v) * (W - L - R), L + 3, W - R - 3);
  const sy = (v) => clamp(B - ty(v) * (B - T), T + 3, B - 3);
  const subject = points.find((p) => p.highlight);
  const better = (p, axis, ref) => (payload[axis].higher_better === false ? p[axis] < ref[axis] : p[axis] > ref[axis]);
  const boxX = subject ? [sx(subject.x), W - R] : null;
  const boxY = subject ? [T, sy(subject.y)] : null;
  const keyed = points.filter((p) => p.label && !p.highlight).sort((a, b) => a.label - b.label); // label: rank, best first
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${Y.label} against ${X.label}`} sx={{ width: '100%' }}>
        <text x={L} y={10} style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{`↑ ${Y.label}${Y.higher_better === false ? ' (lower is better)' : ''}`}</text>
        {subject && payload.box && (
          <rect x={boxX[0]} y={boxY[0]} width={boxX[1] - boxX[0]} height={boxY[1] - boxY[0]} fill={colors.accent} fillOpacity="0.07" />
        )}
        <rect x={L} y={T} width={W - L - R} height={B - T} fill="none" stroke={colors.border} />
        {points.filter((p) => !p.highlight && !p.label).map((p) => {
          const op = Z && p.zp != null ? 0.18 + 0.8 * (p.zp / 100) : 0.55;
          const inBox = subject && better(p, 'x', subject) && better(p, 'y', subject);
          return <circle key={p.name} cx={sx(p.x)} cy={sy(p.y)} r="3.5" fill={Z ? colors.accent : '#7c8aa5'} fillOpacity={op}
            stroke={inBox ? colors.textHi : 'none'} strokeWidth="1" />;
        })}
        {spreadMarkers(keyed, sx, sy, [L + 8, W - R - 8, T + 8, B - 8]).map((m, i) => (
          <g key={m.name}>
            {m.moved && <line x1={m.dx} y1={m.dy} x2={m.mx} y2={m.my} stroke={colors.textMed} strokeWidth="0.8" />}
            {m.moved && <circle cx={m.dx} cy={m.dy} r="2.5" fill={colors.textHi} />}
            <circle cx={m.mx} cy={m.my} r="7.5" fill={colors.textHi} stroke={colors.bg} strokeWidth="1.5" />
            <text x={m.mx} y={m.my + 3.5} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 10, fontWeight: 700, fill: colors.bg }}>{i + 1}</text>
          </g>
        ))}
        {subject && (
          <g>
            <circle cx={sx(subject.x)} cy={sy(subject.y)} r="7" fill={colors.accent} stroke={colors.bg} strokeWidth="2" />
            <text x={sx(subject.x) > (W - R) * 0.65 ? sx(subject.x) - 10 : sx(subject.x) + 10} y={sy(subject.y) - 8}
              textAnchor={sx(subject.x) > (W - R) * 0.65 ? 'end' : 'start'}
              style={{ fontFamily: fonts.body, fontSize: 13, fontWeight: 600, fill: colors.accent }}>
              {subject.short || surname(subject.name)}
            </text>
          </g>
        )}
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
        <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 0.5 }}>{`Brighter dots: higher ${Z.label}`}</Typography>
      )}
    </Box>
  );
};

/**
 * One metric, ranked; the subject in lime, others in their team colour (or slate). Signed metrics draw from zero.
 * payload: {metric:{label, format, signed}, rows:[{name, value, team?, highlight?, detail?}]}
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
          <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: '110px 1fr 58px', gap: 1, alignItems: 'center' }}>
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
 * Cumulative runs or wickets against balls (or innings) for the fastest few to a milestone, the milestone dashed.
 * payload: {unit:'balls'|'innings', target, measure, series:[{name, points:[[x, y]], reached_at, highlight}]}
 */
const RaceLines = ({ payload }) => {
  const W = 300; const H = 220; const L = 8; const R = 64; const T = 12; const B = 190;
  const maxX = Math.max(...payload.series.flatMap((s) => s.points.map((p) => p[0])), 1);
  const maxY = Math.max(payload.target, ...payload.series.flatMap((s) => s.points.map((p) => p[1])));
  const sx = (v) => L + (v / maxX) * (W - L - R);
  const sy = (v) => B - (v / maxY) * (B - T);
  const palette = [colors.accent, SERIES[0], SERIES[1], SERIES[2], '#7c8aa5'];
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Race to ${payload.target} ${payload.measure}`} sx={{ width: '100%' }}>
        <line x1={L} x2={W - R} y1={sy(payload.target)} y2={sy(payload.target)} stroke={colors.textFaint} strokeDasharray="4 4" />
        <text x={L} y={sy(payload.target) - 5} style={{ ...mono, fill: colors.textLo }}>{`${payload.target.toLocaleString('en-US')} ${payload.measure}`}</text>
        {payload.series.map((s, i) => {
          const d = s.points.map((p, k) => `${k ? 'L' : 'M'}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(' ');
          const last = s.points[s.points.length - 1];
          const c = palette[i % palette.length];
          return (
            <g key={s.name}>
              <path d={d} fill="none" stroke={c} strokeWidth={i === 0 ? 2.5 : 1.6} strokeOpacity={i === 0 ? 1 : 0.85} />
              <circle cx={sx(s.reached_at)} cy={sy(payload.target)} r="3.5" fill={c} />
              <text x={sx(last[0]) + 5} y={sy(last[1]) + 4} style={{ fontFamily: fonts.body, fontSize: 11, fill: c }}>
                {`${surname(s.name)} ${s.reached_at}`}
              </text>
            </g>
          );
        })}
        <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" style={{ ...mono, fill: colors.textLo }}>{`${payload.unit} →`}</text>
      </Box>
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
      <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 0.5 }}>
        {`Dot: the estimate (${payload.unit}); line: its 95% interval. Lime: a clear effect. Grey: the line crosses "no effect", so the data can't tell.`}
      </Typography>
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
      <Typography sx={{ fontSize: 12, color: colors.textLo }}>{payload.metric.label}{payload.buckets.some((b) => b.lo != null) ? ' · white line: 95% interval' : ''}</Typography>
    </Box>
  );
};

/**
 * Two values per row (before/after, v pace/v spin): a dumbbell.
 * payload: {series:[a, b], format, rows:[{label, a, b, highlight?}]}
 */
const PairDumbbell = ({ payload }) => {
  const W = 300; const rowH = 30; const H = payload.rows.length * rowH + 26; const L = 104; const R = 44;
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
              <text x="0" y={y + 4} style={{ fontFamily: fonts.body, fontSize: 12, fill: r.highlight ? colors.accent : colors.textHi }}>{surname(r.label)}</text>
              <line x1={sx(r.a)} x2={sx(r.b)} y1={y} y2={y} stroke={colors.borderStrong} strokeWidth="3" />
              <circle cx={sx(r.a)} cy={y} r="5" fill={ca} />
              <circle cx={sx(r.b)} cy={y} r="5" fill={cb} />
              <text x={W} y={y + 4} textAnchor="end" style={{ ...mono, fontSize: 11, fill: colors.textMed }}>{fmt(r.b - r.a, 'signed1')}</text>
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

export const POST_VISUALS = {
  deep_compare: DeepCompare,
  innings_scorecard: InningsScorecard,
  innings_wagon: InningsWagon,
  scorecard: Scorecard,
  scatter_plus: ScatterPlus,
  metric_bars: MetricBars,
  race_lines: RaceLines,
  forest: Forest,
  bucket_bars: BucketBars,
  pair_dumbbell: PairDumbbell,
};
