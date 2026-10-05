// Scripted phone-sized browser session over CDP (headless Chrome), for checking flows by hand.
//
//   node scripts/dev/interact.mjs <out_dir> <steps.json>
//
// steps.json is an array of steps, each one of:
//   {"nav": url} {"wait": ms} {"shot": name} {"eval": js, "label": text}
//   {"click": css} {"text": exact button/link text}  -- clicks the first visible match
//   {"setDate": {"sel": css, "value": v}}             -- sets an input via React's value setter
// Prints one line per click/eval/setDate result, and page exceptions (ERRORS=1 adds console.error). WIDTH/HEIGHT override the 390x844 viewport.
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const [OUT, STEPS] = process.argv.slice(2);
if (!OUT || !STEPS) {
  console.error('usage: node scripts/dev/interact.mjs <out_dir> <steps.json>');
  process.exit(1);
}
mkdirSync(OUT, { recursive: true });
const steps = JSON.parse(readFileSync(STEPS, 'utf8'));
const W = Number(process.env.WIDTH || 390);
const H = Number(process.env.HEIGHT || 844);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  `--user-data-dir=${OUT}/prof`, '--remote-debugging-port=9334', 'about:blank',
], { stdio: 'ignore' });

let wsUrl;
for (let i = 0; i < 40 && !wsUrl; i++) {
  await sleep(500);
  try { wsUrl = (await (await fetch('http://127.0.0.1:9334/json/version')).json()).webSocketDebuggerUrl; } catch {}
}
const ws = new WebSocket(wsUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pending = new Map();
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  // Page errors: uncaught exceptions, and console.error with ERRORS=1.
  if (msg.method === 'Runtime.exceptionThrown') {
    const d = msg.params.exceptionDetails;
    console.log(`page exception: ${d.exception?.description || d.text}`.slice(0, 1500));
  }
  if (process.env.ERRORS && msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
    console.log(`console.error: ${msg.params.args.map((a) => a.value ?? a.description ?? '').join(' ')}`.slice(0, 1500));
  }
};
const send = (method, params = {}, sessionId) => new Promise((res) => {
  const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params, sessionId }));
});

const { result: { targetId } } = await send('Target.createTarget', { url: 'about:blank' });
const { result: { sessionId } } = await send('Target.attachToTarget', { targetId, flatten: true });
const s = (m, p) => send(m, p, sessionId);
await s('Page.enable'); await s('Runtime.enable');
await s('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 768 });
if (W < 768) await s('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });

const evaluate = async (expression) => {
  const r = await s('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  return r.result?.exceptionDetails ? String(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text)
    : r.result?.result?.value;
};

for (const step of steps) {
  if (step.nav) await s('Page.navigate', { url: step.nav });
  if (step.wait) await sleep(step.wait);
  if (step.shot) {
    const r = await s('Page.captureScreenshot', { format: 'png' });
    writeFileSync(`${OUT}/${step.shot}.png`, Buffer.from(r.result.data, 'base64'));
  }
  if (step.click || step.text) {
    const finder = step.click
      ? `[...document.querySelectorAll(${JSON.stringify(step.click)})]`
      : `[...document.querySelectorAll('button, [role=button], a, [role=tab], li')].filter(e => (e.innerText || '').trim() === ${JSON.stringify(step.text)})`;
    const res = await evaluate(`(() => { const el = ${finder}.find(e => e.getBoundingClientRect().width > 0);
      if (!el) return 'NOT FOUND'; el.scrollIntoView({block: 'center'}); el.click(); return 'clicked ' + el.tagName + ' ' + (el.innerText || '').slice(0, 40); })()`);
    console.log(`${JSON.stringify(step.click ? { click: step.click } : { text: step.text })} -> ${res}`);
  }
  if (step.setDate) {
    const res = await evaluate(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(step.setDate.sel)})].find(e => e.getBoundingClientRect().width > 0);
      if (!el) return 'NOT FOUND';
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(el, ${JSON.stringify(step.setDate.value)}); el.dispatchEvent(new Event('input', { bubbles: true })); return 'set ' + el.value; })()`);
    console.log(`setDate -> ${res}`);
  }
  if (step.eval) console.log(`eval ${step.label || ''} -> ${JSON.stringify(await evaluate(step.eval))}`);
}

ws.close();
chrome.kill();
process.exit(0);
