import fs from 'fs';
import path from 'path';
import {
  FRAME, activeCaption, activeScene, back, captionsFromTiming, clamp, countUp, easeOut, enterSx, grow, lift, litAt,
  progress, reveal, ring, u, validateReel,
} from './motion';

describe('motion helpers', () => {
  test('u turns canvas px into CSS px at 2.5', () => {
    expect(u(1080)).toBe(432);
    expect(u(1920)).toBe(768);
  });
  test('clamp, progress, easing', () => {
    expect(clamp(2)).toBe(1);
    expect(progress(1, 0, 2)).toBe(0.5);
    expect(progress(-1, 0, 2)).toBe(0);
    expect(progress(1, 1, 0)).toBe(1);
    expect(easeOut(1)).toBe(1);
    expect(easeOut(0)).toBe(0);
    expect(back(1)).toBeCloseTo(1);
  });
  test('countUp lands exactly on its value', () => {
    expect(countUp(1.98, 1, 2)).toBe(1.98);
    expect(countUp(1.98, 0, 2)).toBe(0);
    expect(countUp(10, 0.5, 0)).toBe(9);
  });
  test('activeScene and lift', () => {
    const scenes = [{ start: 0 }, { start: 4 }, { start: 8 }];
    expect(activeScene(scenes, 0)).toBe(0);
    expect(activeScene(scenes, 5)).toBe(1);
    expect(lift(0, 0, 4).o).toBe(1); // frame 0 is never empty
    expect(lift(4, 0, 4).o).toBe(0);
    expect(lift(3.5, 4, 8).o).toBe(0);
    expect(lift(4.4, 4, 8).o).toBeCloseTo(1, 1);
    expect(lift(100, 8, 12, { last: true }).o).toBe(1);
  });
  test('captions: five words at most, the spoken word lit, off in a captions:false scene', () => {
    const timing = { lines: ['Bumrah added 1.98 wins since the auction.', 'Keep or release?'], starts: [0, 4], lengths: [2.5, 1],
      words: [[0, 0.4, 0.8, 1.2, 1.6, 2, 2.3], [4, 4.3, 4.6]] };
    const caps = captionsFromTiming(timing);
    caps.forEach((c) => expect(c.words.length).toBeLessThanOrEqual(5));
    const line = activeCaption(caps, 0.5, null);
    expect(line.words.filter((w) => w.on).map((w) => w.w)).toEqual(['added']);
    const scenes = [{ start: 0 }, { start: 3.9, captions: false }];
    expect(activeCaption(caps, 4.3, scenes)).toBeNull();
  });
  test('litAt follows the beats', () => {
    const beats = [{ at: 1, key: 'a' }, { at: 2, key: 'b' }];
    expect(litAt(beats, 0.5)).toBeNull();
    expect(litAt(beats, 1.5).key).toBe('a');
    expect(litAt(beats, 3).key).toBe('b');
  });
  test('primitives give the finished state with no motion (the card path)', () => {
    expect(reveal(undefined, 3)).toBe(1);
    expect(grow(undefined, 3)).toBe(1);
    expect(ring(undefined, 'x')).toBe(0);
    expect(enterSx(1)).toEqual({});
    const m = { t: 0, start: 0 };
    expect(reveal(m, 0)).toBe(0);
    expect(reveal({ t: 10, start: 0 }, 5)).toBe(1);
  });
  test('validateReel: the frame keeps out of the keep-clear zones; a good spec passes', () => {
    const spec = { duration: 30, chapters: [{ start: 0, end: 30 }],
      scenes: [{ kind: 'hero', start: 0, end: 27 }, { kind: 'pick_one', start: 27, end: 30, captions: false }], captions: [] };
    expect(validateReel(spec)).toEqual([]);
    expect(validateReel({ ...spec, duration: 40 })).toHaveLength(1);
    expect(validateReel({ ...spec, scenes: [spec.scenes[0], { ...spec.scenes[1], captions: true }] })[0]).toMatch(/captions: false/);
    // The posted round-2 Reel, as a spec, passes with its own voice timing.
    // eslint-disable-next-line global-require
    const r2 = require('./__fixtures__/smat_round2.reel.json');
    expect(validateReel({ ...r2, captions: captionsFromTiming(r2.timing) })).toEqual([]);
    expect(FRAME.content.y).toBeGreaterThanOrEqual(470);
    expect(FRAME.caption.y + FRAME.caption.h).toBeLessThanOrEqual(1600);
  });
});

describe('pure in t', () => {
  // The recorder may render frames in any order: nothing in the reel folder may keep time on its own.
  const files = [];
  const walk = (dir) => fs.readdirSync(dir).forEach((f) => {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) walk(p);
    else if (/\.(jsx?|css)$/.test(f) && !/\.test\./.test(f)) files.push(p);
  });
  walk(__dirname);
  test.each(files.map((f) => [path.relative(__dirname, f), f]))('%s has no transitions, animations, timers or wall clock', (_, f) => {
    // (switching them off, "transition: 'none !important'", is allowed: IgReel does it for library components)
    const src = fs.readFileSync(f, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')
      .replace(/(transition|animation): 'none !important'/g, '');
    expect(src).not.toMatch(/\btransition\s*:|\banimation\s*:|@keyframes|setTimeout|setInterval|Date\.now|performance\.now|new Date\(/);
  });
});
