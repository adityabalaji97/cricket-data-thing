// Shared by api/og.mjs (preview images) and api/meta.mjs (per-page <head> for link unfurlers).
//
// A "share summary" is what a link to a Hindsight page should say about itself when pasted into
// WhatsApp / X / Slack / iMessage or read by a search engine: a title, a one-line description,
// and the data its preview image draws. Every fetch is time-boxed; on any failure the page falls
// back to the site-wide card rather than failing the unfurl.

export const API_BASE = process.env.HINDSIGHT_API_BASE || 'https://cricket-data-thing-672dfbacf476.herokuapp.com';
export const SITE_URL = (process.env.SITE_URL || 'https://hindsight2020.vercel.app').replace(/\/$/, '');
export const SITE_NAME = 'Hindsight';
export const DEFAULT_TITLE = 'Hindsight - T20 cricket analytics';
export const DEFAULT_DESCRIPTION =
  'Ball-by-ball T20 and ODI analytics: Impact, win probability, matchups, match previews and a query builder you can ask in plain English.';

export async function getJSON(path, timeoutMs = 6000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, { signal: controller.signal });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

const signed = (value, digits = 1) => `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(digits)}`;

// "Kolkata Knight Riders" -> "KKR"; short names pass through.
export const shortTeam = (name) => {
  if (!name) return '';
  const words = name.split(/\s+/).filter(Boolean);
  return name.length > 12 && words.length > 1 ? words.map((w) => w[0]).join('').toUpperCase() : name;
};

async function scorecardSummary(id) {
  const data = await getJSON(`/matches/${encodeURIComponent(id)}/scorecard`);
  if (!data?.match) return null;
  const { match, summary } = data;
  const scores = (summary?.innings_scores || []).map((s) => `${shortTeam(s.team)} ${s.runs}/${s.wickets} (${s.overs})`);
  const primer = summary?.primer;
  const impact = primer?.innings?.map((inn) => `${shortTeam(inn.team)} ${signed(inn.impact)}`).join(' · ');
  const top = (summary?.top_performers || []).slice(0, 2).map((p) => `${p.player} ${p.label || ''}`.trim());
  const description = [match.result_text, scores.join(' v '), impact ? `Impact ${impact}` : null, top.length ? `Top: ${top.join(', ')}` : null]
    .filter(Boolean).join(' · ');
  return {
    kind: 'scorecard',
    title: `${match.team1} v ${match.team2}: ${match.result_text} | ${SITE_NAME}`,
    description: description.slice(0, 280),
    card: {
      kicker: [match.competition || match.event_name, match.date].filter(Boolean).join(' · '),
      headline: match.result_text || `${match.team1} v ${match.team2}`,
      lines: (summary?.innings_scores || []).map((s) => ({ team: shortTeam(s.team), score: `${s.runs}/${s.wickets}`, overs: s.overs })),
      impact: primer?.innings?.map((inn) => ({ team: shortTeam(inn.team), value: inn.impact })) || null,
      wp: primer?.win_probability || null,
    },
  };
}

async function playerSummary(name) {
  const base = `format=T20&gender=male&group_by=year&limit=100`;
  let payload = await getJSON(`/query/deliveries?batters=${encodeURIComponent(name)}&${base}`, 8000);
  let role = 'batting';
  let rows = (payload?.data || []).filter((r) => r.metric_balls > 0);
  if (!rows.length) {
    payload = await getJSON(`/query/deliveries?bowlers=${encodeURIComponent(name)}&${base}&group_by=bowler`, 8000);
    rows = (payload?.data || []).filter((r) => r.metric_balls > 0);
    role = 'bowling';
  }
  if (!rows.length) {
    return { kind: 'player', title: `${name}: T20 stats | ${SITE_NAME}`, description: DEFAULT_DESCRIPTION, card: { kicker: 'Player', headline: name, lines: [] } };
  }
  rows.sort((a, b) => Number(b.year) - Number(a.year));
  const latest = rows[0];
  const totalImpact = rows.reduce((sum, r) => sum + (r.impact || 0), 0);
  const totalWpa = rows.reduce((sum, r) => sum + (r.wpa || 0), 0);
  const description = `${name} (${role}), ${latest.year}: Impact ${signed(latest.impact)} (${signed(latest.impact_per_100)} per 100 balls), WPA ${signed(latest.wpa, 2)}. `
    + `Since ${rows[rows.length - 1].year}: Impact ${signed(totalImpact)}, WPA ${signed(totalWpa, 2)}.`;
  return {
    kind: 'player',
    title: `${name}: T20 Impact, WPA & stats | ${SITE_NAME}`,
    description,
    card: {
      kicker: `${role === 'bowling' ? 'Bowling' : 'Batting'} · men's T20`,
      headline: name,
      stats: [
        { label: `Impact ${latest.year}`, value: signed(latest.impact) },
        { label: 'Per 100 balls', value: signed(latest.impact_per_100) },
        { label: `WPA ${latest.year}`, value: signed(latest.wpa, 2) },
      ],
      bars: rows.slice(0, 8).reverse().map((r) => ({ label: String(r.year).slice(2), value: r.impact || 0 })),
    },
  };
}

function venueSummary(params) {
  const venue = params.get('venue');
  if (!venue) return null;
  const t1 = params.get('team1');
  const t2 = params.get('team2');
  const fixture = t1 && t2 ? `${t1} v ${t2} at ` : '';
  const ground = venue.split(',')[0];
  return {
    kind: 'venue',
    title: `${fixture}${ground}: match preview | ${SITE_NAME}`,
    description: `${fixture}${venue}: venue record, par scores, leaders, head-to-head and batter-bowler matchups.`,
    card: { kicker: 'Match preview', headline: t1 && t2 ? `${t1} v ${t2}` : ground, sub: venue, lines: [] },
  };
}

function querySummary(params) {
  const who = [...params.getAll('batters'), ...params.getAll('bowlers'), ...params.getAll('players')].slice(0, 3);
  const groups = params.getAll('group_by');
  const leagues = params.getAll('leagues');
  const parts = [who.join(', '), groups.length ? `by ${groups.join(' & ').replace(/_/g, ' ')}` : null, leagues.join(', ')].filter(Boolean);
  const headline = parts.join(' · ') || 'Ask the ball-by-ball data anything';
  return {
    kind: 'query',
    title: `${headline} | ${SITE_NAME} query builder`,
    description: `Hindsight query builder: ${headline}. Runs, strike rate, Impact and win probability added from ball-by-ball data.`,
    card: { kicker: 'Query builder', headline, lines: [] },
  };
}

/** Summary for a site path + query string, or null for the site-wide card. */
export async function summarize(pathname, search) {
  const params = new URLSearchParams(search || '');
  const scorecard = pathname.match(/^\/scorecard\/([^/]+)/);
  if (scorecard) return scorecardSummary(decodeURIComponent(scorecard[1]));
  if (pathname.startsWith('/player') && params.get('name')) return playerSummary(params.get('name'));
  if (pathname.startsWith('/venue')) return venueSummary(params);
  if (pathname.startsWith('/query')) return querySummary(params);
  return null;
}
