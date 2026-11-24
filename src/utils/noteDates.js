// Dates for the landing page's "Latest notes".
//
// A preview note has no match date field; its dek carries the start, as services/note_drafts.py writes it:
// "Indian Premier League · T20 · M Chinnaswamy Stadium · Fri 2 Oct, 05:30 IST (00:00 GMT)". The year isn't in
// it, so it comes from the publish date (a preview is written days before its match, so a month earlier than
// the publish month means the next year).

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
// How long after the start a match is surely over: a T20 is about 3.5 hours, an ODI about 8.
const MATCH_HOURS = { T20: 4, ODI: 9 };

// The preview's match start as a Date, or null when the dek doesn't carry one.
export const previewStart = (note) => {
  const m = /\b(\d{1,2}) ([A-Z][a-z]{2}),\s*(\d{2}):(\d{2}) IST\b/.exec(note?.dek || '');
  if (!m) return null;
  const month = MONTHS.indexOf(m[2].toLowerCase());
  if (month < 0) return null;
  const published = new Date(note.published_at || note.created_at || Date.now());
  if (Number.isNaN(published.getTime())) return null;
  let year = published.getUTCFullYear();
  if (month < published.getUTCMonth() - 1) year += 1; // published in Dec for a Jan match
  // IST is UTC+5:30.
  const start = new Date(Date.UTC(year, month, Number(m[1]), Number(m[3]), Number(m[4])) - 5.5 * 3600e3);
  return Number.isNaN(start.getTime()) ? null : start;
};

// A preview whose match is over: it reads as current on the landing page otherwise. Notes that aren't
// previews, and previews without a parseable start, never count as passed.
export const previewPassed = (note, now = Date.now()) => {
  if (note?.kind !== 'preview') return false;
  const start = previewStart(note);
  if (!start) return false;
  const hours = /\bODI\b/.test(note.dek || '') ? MATCH_HOURS.ODI : MATCH_HOURS.T20;
  return now > start.getTime() + hours * 3600e3;
};

// "24 Nov", or "24 Nov 2025" outside the current year.
export const noteDateLabel = (note, now = new Date()) => {
  const date = new Date(note?.published_at || note?.created_at || '');
  if (Number.isNaN(date.getTime())) return '';
  const opts = { day: 'numeric', month: 'short', timeZone: 'Asia/Kolkata' };
  if (date.getFullYear() !== now.getFullYear()) opts.year = 'numeric';
  return date.toLocaleDateString('en-GB', opts);
};
