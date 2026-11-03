// A page as a phone sees it, screen by screen: true mobile emulation (390x844, 2x) over CDP, scrolled once to the
// bottom so lazy sections load, then captured one viewport at a time.
//
//   node scripts/mobile_page_shot.mjs <url> <out_dir> [--settle 12] [--click TEXT] [--expand]
//
// --click TEXT: click the first button whose text is TEXT first (e.g. BOWLING); --expand: open every collapsed
// section (aria-expanded="false") so its content is in the captures.
//
// Saves <out_dir>/01.png, 02.png, ... and <out_dir>/sections.json: every heading on the page (h1-h4 and elements
// marked [data-section]) with its offset from the top, for an inventory of what the page shows.
import { writeFileSync, mkdirSync } from 'node:fs';
import { openBrowser } from './lib/cdp.mjs';

const [url, out, ...rest] = process.argv.slice(2);
const settleAt = rest.indexOf('--settle');
const settle = settleAt >= 0 ? Number(rest[settleAt + 1]) : 12;
const clickAt = rest.indexOf('--click');
const clickText = clickAt >= 0 ? rest[clickAt + 1] : null;
const expand = rest.includes('--expand');
if (!url || !out) {
  console.error('usage: node scripts/mobile_page_shot.mjs <url> <out_dir> [--settle seconds]');
  process.exit(1);
}
const W = 390, H = 844, SCALE = 2;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
mkdirSync(out, { recursive: true });
const browser = await openBrowser({ port: 9337 });
try {
  const page = await browser.page({ width: W, height: H, scale: SCALE });
  await page.goto(url);
  await sleep(settle * 1000);
  if (clickText) {
    await page.evaluate(`(() => { const b = [...document.querySelectorAll('button,[role=tab]')]
      .find((el) => el.innerText.trim().toUpperCase() === ${JSON.stringify(clickText.toUpperCase())}); if (b) b.click(); return !!b; })()`);
    await sleep(6000);
  }
  if (expand) {
    for (let round = 0; round < 3; round++) {
      await page.evaluate(`[...document.querySelectorAll('button[aria-expanded="false"]')].forEach((b) => b.click())`);
      await sleep(3000);
    }
  }
  // Scroll to the bottom in steps so anything that loads on sight loads, then back to the top.
  for (let i = 0; i < 40; i++) {
    const done = await page.evaluate(`(() => { const y = window.scrollY + ${H}; window.scrollTo(0, y);
      return window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2; })()`);
    await sleep(1200);
    if (done) break;
  }
  await sleep(2000);
  await page.evaluate('window.scrollTo(0, 0)');
  await sleep(1000);
  const height = await page.evaluate('document.documentElement.scrollHeight');
  const sections = await page.evaluate(`JSON.stringify([...document.querySelectorAll('h1,h2,h3,h4,[data-section]')]
    .map((el) => ({ tag: el.tagName.toLowerCase(), text: (el.getAttribute('data-section') || el.innerText || '').trim().slice(0, 80),
                    top: Math.round(el.getBoundingClientRect().top + window.scrollY) }))
    .filter((s) => s.text))`);
  writeFileSync(`${out}/sections.json`, JSON.stringify({ url, height, sections: JSON.parse(sections || '[]') }, null, 1));
  let n = 0;
  for (let y = 0; y < height; y += H - 80) {  // 80px overlap so nothing falls between two screens
    await page.evaluate(`window.scrollTo(0, ${y})`);
    await sleep(700);
    n += 1;
    writeFileSync(`${out}/${String(n).padStart(2, '0')}.png`, await page.screenshot({ x: 0, y: await page.evaluate('window.scrollY'), width: W, height: H }));
  }
  console.log(JSON.stringify({ url, height, screens: n, errors: browser.errors.slice(-5) }));
} finally {
  await browser.close();
}
