// Render hypothesis share cards: node scripts/notes/render_cards.mjs <note dir>
//
// Reads <note dir>/cards.json (written by build_hypothesis_notes.py prepare) and writes
// card-1.png, card-2.png, ... at 1080x1350 (portrait, the phone-feed size of api/img.mjs), dark,
// with the site's Barlow fonts and the same phone-legibility floors (MIN_FONT: text >= 26px at
// 1080 wide). Layout: hypothesis -> numbers -> verdict, footer "Data: Hindsight ·
// hindsightcricket.com" plus the source credits.
import { ImageResponse } from '@vercel/og';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { FONTS, MIN_FONT } from '../../api/img.mjs';

const W = 1080;
const H = 1350;
const DISPLAY = 'Barlow Semi Condensed';
const C = {
  bg: '#0a0c11', surface: '#14171e', track: '#1d212b', text: '#f3f4f6', mid: '#c3c8d0', low: '#9aa1ac',
  lime: '#b6f24a', red: '#ff6b6b', amber: '#f5b942', grey: '#c3c8d0',
};

const h = (type, style, ...children) => ({
  type,
  props: { style: { display: 'flex', ...style }, children: children.flat().filter((c) => c !== null && c !== undefined && c !== false) },
});

const verdictColour = (card) => C[card.verdict_colour] || C.grey;

function header(card) {
  return h('div', { justifyContent: 'space-between', alignItems: 'center' },
    h('div', { color: C.lime, fontSize: 30, letterSpacing: 5, fontWeight: 600 }, 'HINDSIGHT'),
    h('div', { color: C.low, fontSize: 28 }, card.kicker || ''));
}

function footer(spec) {
  return h('div', { flexDirection: 'column', marginTop: 'auto', paddingTop: 28, borderTop: `2px solid ${C.track}`, gap: 10 },
    h('div', { color: C.lime, fontSize: 30, fontWeight: 600 }, spec.footer),
    h('div', { color: C.low, fontSize: MIN_FONT.footer, lineHeight: 1.3 }, spec.credits));
}

function verdictBlock(card, big) {
  if (!card.verdict) return null;
  return h('div', { flexDirection: 'column', marginTop: big ? 40 : 28, padding: '26px 30px', background: C.surface,
    borderRadius: 18, borderLeft: `10px solid ${verdictColour(card)}` },
  h('div', { color: C.low, fontSize: 30, letterSpacing: 4 }, (card.verdict_label || 'VERDICT').toUpperCase()),
  h('div', { fontFamily: DISPLAY, color: verdictColour(card), fontSize: big ? 96 : 72, fontWeight: 700, lineHeight: 1.05 }, card.verdict));
}

function claimCard(card) {
  const long = (card.title || '').length > 130;
  return [
    h('div', { color: C.mid, fontSize: 36, marginTop: 48 }, card.eyebrow),
    h('div', { fontFamily: DISPLAY, fontSize: long ? 56 : 68, fontWeight: 700, lineHeight: 1.12, marginTop: 14, color: C.text },
      card.title),
    verdictBlock(card, true),
    card.headline && !(card.parts && card.parts.length > 2)
      ? h('div', { color: C.mid, fontSize: 36, lineHeight: 1.3, marginTop: 30 }, card.headline)
      : null,
    card.parts && card.parts.length
      ? h('div', { flexDirection: 'column', gap: 14, marginTop: 26 },
        card.parts.map((p) => h('div', { justifyContent: 'space-between', gap: 20, fontSize: 34 },
          h('div', { color: C.mid, maxWidth: '64%' }, p.label),
          h('div', { color: C.text, fontWeight: 600, textAlign: 'right' }, p.value))))
      : null,
  ];
}

function numberCard(card) {
  return [
    h('div', { color: C.mid, fontSize: 36, marginTop: 48 }, card.eyebrow),
    h('div', { fontFamily: DISPLAY, fontSize: 200, fontWeight: 700, lineHeight: 1, marginTop: 30, color: C.lime }, card.stat),
    h('div', { color: C.text, fontSize: 38, lineHeight: 1.25, marginTop: 18 }, card.stat_label),
    h('div', { color: C.mid, fontSize: 34, marginTop: 14 }, card.sub),
    card.rows && card.rows.length
      ? h('div', { flexDirection: 'column', gap: 12, marginTop: 34 },
        card.rows.map((r) => h('div', { justifyContent: 'space-between', fontSize: 34, padding: '10px 0', borderBottom: `1px solid ${C.track}` },
          h('div', { color: C.mid }, String(r.label)),
          h('div', { color: C.text, fontWeight: 600 }, r.value))))
      : null,
    verdictBlock(card, false),
  ];
}

export function cardTree(spec, card) {
  return h('div', { width: W, height: H, flexDirection: 'column', background: C.bg, color: C.text, fontFamily: 'Barlow',
    padding: 60 },
  header(card),
  ...(card.kind === 'claim' ? claimCard(card) : numberCard(card)),
  footer(spec));
}

async function main() {
  const dir = process.argv[2];
  if (!dir) {
    console.error('usage: node scripts/notes/render_cards.mjs <note dir>');
    process.exit(1);
  }
  const spec = JSON.parse(readFileSync(join(dir, 'cards.json'), 'utf8'));
  for (const [i, card] of spec.cards.entries()) {
    const res = new ImageResponse(cardTree(spec, card), { width: W, height: H, fonts: FONTS });
    const file = join(dir, `card-${i + 1}.png`);
    writeFileSync(file, Buffer.from(await res.arrayBuffer()));
    console.log(file);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
