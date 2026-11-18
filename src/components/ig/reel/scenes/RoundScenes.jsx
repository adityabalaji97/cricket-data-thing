import React from 'react';
import { Box } from '@mui/material';
import { colors } from '../../../../theme/hindsightDark';
import { fmt } from '../../../story/postVisuals';
import { back, clamp, easeOut, fitSize, litAt, progress, ringPulse, teamTone, u } from '../motion';
import { At, Count, PlayerCard, Scope, enter, pop, ringBox, splitName, type } from './common';

/**
 * The Reel-only kinds from the SMAT round-2 Reel (docs/motion_reel_mockups/smat_round2), kept as scene kinds.
 * Timings are the finished Reel's; `at` values in data are absolute seconds (word timestamps), defaulting to offsets
 * from the scene start.
 */

/**
 * hero_card: a deck card at full size with a count-up, then a line under it ("+62.4 runs above par"), its gloss and a
 * lime badge. data: { name, team, corner, rank?, from, value, format?, done?, detail, sub?: { value, format, label,
 * gloss, at }, badge?: { text, at } }
 */
export const HeroCardScene = ({ scene, t }) => {
  const d = scene.data || {};
  const s0 = scene.start;
  const tone = teamTone(d.team);
  const { first, last } = splitName(d.name);
  const settle = easeOut(progress(t, s0, 0.6));
  const subAt = d.sub ? (d.sub.at ?? s0 + 1.4) : null;
  return (
    <>
      <At x={64} y={492} w={876} sx={{ transform: `translateY(${u(6 * Math.sin(t * 1.3))}px)${settle >= 1 ? '' : ` scale(${1.04 - 0.04 * settle})`}`, transformOrigin: 'center' }}>
        <PlayerCard tone={tone} first={first} last={last} rank={d.rank ?? 1} corner={d.corner} apex
          value={<Count value={d.value} from={d.from ?? 0} format={d.format || 'int'} t={t} a={s0} dur={0.8} done={d.done || ''} />}
          detail={d.detail} sizes={{ last: last.length > 8 ? 170 : 220 }} />
      </At>
      {d.sub && (
        <>
          <At x={64} y={1184} w={876} sx={{ display: 'flex', alignItems: 'baseline', gap: `${u(24)}px`, ...enter(t, subAt - 0.1) }}>
            <Box sx={{ ...type.mono(110), color: colors.accent, lineHeight: 1 }}>
              <Count value={d.sub.value} format={d.sub.format || 'signed1'} t={t} a={subAt} dur={1.0} />
            </Box>
            <Box sx={type.display(56)}>{d.sub.label}</Box>
          </At>
          {d.sub.gloss && <At x={64} y={1306} w={876} sx={{ ...type.mono(30, 500), color: colors.textLo, whiteSpace: 'nowrap', opacity: easeOut(progress(t, subAt + 1.2, 0.4)) }}>{d.sub.gloss}</At>}
        </>
      )}
      {d.badge && (
        <At x={64} y={1360} sx={{ px: `${u(22)}px`, py: `${u(12)}px`, borderRadius: `${u(10)}px`, bgcolor: colors.accent, color: colors.bg, ...type.display(44), ...pop(t, (d.badge.at ?? s0 + 3) - 0.1) }}>
          {d.badge.text}
        </At>
      )}
    </>
  );
};

/**
 * team_best: ranked bars in team colours (each franchise's best). Rows enter top down 0.12s apart from the left, bars
 * grow, the lime ring follows the voice (scene.beats [{at, key: name}]); the detail chip shows on the leader and the
 * lit row. Below par draws red, from the par line, as on the cards.
 * data: { format, rows: [{ team, code, name, label, value, detail }] }
 */
export const TeamBestScene = ({ scene, t }) => {
  const d = scene.data || {};
  const rows = d.rows || [];
  const max = Math.max(...rows.map((r) => Math.abs(r.value)), 1e-9);
  const lit = litAt(scene.beats, t);
  const pitch = rows.length > 9 ? 92 : 100;
  return (
    <>
      {rows.map((r, i) => {
        const a = scene.start + i * 0.12;
        const p = progress(t, a, 0.45);
        const tone = teamTone(r.team);
        const below = r.value < 0;
        const fill = below ? colors.red : tone.fill;
        const g = easeOut(progress(t, a + 0.1, 0.6));
        const frac = (Math.abs(r.value) / max) * g;
        const ink = below ? colors.textHi : tone.ink;
        // The code and name are drawn twice: light on the panel, and in the fill's ink clipped to the bar, so each
        // letter reads on whichever it sits over (a short bar never leaves dark ink on the dark panel).
        const label = (colour, clip) => (
          <Box sx={{ position: 'absolute', inset: 0, color: colour, clipPath: clip }}>
            <Box sx={{ position: 'absolute', left: u(20), top: 0, ...type.mono(26), lineHeight: `${u(pitch - 12)}px` }}>{r.code}</Box>
            <Box sx={{ position: 'absolute', left: u(120), top: 0, ...type.display(50), lineHeight: `${u(pitch - 12)}px`, whiteSpace: 'nowrap' }}>{r.label || splitName(r.name).last}</Box>
          </Box>
        );
        const on = lit && lit.key === r.name ? easeOut(progress(t, lit.at - 0.1, 0.3)) : 0;
        return (
          <At key={r.name} x={64} y={490 + i * pitch} w={876} h={pitch - 12}
            sx={{ borderRadius: `${u(10)}px`, bgcolor: colors.surface2, overflow: 'hidden', opacity: clamp(p * 2.5),
              transform: `translateX(${u((1 - back(p)) * -120)}px) scale(${1 + 0.025 * on})`, ...ringBox(on, undefined, lit ? ringPulse({ t, lit }) : 0) }}>
            <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${frac * 100}%`, bgcolor: fill, borderRadius: `${u(10)}px` }} />
            {label(colors.textHi, `inset(0 0 0 ${frac * 100}%)`)}
            {label(ink, `inset(0 ${100 - frac * 100}% 0 0)`)}
            {r.detail && (
              <Box sx={{ position: 'absolute', right: u(170), top: u((pitch - 12 - 50) / 2), px: `${u(14)}px`, borderRadius: `${u(8)}px`, bgcolor: colors.bg, color: colors.textHi,
                ...type.mono(30), lineHeight: `${u(50)}px`, opacity: i === 0 ? 1 : on }}>{r.detail}</Box>
            )}
            <Box sx={{ position: 'absolute', right: u(22), top: 0, ...type.mono(40), lineHeight: `${u(pitch - 12)}px`, color: colors.textHi }}>
              {fmt(r.value * (g >= 1 ? 1 : g), d.format || 'signed1')}
            </Box>
          </At>
        );
      })}
      {scene.scope && <Scope y={490 + rows.length * pitch + 10}>{scene.scope}</Scope>}
    </>
  );
};

/**
 * pool_count: a count with its label ("324 played with no IPL side"), then the one card it is about rises under it as
 * the count shrinks to the top. data: { count, label, card?: { name, corner, from, value, done, detail, line, tag, at } }
 */
export const PoolCountScene = ({ scene, t }) => {
  const d = scene.data || {};
  const s0 = scene.start;
  const c = d.card;
  const cAt = c ? (c.at ?? s0 + 2) : Infinity;
  const pc = c ? progress(t, cAt - 0.3, 0.4) : 0;
  const { first, last } = c ? splitName(c.name) : {};
  const ci = easeOut(progress(t, cAt - 0.2, 0.45));
  return (
    <>
      <At x={64} y={500} w={876} sx={{ transform: `translateY(${u(-pc * 30 + Math.round(6 * Math.sin((t - s0) * 1.6)))}px) scale(${1 - 0.3 * pc})`, transformOrigin: 'left top', opacity: 1 - 0.3 * pc }}>
        <Box sx={{ ...type.display(260), color: colors.textHi }}><Count value={d.count} format="int" t={t} a={s0} dur={1.2} /></Box>
        <Box sx={{ ...type.display(64), color: colors.textLo }}>{d.label}</Box>
      </At>
      {c && (
        <>
          <At x={64} y={750} w={876} sx={{ opacity: ci, transform: `translateY(${u((1 - ci) * 120 + Math.round(6 * Math.sin((t - cAt) * 1.6)))}px)` }}>  {/* lands, then bobs while it's read */}
            <PlayerCard tone={{ fill: colors.surface3, ink: colors.textHi, trim: colors.accent }} first={first} last={last} corner={c.corner} apex
              value={<Count value={c.value} from={c.from ?? 0} format="int" t={t} a={cAt} dur={0.8} done={c.done || ''} />}
              detail={c.detail} sizes={{ last: 150, value: 130, detail: 46 }} />
          </At>
          {c.line && <At x={64} y={1306} sx={{ ...type.mono(54), color: colors.accent, opacity: easeOut(progress(t, cAt + 1.0, 0.4)) }}>{c.line}</At>}
          {c.tag && <At x={64} y={1388} w={876} sx={{ ...type.mono(28, 500), color: colors.textLo, whiteSpace: 'nowrap', opacity: easeOut(progress(t, cAt + 1.6, 0.4)) }}>{c.tag}</At>}
        </>
      )}
    </>
  );
};

/**
 * pick_one: the closing pick-one, two equal choices, then the send line and the credit (the only brand mention,
 * decision 8). The send line is one line (decision 9); captions are off in this scene (the host enforces it).
 * data: { question, lit, sub?, options: [a, b], send: { text, at }, credit: [line, line] }
 */
export const PickOneScene = ({ scene, t }) => {
  const d = scene.data || {};
  const s0 = scene.start;
  const q = easeOut(progress(t, s0 - 0.1, 0.5));
  const sendAt = d.send?.at ?? s0 + 1.6;
  const s = easeOut(progress(t, sendAt - 0.1, 0.4));
  const opts = (d.options || []).slice(0, 2).map((o) => (typeof o === 'string' ? { label: o } : o));
  const lined = opts.some((o) => o.line);
  // The tiles breathe for the hold (2%, alternating), so the last frames are never still; each scales from its outer
  // edge, so the right tile never grows into Instagram's right rail.
  const breathe = (k) => 1 + 0.02 * Math.sin((t - s0) * 2.4 + k * Math.PI) * clamp(progress(t, s0 + 1.2, 0.5));
  // The question: 160px when short, 128px otherwise (the round-2 Reel's size), up to three lines.
  const qSize = `${d.question || ''} ${d.lit || ''}`.length > 24 ? 128 : 160;
  // One column, top to bottom (question, sub, tiles, send line, credit), so nothing overlaps whatever the lengths.
  return (
    <At x={64} y={490} w={876} h={980} sx={{ display: 'flex', flexDirection: 'column', gap: `${u(28)}px` }}>
      <Box sx={{ ...type.display(qSize), transform: `scale(${0.92 + 0.08 * q})`, transformOrigin: 'left top' }}>
        {d.question} <Box component="span" sx={{ color: colors.accent }}>{d.lit}</Box>
      </Box>
      {d.sub && <Box sx={{ ...type.mono(40), color: colors.textLo, opacity: easeOut(progress(t, s0 + 0.9, 0.4)) }}>{d.sub}</Box>}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: u(876), mt: `${u(8)}px` }}>
        {opts.map((o, k) => {
          const p = progress(t, s0 + 0.4 + k * 0.08, 0.45);
          return (
            <Box key={o.label} sx={{ width: u(410), height: u(lined ? 300 : 200), borderRadius: `${u(16)}px`, border: `${u(5)}px solid ${colors.borderStrong}`,
              boxSizing: 'border-box', bgcolor: colors.surface2, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center',
              gap: `${u(14)}px`, px: `${u(24)}px`, opacity: clamp(progress(t, s0 + 0.4, 0.2)),
              transform: `scale(${(0.7 + 0.3 * back(p)) * breathe(k)})`, transformOrigin: k ? 'right center' : 'left center' }}>
              {/* shrunk to the tile's inside (410 less its border and padding): FINISHER at 110px ran out of its box */}
              <Box sx={{ ...type.display(fitSize(o.label, 410 - 2 * 24 - 2 * 5 - 8, lined ? 96 : 110, 'display')), whiteSpace: 'nowrap' }}>{o.label}</Box>
              {o.line && <Box sx={{ ...type.mono(32, 500), color: colors.textMed }}>{o.line}</Box>}
            </Box>
          );
        })}
      </Box>
      {d.send && (
        // One line (decision 9), shrunk to fit; validateReel flags a line too long to read at that size.
        <Box sx={{ ...type.display(fitSize(d.send.text, 876, 66, 'display')), color: colors.accent, whiteSpace: 'nowrap', mt: `${u(12)}px`,
          opacity: s, transform: `translateY(${u((1 - s) * 40)}px)` }}>
          {d.send.text}
        </Box>
      )}
      {d.credit && (
        <Box sx={{ ...type.mono(27, 500), lineHeight: 1.45, color: colors.textLo, opacity: easeOut(progress(t, sendAt + 0.3, 0.4)) }}>
          {d.credit.map((l) => <Box key={l}>{l}</Box>)}
        </Box>
      )}
    </At>
  );
};
