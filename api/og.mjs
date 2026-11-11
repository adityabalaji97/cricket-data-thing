// GET /_og?path=/scorecard/123   (or path=/player?name=V%20Kohli, etc.)
//
// 1200x630 PNG preview card for a Hindsight page: what WhatsApp / X / Slack / iMessage show when
// a link is shared. The previous site-wide og:image was an SVG, which those apps do not render,
// so shared links had no image at all. Built with @vercel/og (Satori + resvg) in the Node runtime.
import { ImageResponse } from '@vercel/og';
import { readFileSync } from 'node:fs';
import { summarize } from './_lib/share.mjs';

// The site's typefaces (src/theme/hindsightDark.js; SIL OFL, api/_lib/fonts/OFL.txt): Barlow for text, Barlow Semi
// Condensed Bold for headlines, IBM Plex Mono for numbers and kickers. Satori's default font matched none of it.
const font = (name) => readFileSync(new URL(`./_lib/fonts/${name}`, import.meta.url));
const FONTS = [
  { name: 'Barlow', data: font('Barlow-Regular.ttf'), weight: 400, style: 'normal' },
  { name: 'Barlow', data: font('Barlow-SemiBold.ttf'), weight: 600, style: 'normal' },
  { name: 'Barlow Semi Condensed', data: font('BarlowSemiCondensed-Bold.ttf'), weight: 700, style: 'normal' },
  { name: 'IBM Plex Mono', data: font('IBMPlexMono-Regular.ttf'), weight: 400, style: 'normal' },
  { name: 'IBM Plex Mono', data: font('IBMPlexMono-Medium.ttf'), weight: 500, style: 'normal' },
];
const DISPLAY = 'Barlow Semi Condensed';
const MONO = 'IBM Plex Mono';

const C = { bg: '#0a0c11', surface: '#14171e', text: '#f3f4f6', mid: '#c3c8d0', low: '#9aa1ac', lime: '#b6f24a', red: '#e5484d', border: 'rgba(255,255,255,0.12)' };

// Satori takes React-element-shaped objects; this keeps the file dependency- and JSX-free.
const h = (type, style, ...children) => ({
  type,
  props: { style: { display: 'flex', ...style }, children: children.flat().filter((c) => c !== null && c !== undefined && c !== false) },
});

// The site's header: the brand, and the page's kicker in mono capitals (as the profile cards and the carousel set it).
const top = (kicker, size = 22) => h('div', { justifyContent: 'space-between', alignItems: 'center' },
  h('div', { color: C.lime, fontSize: size + 2, letterSpacing: 5, fontWeight: 600 }, 'HINDSIGHT'),
  h('div', { color: C.low, fontSize: size - 2, letterSpacing: 3, fontFamily: MONO }, String(kicker || '').toUpperCase()));

const signed = (v, d = 1) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}`;

function frame(kicker, headline, body) {
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '52px 60px', fontFamily: 'Barlow' },
    top(kicker, 24),
    h('div', { fontFamily: DISPLAY, fontSize: headline && headline.length > 42 ? 56 : 68, fontWeight: 700, marginTop: 34, lineHeight: 1.1 }, headline || ''),
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
      h('div', { width: 160, color: C.mid, fontWeight: 600 }, line.team),
      h('div', { fontFamily: MONO, fontWeight: 500 }, line.score),
      h('div', { color: C.low, fontSize: 26, fontFamily: MONO }, `(${line.overs})`))));
  const impact = card.impact
    ? h('div', { flexDirection: 'column', marginLeft: 'auto', alignItems: 'flex-end', gap: 12 },
      h('div', { color: C.lime, fontSize: 18, letterSpacing: 3, fontFamily: MONO }, 'WIN PROBABILITY · IMPACT'),
      sparkline(card.wp?.points, 420, 120),
      h('div', { gap: 22, fontSize: 28, fontFamily: MONO, fontWeight: 500 },
        card.impact.map((i) => h('div', { color: i.value >= 0 ? C.lime : C.red }, `${i.team} ${signed(i.value)}`))))
    : null;
  const story = card.story
    ? h('div', { color: C.mid, fontSize: 26, marginTop: 16, lineHeight: 1.3 }, card.story.length > 120 ? `${card.story.slice(0, 117)}...` : card.story)
    : null;
  return frame(card.kicker, card.headline, h('div', { flexDirection: 'column' }, story, h('div', { alignItems: 'flex-end' }, scores, impact)));
}

const ROLE = { bowl: { colour: '#5b8def', name: 'Bowling' }, bat: { colour: '#c4850f', name: 'Batting' } };

// The verdict screen as a link preview: the claim, wins added by season (bat and ball), the three best ranks.
function verdictCard(card) {
  const years = [...new Set(card.seasons.flatMap((s) => s.rows.map((r) => r.year)))].sort();
  const max = Math.max(0.5, ...card.seasons.flatMap((s) => s.rows.map((r) => Math.abs(r.wpa || 0))));
  const half = 150;
  const seasonRows = years.length
    ? h('div', { flexDirection: 'column', gap: 10, width: 560 },
      h('div', { color: C.lime, fontSize: 18, letterSpacing: 3, fontFamily: MONO }, 'WINS ADDED BY SEASON'),
      years.map((yr) => h('div', { alignItems: 'center', gap: 12 },
        h('div', { width: 70, fontSize: 22, color: C.mid, fontFamily: MONO }, String(yr)),
        h('div', { flexDirection: 'column', gap: 4 },
          card.seasons.map((s) => {
            const r = s.rows.find((x) => x.year === yr);
            const v = r?.wpa || 0;
            const w = Math.max(3, (Math.abs(v) / max) * half);
            return h('div', { alignItems: 'center', width: half * 2 + 90 },
              h('div', { width: half, justifyContent: 'flex-end' }, v < 0 ? h('div', { width: w, height: 14, background: ROLE[s.role].colour, borderRadius: 4 }) : null),
              h('div', { width: 2, height: 18, background: 'rgba(255,255,255,0.3)' }),
              h('div', { width: half }, v >= 0 ? h('div', { width: w, height: 14, background: ROLE[s.role].colour, borderRadius: 4 }) : null),
              h('div', { fontSize: 19, color: C.mid, marginLeft: 8, fontFamily: MONO }, `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(2)}`));
          })))))
    : null;
  const ranks = h('div', { flexDirection: 'column', gap: 12, marginLeft: 'auto', width: 440 },
    card.ranks.map((m) => h('div', { justifyContent: 'space-between', alignItems: 'center', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: '12px 20px' },
      h('div', { alignItems: 'center', gap: 10 },
        h('div', { width: 12, height: 12, borderRadius: 3, background: ROLE[m.role].colour }),
        h('div', { fontSize: 24, color: C.mid }, m.label)),
      h('div', { fontSize: 26, fontFamily: MONO, fontWeight: 500, color: m.top ? C.lime : C.mid }, m.rank))));
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '44px 56px', fontFamily: 'Barlow' },
    top(card.scope),
    h('div', { fontFamily: DISPLAY, fontSize: 64, fontWeight: 700, marginTop: 22, lineHeight: 1.05 }, card.headline),
    h('div', { color: C.low, fontSize: 24, marginTop: 6 }, card.kicker),
    card.verdict ? h('div', { fontFamily: DISPLAY, fontSize: 38, fontWeight: 700, marginTop: 20, lineHeight: 1.2, color: C.text }, card.verdict) : null,
    h('div', { marginTop: 'auto', alignItems: 'flex-end' }, seasonRows, ranks));
}

function playerCard(card) {
  if (card.ranks) return verdictCard(card);
  const stats = h('div', { gap: 22, marginTop: 30 },
    (card.stats || []).map((s) => h('div', { flexDirection: 'column', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 18, padding: '18px 24px', minWidth: 230 },
      h('div', { color: C.low, fontSize: 22 }, s.label),
      h('div', { fontSize: 44, fontFamily: MONO, fontWeight: 500, color: String(s.value).startsWith('−') ? C.red : C.lime }, s.value))));
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

// A team page as a link preview: the side's colour, its record and rating, where it ranks by phase (bat and ball), and
// its best batter and wicket-taker.
function teamCard(card) {
  const accent = card.colour || C.lime;
  const ORD = (n) => `${n}${[11, 12, 13].includes(n % 100) ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th')}`;
  const tone = (r) => (!r ? C.low : r.rank <= Math.ceil(r.of / 3) ? C.lime : r.rank > r.of - Math.ceil(r.of / 3) ? C.red : C.mid);
  const cell = (r) => h('div', { width: 150, justifyContent: 'center', fontSize: 32, fontFamily: MONO, fontWeight: 500, color: tone(r) }, r ? ORD(r.rank) : '–');
  const of = card.phases.find((x) => x.bat || x.bowl);
  const grid = h('div', { flexDirection: 'column', gap: 10 },
    h('div', { gap: 0 }, h('div', { width: 130 }),
      card.phases.map((x) => h('div', { width: 150, justifyContent: 'center', color: C.low, fontSize: 22 }, x.label))),
    ['bat', 'bowl'].map((k) => h('div', { alignItems: 'center' },
      h('div', { width: 130, color: C.mid, fontSize: 24 }, k === 'bat' ? 'Batting' : 'Bowling'),
      card.phases.map((x) => cell(x[k])))),
    h('div', { color: C.low, fontSize: 20, marginTop: 4 }, `Rank by phase, of ${(of?.bat || of?.bowl)?.of || ''} sides`));
  const best = h('div', { flexDirection: 'column', gap: 12, marginLeft: 'auto', width: 430 },
    card.best.map((b) => h('div', { flexDirection: 'column', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: '12px 20px' },
      h('div', { color: C.low, fontSize: 20 }, b.role),
      h('div', { fontSize: 30, fontWeight: 600 }, b.name),
      h('div', { color: C.mid, fontSize: 22 }, b.value))));
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '44px 56px', fontFamily: 'Barlow', borderTop: `12px solid ${accent}` },
    top(card.kicker),
    h('div', { fontFamily: DISPLAY, fontSize: card.headline.length > 22 ? 62 : 72, fontWeight: 700, marginTop: 18, lineHeight: 1.05, color: accent }, card.headline),
    h('div', { color: C.mid, fontSize: 30, marginTop: 10 }, card.sub),
    h('div', { marginTop: 'auto', alignItems: 'flex-end' }, grid, best));
}

// A built squad as a link preview: the team, roles at playoff level against the real squad's, the seven roles by status.
function xiCard(card) {
  const accent = card.colour || C.lime;
  const tone = { 'playoff level': C.lime, short: '#f0b429', gap: C.red };
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '44px 56px', fontFamily: 'Barlow', borderTop: `12px solid ${accent}` },
    top('Fix my team · IPL 2027'),
    h('div', { fontFamily: DISPLAY, fontSize: 60, fontWeight: 700, marginTop: 14, lineHeight: 1.05, color: accent }, `${card.team}, rebuilt`),
    h('div', { alignItems: 'baseline', gap: 14, marginTop: 10 },
      h('div', { fontFamily: MONO, fontSize: 44, fontWeight: 500, color: C.text }, `${card.at} of ${card.of}`),
      h('div', { fontSize: 28, color: C.mid }, `roles at playoff level · the real squad ${card.was}`)),
    card.moves ? h('div', { fontSize: 24, color: C.low, marginTop: 6 }, card.moves) : null,
    h('div', { marginTop: 'auto', flexWrap: 'wrap', gap: 10 },
      card.roles.map((r) => h('div', { alignItems: 'center', gap: 8, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 14px' },
        h('div', { width: 12, height: 12, borderRadius: 6, background: tone[r.status] || C.low }),
        h('div', { fontSize: 22, color: C.mid }, r.label)))));
}

// A locked-in Season Draft: the score and the one-line result, the drafted XI (plane: overseas, WK: keeper), and the
// 19 seasons as a strip (made / topped / missed). With no valid draft in the link: the game's own card.
// The overseas mark, as in the app (Material's Flight, tilted): drawn, as the card's fonts have no plane.
const PLANE = { type: 'svg', props: { width: 22, height: 22, viewBox: '0 0 24 24', style: { transform: 'rotate(45deg)' },
  children: { type: 'path', props: { fill: C.mid, d: 'M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z' } } } };

// The keeper's glove and the topped season's star, drawn like the app's icons (src/components/common/CricketIcons.jsx).
const GLOVE = { type: 'svg', props: { width: 22, height: 22, viewBox: '0 0 24 24', children: { type: 'path', props: { fill: C.mid,
  d: 'M7.5 21.5v-6.2L4.6 12a1.4 1.4 0 0 1 2.05-1.9L8 11.4V5.2a1.3 1.3 0 0 1 2.6 0v4.6h.6V3.8a1.3 1.3 0 0 1 2.6 0v6h.6V4.8a1.3 1.3 0 0 1 2.6 0v5.6h.6V6.9a1.3 1.3 0 0 1 2.6 0v8.1c0 3.6-2.9 6.5-6.5 6.5H7.5z' } } } };
const STAR = { type: 'svg', props: { width: 14, height: 14, viewBox: '0 0 24 24', children: { type: 'path', props: { fill: C.bg,
  d: 'M12 17.27l4.15 2.51c.76.46 1.69-.22 1.49-1.08l-1.1-4.72 3.67-3.18c.67-.58.31-1.68-.57-1.75l-4.83-.41-1.89-4.46c-.34-.81-1.5-.81-1.84 0L9.19 8.63l-4.83.41c-.88.07-1.24 1.17-.57 1.75l3.67 3.18-1.1 4.72c-.2.86.73 1.54 1.49 1.08l4.15-2.5z' } } } };

function draftCard(card) {
  if (!card) {
    return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '44px 56px', fontFamily: 'Barlow' },
      top('Game'),
      h('div', { fontFamily: MONO, fontSize: 120, fontWeight: 500, color: C.lime, marginTop: 30, lineHeight: 1 }, '19-0'),
      h('div', { fontSize: 32, color: C.mid, marginTop: 12, width: 900 }, 'Build an XI from 19 years of IPL player-seasons on a budget. It plays all 19 seasons: can it make the playoffs every time?'));
  }
  const row = (p) => h('div', { alignItems: 'center', gap: 10, height: 31 },
    h('div', { width: 90, fontSize: 18, color: C.low }, p.slot),
    h('div', { fontSize: 23, color: C.text }, p.name),
    p.overseas ? PLANE : null,
    p.wk ? GLOVE : null);
  return h('div', { width: '100%', height: '100%', flexDirection: 'column', background: C.bg, color: C.text, padding: '40px 56px', fontFamily: 'Barlow' },
    top('19-0 · IPL draft'),
    h('div', { marginTop: 22, gap: 16 },
      h('div', { flexDirection: 'column', width: 540 },
        h('div', { fontFamily: MONO, fontSize: 120, fontWeight: 500, color: C.lime, lineHeight: 1 }, `${card.made}-${19 - card.made}`),
        h('div', { fontFamily: DISPLAY, fontSize: 27, fontWeight: 700, lineHeight: 1.15, marginTop: 14 }, card.line),
        card.why ? h('div', { fontSize: 21, color: C.mid, marginTop: 10 }, card.why) : null,
        h('div', { fontSize: 22, color: C.low, marginTop: 14 }, 'Same deal, can you beat it?')),
      h('div', { flexDirection: 'column' }, card.xi.map(row))),
    h('div', { marginTop: 'auto', gap: 6 },
      card.strip.map((x) => h('div', { width: 50, height: 40, borderRadius: 8, alignItems: 'center', justifyContent: 'center', gap: 2, fontFamily: MONO, fontSize: 18,
        background: x.topped ? '#c9a227' : x.made ? C.lime : C.surface, color: x.made ? C.bg : C.low }, x.s, x.topped ? STAR : null))),
    h('div', { marginTop: 10, fontSize: 17, color: C.low }, 'hindsightcricket.com · Data: Himanish Ganjoo & TechRadar, Cricsheet'));
}

function homeCard(card) {
  const tiles = h('div', { flexWrap: 'wrap', gap: 14, marginTop: 24, width: card.latest ? 620 : 1080 },
    card.features.map(([name, what]) => h('div', { flexDirection: 'column', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, padding: '14px 20px', width: card.latest ? 300 : 520 },
      h('div', { fontSize: 26, fontWeight: 600 }, name),
      h('div', { fontSize: 20, color: C.low, marginTop: 4 }, what))));
  const latest = card.latest
    ? h('div', { flexDirection: 'column', marginLeft: 'auto', width: 380, background: C.surface, border: `2px solid ${C.lime}`, borderRadius: 20, padding: '20px 26px', marginTop: 24 },
      h('div', { color: C.lime, fontSize: 18, letterSpacing: 3, fontFamily: MONO }, 'LATEST MATCH'),
      h('div', { color: C.mid, fontSize: 22, marginTop: 8 }, card.latest.result),
      h('div', { fontFamily: DISPLAY, fontSize: 38, fontWeight: 700, marginTop: 16 }, card.latest.player),
      h('div', { color: C.mid, fontSize: 26, marginTop: 2 }, card.latest.figure),
      h('div', { alignItems: 'baseline', gap: 10, marginTop: 14 },
        h('div', { fontSize: 50, fontFamily: MONO, fontWeight: 500, color: C.lime }, card.latest.impact),
        h('div', { fontSize: 22, color: C.low }, 'runs of Impact')))
    : null;
  return frame('hindsightcricket.com', card.headline, h('div', { flexDirection: 'column' },
    h('div', { color: C.mid, fontSize: 28, marginTop: 30 }, card.sub),
    h('div', { alignItems: 'flex-start' }, tiles, latest)));
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
    : summary?.kind === 'home' ? homeCard(card)
    : summary?.kind === 'player' ? playerCard(card)
    : summary?.kind === 'team' ? teamCard(card)
    : summary?.kind === 'xi' ? xiCard(card)
    : summary?.kind === 'draft' ? draftCard(card)
      : textCard(card);

  const image = new ImageResponse(element, { width: 1200, height: 630, fonts: FONTS });
  const png = Buffer.from(await image.arrayBuffer());
  res.setHeader('Content-Type', 'image/png');
  // Finished matches never change; players and pages change slowly.
  // The home card shows the latest match, so it turns over within hours.
  const sMaxAge = summary?.kind === 'scorecard' ? 604800 : summary?.kind === 'home' ? 3600 : 86400;
  res.setHeader('Cache-Control', `public, max-age=3600, s-maxage=${sMaxAge}, stale-while-revalidate=86400`);
  res.end(png);
}
