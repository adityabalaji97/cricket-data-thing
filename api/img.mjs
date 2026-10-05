// GET /img/:snapshotId.png?size=portrait|square|card
//
// Share images for chart snapshots: the native image a person posts to Reddit, X, Instagram or
// WhatsApp. Built for phones first (docs/content_guidelines.md):
//   * portrait 1080x1350 by default (fills a phone feed); square 1080x1080; card 1200x630;
//   * one message per image: the headline IS the stat, the chart proves it;
//   * legible at ~390px phone width: headline >= 64px, labels >= 34px, footer >= 26px at 1080w;
//   * at most 8 bars, direct labels instead of legends, 60px safe margins;
//   * source line + hindsightcricket.com watermark on every image.
// Snapshots never change, so images are cached hard at the edge.
import { ImageResponse } from '@vercel/og';
import { readFileSync } from 'node:fs';
import { getJSON } from './_lib/share.mjs';

// The site's own typefaces (SIL OFL, api/_lib/fonts/OFL.txt): Barlow for text, Barlow Semi
// Condensed Bold for headlines. Satori's default font has no bold and no bullet glyphs.
const font = (name) => readFileSync(new URL(`./_lib/fonts/${name}`, import.meta.url));
export const FONTS = [
  { name: 'Barlow', data: font('Barlow-Regular.ttf'), weight: 400, style: 'normal' },
  { name: 'Barlow', data: font('Barlow-SemiBold.ttf'), weight: 600, style: 'normal' },
  { name: 'Barlow Semi Condensed', data: font('BarlowSemiCondensed-Bold.ttf'), weight: 700, style: 'normal' },
];
const DISPLAY = 'Barlow Semi Condensed';

const C = {
  bg: '#0a0c11', surface: '#14171e', track: '#1d212b', text: '#f3f4f6', mid: '#c3c8d0', low: '#9aa1ac',
  lime: '#b6f24a', bar: '#5b6b85', red: '#e5484d',
};

export const SIZES = {
  portrait: { width: 1080, height: 1350, rows: 8, gap: 18, headline: 72, label: 36, value: 38, small: 28 },
  square: { width: 1080, height: 1080, rows: 6, gap: 22, headline: 66, label: 34, value: 36, small: 26 },
  // Link previews (og:image for notes): 510px inside the margins holds four bars and the footer.
  card: { width: 1200, height: 630, rows: 4, gap: 12, headline: 52, label: 28, value: 30, small: 22 },
};

// Font sizes the phone-legibility rule requires at 1080px width (checked by a test).
export const MIN_FONT = { headline: 64, label: 34, footer: 26 };

const h = (type, style, ...children) => ({
  type,
  props: { style: { display: 'flex', ...style }, children: children.flat().filter((c) => c !== null && c !== undefined && c !== false) },
});

const METRIC_LABELS = {
  control_percentage: 'Control %', strike_rate: 'Strike rate', impact: 'Impact', impact_per_innings: 'Impact per innings',
  economy: 'Economy', average: 'Average', runs: 'Runs', wickets: 'Wickets', balls: 'Balls', dot_percentage: 'Dot %',
  boundary_percentage: 'Boundary %', wpa: 'Win probability added', raa: 'Runs above average', innings_count: 'Innings',
};

export const metricLabel = (m) => METRIC_LABELS[m] || String(m || '').replace(/_/g, ' ');

export function formatValue(metric, v) {
  if (typeof v !== 'number') return String(v ?? '–');
  if (/percentage/.test(metric)) return `${v.toFixed(1)}%`;
  if (metric === 'wpa') return `${v > 0 ? '+' : ''}${v.toFixed(2)}`;
  if (['impact', 'raa', 'impact_per_innings'].includes(metric)) return `${v > 0 ? '+' : ''}${v.toFixed(1)}`;
  if (Number.isInteger(v)) return v.toLocaleString('en-US');
  return v.toFixed(Math.abs(v) >= 100 ? 0 : 1);
}

function frame(size, kicker, headline, body, source) {
  const long = (headline || '').length > 70;
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: 60, fontFamily: 'Barlow' },
    h('div', { justifyContent: 'space-between', alignItems: 'center' },
      h('div', { color: C.lime, fontSize: size.small + 2, letterSpacing: 5, fontWeight: 600 }, 'HINDSIGHT'),
      h('div', { color: C.low, fontSize: size.small }, kicker || '')),
    h('div', { fontFamily: DISPLAY, flexShrink: 0, fontSize: long ? Math.max(size.headline - 8, MIN_FONT.headline * (size.width / 1080)) : size.headline, fontWeight: 700, marginTop: 30, lineHeight: 1.08 }, headline || ''),
    body,
    h('div', { marginTop: 'auto', paddingTop: 24, justifyContent: 'space-between', alignItems: 'flex-end', gap: 20 },
      h('div', { color: C.low, fontSize: size.small, maxWidth: '70%' }, source || 'Hindsight · ball-by-ball cricket data'),
      h('div', { color: C.lime, fontSize: size.small + 2, fontWeight: 600 }, 'hindsightcricket.com')));
}

function barsBody(size, data) {
  const chart = data.chart || {};
  const labelKey = chart.label_key || (data.group_by || [])[0];
  const metric = chart.metric || (data.metric_columns || [])[0];
  // A three-line headline leaves room for one bar fewer. A full league table (data.row_limit, e.g. 10
  // teams in a playoff race) must show every team, so on the tall sizes it gets up to two extra rows,
  // drawn tighter, whatever the headline length.
  const extra = data.row_limit && size.height >= size.width ? Math.min(2, Math.max(0, data.row_limit - size.rows)) : 0;
  const maxRows = extra ? size.rows + extra : size.rows - ((data.title || '').length > 70 ? 1 : 0);
  const all = (data.rows || []).filter((r) => typeof r[metric] === 'number');
  let rows = all.slice(0, maxRows);
  // The highlighted row is the point of the chart: never let the row limit cut it off.
  const hi = all.findIndex((r) => r.highlight === true);
  if (hi >= maxRows) rows = [...rows.slice(0, maxRows - 1), all[hi]];
  const values = rows.map((r) => r[metric]);
  const max = Math.max(...values.map(Math.abs), 1e-9);
  const min = Math.min(...values);
  // Compress the axis when all values are close (e.g. control % 80-90) so differences show.
  const floor = min > 0 && (max - min) / max < 0.25 ? min * 0.9 : 0;
  const highlight = (data.highlight || '').toLowerCase();
  return h('div', { flexDirection: 'column', marginTop: size.height < size.width ? 24 : 34, gap: extra ? Math.round(size.gap * 0.5) : size.gap },
    h('div', { color: C.mid, fontSize: size.small }, [data.metric_label ? data.metric_label[0].toUpperCase() + data.metric_label.slice(1) : metricLabel(metric), ...chipsFor(data)].join(' · ')),
    rows.map((r, i) => {
      const label = String(r[labelKey] ?? '');
      // Ranking snapshots (content packs) flag their row and carry the true rank and a display
      // value ("142 (118)", "5/21"); query snapshots match a highlight string.
      const isHi = r.highlight === true || (highlight && label.toLowerCase().includes(highlight));
      // "Fastest to 100": fewest balls is best, so the best row gets the longest bar.
      const pct = data.lower_is_better
        ? Math.max(0.04, min / r[metric])
        : Math.max(0.04, (Math.abs(r[metric]) - floor) / (max - floor));
      return h('div', { flexDirection: 'column', gap: 6 },
        h('div', { justifyContent: 'space-between', alignItems: 'baseline', fontSize: size.label, color: isHi ? C.lime : C.text, fontWeight: isHi ? 600 : 400 },
          h('div', { maxWidth: '74%' }, `${r.rank ?? i + 1}. ${label}`),
          h('div', { fontSize: size.value, fontWeight: 600 }, r.display ?? formatValue(metric, r[metric]))),
        h('div', { height: 14, width: '100%', background: C.track, borderRadius: 7 },
          h('div', { height: 14, width: `${(pct * 100).toFixed(1)}%`, background: isHi ? C.lime : C.bar, borderRadius: 7 })));
    }));
}

// ---- Pack chart forms beyond ranked bars (services/pack_charts.py picks one per idea) ----

const chartHeight = (size) => Math.round(size.height * (size.height > size.width ? 0.44 : 0.34));

// A trend: one series over time (seasons, overs...). Points are labelled where they fit.
function lineBody(size, data) {
  const pts = (data.points || []).filter((p) => typeof p.y === 'number');
  const width = size.width - 120;
  const height = chartHeight(size);
  const pad = 16;
  const ys = pts.map((p) => p.y);
  const lo = Math.min(...ys, 0 <= Math.min(...ys) ? Math.min(...ys) : 0);
  const hi = Math.max(...ys);
  const span = hi - lo || 1;
  const x = (i) => pad + (i / Math.max(1, pts.length - 1)) * (width - 2 * pad);
  const y = (v) => pad + (1 - (v - lo) / span) * (height - 2 * pad);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.y).toFixed(1)}`).join(' ');
  const children = [
    { type: 'rect', props: { x: 0, y: 0, width, height, fill: C.surface } },
    { type: 'path', props: { d, fill: 'none', stroke: C.lime, strokeWidth: 6 } },
    ...pts.map((p, i) => ({ type: 'circle', props: { cx: x(i), cy: y(p.y), r: p.highlight ? 13 : 9, fill: p.highlight ? C.lime : C.text } })),
  ];
  if (lo < 0 && hi > 0) children.splice(1, 0, { type: 'line', props: { x1: 0, y1: y(0), x2: width, y2: y(0), stroke: 'rgba(255,255,255,0.25)', strokeDasharray: '10 10', strokeWidth: 3 } });
  // Labels under the chart: every point if they fit, else first, last and the highlighted one.
  const room = Math.floor(width / (size.small * 3.2));
  const show = pts.length <= room ? pts.map((_, i) => i) : [0, pts.length - 1, pts.findIndex((p) => p.highlight)].filter((i, k, a) => i >= 0 && a.indexOf(i) === k);
  const last = pts[pts.length - 1];
  return h('div', { flexDirection: 'column', marginTop: 30, gap: 14 },
    h('div', { justifyContent: 'space-between', fontSize: size.small, color: C.mid },
      h('div', {}, [data.metric_label || metricLabel(data.metric), ...chipsFor(data)].join(' · ')),
      last ? h('div', { color: C.lime, fontWeight: 600 }, `${last.x}: ${last.display ?? formatValue(data.metric, last.y)}`) : null),
    { type: 'svg', props: { width, height, viewBox: `0 0 ${width} ${height}`, children } },
    h('div', { position: 'relative', height: size.small + 8, width },
      show.map((i) => h('div', { position: 'absolute', left: Math.max(0, Math.min(width - size.small * 3, x(i) - size.small * 1.5)), fontSize: size.small, color: pts[i].highlight ? C.lime : C.low }, String(pts[i].x)))));
}

// Two metrics across many rows: the subject in lime and named, the field in grey, medians dashed.
// Lines a headline wraps to at feed sizes (about 34 display characters a line), for layouts that
// give the room of a fourth headline line back from the chart.
function headlineLines(text, perLine = 34) {
  let lines = 1, len = 0;
  for (const word of String(text || '').split(/\s+/).filter(Boolean)) {
    if (len && len + 1 + word.length > perLine) { lines += 1; len = word.length; } else len += (len ? 1 : 0) + word.length;
  }
  return lines;
}

function scatterBody(size, data) {
  const pts = (data.points || []).filter((p) => typeof p.x === 'number' && typeof p.y === 'number');
  const width = size.width - 120;
  // The key under the chart (rows that beat the subject, two to a line) takes its room from the chart.
  const keyLines = Math.ceil(pts.filter((p) => p.mark).length / 2);
  const height = chartHeight(size) - keyLines * (size.small + 10) - (data.conditions ? size.small + 10 : 0)
    - (data.key_caption ? size.small + 10 : 0)
    - Math.max(0, headlineLines(data.title) - 3) * Math.round((size.headline - 8) * 1.08)
    - (pts.some((p) => p.highlight) ? size.small + 14 : 0) + (size.height > size.width ? 30 : 100);
  const pad = 22;
  const ext = (vals) => { const a = Math.min(...vals); const b = Math.max(...vals); const m = (b - a) * 0.06 || 1; return [a - m, b + m]; };
  const [x0, x1] = ext(pts.map((p) => p.x));
  const [y0, y1] = ext(pts.map((p) => p.y));
  const sx = (v) => pad + ((v - x0) / (x1 - x0)) * (width - 2 * pad);
  const sy = (v) => pad + (1 - (v - y0) / (y1 - y0)) * (height - 2 * pad);
  const median = (vals) => { const a = [...vals].sort((m, n) => m - n); return a[Math.floor(a.length / 2)]; };
  const mx = median(pts.map((p) => p.x));
  const my = median(pts.map((p) => p.y));
  const subject = pts.filter((p) => p.highlight);
  // Extra metrics the headline also compares on (content_ideas `also`): in the subject line and the key.
  const alsoMetrics = data.also_metrics || [];
  const alsoText = (m, i, p) => {
    const label = (data.also_labels?.[i] || m).toLowerCase();
    return `${formatValue(m, p.also?.[i])} ${/%$/.test(label) && /percentage/.test(m) ? label.replace(/\s*%$/, '') : label}`;
  };
  // Rows that beat the subject on both axes (content_ideas._scatter_form): numbered white dots, keyed below.
  const marked = pts.filter((p) => p.mark).sort((a, b) => a.mark - b.mark);
  const many = pts.length > 80;
  const children = [
    { type: 'rect', props: { x: 0, y: 0, width, height, fill: C.surface } },
    { type: 'line', props: { x1: sx(mx), y1: 0, x2: sx(mx), y2: height, stroke: 'rgba(255,255,255,0.18)', strokeDasharray: '10 10', strokeWidth: 3 } },
    { type: 'line', props: { x1: 0, y1: sy(my), x2: width, y2: sy(my), stroke: 'rgba(255,255,255,0.18)', strokeDasharray: '10 10', strokeWidth: 3 } },
    ...pts.filter((p) => !p.highlight && !p.mark).map((p) => ({ type: 'circle', props: { cx: sx(p.x), cy: sy(p.y), r: many ? 7 : 10, fill: C.bar } })),
    ...marked.map((p) => ({ type: 'circle', props: { cx: sx(p.x), cy: sy(p.y), r: 19, fill: C.text, stroke: C.bg, strokeWidth: 3 } })),
    ...subject.map((p) => ({ type: 'circle', props: { cx: sx(p.x), cy: sy(p.y), r: 16, fill: C.lime, stroke: C.bg, strokeWidth: 4 } })),
  ];
  const numbers = marked.map((p) => h('div', {
    position: 'absolute', left: sx(p.x) - 19, top: sy(p.y) - 19, width: 38, height: 38, justifyContent: 'center',
    alignItems: 'center', fontSize: 26, fontWeight: 600, color: C.bg }, String(p.mark)));
  const xl = data.x_label || metricLabel(data.x_metric);
  const yl = data.y_label || metricLabel(data.y_metric);
  // Surnames, keeping particles: "AB de Villiers" -> "de Villiers".
  const surname = (n) => { const w = n.split(' '); const i = w.length >= 3 && /^(de|du|van|von|der|ul|al)$/i.test(w[w.length - 2]) ? w.length - 2 : w.length - 1; return w.slice(i).join(' '); };
  const short = (label) => String(label).split(' & ').map(surname).join(' & ');
  return h('div', { flexDirection: 'column', marginTop: 20, gap: 10 },
    data.conditions ? h('div', { fontSize: size.small, color: C.mid }, data.conditions) : null,
    h('div', { justifyContent: 'space-between', fontSize: size.small, color: C.mid },
      h('div', {}, `↑ ${yl}`), h('div', {}, `${pts.length} ${data.unit || 'players'} · dashes = median`)),
    h('div', { position: 'relative', width, height },
      { type: 'svg', props: { width, height, viewBox: `0 0 ${width} ${height}`, children } }, numbers),
    h('div', { justifyContent: 'space-between', fontSize: size.small, color: C.mid },
      h('div', {}, `${formatValue(data.x_metric, x0)}`), h('div', {}, `${xl} →`), h('div', {}, `${formatValue(data.x_metric, x1)}`)),
    subject.map((p) => h('div', { fontSize: size.small + 4, color: C.lime, fontWeight: 600 },
      `${p.label}: ${[`${formatValue(data.y_metric, p.y)} ${yl.toLowerCase()}`, `${formatValue(data.x_metric, p.x)} ${xl.toLowerCase()}`,
        ...alsoMetrics.map((m, i) => alsoText(m, i, p))].join(', ')}`)),
    data.key_caption && marked.length ? h('div', { fontSize: size.small, color: C.mid }, data.key_caption) : null,
    marked.length ? h('div', { flexWrap: 'wrap', columnGap: 24, rowGap: 4, fontSize: size.small, color: C.text },
      marked.map((p) => h('div', { width: '48%' }, `${p.mark}. ${short(p.label)} ${[formatValue(data.y_metric, p.y), formatValue(data.x_metric, p.x),
        ...alsoMetrics.map((m, i) => formatValue(m, p.also?.[i]))].join(' · ')}`))) : null);
}

// One number: the headline value, its rank, and the next few for context.
function statBody(size, data) {
  const runners = (data.context || []).slice(0, 3);
  return h('div', { flexDirection: 'column', marginTop: 40, gap: 18 },
    h('div', { fontSize: size.small, color: C.mid, letterSpacing: 2 }, (data.metric_label || metricLabel(data.metric)).toUpperCase()),
    h('div', { alignItems: 'baseline', gap: 24 },
      h('div', { fontFamily: DISPLAY, fontWeight: 700, fontSize: Math.round(size.headline * 2.6), color: C.lime, lineHeight: 1 }, data.value_display || ''),
      h('div', { fontSize: size.label, color: C.text, fontWeight: 600 }, data.subject || '')),
    data.rank_text ? h('div', { fontSize: size.label, color: C.mid }, data.rank_text) : null,
    runners.length ? h('div', { flexDirection: 'column', gap: 10, marginTop: 20, paddingTop: 20, borderTop: `2px solid ${C.track}` },
      h('div', { fontSize: size.small, color: C.low }, 'Next on the list'),
      runners.map((r) => h('div', { justifyContent: 'space-between', fontSize: size.small + 4, color: C.mid },
        h('div', {}, `${r.rank}. ${r.label}`), h('div', { fontWeight: 600 }, r.display)))) : null,
    ...chipsFor(data).length ? [h('div', { fontSize: size.small, color: C.low, marginTop: 10 }, chipsFor(data).join(' · '))] : []);
}

// Bars either side of zero for signed metrics (Impact, RAA, WPA): below-average reads as below.
function divergingBody(size, data) {
  const metric = data.metric;
  const rows = (data.rows || []).filter((r) => typeof r[metric] === 'number').slice(0, size.rows);
  const max = Math.max(...rows.map((r) => Math.abs(r[metric])), 1e-9);
  return h('div', { flexDirection: 'column', marginTop: 34, gap: size.gap },
    h('div', { color: C.mid, fontSize: size.small }, [data.metric_label || metricLabel(metric), ...chipsFor(data)].join(' · ')),
    rows.map((r, i) => {
      const v = r[metric];
      const w = Math.max(1, (Math.abs(v) / max) * 50);
      const isHi = r.highlight === true;
      return h('div', { flexDirection: 'column', gap: 6 },
        h('div', { justifyContent: 'space-between', alignItems: 'baseline', fontSize: size.label, color: isHi ? C.lime : C.text, fontWeight: isHi ? 600 : 400 },
          h('div', { maxWidth: '74%' }, `${r.rank ?? i + 1}. ${r.label}`),
          h('div', { fontSize: size.value, fontWeight: 600 }, r.display ?? formatValue(metric, v))),
        h('div', { height: 14, width: '100%', background: C.track, borderRadius: 7, position: 'relative' },
          h('div', { position: 'absolute', left: '50%', top: -4, width: 3, height: 22, background: 'rgba(255,255,255,0.35)' }),
          h('div', { position: 'absolute', top: 0, height: 14, borderRadius: 7, left: v >= 0 ? '50%' : `${50 - w}%`, width: `${w}%`,
            background: isHi ? C.lime : (v >= 0 ? '#3987e5' : '#e66767') })));
    }));
}

// Two splits per entity (v pace / v spin, 1st / 2nd innings): two dots on one shared scale.
function dumbbellBody(size, data) {
  const rows = (data.rows || []).filter((r) => typeof r.a === 'number' && typeof r.b === 'number').slice(0, size.rows);
  const vals = rows.flatMap((r) => [r.a, r.b]);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const span = hi - lo || 1;
  const pos = (v) => `${(4 + ((v - lo) / span) * 92).toFixed(1)}%`;
  const [la, lb] = data.series || ['A', 'B'];
  const ca = '#3987e5';
  const cb = '#d95926';
  const dot = (left, color, big) => h('div', { position: 'absolute', top: big ? -7 : -5, left, width: big ? 28 : 24, height: big ? 28 : 24, marginLeft: big ? -14 : -12, borderRadius: 14, background: color, border: `4px solid ${C.bg}` });
  return h('div', { flexDirection: 'column', marginTop: 34, gap: size.gap },
    h('div', { gap: 28, fontSize: size.small, color: C.mid, alignItems: 'center' },
      h('div', {}, data.metric_label || metricLabel(data.metric)),
      h('div', { alignItems: 'center', gap: 8 }, h('div', { width: 20, height: 20, borderRadius: 10, background: ca }), la),
      h('div', { alignItems: 'center', gap: 8 }, h('div', { width: 20, height: 20, borderRadius: 10, background: cb }), lb)),
    rows.map((r) => {
      const isHi = r.highlight === true;
      const left = Math.min(r.a, r.b);
      const right = Math.max(r.a, r.b);
      return h('div', { flexDirection: 'column', gap: 10 },
        h('div', { justifyContent: 'space-between', fontSize: size.label, color: isHi ? C.lime : C.text, fontWeight: isHi ? 600 : 400 },
          h('div', { maxWidth: '58%' }, r.label),
          h('div', { fontSize: size.small + 4, color: C.mid, gap: 14 },
            h('div', { color: ca }, formatValue(data.metric, r.a)), h('div', { color: cb }, formatValue(data.metric, r.b)))),
        h('div', { height: 14, width: '100%', position: 'relative' },
          h('div', { position: 'absolute', top: 5, left: 0, right: 0, height: 4, background: C.track }),
          h('div', { position: 'absolute', top: 3, height: 8, left: pos(left), width: `${(((right - left) / span) * 92).toFixed(1)}%`, background: 'rgba(255,255,255,0.35)' }),
          dot(pos(r.a), ca, isHi), dot(pos(r.b), cb, isHi)));
    }));
}

// A split of a whole per entity (runs by phase, dismissals by type) as 100% bars.
const STACK_COLORS = ['#3987e5', '#199e70', '#d95926', '#c98500', '#9085e9', '#d55181'];
function stackedBody(size, data) {
  const parts = data.parts || [];
  const rows = (data.rows || []).slice(0, size.rows);
  return h('div', { flexDirection: 'column', marginTop: 34, gap: size.gap },
    h('div', { gap: 22, flexWrap: 'wrap', fontSize: size.small, color: C.mid, alignItems: 'center' },
      parts.map((p, i) => h('div', { alignItems: 'center', gap: 8 }, h('div', { width: 20, height: 20, borderRadius: 4, background: STACK_COLORS[i % STACK_COLORS.length] }), p))),
    rows.map((r) => {
      const total = parts.reduce((t, p) => t + (r.values?.[p] || 0), 0) || 1;
      const isHi = r.highlight === true;
      return h('div', { flexDirection: 'column', gap: 8 },
        h('div', { justifyContent: 'space-between', fontSize: size.label, color: isHi ? C.lime : C.text, fontWeight: isHi ? 600 : 400 },
          h('div', { maxWidth: '70%' }, r.label), h('div', { fontSize: size.small + 4, color: C.mid }, r.display || '')),
        h('div', { height: 34, width: '100%', borderRadius: 8, overflow: 'hidden', gap: 3 },
          parts.map((p, i) => {
            const share = (r.values?.[p] || 0) / total;
            return share > 0 ? h('div', { width: `${(share * 100).toFixed(1)}%`, height: 34, background: STACK_COLORS[i % STACK_COLORS.length],
              alignItems: 'center', paddingLeft: 8, fontSize: size.small, color: C.bg, fontWeight: 600 }, share >= 0.14 ? `${Math.round(share * 100)}%` : '') : null;
          })));
    }));
}

// Runs by wagon-wheel zone: eight wedges, length = share of runs (area-honest), subject's biggest zone in lime.
function fieldBody(size, data) {
  const zones = data.zones || [];
  const total = zones.reduce((t, z) => t + (z.value || 0), 0) || 1;
  const maxShare = Math.max(...zones.map((z) => (z.value || 0) / total), 1e-9);
  const S = Math.min(size.width - 120, chartHeight(size) + 160);
  const cx = S / 2;
  const cy = S / 2;
  const R = S * 0.36;
  const pt = (deg, r) => { const a = ((deg - 90) * Math.PI) / 180; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const order = [8, 1, 2, 3, 4, 5, 6, 7];
  const top = [...zones].sort((a, b) => (b.value || 0) - (a.value || 0))[0];
  const children = [{ type: 'circle', props: { cx, cy, r: R, fill: C.surface, stroke: 'rgba(255,255,255,0.18)', strokeWidth: 3 } }];
  const labels = [];
  order.forEach((zn, i) => {
    const z = zones.find((q) => q.zone === zn);
    if (!z || !z.value) return;
    const share = z.value / total;
    const r = R * 0.95 * Math.sqrt(share / maxShare);
    const [x0, y0] = pt(i * 45 - 21, r);
    const [x1, y1] = pt(i * 45 + 21, r);
    children.push({ type: 'path', props: { d: `M${cx},${cy} L${x0.toFixed(1)},${y0.toFixed(1)} A${r.toFixed(1)},${r.toFixed(1)} 0 0 1 ${x1.toFixed(1)},${y1.toFixed(1)} Z`, fill: z === top ? C.lime : '#3987e5', fillOpacity: z === top ? 1 : 0.8 } });
    const [lx, ly] = pt(i * 45, R + size.small * 1.6);
    labels.push(h('div', { position: 'absolute', left: lx - 90, top: ly - size.small, width: 180, flexDirection: 'column', alignItems: 'center', fontSize: size.small, color: z === top ? C.lime : C.mid },
      h('div', {}, z.label), h('div', { fontWeight: 600, color: z === top ? C.lime : C.text }, `${Math.round(share * 100)}%`)));
  });
  children.push({ type: 'rect', props: { x: cx - 6, y: cy - 16, width: 12, height: 32, rx: 3, fill: C.text } });
  return h('div', { flexDirection: 'column', marginTop: 24, gap: 10, alignItems: 'center' },
    h('div', { color: C.mid, fontSize: size.small, alignSelf: 'flex-start' }, [`Share of ${(data.metric_label || 'runs').toLowerCase()} by zone`, ...chipsFor(data)].join(' · ')),
    h('div', { position: 'relative', width: S, height: S },
      { type: 'svg', props: { width: S, height: S, viewBox: `0 0 ${S} ${S}`, children } },
      labels));
}

function winProbBody(size, data) {
  const wp = data.primer?.win_probability || {};
  const points = wp.points || [];
  const width = size.width - 120;
  const height = Math.round(size.height * (size.height > size.width ? 0.44 : 0.36));
  const n = Math.max(1, points.length - 1);
  const x = (i) => (i / n) * width;
  const y = (p) => height - p * height;
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join(' ');
  const area = `${line} L${width},${height} L0,${height} Z`;
  const teams = data.teams || [];
  const first = wp.team;
  const second = (data.scores || []).find((s) => s.team !== first)?.team || teams.find((t) => t.name !== first)?.name;
  const accent = (name, fb) => teams.find((t) => t.name === name)?.accent || fb;
  const children = [
    { type: 'rect', props: { x: 0, y: 0, width, height, fill: C.surface } },
    { type: 'line', props: { x1: 0, y1: height / 2, x2: width, y2: height / 2, stroke: 'rgba(255,255,255,0.22)', strokeDasharray: '10 10', strokeWidth: 3 } },
    { type: 'path', props: { d: area, fill: accent(first, C.lime), fillOpacity: 0.18 } },
    { type: 'path', props: { d: line, fill: 'none', stroke: accent(first, C.lime), strokeWidth: 6 } },
  ];
  if (wp.innings_break) children.push({ type: 'line', props: { x1: x(wp.innings_break), y1: 0, x2: x(wp.innings_break), y2: height, stroke: 'rgba(255,255,255,0.35)', strokeWidth: 3 } });
  (wp.wickets || []).forEach((i) => children.push({ type: 'circle', props: { cx: x(i), cy: y(points[i] ?? 0.5), r: 9, fill: C.red } }));
  const scores = (data.scores || []).map((s) => h('div', { justifyContent: 'space-between', fontSize: size.label, color: C.text },
    h('div', { color: accent(s.team, C.mid), fontWeight: 600 }, s.team),
    h('div', { fontWeight: 600 }, `${s.runs}/${s.wickets} (${s.overs})`)));
  return h('div', { flexDirection: 'column', marginTop: 30, gap: 16 },
    h('div', { justifyContent: 'space-between', fontSize: size.small, color: C.mid },
      h('div', {}, `${first || ''} 100%`), h('div', {}, 'Win probability')),
    { type: 'svg', props: { width, height, viewBox: `0 0 ${width} ${height}`, children } },
    h('div', { justifyContent: 'space-between', fontSize: size.small, color: C.mid },
      h('div', {}, `${second || ''} 100%`),
      h('div', { alignItems: 'center', gap: 10, color: C.mid },
        h('div', { width: 18, height: 18, borderRadius: 9, background: C.red }), 'wicket')),
    h('div', { flexDirection: 'column', gap: 8, marginTop: 10 }, scores));
}

// "Every ODI innings with 3+ centuries": a header per innings (teams, date) with its individual
// performances comma-separated beneath. Tries normal sizes, then a compact set (still at the
// legibility minimums) so the whole list fits; only then does it cut to "+ N more".
function listLayout(size, data, compact) {
  const head = compact ? Math.max(MIN_FONT.label - 2, 32) : size.label;
  const detail = compact ? MIN_FONT.footer : size.small;
  const gap = compact ? 12 : 20;
  const headlineLines = Math.ceil(((data.title || '').length * size.headline * 0.36) / (size.width - 120));
  let budget = size.height - 120 - 60 - headlineLines * size.headline * 1.1 - 34 - size.small * 1.6 - 60;
  const perLine = (size.width - 120 - 18) / (detail * 0.5);
  const shown = [];
  for (const row of data.rows || []) {
    const text = (row.details || []).join(', ');
    const cost = head * 1.3 + Math.ceil(text.length / perLine) * detail * 1.35 + gap;
    if (cost > budget) break;
    budget -= cost;
    shown.push({ ...row, text });
  }
  return { head, detail, gap, shown };
}

function listBody(size, data) {
  let layout = listLayout(size, data, false);
  if (layout.shown.length < (data.rows || []).length) layout = listLayout(size, data, true);
  const { head, detail, gap } = layout;
  const shown = layout.shown.length ? layout.shown : [{ ...(data.rows || [])[0], text: ((data.rows || [])[0]?.details || []).join(', ') }];
  const more = (data.rows || []).length - shown.length;
  return h('div', { flexDirection: 'column', marginTop: 30, gap },
    h('div', { color: C.mid, fontSize: size.small }, [data.subtitle, ...chipsFor(data).slice(1)].filter(Boolean).join(' · ')),
    shown.map((row, i) => h('div', { flexDirection: 'column', gap: 2 },
      h('div', { justifyContent: 'space-between', alignItems: 'baseline', fontSize: head, color: i === 0 ? C.lime : C.text, fontWeight: 600 },
        h('div', { maxWidth: '70%' }, row.label), h('div', { fontSize: detail, color: C.low, fontWeight: 400 }, row.sub || '')),
      h('div', { fontSize: detail, color: C.mid, lineHeight: 1.3 }, row.text))),
    more > 0 ? h('div', { fontSize: detail, color: C.low }, `+ ${more} more at hindsightcricket.com`) : null);
}

function recapBody(size, data) {
  const bullets = (data.recap?.bullets || []).slice(0, size.rows > 6 ? 4 : 3);
  return h('div', { flexDirection: 'column', marginTop: 34, gap: 22 },
    bullets.map((b) => h('div', { gap: 16, fontSize: size.label, color: C.mid, lineHeight: 1.3 },
      h('div', { width: 12, height: 12, borderRadius: 6, background: C.lime, marginTop: size.label * 0.45, flexShrink: 0 }),
      h('div', { flex: 1 }, b))));
}

const asOf = (snap) => {
  const d = snap.created_at ? new Date(snap.created_at) : new Date();
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

// Filter chips minus noise; "→ today" becomes the snapshot's date (an image is frozen in time).
function chipsFor(data) {
  return (data.filter_chips || [])
    .filter((c) => !/^All formats$/.test(c))
    .map((c) => c.replace('→ today', '→ now'))
    .slice(0, 3);
}

// ---- Preview story cards (services/preview_cards/snapshot.py) ----------------------------------

// How batters get out: a donut of up to four kinds, each with its usual share beside it.
function donutBody(size, data) {
  const slices = (data.slices || []).slice(0, 4);
  const total = slices.reduce((t, s) => t + (s.value || 0), 0) || 1;
  const S = Math.min(chartHeight(size), 460);
  const cx = S / 2; const cy = S / 2; const R = S * 0.46; const r0 = S * 0.28;
  let a = -Math.PI / 2;
  const children = slices.map((s, i) => {
    const a1 = a + (2 * Math.PI * (s.value || 0)) / total;
    const big = a1 - a > Math.PI ? 1 : 0;
    const d = `M${cx + R * Math.cos(a)},${cy + R * Math.sin(a)} A${R},${R} 0 ${big} 1 ${cx + R * Math.cos(a1)},${cy + R * Math.sin(a1)} `
      + `L${cx + r0 * Math.cos(a1)},${cy + r0 * Math.sin(a1)} A${r0},${r0} 0 ${big} 0 ${cx + r0 * Math.cos(a)},${cy + r0 * Math.sin(a)} Z`;
    a = a1;
    return { type: 'path', props: { d, fill: STACK_COLORS[i % STACK_COLORS.length], stroke: C.bg, strokeWidth: 4 } };
  });
  return h('div', { marginTop: 40, gap: 40, alignItems: 'center' },
    { type: 'svg', props: { width: S, height: S, viewBox: `0 0 ${S} ${S}`, children } },
    h('div', { flexDirection: 'column', gap: 26, flex: 1 },
      slices.map((s, i) => h('div', { flexDirection: 'column', gap: 4 },
        h('div', { alignItems: 'center', gap: 12, fontSize: size.label, color: C.text },
          h('div', { width: 22, height: 22, borderRadius: 5, background: STACK_COLORS[i % STACK_COLORS.length] }), s.label),
        h('div', { fontSize: size.small, color: C.mid }, `${s.pct}% · usually ${s.usual}%`)))));
}

// Form strips: each batter's last ten scores as bars, 50+ in lime.
function stripsBody(size, data) {
  const strips = (data.strips || []).slice(0, 6);
  const barH = Math.max(60, Math.floor((chartHeight(size) - strips.length * 12) / Math.max(1, strips.length)) - size.small);
  return h('div', { flexDirection: 'column', marginTop: 34, gap: 14 },
    strips.map((s) => h('div', { alignItems: 'flex-end', gap: 20 },
      h('div', { width: 300, fontSize: size.small + 2, color: C.text, flexShrink: 0 }, s.name),
      h('div', { flex: 1, height: barH, alignItems: 'flex-end', gap: 8 },
        (s.runs || []).slice(-10).map((r) => h('div', { flex: 1, height: Math.max(4, Math.min(barH, (barH * r) / 100)),
          borderRadius: 4, background: r >= 50 ? C.lime : C.bar }))))),
    h('div', { fontSize: size.small, color: C.mid, marginTop: 6 }, 'Last 10 innings, oldest first · lime: 50 or more'));
}

// Where a bowler pitches it: share of balls by line and length; lime marks 1.5x an average pace bowler.
const LINE_SHORT = { DOWN_LEG: 'Leg', ON_THE_STUMPS: 'Stumps', OUTSIDE_OFFSTUMP: 'Off', WIDE_OUTSIDE_OFFSTUMP: 'Wide' };
const LENGTH_SHORT = { FULL_TOSS: 'Full toss', YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };
function gridBody(size, data) {
  const lines = data.lines || []; const lengths = data.lengths || [];
  const max = Math.max(...(data.cells || []).map((c) => c.pct), 1);
  const cell = (l, len) => (data.cells || []).find((c) => c.line === l && c.length === len) || { pct: 0, usual: 0 };
  const rowH = Math.min(96, Math.floor((chartHeight(size) - 60) / Math.max(1, lengths.length)));
  return h('div', { flexDirection: 'column', marginTop: 30, gap: 8 },
    h('div', { gap: 8, paddingLeft: 250 }, lines.map((l) => h('div', { flex: 1, justifyContent: 'center', fontSize: size.small, color: C.mid }, LINE_SHORT[l] || l))),
    lengths.map((len) => h('div', { gap: 8, alignItems: 'center' },
      h('div', { width: 242, fontSize: size.small + 2, color: C.text, justifyContent: 'flex-end', paddingRight: 8 }, LENGTH_SHORT[len] || len),
      lines.map((l) => {
        const c = cell(l, len);
        const standout = c.usual > 0 && c.pct >= 2 && c.pct / c.usual >= 1.5;
        return h('div', { flex: 1, height: rowH, borderRadius: 10, background: `rgba(57,135,229,${(0.08 + (0.8 * c.pct) / max).toFixed(2)})`,
          alignItems: 'center', justifyContent: 'center', fontSize: size.small, fontWeight: 600,
          color: C.text, border: standout ? `4px solid ${C.lime}` : '4px solid transparent' }, c.pct >= 1 ? `${Math.round(c.pct)}%` : '');
      }))),
    h('div', { fontSize: size.small, color: C.mid, marginTop: 6 }, 'Share of balls · lime border: 1.5× an average pace bowler'));
}

const CARD_BODIES = {
  line: (s, d) => lineBody(s, d), scatter: (s, d) => scatterBody(s, d), stat: (s, d) => statBody(s, d),
  diverging: (s, d) => divergingBody(s, d), dumbbell: (s, d) => dumbbellBody(s, d), stacked: (s, d) => stackedBody(s, d),
  field: (s, d) => fieldBody(s, d), list: (s, d) => listBody(s, d), bars: (s, d) => barsBody(s, d),
  win_prob: (s, d) => winProbBody(s, d), donut: donutBody, strips: stripsBody, grid: gridBody,
};

// Footer text next to "Data as of": a ranking's filters, how complete its tagged data is (shot control,
// shot type...) and any shot-family definition (services/content_ideas._footnote), else the source.
const sourceLine = (snap, data) => `Data as of ${asOf(snap)} · ${data.footnote || data.source || 'ball-by-ball'}`;

export function renderSnapshot(snap, sizeName = 'portrait') {
  const size = SIZES[sizeName] || SIZES.portrait;
  const data = snap.data || {};
  if (snap.kind === 'win_prob') {
    const kicker = [data.competition, data.date].filter(Boolean).join(' · ');
    return frame(size, kicker, snap.title?.startsWith('Win probability') ? data.result : snap.title, winProbBody(size, data),
      'Win probability by ball · Hindsight');
  }
  if (snap.kind === 'preview_card') {
    const body = (CARD_BODIES[data.layout] || CARD_BODIES.list)(size, data);
    return frame(size, data.kicker || '', data.title || snap.title, body, `${data.source || ''} · Data as of ${asOf(snap)}`);
  }
  if (snap.kind === 'recap') {
    const kicker = [data.competition, data.date].filter(Boolean).join(' · ');
    return frame(size, kicker, data.recap?.headline || snap.title, recapBody(size, data), `${data.result || ''} · Impact & WPA by Hindsight`);
  }
  if (data.layout === 'list') {
    return frame(size, data.kicker || '', data.title || snap.title, listBody(size, data), sourceLine(snap, data));
  }
  const body = { line: lineBody, scatter: scatterBody, stat: statBody, diverging: divergingBody, dumbbell: dumbbellBody, stacked: stackedBody, field: fieldBody }[data.layout];
  if (body) {
    const fmtChip = (data.filter_chips || []).find((c) => /^(T20I?|ODI|Test|T20s?)$/i.test(c));
    const kick = data.kicker || [fmtChip, ...(data.group_by || []).map((g) => g.replace(/_/g, ' ') + (g.endsWith('s') ? '' : 's'))].filter(Boolean).join(' · ');
    return frame(size, kick, data.title || snap.title, body(size, data), sourceLine(snap, data));
  }
  // "ODI · partnerships": the format chip, then what each bar is.
  const fmt = (data.filter_chips || []).find((c) => /^(T20I?|ODI|Test|T20s?)$/i.test(c));
  const kicker = data.kicker || [fmt, ...(data.group_by || []).map((g) => g.replace(/_/g, ' ') + (g.endsWith('s') ? '' : 's'))]
    .filter(Boolean).join(' · ');
  return frame(size, kicker, data.title || snap.title, barsBody(size, data), sourceLine(snap, data));
}

export default async function handler(req, res) {
  const url = new URL(req.url, 'http://local');
  const id = (url.searchParams.get('id') || '').replace(/\.png$/, '');
  const sizeName = url.searchParams.get('size') || 'portrait';
  const snap = /^[A-Za-z0-9]{6,16}$/.test(id) ? await getJSON(`/snapshots/${id}`, 15000) : null;
  if (!snap) {
    res.statusCode = 404;
    res.end('Not found');
    return;
  }
  const size = SIZES[sizeName] || SIZES.portrait;
  const image = new ImageResponse(renderSnapshot(snap, sizeName), { width: size.width, height: size.height, fonts: FONTS });
  const png = Buffer.from(await image.arrayBuffer());
  res.setHeader('Content-Type', 'image/png');
  res.setHeader('Cache-Control', 'public, max-age=86400, s-maxage=31536000, immutable');
  if (url.searchParams.get('download')) res.setHeader('Content-Disposition', `attachment; filename="hindsight-${id}.png"`);
  res.end(png);
}
