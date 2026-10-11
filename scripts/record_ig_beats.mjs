// Record Reel v2 beats (services/ig_reel_v2.py): each slide's chart revealed frame by frame.
//
//   node scripts/record_ig_beats.mjs <carousel_id> <n,n,...> <out_dir> [--base URL] [--fps 30]
//
// Opens <base>/ig/<id>/<n>?animate=1 (src/components/ig/IgSlide.jsx), pauses its CSS animations and steps them:
// <out_dir>/<n>/<frame>.png at 1080x1350 for the length of the reveal, the last frame being the finished slide.
// Prints one JSON line: {"ok": {n: frames}, "failed": [...]}.
import { writeFileSync, mkdirSync } from 'node:fs';
import { openBrowser } from './lib/cdp.mjs';

const [id, list, out, ...rest] = process.argv.slice(2);
const opt = (k, d) => { const i = rest.indexOf(k); return i >= 0 ? rest[i + 1] : d; };
const base = opt('--base', 'https://hindsightcricket.com').replace(/\/$/, '');
const fps = Number(opt('--fps', '30'));
if (!id || !list || !out) {
  console.error('usage: node scripts/record_ig_beats.mjs <carousel_id> <n,n,...> <out_dir> [--base URL] [--fps 30]');
  process.exit(1);
}
const W = 432, H = 540, SCALE = 2.5, REVEAL_MS = 1400;
const browser = await openBrowser();
const result = { ok: {}, failed: [] };
try {
  for (const n of list.split(',').map(Number)) {
    const page = await browser.page({ width: W, height: H, scale: SCALE });
    await page.goto(`${base}/ig/${id}/${n}?animate=1&r=${Date.now()}`);
    const ready = await page.waitFor("document.querySelector('[data-ig-slide][data-ready=\"true\"]') !== null");
    if (!ready) { result.failed.push({ n, reason: 'not ready' }); await page.close(); continue; }
    mkdirSync(`${out}/${n}`, { recursive: true });
    const frames = Math.ceil((REVEAL_MS / 1000) * fps);
    for (let f = 0; f <= frames; f++) {
      const t = Math.min(REVEAL_MS, (f * 1000) / fps);
      await page.evaluate(`(() => { document.getAnimations().forEach((a) => { a.pause(); a.currentTime = ${t}; }); return true; })()`);
      writeFileSync(`${out}/${n}/${String(f).padStart(3, '0')}.png`, await page.screenshot({ x: 0, y: 0, width: W, height: H }));
    }
    result.ok[n] = frames + 1;
    await page.close();
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify(result));
