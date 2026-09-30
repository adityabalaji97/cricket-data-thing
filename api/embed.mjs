/**
 * Embeddable charts: /embed/{q|wp|recap}/:snapshotId -> self-contained HTML for an iframe.
 *
 * A snapshot (services/snapshots.py) is frozen data, so an embed never re-runs a query per
 * viewer and the page is cached hard at the edge. No React bundle: it loads fast on any site.
 *
 *   q      the connector's chart/table widget (mcp_server/widget.html) in its static mode
 *   wp     win-probability path, as inline SVG (the scorecard's Impact card, minus the app)
 *   recap  "how it was won": headline and bullets
 *
 * Every embed posts {type:'hindsight:resize', height} to its parent so the host can size the
 * frame, links back with utm_source=embed, and logs one embed_view event with the host site.
 */
import { readFileSync } from 'node:fs';
import { getJSON, SITE_URL } from './_lib/share.mjs';

const WIDGET = readFileSync(new URL('../mcp_server/widget.html', import.meta.url), 'utf8');
const ID = /^[A-Za-z0-9]{6,16}$/;
const KIND_FOR = { q: 'query', wp: 'win_prob', recap: 'recap' };

const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// JSON inside a <script>: escape "<" so a value can never close the tag.
const inlineJSON = (v) => JSON.stringify(v).replace(/</g, '\\u003c');

const withUtm = (url) => {
  const u = new URL(url, SITE_URL);
  u.searchParams.set('utm_source', 'embed');
  return u.toString();
};

const asOf = (snap) => new Date(snap.created_at || Date.now())
  .toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

// Reports height and logs the view. Shared by all three kinds; the q widget reports its own
// height, so it only needs the event half.
function runtime(snap, kind, { resize = true } = {}) {
  return `<script>
(function () {
  ${resize ? `function size() { parent.postMessage({ type: "hindsight:resize", height: Math.ceil(document.body.getBoundingClientRect().height) }, "*"); }
  if (window.ResizeObserver) new ResizeObserver(size).observe(document.body); size();` : ''}
  try {
    var host = ""; try { host = new URL(document.referrer).hostname; } catch (e) {}
    fetch("/api/events", { method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true,
      body: JSON.stringify({ anon_id: "embed-" + Math.random().toString(36).slice(2, 12), referrer: document.referrer.slice(0, 200) || null,
        events: [{ event: "embed_view", path: location.pathname, props: { kind: ${inlineJSON(kind)}, id: ${inlineJSON(snap.id)}, host: host } }] }) }).catch(function () {});
  } catch (e) {}
})();
</script>`;
}

const PAGE_CSS = `
  :root { --bg:#0a0c11; --surface:#14171e; --hi:#f3f4f6; --med:#c3c8d0; --lo:#9aa1ac; --accent:#b6f24a; --red:#e5484d; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--hi); font: 14px/1.45 "Barlow", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .wrap { padding: 14px 16px 12px; }
  .kicker { font: 600 10px/1 ui-monospace, monospace; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 6px; }
  h1 { font-size: 17px; margin: 0 0 4px; line-height: 1.25; }
  .sub { color: var(--lo); font-size: 12px; }
  ul { margin: 12px 0 4px; padding-left: 18px; }
  li { color: var(--med); margin-bottom: 8px; }
  li::marker { color: var(--accent); }
  svg { display: block; width: 100%; height: auto; margin-top: 10px; }
  .axis { display: flex; justify-content: space-between; color: var(--lo); font-size: 11px; margin-top: 4px; }
  .scores { margin-top: 10px; }
  .scores div { display: flex; justify-content: space-between; font-weight: 600; }
  .foot { display: flex; justify-content: space-between; gap: 12px; margin-top: 12px; padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,.08); font-size: 11px; color: var(--lo); }
  .foot a { color: var(--accent); text-decoration: none; font-weight: 600; white-space: nowrap; }
`;

function page(snap, kind, title, body, openUrl) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} · Hindsight</title><meta name="robots" content="noindex"><style>${PAGE_CSS}</style></head>
<body><div class="wrap">${body}
<div class="foot"><span>Data as of ${esc(asOf(snap))} · Hindsight</span><a href="${esc(withUtm(openUrl))}" target="_blank" rel="noopener">Open live ↗</a></div>
</div>${runtime(snap, kind)}</body></html>`;
}

function matchKicker(d) {
  return [d.competition, d.date && d.date !== 'None' ? d.date : null].filter(Boolean).join(' · ');
}

function winProbHtml(snap) {
  const d = snap.data || {};
  const wp = d.primer?.win_probability || {};
  const points = wp.points || [];
  const W = 600, H = 240, n = Math.max(1, points.length - 1);
  const x = (i) => ((i / n) * W).toFixed(1);
  const y = (p) => (H - p * H).toFixed(1);
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p)}`).join(' ');
  const teams = d.teams || [];
  const first = wp.team;
  const second = (d.scores || []).find((s) => s.team !== first)?.team || teams.find((t) => t.name !== first)?.name || '';
  const color = (name, fb) => teams.find((t) => t.name === name)?.accent || fb;
  const c1 = color(first, '#b6f24a');
  const brk = wp.innings_break ? `<line x1="${x(wp.innings_break)}" y1="0" x2="${x(wp.innings_break)}" y2="${H}" stroke="rgba(255,255,255,.35)" stroke-width="1.5"/>` : '';
  const wkts = (wp.wickets || []).map((i) => `<circle cx="${x(i)}" cy="${y(points[i] ?? 0.5)}" r="4" fill="#e5484d"/>`).join('');
  const svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Win probability by ball">
    <rect width="${W}" height="${H}" fill="#14171e"/>
    <line x1="0" y1="${H / 2}" x2="${W}" y2="${H / 2}" stroke="rgba(255,255,255,.22)" stroke-dasharray="5 5"/>
    <path d="${line} L${W},${H} L0,${H} Z" fill="${esc(c1)}" fill-opacity=".18"/>
    <path d="${line}" fill="none" stroke="${esc(c1)}" stroke-width="2.5"/>${brk}${wkts}</svg>`;
  const scores = (d.scores || []).map((s) => `<div><span style="color:${esc(color(s.team, '#c3c8d0'))}">${esc(s.team)}</span><span>${esc(`${s.runs}/${s.wickets} (${s.overs})`)}</span></div>`).join('');
  const body = `<div class="kicker">Win probability${matchKicker(d) ? ' · ' + esc(matchKicker(d)) : ''}</div>
<h1>${esc(d.result || snap.title)}</h1>
<div class="axis"><span>${esc(first || '')} 100%</span><span></span></div>${svg}
<div class="axis"><span>${esc(second)} 100%</span><span><span style="color:#e5484d">●</span> wicket</span></div>
<div class="scores">${scores}</div>`;
  return page(snap, 'wp', d.result || snap.title, body, `/scorecard/${encodeURIComponent(d.match_id || '')}`);
}

function recapHtml(snap) {
  const d = snap.data || {};
  const recap = d.recap || {};
  const bullets = (recap.bullets || []).map((b) => `<li>${esc(b)}</li>`).join('');
  const body = `<div class="kicker">How it was won${matchKicker(d) ? ' · ' + esc(matchKicker(d)) : ''}</div>
<h1>${esc(recap.headline || snap.title)}</h1><div class="sub">${esc(d.result || '')}</div><ul>${bullets}</ul>`;
  return page(snap, 'recap', recap.headline || snap.title, body, `/scorecard/${encodeURIComponent(d.match_id || '')}`);
}

function queryHtml(snap) {
  const data = { ...(snap.data || {}) };
  if (data.hindsight_url) data.hindsight_url = withUtm(data.hindsight_url);
  data.filter_chips = (data.filter_chips || []).map((c) => c.replace('→ today', `→ ${asOf(snap)}`));
  data.note = [data.note, `Data as of ${asOf(snap)} · Hindsight`].filter(Boolean).join(' · ');
  const boot = `<script>window.__HINDSIGHT_SNAPSHOT__ = ${inlineJSON(data)};</script>`;
  return WIDGET
    .replace('<title>Hindsight query result</title>', `<title>${esc(snap.title || 'Hindsight chart')} · Hindsight</title><meta name="robots" content="noindex">`)
    .replace('<script>', `${boot}\n<script>`)
    .replace('</body>', `${runtime(snap, 'q', { resize: false })}</body>`);
}

const RENDER = { q: queryHtml, wp: winProbHtml, recap: recapHtml };

export default async function handler(req, res) {
  const url = new URL(req.url, 'http://local');
  const kind = url.searchParams.get('kind');
  const id = url.searchParams.get('id') || '';
  const snap = RENDER[kind] && ID.test(id) ? await getJSON(`/snapshots/${id}`, 15000) : null;
  // q also renders ranking snapshots (content packs), which are shaped like query results.
  if (!snap || !(snap.kind === KIND_FOR[kind] || (kind === 'q' && snap.kind === 'ranking'))) {
    res.statusCode = 404;
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end('<!doctype html><meta charset="utf-8"><p style="font-family:sans-serif;color:#9aa1ac">Chart not found.</p>');
    return;
  }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  // Snapshots never change: cache at the edge for a day, serve stale while revalidating.
  res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800');
  // Embeddable anywhere: no X-Frame-Options, and an explicit frame-ancestors *.
  res.setHeader('Content-Security-Policy', 'frame-ancestors *');
  res.end(RENDER[kind](snap));
}
