// UI sweep over every route via the Chrome DevTools Protocol (Node 22+, no dependencies).
//
//   node scripts/dev/ui_sweep.mjs <out_dir>                      # phone (390x844), live site
//   BASE=http://localhost:3000 node scripts/dev/ui_sweep.mjs out  # local dev server
//   WIDTH=1440 HEIGHT=900 node scripts/dev/ui_sweep.mjs out       # desktop
//   ONLY=player,venue_empty node scripts/dev/ui_sweep.mjs out     # subset of routes
//
// Writes a full-page PNG per route plus report.json: horizontal overflow and its offending
// elements, tap targets under 32px, text under 11px, body background, and failed requests.
//
// Why CDP and not `chrome --headless --screenshot --window-size=390,...`: headless Chrome will
// not lay a page out narrower than 500px, so plain screenshots at 390px are a 500px layout
// cropped — they show fake right-edge clipping on every page. Emulation.setDeviceMetricsOverride
// with mobile:true gives a real phone viewport (and touch + an iOS user agent below).
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';

const OUT = process.argv[2];
if (!OUT) {
  console.error('usage: node scripts/dev/ui_sweep.mjs <out_dir>');
  process.exit(1);
}
const B = process.env.BASE || 'https://hindsight2020.vercel.app';
const ROUTES = [
  ['home', '/'],
  ['search', '/search'],
  ['venue_empty', '/venue?venue=Korogi%20Sports%20Park%2C%20Nisshin&team1=AFG&team2=NEP&includeInternational=true&topTeams=20&autoload=true'],
  ['venue_full', '/venue?venue=Wankhede%20Stadium%2C%20Mumbai&team1=Mumbai%20Indians&team2=Chennai%20Super%20Kings&autoload=true'],
  ['player', '/player?name=V%20Kohli&autoload=true'],
  ['comparison', '/comparison'],
  ['matchups', '/matchups'],
  ['query', '/query'],
  ['query_res', '/query?batters=V%20Kohli&group_by=bowl_kind&autoload=true'],
  ['team', '/team?team=Mumbai%20Indians&autoload=true'],
  ['teamcomp', '/team-comparison'],
  ['doppel', '/doppelgangers'],
  ['iplpred', '/ipl-predictions'],
  ['rankings', '/rankings'],
  ['guess', '/games/guess-innings'],
  ['journeys', '/games/player-journeys'],
  ['wrapped', '/wrapped/2025'],
  ['credits', '/credits'],
  ['fantasy', '/fantasy-planner'],
  ['scorecard', '/scorecard/1530204'],
  ['preview_odi', '/venue?venue=Kingsmead%2C%20Durban&team1=Australia&team2=South%20Africa&includeInternational=true&topTeams=10&autoload=true&fmt=mens-odi'],
];
const W = Number(process.env.WIDTH || 390);
const H = Number(process.env.HEIGHT || 844);
const MOBILE = W < 768;
const MAX_H = 6000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
mkdirSync(OUT, { recursive: true });

const chrome = spawn(process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  `--user-data-dir=${OUT}/prof`, '--remote-debugging-port=9333', 'about:blank',
], { stdio: 'ignore' });

let wsUrl;
for (let i = 0; i < 40 && !wsUrl; i++) {
  await sleep(500);
  try { wsUrl = (await (await fetch('http://127.0.0.1:9333/json/version')).json()).webSocketDebuggerUrl; } catch {}
}
const ws = new WebSocket(wsUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map(); const listeners = [];
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  else listeners.forEach((l) => l(msg));
};
const send = (method, params = {}, sessionId) => new Promise((res) => {
  const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params, sessionId }));
});

const report = {};
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;
for (const [name, path] of ROUTES.filter(([n]) => !ONLY || ONLY.includes(n))) {
  const { result: { targetId } } = await send('Target.createTarget', { url: 'about:blank' });
  const { result: { sessionId } } = await send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => send(m, p, sessionId);
  const failures = [];
  const onMsg = (msg) => {
    if (msg.sessionId !== sessionId) return;
    if (msg.method === 'Network.responseReceived' && msg.params.response.status >= 400)
      failures.push(`${msg.params.response.status} ${msg.params.response.url.replace(/^https?:\/\/[^/]+/, '').slice(0, 120)}`);
    if (msg.method === 'Network.loadingFailed' && !msg.params.canceled)
      failures.push(`FAILED ${msg.params.errorText}`);
    if (msg.method === 'Runtime.exceptionThrown')
      failures.push(`JS ${msg.params.exceptionDetails.exception?.description?.split('\n')[0] || msg.params.exceptionDetails.text}`);
  };
  listeners.push(onMsg);
  await s('Network.enable'); await s('Runtime.enable'); await s('Page.enable');
  await s('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: MOBILE });
  if (MOBILE) await s('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  if (MOBILE) await s('Network.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1' });
  await s('Page.navigate', { url: B + path });
  await sleep(14000);
  const probe = await s('Runtime.evaluate', { returnByValue: true, expression: `(() => {
    const vw = window.innerWidth, sw = document.documentElement.scrollWidth;
    const off = [];
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.right <= vw + 1) continue;
      // Skip elements inside an intentional horizontal scroller (auto/scroll). Not 'hidden':
      // that clips content, which is exactly the bug -- and body has overflow-x: hidden, so
      // counting it hid every clipped card on the page.
      let p = el.parentElement, scrolled = false;
      while (p && p !== document.body) {
        const ox = getComputedStyle(p).overflowX;
        if ((ox === 'auto' || ox === 'scroll') && p.getBoundingClientRect().right <= vw + 1) { scrolled = true; break; }
        p = p.parentElement;
      }
      if (scrolled) continue;
      // Report the outermost offender only.
      const parentRect = el.parentElement && el.parentElement.getBoundingClientRect();
      if (parentRect && parentRect.right > vw + 1) continue;
      const cls = (el.className && typeof el.className === 'string') ? el.className.split(' ').filter(c => !c.startsWith('css-')).slice(0, 3).join('.') : '';
      off.push({ tag: el.tagName.toLowerCase(), cls, right: Math.round(r.right), w: Math.round(r.width), text: (el.innerText || '').trim().slice(0, 40) });
    }
    // Keep outermost offenders only.
    const small = [];
    const tiny = [...document.querySelectorAll('button, a, [role=button], input, [role=tab]')]
      .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.height < 32 || r.width < 32); }).length;
    const smallText = [...document.querySelectorAll('body *')].filter(e => e.childElementCount === 0 && (e.innerText||'').trim() && parseFloat(getComputedStyle(e).fontSize) < 11).length;
    return { vw, sw, docH: document.documentElement.scrollHeight, overflow: sw > vw + 1 || off.length > 0, offenders: off.slice(0, 8), tinyTapTargets: tiny, textUnder11px: smallText, bg: getComputedStyle(document.body).backgroundColor };
  })()` });
  const info = probe.result?.result?.value || {};
  const h = Math.min(info.docH || H, MAX_H);
  await s('Emulation.setDeviceMetricsOverride', { width: W, height: h, deviceScaleFactor: 1, mobile: MOBILE });
  await sleep(800);
  const shot = await s('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: W, height: h, scale: 1 } });
  if (shot.result?.data) writeFileSync(`${OUT}/${name}.png`, Buffer.from(shot.result.data, 'base64'));
  report[name] = { ...info, failures: [...new Set(failures)].slice(0, 12) };
  listeners.splice(listeners.indexOf(onMsg), 1);
  await send('Target.closeTarget', { targetId });
  console.log(name, JSON.stringify({ overflow: info.overflow, sw: info.sw, docH: info.docH, tiny: info.tinyTapTargets, small: info.textUnder11px, fails: report[name].failures.length }));
}
writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
ws.close(); chrome.kill();
process.exit(0);
