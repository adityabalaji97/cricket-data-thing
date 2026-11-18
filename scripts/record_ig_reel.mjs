// Record a motion Reel (src/components/ig/reel/IgReel.jsx, MOTION_REEL_PLAN.md M1) frame by frame from its clock.
//
//   node scripts/record_ig_reel.mjs --spec reel.json [--base http://localhost:3000] [--out dir] [--mp4 out.mp4]
//   node scripts/record_ig_reel.mjs --id <carousel_id> ...         the spec from the carousel's snapshot (data.reel)
//
// Options: --fps 30 · --from 0 --to <duration> · --stills 0,0.5,1,... (PNG stills into --out, plus contact.png)
//   --audio voice.mp3 (muxed with loudnorm, as the finished Reels) · --format jpeg|png (frame capture, default jpeg)
//   --check (render five times twice, out of order, and compare bytes) · --guides (draw the keep-clear zones)
//   --nodrift (the slow bob off: record this way for scripts/check_ig_reel.py --video, so the still check sees stills)
//   --port 9361 (Chrome's DevTools port) · --stills-only
// The page is 432 x 768 CSS px at device scale 2.5: frames are 1080 x 1920. Prints one JSON line:
//   {frames, seconds, ms_per_frame, record_s, encode_s, stills, check}
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { openBrowser } from './lib/cdp.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const flag = (k) => args.includes(k);
const base = opt('--base', 'http://localhost:3000').replace(/\/$/, '');
const specPath = opt('--spec');
const id = opt('--id');
if (!specPath && !id) {
  console.error('usage: node scripts/record_ig_reel.mjs (--spec reel.json | --id <carousel>) [--base URL] [--mp4 out.mp4] [--stills 0,1.5,...]');
  process.exit(1);
}
const fps = Number(opt('--fps', '30'));
const out = resolve(opt('--out', 'reel_out'));
const mp4 = opt('--mp4');
const audio = opt('--audio');
const format = opt('--format', 'jpeg');
const stills = (opt('--stills', '') || '').split(',').filter(Boolean).map(Number);
const W = 432, H = 768, SCALE = 2.5;
mkdirSync(out, { recursive: true });

const t0 = Date.now();
const browser = await openBrowser({ port: Number(opt('--port', '9361')) });
const result = {};
try {
  const page = await browser.page({ width: W, height: H, scale: SCALE });
  const q = `?r=${Date.now()}${flag('--guides') ? '&guides=1' : ''}${flag('--nodrift') ? '&nodrift=1' : ''}`;
  await page.goto(id ? `${base}/ig/${id}/reel${q}` : `${base}/ig/reel${q}`);
  if (!(await page.waitFor('typeof window.setReel === "function" || typeof window.renderAt === "function"', 90000))) throw new Error('reel page did not load');
  let allow = [];
  if (specPath) {
    const spec = JSON.parse(readFileSync(specPath, 'utf8'));
    allow = spec.checkAllow || [];
    await page.evaluate(`window.setReel(${JSON.stringify(spec)})`);
  }
  if (!(await page.waitFor("document.querySelector('[data-ig-reel][data-reel-ready=\"true\"]') !== null", 90000))) throw new Error('reel not ready');
  const duration = await page.evaluate('window.REEL_DURATION');
  // One throwaway frame after ready: the first paint after load can differ by a few antialiased pixels from every
  // later paint of the same t (seen at a transformed card's ring), so nothing recorded is the very first paint.
  // Then a warm-up pass: every scene drawn once (0.6s in), and the fonts settled again. A face's unicode-range subset
  // can still arrive after document.fonts.load() for text the visuals write themselves, so without this the first
  // draw of a late scene could differ from a later draw of the same t (seen intermittently on ₹ and some letters).
  const warm = ((await page.evaluate('window.REEL_SCENE_STARTS')) || []).map((s) => s + 0.6);
  for (const t of [0, ...warm]) {
    await page.evaluate(`window.renderAt(${t})`);
    await page.screenshot({ x: 0, y: 0, width: W, height: H }, { format: 'png' });
  }
  await page.waitFor("document.fonts.status === 'loaded'", 30000);
  await page.evaluate('window.renderAt(0)');
  await page.screenshot({ x: 0, y: 0, width: W, height: H }, { format: 'png' });
  const from = Number(opt('--from', '0'));
  const to = Math.min(Number(opt('--to', String(duration))), duration);
  const clip = { x: 0, y: 0, width: W, height: H };
  const frame = async (t, fmt = format) => {
    await page.evaluate(`window.renderAt(${t})`);
    return page.screenshot(clip, { format: fmt });
  };

  if (flag('--check')) {
    // The same t twice, out of order, must give the same bytes.
    // Run before anything else is drawn, so each scene's first use of its fonts is among the frames compared: the
    // first pass draws every scene for the first time (0.6s in), late scenes first; the second pass repeats them.
    const starts = (await page.evaluate('window.REEL_SCENE_STARTS')) || [];
    const ts = [...new Set([...starts.map((s) => Math.min(to, s + 0.6)).reverse(), 0, 1.5, Math.max(0, to - 1)])];
    const first = [];
    for (const t of ts) first.push((await frame(t, 'png')).toString('base64'));
    const second = {};
    for (const t of [...ts].reverse()) second[t] = (await frame(t, 'png')).toString('base64');
    const bad = ts.filter((t, i) => second[t] !== first[i]);
    // A differing pair is saved (check_<t>_1.png, _2.png, t to 2 decimals) to see what moved.
    const name = (t, k) => join(out, `check_${t.toFixed(2)}_${k}.png`);
    bad.forEach((t) => {
      writeFileSync(name(t, 1), Buffer.from(first[ts.indexOf(t)], 'base64'));
      writeFileSync(name(t, 2), Buffer.from(second[t], 'base64'));
    });
    // How big each difference is, per channel (a colour swap at the same brightness counts): pixels that differ, the
    // largest channel difference, and their bounding box in canvas px. Headless Chrome's software raster can leave a
    // few antialiased pixels different between two draws of identical content (seen: 1-2 levels of 255 on SVG dashes
    // and stroked circles; 1 level over whole areas faded with group opacity). A difference of 1 level anywhere, or up
    // to 50 pixels at 2-3 levels, passes, reported as raster noise with its box;
    // anything more is a real difference.
    const measure = (t) => {
      const w = W * SCALE;
      const raw = execFileSync('ffmpeg', ['-loglevel', 'error', '-i', name(t, 1), '-i', name(t, 2),
        '-filter_complex', '[0][1]blend=all_mode=difference,format=rgb24', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { maxBuffer: 64 * 1024 * 1024 });
      let px = 0; let max = 0; let x0 = Infinity; let y0 = Infinity; let x1 = -1; let y1 = -1;
      for (let i = 0; i < raw.length; i += 3) {
        const m = Math.max(raw[i], raw[i + 1], raw[i + 2]);
        if (!m) continue;
        px += 1; if (m > max) max = m;
        const x = (i / 3) % w; const y = Math.floor(i / 3 / w);
        x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
      }
      return { t: Number(t.toFixed(2)), px, max, box: [x0, y0, x1, y1] };
    };
    const sizes = bad.map(measure);
    const fmtD = (d) => `${d.t} (${d.px}px, max ${d.max}, box ${d.box.join(',')}${d.allowed ? `, allowed: ${d.allowed}` : ''})`;
    // A spec may list known raster differences it has looked into (checkAllow: [{t, px, max, reason}]): one at that t,
    // no bigger than listed, is reported as allowed with its reason, never silently; nothing else is loosened.
    const allowed = (d) => allow.find((a) => Math.abs(a.t - d.t) < 0.01 && d.px <= a.px && d.max <= a.max);
    sizes.forEach((d) => { const a = allowed(d); if (a) d.allowed = a.reason; });
    const real = sizes.filter((d) => !d.allowed && (d.max > 3 || (d.max > 1 && d.px > 50)));
    result.check = !bad.length ? 'identical' : real.length ? `differs at ${real.map(fmtD).join('; ')}`
      : `identical but raster noise at ${sizes.map(fmtD).join('; ')}`;
  }

  for (const t of stills) writeFileSync(join(out, `t${t.toFixed(1).padStart(4, '0')}.png`), await frame(t, 'png'));
  if (stills.length) {
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-pattern_type', 'glob', '-i', join(out, 't*.png'),
      '-vf', `scale=270:480,pad=276:486:3:3:color=0x303540,tile=${Math.min(stills.length, 8)}x${Math.ceil(stills.length / 8)}:color=0x303540`,
      '-frames:v', '1', join(out, 'contact.png')]);
    result.stills = stills.length;
  }

  if (mp4 && !flag('--stills-only')) {
    const n = Math.ceil((to - from) * fps);
    const enc = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', format === 'jpeg' ? 'mjpeg' : 'png', '-i', '-'];
    if (audio) enc.push('-i', audio, '-filter_complex', `[1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:${(to - from).toFixed(3)},loudnorm=I=-16:TP=-1.5:LRA=11[a]`, '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000');
    enc.push('-t', (to - from).toFixed(3), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(fps), '-movflags', '+faststart', resolve(mp4));
    const ff = spawn('ffmpeg', enc, { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise((r, j) => ff.on('exit', (c) => (c === 0 ? r() : j(new Error(`ffmpeg exited ${c}`)))));
    const tr = Date.now();
    for (let f = 0; f < n; f++) {
      const buf = await frame(from + f / fps);
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    }
    result.record_s = (Date.now() - tr) / 1000;
    ff.stdin.end();
    const te = Date.now();
    await done;
    Object.assign(result, { frames: n, seconds: to - from, ms_per_frame: Math.round((result.record_s * 1000) / n), encode_s: (Date.now() - te) / 1000 });
  }
  if (browser.errors.length) result.page_errors = browser.errors.slice(0, 5);
} finally {
  await browser.close();
}
result.wall_s = (Date.now() - t0) / 1000;
console.log(JSON.stringify(result));
