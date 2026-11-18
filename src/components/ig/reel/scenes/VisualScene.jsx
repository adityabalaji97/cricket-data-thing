import React, { useLayoutEffect, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../../theme/hindsightDark';
import { MOTION_KINDS, POST_VISUALS } from '../../../story/postVisuals';
import { VISUALS } from '../../../story/visuals';
import { alpha, camera, easeInOut, easeOut, litAt, progress, ringPulse, u } from '../motion';
import { At, Scope } from './common';

/** The carousel visual for a kind, from either registry (the same lookup toStoryCard uses). */
export const visualFor = (kind) => VISUALS[kind] || POST_VISUALS[kind] || null;

/**
 * Where a card visual sits in the Reel: the content zone, above the scope line. The visual is laid out in a box
 * 1/zoom the size and scaled by zoom; the default 0.92 lays it out at about a slide's own content box (384 x 400 CSS
 * px, 960 x 1000 canvas), so every label keeps the size it has on the carousel and nothing reflows.
 */
export const VISUAL_BOX = { x: 64, y: 480, w: 876, h: 920 };
export const VISUAL_ZOOM = 0.92;
/**
 * Chart kinds drawn as one SVG 100% wide keep their aspect ratio, so laying them out narrower doesn't enlarge them:
 * they take the full box width (1.0) instead of the slide's 0.92, 8% larger. Their labels stay the card's.
 */
export const KIND_ZOOM = Object.fromEntries(['win_prob_line', 'race_lines', 'score_race', 'metric_lines', 'game_timeline', 'bid_trail',
  'worm', 'elo_lines', 'scatter_plus', 'totals_scatter', 'suits_scatter', 'last_meeting', 'par'].map((k) => [k, 1])
  // radial charts drawn small inside their SVG margins (twin_cloud caps its height): laid out narrower, scaled up
  .concat([['twin_cloud', 1.3], ['distance_star', 1.3], ['over_strips', 1.3]]));
/** A board with this many keyed marks or more is pushed in on (spec section 3 says about 21; at slide size 16+ chips are already too small on a phone). */
export const PUSH_MARKS = 16;

/**
 * Any carousel visual in a Reel, drawn by its own component at the size it has on a slide.
 *
 * A kind with motion (MOTION_KINDS) gets the `motion` prop: { t, start, end, lit, plan } and moves itself (rows enter,
 * bars grow from par, numbers count, the ring follows the voice). Any other kind is the fallback (plan point 3): the
 * visual drawn whole, revealed left to right over 0.8s as today's Reel does, then a slow camera push for the rest of
 * the scene (or a push in on scene.camera's region), so it is never still and never a placeholder.
 *
 * scene: { kind, payload, teams?, start, end, beats?:[{at, key, box?: {x, y, w, h}}], plan?, camera?: {x, y, s, at, out}, zoom? (0.92),
 *          push?: true | false | {s} (the board push; on by itself at PUSH_MARKS keyed marks), pages?: {field, size, zoom}, scope? }
 */

/**
 * Where each keyed mark sits in the visual ({key: {x, y, w, h}} as fractions of the layout box), from the layout:
 * offsets ignore CSS transforms, so the motion's own scales and the camera never move the answer. Only Reel motion
 * kinds write data-motion-key (and only with the motion prop), so carousels are untouched.
 */
const measureMarks = (root) => {
  const out = {};
  if (!root) return out;
  const W = root.offsetWidth || 1;
  const H = root.offsetHeight || 1;
  const boxOf = (el) => {
    let x = 0;
    let y = 0;
    let n = el;
    while (n && n !== root) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
    return n === root ? { x: x / W, y: y / H, w: el.offsetWidth / W, h: el.offsetHeight / H } : null;
  };
  const members = new Map(); // group element -> its marks' boxes
  root.querySelectorAll('[data-motion-key]').forEach((el) => {
    const b = boxOf(el);
    if (!b) return;
    const g = el.closest('[data-motion-group]');
    const key = el.getAttribute('data-motion-key');
    out[key] = { ...b, groupEl: g && root.contains(g) ? g : null };
    if (out[key].groupEl) members.set(g, [...(members.get(g) || []), b]);
  });
  // the mark's group (a role's chips) as the union of its marks: the push frames the whole group, so the lit chip's
  // row is never cut
  Object.values(out).forEach((m) => {
    const list = m.groupEl ? members.get(m.groupEl) : null;
    m.group = list ? (() => {
      const x0 = Math.min(...list.map((b) => b.x)); const y0 = Math.min(...list.map((b) => b.y));
      const x1 = Math.max(...list.map((b) => b.x + b.w)); const y1 = Math.max(...list.map((b) => b.y + b.h));
      return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    })() : null;
    delete m.groupEl;
  });
  return out;
};

/**
 * The board push (spec section 3): a board too big to read whole (PUSH_MARKS or more, or scene.push) is shown whole for
 * 0.6s, then the camera pushes in on the group of the mark the voice names (a role's chips), pans between named
 * groups (0.5s) and holds while each is read, and pulls back out over the scene's last 0.5s. The view is anchored at
 * the board's left edge, so its role labels stay whole; the scale is at most scene.push.s (1.6) and small enough that
 * the framed group still fits (its right edge in view, 85% of the height); the
 * view never leaves the visual (no empty edge), and the visual's box clips it, so nothing spills over the kicker or
 * the scope line. Returns a CSS transform, or null when there is nothing to push to.
 */
const pushCamera = (scene, t, marks) => {
  const beats = (scene.beats || []).filter((b) => b.key != null && marks[b.key]);
  if (!beats.length) return null;
  const sMax = (scene.push && scene.push.s) || 1.6;
  const frame = (b) => {
    const m = marks[b.key].group || marks[b.key];
    // anchored at the board's left edge (its labels stay whole): the group's right edge must stay in view
    return { x: m.x + m.w / 2, y: m.y + m.h / 2, s: Math.max(1, Math.min(sMax, 0.97 / (m.x + m.w), 0.85 / m.h)) };
  };
  let c = frame(beats[0]);
  beats.forEach((b, i) => {
    if (!i) return;
    const p = easeInOut(progress(t, b.at - 0.35, 0.5));
    const prev = c; const next = frame(b);
    c = { x: prev.x + (next.x - prev.x) * p, y: prev.y + (next.y - prev.y) * p, s: prev.s + (next.s - prev.s) * p };
  });
  const k = easeInOut(progress(t, scene.start + 0.6, 0.5)) * (1 - easeInOut(progress(t, scene.end - 0.5, 0.5)));
  const sc = 1 + (c.s - 1) * k;
  // origin top-left: the framed centre c moves toward the middle as k grows (c*sc + d = c + (0.5 - c)*k), and
  // the offset is clamped so the scaled visual always covers the box (no empty edge shows)
  const off = (cv) => Math.min(0, Math.max(1 - sc, cv + (0.5 - cv) * k - cv * sc));
  const dx = 0; // left-anchored
  const dy = off(c.y) * 100;
  return `translate(${dx}%, ${dy}%) scale(${sc})`;
};

/**
 * Pages (spec section 3, "zoom instead of shrinking"): a board whose items can't be read whole at Reel size plays its
 * list a page at a time, bigger. scene.pages = { field: 'cases', size: 1, zoom: 1.3, count? }: payload[field] is cut into
 * pages of `size`; page k starts at the beat naming its first item (beats[].key), else the scene is split evenly.
 * Each page is the card's own drawing of those items, with its motion starting at the page's start.
 */
const pageAt = (scene, t) => {
  const P = scene.pages;
  const list = (scene.payload && scene.payload[P.field]) || [];
  const size = P.size || 1;
  const n = Math.max(1, Math.min(P.count || Infinity, Math.ceil(list.length / size))); // count: only the first pages (the rest stays in the carousel)
  const keyOf = (x) => (x && typeof x === 'object' ? x.name || x.label || x.key : x);
  const span = (scene.end - scene.start) / n;
  const starts = Array.from({ length: n }, (_, k) => {
    const b = (scene.beats || []).find((x) => x.key === keyOf(list[k * size]));
    return k === 0 ? scene.start : b ? b.at - 0.15 : scene.start + k * span;
  });
  let k = 0;
  starts.forEach((s0, i) => { if (t >= s0) k = i; });
  const next = k + 1 < n ? starts[k + 1] : null;
  const o = Math.min(k ? easeOut(progress(t, starts[k], 0.25)) : 1, next == null ? 1 : 1 - easeInOut(progress(t, next - 0.2, 0.2)));
  return { start: starts[k], o, payload: { ...scene.payload, [P.field]: list.slice(k * size, (k + 1) * size) } };
};

const VisualScene = ({ scene, t }) => {
  const Visual = visualFor(scene.kind);
  const layoutRef = useRef(null);
  const [marks, setMarks] = useState({});
  useLayoutEffect(() => { setMarks(measureMarks(layoutRef.current)); }, [scene]);
  if (!Visual) return null;
  const hasMotion = MOTION_KINDS.has(scene.kind);
  const page = scene.pages ? pageAt(scene, t) : null;
  const motion = { t, start: page ? page.start : scene.start, end: scene.end, lit: litAt(scene.beats, t), plan: scene.plan || {} };
  const wipe = hasMotion ? 1 : easeOut(progress(t, scene.start, 0.8));
  const B = VISUAL_BOX;
  const zoom = (page && scene.pages.zoom) || scene.zoom || KIND_ZOOM[scene.kind] || VISUAL_ZOOM;
  const pushing = hasMotion && scene.push !== false && (scene.push || Object.keys(marks).length >= PUSH_MARKS);
  const push = pushing ? pushCamera(scene, t, marks) : null;
  return (
    <>
      <At x={B.x} y={B.y} w={B.w} h={B.h} sx={{ overflow: push || page ? 'hidden' : 'visible' }} data-reel-visual={scene.kind}>
        <Box sx={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          // every visual drifts slowly (translate only, its own layer) so the content zone never holds still (M7: 0.8s)
          transform: push || camera(motion, scene.camera), willChange: 'transform',
          transformOrigin: push ? '0 0' : 'center center' }}>
          {/* Laid out 1/zoom the box's size, then scaled by zoom (VISUAL_BOX). */}
          <Box ref={layoutRef} sx={{ position: 'relative', width: `${100 / zoom}%`, height: `${100 / zoom}%`, display: 'flex', flexDirection: 'column',
            fontFamily: fonts.body, color: colors.textHi, transform: zoom === 1 ? undefined : `scale(${zoom})`, transformOrigin: 'left top',
            clipPath: wipe >= 1 ? undefined : `inset(0 ${(1 - wipe) * 100}% 0 0)`, opacity: page ? page.o : undefined }}>
            <Visual payload={page ? page.payload : scene.payload} teams={scene.teams} isMobile motion={hasMotion ? motion : undefined} />
          </Box>
          {/* Fallback kinds don't read `lit`: the ring goes round the beat's region instead (beats[].box, 0..1 of the visual). */}
          {!hasMotion && motion.lit && motion.lit.box && (
            <Box data-reel-ring sx={{ position: 'absolute', left: `${motion.lit.box.x * 100}%`, top: `${motion.lit.box.y * 100}%`,
              width: `${motion.lit.box.w * 100}%`, height: `${motion.lit.box.h * 100}%`, borderRadius: `${u(12)}px`, pointerEvents: 'none',
              boxShadow: `0 0 0 ${u(5 + Math.round(5 * ringPulse(motion)))}px ${alpha(colors.textHi, easeOut(progress(t, motion.lit.at - 0.1, 0.3)))}` }} />
          )}
        </Box>
      </At>
      {scene.scope && <Scope y={B.y + B.h + 12}>{scene.scope}</Scope>}
    </>
  );
};

/** Unknown kinds: the kicker and a label, so a full spec still plays through. */
export const PlaceholderScene = ({ scene }) => (
  <At x={64} y={700} w={876} sx={{ border: `${u(3)}px dashed ${colors.borderStrong}`, borderRadius: `${u(20)}px`, p: `${u(40)}px`, textAlign: 'center' }}>
    <Box sx={{ fontFamily: fonts.mono, fontSize: u(40), color: colors.textLo }}>{scene.kind}</Box>
    {scene.label && <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: u(80), mt: 1 }}>{scene.label}</Box>}
  </At>
);

export default VisualScene;
