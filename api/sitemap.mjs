// Sitemaps, from the API's /seo endpoints (growth plan G1):
//   GET /sitemap.xml                        the index: the pages sitemap and one scorecard sitemap per year
//   GET /sitemap-pages.xml                  home, tools, notes, players, venues
//   GET /sitemap-scorecards-<year>.xml      every T20 and ODI scorecard of that year
// One file per year keeps each well under the 50,000-URL limit, and lets a past year's file be cached for long.
import { SITE_URL, getJSON } from './_lib/share.mjs';

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const urlset = (urls) => [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...urls.map((u) => `  <url><loc>${esc(u.loc)}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}<changefreq>${u.changefreq}</changefreq><priority>${u.priority}</priority></url>`),
  '</urlset>',
].join('\n');

async function index() {
  const data = (await getJSON('/seo/scorecard-years', 20000)) || { years: [] };
  const today = new Date().toISOString().slice(0, 10);
  const maps = [
    { loc: `${SITE_URL}/sitemap-pages.xml`, lastmod: today },
    ...data.years.map((y) => ({ loc: `${SITE_URL}/sitemap-scorecards-${y.year}.xml`, lastmod: y.lastmod })),
  ];
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...maps.map((m) => `  <sitemap><loc>${esc(m.loc)}</loc><lastmod>${m.lastmod}</lastmod></sitemap>`),
    '</sitemapindex>',
  ].join('\n');
}

async function pages() {
  const data = (await getJSON('/seo/sitemap-entries', 20000)) || { players: [], venues: [], notes: [] };
  return urlset([
    { loc: `${SITE_URL}/`, priority: '1.0', changefreq: 'daily' },
    { loc: `${SITE_URL}/query`, priority: '0.9', changefreq: 'weekly' },
    { loc: `${SITE_URL}/scorecards`, priority: '0.8', changefreq: 'daily' },
    { loc: `${SITE_URL}/rankings`, priority: '0.7', changefreq: 'weekly' },
    { loc: `${SITE_URL}/notes`, priority: '0.8', changefreq: 'daily' },
    ...(data.notes || []).map((n) => ({ loc: `${SITE_URL}/notes/${encodeURIComponent(n.slug)}`, lastmod: n.lastmod, priority: '0.8', changefreq: 'monthly' })),
    ...(data.players || []).map((name) => ({ loc: `${SITE_URL}/player?name=${encodeURIComponent(name)}`, priority: '0.7', changefreq: 'weekly' })),
    ...(data.venues || []).map((venue) => ({ loc: `${SITE_URL}/venue?venue=${encodeURIComponent(venue)}`, priority: '0.5', changefreq: 'monthly' })),
  ]);
}

async function scorecards(year) {
  const data = (await getJSON(`/seo/scorecards?year=${year}`, 20000)) || { matches: [] };
  const current = year >= new Date().getFullYear();
  return urlset(data.matches.map((m) => ({
    loc: `${SITE_URL}/scorecard/${encodeURIComponent(m.id)}`, lastmod: m.date,
    priority: current ? '0.6' : '0.5', changefreq: current ? 'weekly' : 'yearly',
  })));
}

export default async function handler(req, res) {
  const url = new URL(req.url, 'http://local');
  const kind = url.searchParams.get('kind') || 'index';
  const year = Number(url.searchParams.get('year'));
  const body = kind === 'pages' ? await pages()
    : kind === 'scorecards' && year >= 2000 && year <= 2100 ? await scorecards(year)
      : await index();
  const past = kind === 'scorecards' && year < new Date().getFullYear();
  res.setHeader('Content-Type', 'application/xml; charset=utf-8');
  // A past year's scorecards don't change: cache it for a week at the edge.
  res.setHeader('Cache-Control', `public, max-age=3600, s-maxage=${past ? 604800 : 86400}, stale-while-revalidate=86400`);
  res.end(body);
}
