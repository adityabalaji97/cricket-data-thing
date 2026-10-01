// Note bodies: markdown with chart fences (services/notes.py), rendered the same way for people
// (NoteBody.jsx) and for crawlers (api/meta.mjs), so search engines index what readers see.
//
//   ```hindsight
//   chart: Ab12Cd34E
//   ```
//
// Raw HTML in a body is shown as text, never run; links and images must be http(s), relative or
// mailto. Bodies are only ever written by the bot or a trusted author and published by the admin,
// but the renderer does not rely on that.
import { Marked } from 'marked';

// Same pattern as services/notes.py CHART_FENCE.
const CHART_FENCE = /^```hindsight[ \t]*\n[ \t]*chart:[ \t]*([A-Za-z0-9]{6,16})[ \t]*\n```[ \t]*$/gm;

export const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const SAFE_URL = /^(https?:\/\/|\/(?!\/)|#|mailto:)/i;
const isExternal = (href) => /^https?:\/\//i.test(href) && !/^https?:\/\/(www\.)?hindsightcricket\.com(\/|$)/i.test(href);

const marked = new Marked({ gfm: true, breaks: false });
marked.use({
  renderer: {
    html(token) {
      return escapeHtml(token.text);
    },
    // The page title is the h1; body headings start at h2.
    heading(token) {
      const level = Math.min(6, Math.max(2, token.depth + 1));
      return `<h${level}>${this.parser.parseInline(token.tokens)}</h${level}>\n`;
    },
    link(token) {
      const text = this.parser.parseInline(token.tokens);
      const href = String(token.href || '').trim();
      if (!SAFE_URL.test(href)) return text;
      const title = token.title ? ` title="${escapeHtml(token.title)}"` : '';
      const target = isExternal(href) ? ' target="_blank" rel="noopener noreferrer"' : '';
      return `<a href="${escapeHtml(href)}"${title}${target}>${text}</a>`;
    },
    image(token) {
      const href = String(token.href || '').trim();
      if (!/^(https:\/\/|\/(?!\/))/i.test(href)) return escapeHtml(token.text || '');
      return `<img src="${escapeHtml(href)}" alt="${escapeHtml(token.text || '')}" loading="lazy">`;
    },
  },
});

export function markdownToHtml(markdown) {
  return marked.parse(markdown || '', { async: false });
}

/** Split a body into markdown and chart segments, in order: [{type:'md', text} | {type:'chart', id}]. */
export function splitBody(body) {
  const segments = [];
  let last = 0;
  const text = body || '';
  for (const match of text.matchAll(CHART_FENCE)) {
    if (match.index > last) segments.push({ type: 'md', text: text.slice(last, match.index) });
    segments.push({ type: 'chart', id: match[1] });
    last = match.index + match[0].length;
  }
  if (last < text.length) segments.push({ type: 'md', text: text.slice(last) });
  return segments.filter((s) => s.type === 'chart' || s.text.trim());
}

/** Plain-text summary of a body for descriptions: first paragraph, no markdown. */
export function plainExcerpt(body, max = 200) {
  const first = splitBody(body).find((s) => s.type === 'md');
  const plain = (first?.text || '')
    .replace(/^#+.*$/gm, '').replace(/[*_`>]/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\s+/g, ' ').trim();
  return plain.length > max ? `${plain.slice(0, max - 1).trimEnd()}…` : plain;
}

export const formatNoteDate = (iso) => (iso
  ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  : '');

export const KIND_LABEL = { recap: 'Match recap', preview: 'Preview', analysis: 'Analysis', article: 'Article' };
