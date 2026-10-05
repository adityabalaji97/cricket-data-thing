// Render an Instagram carousel's slides from the app's own components (src/components/ig/IgSlide.jsx).
//
//   node scripts/render_ig_slides.mjs <carousel_id> <slide_count> <out_dir> [--base https://hindsightcricket.com]
//
// Opens <base>/ig/<id>/<n> at 432x540 CSS px with a 2.5x device scale and saves <out_dir>/<n>.png (1080x1350).
// Prints one JSON line: {"ok": [...files], "failed": [...]}. services/ig_slides stores the PNGs (Python side).
import { writeFileSync, mkdirSync } from 'node:fs';
import { openBrowser } from './lib/cdp.mjs';

const [id, countArg, out, ...rest] = process.argv.slice(2);
const baseAt = rest.indexOf('--base');
const base = (baseAt >= 0 ? rest[baseAt + 1] : 'https://hindsightcricket.com').replace(/\/$/, '');
if (!id || !countArg || !out) {
  console.error('usage: node scripts/render_ig_slides.mjs <carousel_id> <slide_count> <out_dir> [--base URL]');
  process.exit(1);
}
const W = 432, H = 540, SCALE = 2.5;
mkdirSync(out, { recursive: true });
const browser = await openBrowser();
const result = { ok: [], failed: [] };
try {
  for (let n = 1; n <= Number(countArg); n++) {
    const page = await browser.page({ width: W, height: H, scale: SCALE });
    await page.goto(`${base}/ig/${id}/${n}?r=${Date.now()}`);
    const ready = await page.waitFor("document.querySelector('[data-ig-slide][data-ready=\"true\"]') !== null");
    if (!ready) { result.failed.push({ n, reason: 'not ready', errors: browser.errors.slice(-3) }); await page.close(); continue; }
    const file = `${out}/${n}.png`;
    writeFileSync(file, await page.screenshot({ x: 0, y: 0, width: W, height: H }));
    result.ok.push(file);
    await page.close();
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify(result));
