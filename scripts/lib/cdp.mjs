// A small headless-Chrome session over the DevTools protocol (no puppeteer): launch, open a page, wait for a
// selector, screenshot. Used by scripts/render_ig_slides.mjs. CHROME overrides the browser path (google-chrome on
// Linux runners).
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const DEFAULT_CHROME = process.platform === 'darwin'
  ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'google-chrome';

export async function openBrowser({ port = 9335 } = {}) {
  const profile = mkdtempSync(join(tmpdir(), 'hindsight-cdp-'));
  const chrome = spawn(process.env.CHROME || DEFAULT_CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-sandbox',
    `--user-data-dir=${profile}`, `--remote-debugging-port=${port}`, 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  chrome.stderr.on('data', (d) => { stderr = (stderr + d).slice(-2000); });
  let wsUrl;
  for (let i = 0; i < 120 && !wsUrl; i++) { // up to 30 s: a cold start with a fresh profile can be slow
    await sleep(250);
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).webSocketDebuggerUrl; } catch { /* starting */ }
  }
  if (!wsUrl) { chrome.kill(); throw new Error(`Chrome did not start: ${stderr.trim().slice(-600)}`); }
  const ws = new WebSocket(wsUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0;
  const pending = new Map();
  const errors = [];
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails?.exception?.description || 'exception');
  };
  const send = (method, params = {}, sessionId) => new Promise((res) => {
    const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params, sessionId }));
  });

  async function page({ width, height, scale = 1 }) {
    const { result: { targetId } } = await send('Target.createTarget', { url: 'about:blank' });
    const { result: { sessionId } } = await send('Target.attachToTarget', { targetId, flatten: true });
    const s = (m, p) => send(m, p, sessionId);
    await s('Page.enable'); await s('Runtime.enable');
    await s('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: scale, mobile: true });
    const evaluate = async (expression) => (await s('Runtime.evaluate', { expression, returnByValue: true }))?.result?.result?.value;
    return {
      goto: (url) => s('Page.navigate', { url }),
      async waitFor(expression, timeoutMs = 30000) {
        const until = Date.now() + timeoutMs;
        while (Date.now() < until) { if (await evaluate(expression)) return true; await sleep(200); }
        return false;
      },
      evaluate,
      async screenshot(clip) {
        const r = await s('Page.captureScreenshot', { format: 'png', clip: { ...clip, scale: 1 }, captureBeyondViewport: false });
        return Buffer.from(r.result.data, 'base64');
      },
      close: () => send('Target.closeTarget', { targetId }),
    };
  }

  return {
    page,
    errors,
    async close() {
      try { ws.close(); } catch { /* closed */ }
      // Chrome keeps writing its profile for a moment after the kill: wait for it to exit, then tidy up best-effort.
      const exited = new Promise((r) => chrome.once('exit', r));
      chrome.kill();
      await Promise.race([exited, sleep(3000)]);
      try { rmSync(profile, { recursive: true, force: true, maxRetries: 3 }); } catch { /* left in the temp dir */ }
    },
  };
}
