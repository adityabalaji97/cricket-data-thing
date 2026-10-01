// Serve the Vercel functions (api/*.mjs) locally, with vercel.json's rewrites, against the local API.
//
//   node scripts/dev/serve_functions.mjs            # http://localhost:3100, API http://localhost:8000
//   REACT_APP_EMBED_ORIGIN=http://localhost:3100 npm start   # note pages then iframe these embeds
//
//   /embed/{q,wp,recap}/:id   /img/:id.png   /_og?path=   /sitemap.xml
//   /bot/<any site path>      what a crawler gets from api/meta.mjs (the SPA shell from :3000)
import http from 'node:http';

const PORT = Number(process.env.PORT || 3100);
process.env.HINDSIGHT_API_BASE ||= 'http://localhost:8000';
process.env.SITE_URL ||= `http://localhost:${PORT}`;
process.env.SHELL_ORIGIN ||= 'http://localhost:3000';

const load = async (name) => (await import(new URL(`../../api/${name}`, import.meta.url))).default;
const handlers = {
  embed: await load('embed.mjs'), img: await load('img.mjs'), og: await load('og.mjs'),
  sitemap: await load('sitemap.mjs'), meta: await load('meta.mjs'),
};

const ROUTES = [
  [/^\/embed\/(q|wp|recap)\/([A-Za-z0-9]{6,16})$/, (m) => ['embed', `kind=${m[1]}&id=${m[2]}`]],
  [/^\/img\/([A-Za-z0-9]{6,16})\.png$/, (m) => ['img', `id=${m[1]}`]],
  [/^\/_og$/, () => ['og', '']],
  [/^\/sitemap\.xml$/, () => ['sitemap', '']],
  [/^\/bot(\/.*)$/, (m) => ['meta', `__path=${encodeURIComponent(m[1])}`]],
];

http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  for (const [pattern, to] of ROUTES) {
    const m = url.pathname.match(pattern);
    if (!m) continue;
    const [name, extra] = to(m);
    const query = [extra, url.search.slice(1)].filter(Boolean).join('&');
    req.url = `/api/${name}${query ? `?${query}` : ''}`;
    try { await handlers[name](req, res); } catch (err) { res.statusCode = 500; res.end(String(err?.stack || err)); }
    return;
  }
  if (url.pathname === '/api/events') { res.statusCode = 204; res.end(); return; }
  res.statusCode = 404;
  res.end('not a function route');
}).listen(PORT, () => console.log(`functions on http://localhost:${PORT} (API ${process.env.HINDSIGHT_API_BASE})`));
