/**
 * Motion Reels (MOTION_REEL_PLAN.md): the clock maths every Reel scene and every visual's `motion` prop share.
 *
 * Everything here is a pure function of the time t (seconds). Nothing in src/components/ig/reel may use CSS
 * transitions or animations, timers or the wall clock (motion.test.js greps for them): the recorder calls
 * window.renderAt(t) for each frame, in any order, and must get the same pixels for the same t.
 *
 * Units: the page is 432 x 768 CSS px, recorded at device scale 2.5 (1080 x 1920), as IgSlide is 432 x 540 at 2.5.
 * Layout numbers below are canvas px (the spec's and the finished Reels'); u(px) turns them into CSS px.
 */
import { colors } from '../../../theme/hindsightDark';
import { getTeamPalette, readableOnDark, textOn } from '../../../utils/teamColors';
import FRAME_SPEC from './frame.json';

export const SCALE = 2.5;
export const PAGE = { w: 432, h: 768 };
export const CANVAS = { w: 1080, h: 1920 };
export const u = (px) => px / SCALE;

/**
 * The frame, in canvas px (owner's decisions 7 and 8): the whole frame sits 120px lower than the spec's section 4, so
 * content runs about y 470-1440 and captions y 1500-1584; no wordmark or site name in the header, which is the chapter
 * bars only. The keep-clear zones are Instagram's own overlays and do not move with the frame.
 */
// One source with the Python checks (services/social_rules.reel_problems): frame.json.
const { _note: _frameNote, rules: _frameRules, ...FRAME_JSON } = FRAME_SPEC;
export const FRAME = FRAME_JSON;
/** The Reel rules the checks share with Python (M7): length, longest still, dwell, caption size, kicker/send size. */
export const REEL_RULES = _frameRules;

/** Every face and weight the Reel draws (src/index.css loads them); IgReel loads all before it reports ready. */
export const REEL_FACES = [
  ...[400, 500, 600, 700].map((w) => `${w} 40px "Barlow"`),
  ...[500, 600, 700].map((w) => `${w} 40px "Barlow Semi Condensed"`),
  ...[400, 500, 600].map((w) => `${w} 40px "IBM Plex Mono"`),
];

/**
 * A one-line text's size so it fits `width` canvas px: at most `max`, shrunk by an estimate of the face's average
 * advance (em per character, letter-spacing included). Deterministic, so frames stay pure.
 */
export const EM_PER_CHAR = { mono: 0.6, display: 0.5, body: 0.52 };
export const fitSize = (text, width, max, face = 'mono', tracking = 0) => {
  const n = Math.max(1, String(text || '').length);
  return Math.min(max, width / (n * (EM_PER_CHAR[face] + tracking)));
};

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, p) => a + (b - a) * p;
export const easeOut = (p) => 1 - (1 - clamp(p)) ** 3;
export const easeInOut = (p) => {
  const q = clamp(p);
  return q < 0.5 ? 4 * q * q * q : 1 - (-2 * q + 2) ** 3 / 2;
};
/** Ease out with an overshoot (chips and tiles): 1.5 as in the finished Reels. */
export const back = (p) => {
  const q = clamp(p);
  const c = 1.5;
  return 1 + (c + 1) * (q - 1) ** 3 + c * (q - 1) ** 2;
};
/** 0 before start, 1 after start + dur, linear between. dur <= 0 is a step. */
export const progress = (t, start, dur) => (dur <= 0 ? (t >= start ? 1 : 0) : clamp((t - start) / dur));

/** A number ticking to its value: v * easeOut(p), rounded to `dp` places on the way (the card's format is applied by the caller). */
export const countUp = (v, p, dp = 1) => {
  const x = v * easeOut(p);
  const k = 10 ** dp;
  return p >= 1 ? v : Math.round(x * k) / k;
};

const hexRgb = (hex) => {
  const h = String(hex || '').replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const n = parseInt(full, 16);
  return Number.isNaN(n) || full.length !== 6 ? [255, 255, 255] : [n >> 16, (n >> 8) & 255, n & 255];
};
/** A token or palette colour at an alpha (no new colours: the hue always comes from the theme or the palette). */
export const alpha = (hex, a) => {
  const [r, g, b] = hexRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
};

/**
 * The team's colours for a Reel: fill (the primary, as the cards fill marks), ink (text on that fill, the squad
 * board's ink rule), light (the primary lifted until it reads on the dark background: numbers, the stripe, the
 * progress) and trim (the secondary). Unknown teams take the site's accent.
 */
export const teamTone = (team) => {
  const p = team ? getTeamPalette(team) : null;
  const fill = p?.primary || colors.accent;
  return { name: p?.name || null, fill, ink: textOn(fill), light: readableOnDark(fill, 0.2), trim: p?.secondary || colors.gold };
};

/** The scene at t: the last whose start <= t (scenes are in time order). */
export const activeScene = (scenes, t) => {
  let k = 0;
  (scenes || []).forEach((s, i) => { if (t >= s.start) k = i; });
  return k;
};

/**
 * The scene's in/out: the lift (old up 80px and out over 0.3s, new up 60px and in over 0.35s, 0.1s overlap).
 * A scene starting at 0 is fully in on frame 0 (frame 0 is never empty); the last scene never leaves.
 * Returns { o, dy } with dy in canvas px.
 */
export const lift = (t, start, end, { inDur = 0.35, outDur = 0.3, last = false } = {}) => {
  const a = start - 0.1;
  const pin = start <= 0 ? 1 : easeOut(progress(t, a, inDur));
  const pout = last || end == null ? 0 : easeInOut(progress(t, end - outDur, outDur));
  const o = Math.min(pin, 1 - pout);
  return { o, dy: (1 - pin) * 60 - pout * 80 };
};

/**
 * The caption line at t: one line, at most five words, the spoken word lit. Captions are off in a scene that sets
 * `captions: false` (the closing scene, decision 9). Returns { words:[{w, on}] } or null.
 */
export const activeCaption = (captions, t, scenes) => {
  const sc = scenes && scenes.length ? scenes[activeScene(scenes, t)] : null;
  if (sc && sc.captions === false && t >= sc.start - 0.1) return null;
  const line = (captions || []).find((c) => t >= c.start - 0.02 && t < c.end);
  if (!line) return null;
  const ws = line.words || [];
  let lit = -1;
  ws.forEach((w, i) => { if (t >= w.at - 0.02) lit = i; });
  return { words: ws.map((w, i) => ({ w: w.w, on: i === lit })) };
};

/**
 * Captions from a voice timing file (the finished Reels' timing.json: lines, starts, lengths, words[line][word]):
 * break at sentence ends and colons, at commas after two words, at five words and before a word that would pass
 * 30 characters; no one-word orphans; a line holds
 * until the next starts or 0.25s past its sentence's end.
 */
export const captionsFromTiming = (timing) => {
  const caps = [];
  timing.lines.forEach((line, li) => {
    const ws = line.split(' ');
    let cur = [];
    ws.forEach((w, wi) => {
      // one line: a word that would take the line past captionChars starts the next line
      if (cur.length && [...cur.map((x) => x.w), w].join(' ').length > FRAME_SPEC.rules.captionChars) { caps.push(cur); cur = []; }
      cur.push({ w, at: timing.words[li][wi], li });
      const brk = /[.?!:]$/.test(w) || (/,$/.test(w) && cur.length >= 2) || cur.length >= 5;
      if (brk || wi === ws.length - 1) { caps.push(cur); cur = []; }
    });
  });
  // No one-word orphans: join a short line, or take a word from a full one (5 + 1 becomes 4 + 2).
  for (let i = caps.length - 1; i > 0; i -= 1) {
    if (caps[i].length === 1 && caps[i][0].li === caps[i - 1][0].li) {
      if (caps[i - 1].length < 5 && [...caps[i - 1], ...caps[i]].map((x) => x.w).join(' ').length <= FRAME_SPEC.rules.captionChars) {
        caps[i - 1].push(...caps[i]);
        caps.splice(i, 1);
      } else {
        caps[i].unshift(caps[i - 1].pop());
      }
    }
  }
  return caps.map((c, i) => {
    const li = c[0].li;
    const lineEnd = timing.starts[li] + timing.lengths[li] + 0.25;
    const next = caps[i + 1] ? caps[i + 1][0].at - 0.02 : Infinity;
    return { start: c[0].at, end: Math.min(next, Math.max(lineEnd, c[c.length - 1].at + 0.3)), words: c.map(({ w, at }) => ({ w, at })) };
  });
};

/** The lit item at t from a scene's beats ([{at, key}], times absolute): the last beat reached, else null. */
export const litAt = (beats, t) => {
  let cur = null;
  (beats || []).forEach((b) => { if (b.key != null && t >= b.at - 0.1) cur = b; });
  return cur;
};

/* ------------------------------------------------------------------------------------------------------------------
 * The `motion` prop: { t, start, end, lit, plan } handed to a visual by the Reel page only. Without it a visual draws
 * exactly as on its card. Each primitive returns the finished state (1, {}, the value) when motion is undefined, so
 * the card path is untouched, and also once the motion has played out, so "motion at its end" draws the same markup.
 * ---------------------------------------------------------------------------------------------------------------- */

const P = (m, key, d) => (m && m.plan && m.plan[key] != null ? m.plan[key] : d);

/**
 * Fractions snapped to steps of 1/64: a fade or fill mid-way through then lands on one of 64 opacities. Arbitrary
 * fractional opacities on many small overlapping marks (a cloud of dots, translucent wedges) left Chrome's raster
 * differing by a few levels between two draws of the same t; whole steps don't. 1/64 is finer than a 30fps frame's
 * change in a 0.35-0.6s entrance, so the motion reads the same.
 */
export const snap = (p) => (p >= 1 ? 1 : p <= 0 ? 0 : Math.round(p * 64) / 64);

/** reveal(m, i): the i-th row or mark entering, in reading order, 0.1s apart. 0..1. */
export const reveal = (m, i = 0) => {
  if (!m) return 1;
  const a = m.start + P(m, 'delay', 0.05) + i * P(m, 'stagger', 0.1);
  return snap(easeOut(progress(m.t, a, P(m, 'enter', 0.35))));
};

/** grow(m, i): a bar's length, 0..1, starting just after its row enters (from the par line: the caller draws from it). */
export const grow = (m, i = 0) => {
  if (!m) return 1;
  const a = m.start + P(m, 'delay', 0.05) + i * P(m, 'stagger', 0.1) + 0.1;
  return snap(easeOut(progress(m.t, a, P(m, 'grow', 0.6))));
};

/** draw(m, from, dur): an SVG path drawn left to right (stroke-dashoffset), 0..1 at constant speed. */
export const draw = (m, from = 0.1, dur = P(m, 'draw', 2.5)) => {
  if (!m) return 1;
  return progress(m.t, m.start + from, dur);
};

/** deal(m, i): a card dealt into a grid (overshoot), 0..~1.1. */
export const deal = (m, i = 0) => {
  if (!m) return 1;
  const a = m.start + P(m, 'delay', 0.05) + i * P(m, 'stagger', 0.08);
  return back(progress(m.t, a, 0.45));
};

/** ring(m, key): 0..1, the ring on the item the voice names (fades in over 0.3s from its beat). */
export const ring = (m, key) => {
  if (!m || !m.lit || key == null || m.lit.key !== key) return 0;
  return easeOut(progress(m.t, m.lit.at - 0.1, 0.3));
};

/** Styles for an entering item: {} once in (or with no motion), so the finished markup is the card's own. */
export const enterSx = (p, { dx = 0, dy = 12 } = {}) => (p >= 1 ? {} : {
  opacity: clamp(p * 1.6),
  transform: `translate(${(1 - p) * dx}px, ${(1 - p) * dy}px)`,
});

/**
 * countText(text, p): the first number inside a card's text ("+1.98", "₹16.30 crore", "54%") counted up to p of its
 * value, keeping its decimals, sign and the words around it. p >= 1 returns the text untouched.
 */
export const countText = (text, p) => {
  if (p >= 1 || text == null) return text;
  const str = String(text);
  const m = str.match(/(\d[\d,]*)(\.\d+)?/);
  if (!m) return str;
  const dp = m[2] ? m[2].length - 1 : 0;
  const v = Number((m[1] + (m[2] || '')).replace(/,/g, '')) * easeOut(p);
  const body = m[1].includes(',') ? v.toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp }) : v.toFixed(dp);
  return str.slice(0, m.index) + body + str.slice(m.index + m[0].length);
};

/** The ring style the cards use for "best"/"this one" (2px in the brightest text), at opacity k. {} when off. */
export const ringSx = (k, pulse = 0) => (k > 0 ? {
  outline: `2px solid ${alpha(colors.textHi, k)}`,
  outlineOffset: `${2 + Math.round(pulse * 5) / SCALE}px`, // whole canvas pixels (see drift)
} : {});

/**
 * The pulse of a held ring, 0..1: the ring breathes out and back once a second while its item is being read, so a lit
 * item is never a still picture (M7: something moves every 0.8s) without lighting anything the voice doesn't say.
 */
export const ringPulse = (m) => (m && m.lit ? (1 - Math.cos(2 * Math.PI * Math.max(0, m.t - m.lit.at))) / 2 : 0);

/** ringOn(m, key): the cards' ring on the item the voice names, breathing while it's read ({} with no motion). */
export const ringOn = (m, key) => ringSx(ring(m, key), ringPulse(m));

/**
 * camera(m, box): a slow drift on the whole visual, or a push in on one region of it ({x, y, s} in 0..1 of the visual and
 * a scale), then back out by the scene's end. Returns a CSS transform (with no motion: none).
 */
export const camera = (m, box) => {
  if (!m) return 'none';
  const span = Math.max(0.5, (m.end ?? m.start + 3) - m.start);
  // No region: the slow bob (drift), so the picture is never quite still. Translate, not scale: Chrome reuses a layer's
  // raster while its scale changes, so a per-frame scale made pixels depend on the previous frame.
  if (!box) return `translateY(${drift(m.t - m.start)}px)`;
  const inP = easeInOut(progress(m.t, box.at ?? m.start + 0.6 * span * 0.3, 0.6));
  const outP = box.out ? easeInOut(progress(m.t, box.out, 0.5)) : 0;
  const k = inP * (1 - outP);
  const s = lerp(1, box.s || 1.4, k);
  return `translate(${(0.5 - box.x) * 100 * k}%, ${(0.5 - box.y) * 100 * k}%) scale(${s})`;
};

/**
 * drift(dt): a slow bob dt seconds into a scene, in CSS px: up 12 canvas px and back every 4 seconds (6 px a second, a
 * triangle wave), so it never carries a visual into the kicker however long the scene. Whole canvas pixels (multiples
 * of 0.4 CSS px): a sub-pixel offset made the composited layer's pixels depend on the frame before. Off on a page
 * opened with ?nodrift=1 (setDrift(false)), which the still check records, so drift can't hide a still picture.
 */
let driftOn = true;
export const setDrift = (on) => { driftOn = Boolean(on); };
export const drift = (dt) => {
  if (!driftOn) return 0;
  const ph = Math.max(0, dt) % 4;
  return -Math.round(ph < 2 ? 6 * ph : 6 * (4 - ph)) / SCALE;
};

/* ------------------------------------------------------------------------------------------------------------------
 * Checks.
 * ---------------------------------------------------------------------------------------------------------------- */

const overlaps = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
/** The frame's own reading boxes (shifted), in canvas px. */
export const frameBoxes = () => [
  { name: 'chapters', ...FRAME.chapters },
  { name: 'kicker', ...FRAME.kicker },
  { name: 'content', ...FRAME.content },
  { name: 'caption', ...FRAME.caption },
];

/**
 * Problems with a reel spec, as strings (empty = fine): times in order, at most four chapters, one-line captions of
 * five words or fewer, length 28-33s, the closing scene's captions off, and no frame box in a keep-clear zone.
 */
export const validateReel = (spec) => {
  const out = [];
  if (!spec || !Array.isArray(spec.scenes) || !spec.scenes.length) return ['no scenes'];
  const d = spec.duration;
  const R = REEL_RULES;
  if (!(d >= R.lengthMin && d <= R.lengthMax)) out.push(`duration ${d}s is outside ${R.lengthMin}-${R.lengthMax}s`);
  if ((spec.chapters || []).length > 4) out.push('more than four chapters');
  spec.scenes.forEach((s, i) => {
    if (!(s.end > s.start)) out.push(`scene ${i} (${s.kind}) ends before it starts`);
    if (i && s.start < spec.scenes[i - 1].start) out.push(`scene ${i} starts before scene ${i - 1}`);
  });
  if (spec.scenes[0].start !== 0) out.push('the first scene must start at 0');
  spec.scenes.forEach((s, i) => {
    // Kickers shrink to fit one line; below 22px (canvas) they are too long to read: shorten them.
    if (s.kicker && fitSize(s.kicker, FRAME.kicker.w, 30, 'mono', 0.14) < R.kickerMinPx) out.push(`scene ${i} kicker is too long for one line`);
    const send = s.data && s.data.send && s.data.send.text;
    if (send && fitSize(send, FRAME.content.w, 66, 'display') < R.sendMinPx) out.push(`scene ${i} send line is too long for one line`);
  });
  const lastScene = spec.scenes[spec.scenes.length - 1];
  if (lastScene.captions !== false) out.push('the closing scene must set captions: false');
  (spec.captions || []).forEach((c, i) => {
    if ((c.words || []).length > R.captionWords) out.push(`caption ${i} has more than ${R.captionWords} words`);
    if ((c.words || []).map((w) => w.w).join(' ').length > R.captionChars) out.push(`caption ${i} is longer than ${R.captionChars} characters`);
  });
  frameBoxes().forEach((b) => FRAME.keepClear.forEach((k) => {
    if (overlaps(b, k)) out.push(`${b.name} box sits in the ${k.name}`);
  }));
  return out;
};
