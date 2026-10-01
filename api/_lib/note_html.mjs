// The crawler's view of a note (api/meta.mjs): the article as plain HTML inside #root, so search
// engines index its words and numbers without running JavaScript. Markdown goes through the same
// renderer the site uses (src/components/notes/noteMarkdown.mjs); each chart fence becomes the
// snapshot's numbers as a table, with a link to the live chart.
import { escapeHtml as esc, markdownToHtml, splitBody } from '../../src/components/notes/noteMarkdown.mjs';

const KIND = { recap: 'Match recap', preview: 'Preview', analysis: 'Analysis', article: 'Article' };
const HEADLINE_METRICS = ['runs', 'balls', 'strike_rate', 'average', 'wickets', 'economy', 'impact', 'wpa'];
const LABEL = {
  strike_rate: 'Strike rate', average: 'Average', economy: 'Economy', impact: 'Impact', wpa: 'WPA', runs: 'Runs',
  balls: 'Balls', wickets: 'Wickets', control_percentage: 'Control %', dot_percentage: 'Dot %', boundary_percentage: 'Boundary %',
};
const label = (c) => LABEL[c] || c.replace(/_percentage$/, ' %').replace(/_/g, ' ').replace(/^./, (x) => x.toUpperCase());
const cell = (v) => (v === null || v === undefined ? '' : typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(2) : String(v));
const date = (iso) => (iso ? new Date(iso).toISOString().slice(0, 10) : '');

function table(columns, rows) {
  return `<table><thead><tr>${columns.map((c) => `<th>${esc(label(c))}</th>`).join('')}</tr></thead><tbody>${
    rows.map((r) => `<tr>${columns.map((c) => `<td>${esc(cell(r[c]))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

function queryChart(d) {
  if (d.layout === 'list') {
    return `<ul>${(d.rows || []).map((r) => `<li><b>${esc(r.label)}</b> ${esc(r.sub || '')}: ${esc((r.details || []).join(', '))}</li>`).join('')}</ul>`;
  }
  if (d.query_mode === 'ranking') return table(['rank', 'label', 'display'], d.rows || []);
  const rows = d.rows || [];
  const groups = (d.group_by || []).filter((g) => rows.some((r) => r[g] !== undefined));
  const metric = d.chart?.metric;
  const filled = (c) => rows.some((r) => r[c] !== null && r[c] !== undefined);
  // A batter's "wickets" are dismissals; only bowler charts show them.
  const wanted = HEADLINE_METRICS.filter((c) => c !== 'wickets' || groups.includes('bowler'));
  const metrics = [...new Set([metric, ...wanted].filter((c) => c && (d.metric_columns || []).includes(c) && filled(c)))].slice(0, 6);
  return table([...groups, ...metrics], rows);
}

function winProbChart(d) {
  const scores = (d.scores || []).map((s) => ({ team: s.team, score: `${s.runs}/${s.wickets}`, overs: s.overs }));
  return `<p>${esc(d.result || '')}</p>${scores.length ? table(['team', 'score', 'overs'], scores) : ''}`;
}

function recapChart(d) {
  const recap = d.recap || {};
  return `<p><b>${esc(recap.headline || '')}</b></p><ul>${(recap.bullets || []).map((b) => `<li>${esc(b)}</li>`).join('')}</ul>`;
}

export function chartHtml(chart, siteUrl) {
  if (!chart) return '';
  const d = chart.data || {};
  const body = chart.kind === 'win_prob' ? winProbChart(d) : chart.kind === 'recap' ? recapChart(d) : queryChart(d);
  const live = d.hindsight_url || (d.match_id ? `${siteUrl}/scorecard/${encodeURIComponent(d.match_id)}` : null);
  return `<figure><figcaption>${esc(chart.title || d.title || 'Chart')}${d.subtitle ? ` (${esc(d.subtitle)})` : ''}</figcaption>${body}${
    live ? `<p><a href="${esc(live)}">Open the live chart</a></p>` : ''}</figure>`;
}

export function noteArticleHtml(note, siteUrl) {
  const body = splitBody(note.body_md).map((s) => (s.type === 'chart' ? chartHtml(note.charts?.[s.id], siteUrl) : markdownToHtml(s.text))).join('\n');
  const by = note.author?.is_bot ? `${note.author.name}, an AI analyst (sentences written by code from Hindsight data)` : note.author?.name;
  return `<article>
<p>${esc(KIND[note.kind] || 'Note')}</p>
<h1>${esc(note.title)}</h1>
${note.dek ? `<p>${esc(note.dek)}</p>` : ''}
<p>By ${esc(by || 'Hindsight')} · <time datetime="${esc(note.published_at || '')}">${esc(date(note.published_at))}</time></p>
${body}
${note.match_id && note.kind !== 'preview' ? `<p><a href="${siteUrl}/scorecard/${encodeURIComponent(note.match_id)}">Full scorecard</a></p>` : ''}
<p><a href="${siteUrl}/notes">More notes from Hindsight</a></p>
</article>`;
}

export function notesIndexHtml(notes, siteUrl) {
  return `<main><h1>Notes</h1><p>Match recaps, previews and analysis from ball-by-ball cricket data.</p><ul>${
    notes.map((n) => `<li><a href="${siteUrl}/notes/${esc(n.slug)}">${esc(n.title)}</a>${n.dek ? ` · ${esc(n.dek)}` : ''} (${esc(date(n.published_at))})</li>`).join('')
  }</ul></main>`;
}
