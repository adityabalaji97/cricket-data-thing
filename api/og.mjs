// GET /_og?path=/scorecard/123   (or path=/player?name=V%20Kohli, etc.)
//
// 1200x630 PNG preview card for a Hindsight page: what WhatsApp / X / Slack / iMessage show when
// a link is shared. The previous site-wide og:image was an SVG, which those apps do not render,
// so shared links had no image at all. Built with @vercel/og (Satori + resvg) in the Node runtime.
import { ImageResponse } from '@vercel/og';
import { summarize } from './_lib/share.mjs';

const C = { bg: '#0a0c11', surface: '#14171e', text: '#f3f4f6', mid: '#c3c8d0', low: '#9aa1ac', lime: '#b6f24a', red: '#e5484d', border: 'rgba(255,255,255,0.12)' };

// Satori takes React-element-shaped objects; this keeps the file dependency- and JSX-free.
const h = (type, style, ...children) => ({
  type,
  props: { style: { display: 'flex', ...style }, children: children.flat().filter((c) => c !== null && c !== undefined && c !== false) },
});

const signed = (v, d = 1) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}`;

function frame(kicker, headline, body) {
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '52px 60px', fontFamily: 'sans-serif' },
    h('div', { justifyContent: 'space-between', alignItems: 'center' },
      h('div', { color: C.lime, fontSize: 26, letterSpacing: 4, fontWeight: 700 }, 'HINDSIGHT'),
      h('div', { color: C.low, fontSize: 24 }, kicker || '')),
    h('div', { fontSize: headline && headline.length > 42 ? 50 : 60, fontWeight: 700, marginTop: 34, lineHeight: 1.1 }, headline || ''),
    body,
    h('div', { marginTop: 'auto', color: C.low, fontSize: 22 }, 'Ball-by-ball T20 analytics · Impact · win probability'));
}

function sparkline(points, width, height) {
  if (!points || points.length < 2) return null;
  const n = points.length - 1;
  const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${((i / n) * width).toFixed(1)},${(height - p * height).toFixed(1)}`).join(' ');
  return {
    type: 'svg',
    props: {
      width, height, viewBox: `0 0 ${width} ${height}`,
      children: [
        { type: 'line', props: { x1: 0, y1: height / 2, x2: width, y2: height / 2, stroke: 'rgba(255,255,255,0.18)', strokeDasharray: '6 6', strokeWidth: 2 } },
        { type: 'path', props: { d, fill: 'none', stroke: C.lime, strokeWidth: 4 } },
      ],
    },
  };
}

function scorecardCard(card) {
  const scores = h('div', { flexDirection: 'column', marginTop: 28, gap: 10 },
    card.lines.map((line) => h('div', { alignItems: 'baseline', gap: 18, fontSize: 40 },
      h('div', { width: 160, color: C.mid, fontWeight: 700 }, line.team),
      h('div', { fontWeight: 700 }, line.score),
      h('div', { color: C.low, fontSize: 28 }, `(${line.overs})`))));
  const impact = card.impact
    ? h('div', { flexDirection: 'column', marginLeft: 'auto', alignItems: 'flex-end', gap: 12 },
      h('div', { color: C.low, fontSize: 22 }, 'WIN PROBABILITY · IMPACT'),
      sparkline(card.wp?.points, 420, 120),
      h('div', { gap: 22, fontSize: 30, fontWeight: 700 },
        card.impact.map((i) => h('div', { color: i.value >= 0 ? C.lime : C.red }, `${i.team} ${signed(i.value)}`))))
    : null;
  return frame(card.kicker, card.headline, h('div', { alignItems: 'flex-end' }, scores, impact));
}

function playerCard(card) {
  const stats = h('div', { gap: 22, marginTop: 30 },
    (card.stats || []).map((s) => h('div', { flexDirection: 'column', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 18, padding: '18px 24px', minWidth: 230 },
      h('div', { color: C.low, fontSize: 22 }, s.label),
      h('div', { fontSize: 46, fontWeight: 700, color: String(s.value).startsWith('−') ? C.red : C.lime }, s.value))));
  const bars = card.bars?.length
    ? (() => {
      const max = Math.max(1, ...card.bars.map((b) => Math.abs(b.value)));
      return h('div', { alignItems: 'center', gap: 10, marginTop: 26, height: 110 },
        card.bars.map((b) => h('div', { flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 110 },
          h('div', { width: 44, height: Math.max(4, (Math.abs(b.value) / max) * 80), background: b.value >= 0 ? C.lime : C.red, borderRadius: 6 }),
          h('div', { color: C.low, fontSize: 18, marginTop: 6 }, `'${b.label}`))));
    })()
    : null;
  return frame(card.kicker, card.headline, h('div', { flexDirection: 'column' }, stats, bars));
}

function textCard(card) {
  return frame(card?.kicker || 'T20 analytics', card?.headline || 'Every ball, in context', card?.sub
    ? h('div', { color: C.mid, fontSize: 32, marginTop: 18 }, card.sub)
    : null);
}

export default async function handler(req, res) {
  const url = new URL(req.url, 'http://local');
  const target = new URL(url.searchParams.get('path') || '/', 'http://local');
  let summary = null;
  try {
    summary = await summarize(target.pathname, target.search);
  } catch {
    summary = null;
  }
  const card = summary?.card;
  const element = summary?.kind === 'scorecard' ? scorecardCard(card)
    : summary?.kind === 'player' ? playerCard(card)
      : textCard(card);

  const image = new ImageResponse(element, { width: 1200, height: 630 });
  const png = Buffer.from(await image.arrayBuffer());
  res.setHeader('Content-Type', 'image/png');
  // Finished matches never change; players and pages change slowly.
  res.setHeader('Cache-Control', `public, max-age=3600, s-maxage=${summary?.kind === 'scorecard' ? 604800 : 86400}, stale-while-revalidate=86400`);
  res.end(png);
}
