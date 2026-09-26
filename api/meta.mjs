// Serves index.html with a page-specific <head> (title, description, Open Graph / Twitter card,
// canonical) to link unfurlers and search crawlers. vercel.json routes ONLY bot user-agents here,
// so people keep getting the static app with no extra hop; the page body is the same SPA shell
// either way, so crawlers see what users see, just with an accurate head.
import { DEFAULT_DESCRIPTION, DEFAULT_TITLE, SITE_URL, summarize } from './_lib/share.mjs';

let cachedShell = null;

async function shell(host) {
  if (cachedShell) return cachedShell;
  const response = await fetch(`https://${host}/index.html`);
  cachedShell = await response.text();
  return cachedShell;
}

const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function headTags({ title, description, url, image }) {
  return [
    `<title>${esc(title)}</title>`,
    `<meta name="description" content="${esc(description)}" />`,
    `<link rel="canonical" href="${esc(url)}" />`,
    `<meta property="og:type" content="website" />`,
    `<meta property="og:site_name" content="Hindsight" />`,
    `<meta property="og:url" content="${esc(url)}" />`,
    `<meta property="og:title" content="${esc(title)}" />`,
    `<meta property="og:description" content="${esc(description)}" />`,
    `<meta property="og:image" content="${esc(image)}" />`,
    `<meta property="og:image:width" content="1200" />`,
    `<meta property="og:image:height" content="630" />`,
    `<meta name="twitter:card" content="summary_large_image" />`,
    `<meta name="twitter:title" content="${esc(title)}" />`,
    `<meta name="twitter:description" content="${esc(description)}" />`,
    `<meta name="twitter:image" content="${esc(image)}" />`,
  ].join('\n    ');
}

export default async function handler(req, res) {
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  // Vercel passes the original path in the query (see vercel.json); fall back to the URL.
  const incoming = new URL(req.url, `https://${host}`);
  const path = incoming.searchParams.get('__path') || incoming.pathname;
  incoming.searchParams.delete('__path');
  const search = incoming.searchParams.toString();
  const pagePath = `${path}${search ? `?${search}` : ''}`;

  let summary = null;
  try {
    summary = await summarize(path, search);
  } catch {
    summary = null;
  }
  const tags = headTags({
    title: summary?.title || DEFAULT_TITLE,
    description: summary?.description || DEFAULT_DESCRIPTION,
    url: `${SITE_URL}${pagePath}`,
    image: `${SITE_URL}/_og?path=${encodeURIComponent(pagePath)}`,
  });

  let html;
  try {
    html = await shell(host);
  } catch {
    res.statusCode = 502;
    res.end('');
    return;
  }
  // Drop the static head's title/description/OG/Twitter tags and insert the page's own.
  html = html
    .replace(/<title>[\s\S]*?<\/title>/i, '')
    .replace(/<meta\s+(?:name|property)="(?:description|og:[^"]+|twitter:[^"]+)"[^>]*>/gi, '')
    .replace(/<head>/i, `<head>\n    ${tags}`);

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400');
  res.end(html);
}
