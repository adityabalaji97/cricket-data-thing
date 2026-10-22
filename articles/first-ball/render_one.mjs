import { writeFileSync } from 'node:fs';
import { openBrowser } from '../../scripts/lib/cdp.mjs';
// node articles/first-ball/render_one.mjs <carousel> <n> <out.png> [base]: one slide, waiting up to 3 min for it to be ready
const [id, n, out, base = 'https://hindsightcricket.com'] = process.argv.slice(2);
const b = await openBrowser();
const p = await b.page({ width: 432, height: 540, scale: 2.5 });
await p.goto(`${base}/ig/${id}/${n}?r=${Date.now()}`);
const ok = await p.waitFor("document.querySelector('[data-ig-slide][data-ready=\"true\"]') !== null", 180000);
if (!ok) await new Promise(r => setTimeout(r, 3000));
writeFileSync(out, await p.screenshot({ x: 0, y: 0, width: 432, height: 540 }));
console.log(ok ? 'ready' : 'forced');
await b.close();
