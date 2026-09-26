// GET /sitemap.xml -- pages worth indexing, from the API's /seo/sitemap-entries (growth plan G1).
import { SITE_URL, getJSON } from './_lib/share.mjs';

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export default async function handler(req, res) {
  const data = (await getJSON('/seo/sitemap-entries', 20000)) || { matches: [], players: [], venues: [] };
  const urls = [
    { loc: `${SITE_URL}/`, priority: '1.0', changefreq: 'daily' },
    { loc: `${SITE_URL}/query`, priority: '0.9', changefreq: 'weekly' },
    { loc: `${SITE_URL}/rankings`, priority: '0.7', changefreq: 'weekly' },
    ...data.players.map((name) => ({ loc: `${SITE_URL}/player?name=${encodeURIComponent(name)}`, priority: '0.7', changefreq: 'weekly' })),
    ...data.venues.map((venue) => ({ loc: `${SITE_URL}/venue?venue=${encodeURIComponent(venue)}`, priority: '0.5', changefreq: 'monthly' })),
    ...data.matches.map((m) => ({ loc: `${SITE_URL}/scorecard/${encodeURIComponent(m.id)}`, lastmod: m.date, priority: '0.6', changefreq: 'yearly' })),
  ];
  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls.map((u) => `  <url><loc>${esc(u.loc)}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}<changefreq>${u.changefreq}</changefreq><priority>${u.priority}</priority></url>`),
    '</urlset>',
  ].join('\n');
  res.setHeader('Content-Type', 'application/xml; charset=utf-8');
  res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=86400, stale-while-revalidate=86400');
  res.end(body);
}
