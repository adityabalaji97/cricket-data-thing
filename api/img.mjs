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
      h('div', { color: C.low, fontSize: size.small, maxWidth: '62%' }, source || 'Hindsight · ball-by-ball cricket data'),
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
  const rows = (data.rows || []).filter((r) => typeof r[metric] === 'number').slice(0, maxRows);
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

export function renderSnapshot(snap, sizeName = 'portrait') {
  const size = SIZES[sizeName] || SIZES.portrait;
  const data = snap.data || {};
  if (snap.kind === 'win_prob') {
    const kicker = [data.competition, data.date].filter(Boolean).join(' · ');
    return frame(size, kicker, snap.title?.startsWith('Win probability') ? data.result : snap.title, winProbBody(size, data),
      'Win probability by ball · Hindsight');
  }
  if (snap.kind === 'recap') {
    const kicker = [data.competition, data.date].filter(Boolean).join(' · ');
    return frame(size, kicker, data.recap?.headline || snap.title, recapBody(size, data), `${data.result || ''} · Impact & WPA by Hindsight`);
  }
  if (data.layout === 'list') {
    return frame(size, data.kicker || '', data.title || snap.title, listBody(size, data), `Data as of ${asOf(snap)} · ${data.source || 'ball-by-ball'}`);
  }
  // "ODI · partnerships": the format chip, then what each bar is.
  const fmt = (data.filter_chips || []).find((c) => /^(T20I?|ODI|Test|T20s?)$/i.test(c));
  const kicker = data.kicker || [fmt, ...(data.group_by || []).map((g) => g.replace(/_/g, ' ') + (g.endsWith('s') ? '' : 's'))]
    .filter(Boolean).join(' · ');
  return frame(size, kicker, data.title || snap.title, barsBody(size, data), `Data as of ${asOf(snap)} · ${data.source || 'ball-by-ball'}`);
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
