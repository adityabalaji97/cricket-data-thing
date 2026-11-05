// Plain words for the query builder (QUERY_BUILDER_PLAN.md): the chips that state a query, the labels in the filter
// sheet, and row labels in the answer. The query itself keeps the API's keys and values; only what the reader sees
// changes.

export const LINE_WORDS = {
  WIDE_OUTSIDE_OFFSTUMP: 'Wide off', OUTSIDE_OFFSTUMP: 'Off stump', ON_THE_STUMPS: 'Stumps', DOWN_LEG: 'Leg', WIDE_DOWN_LEG: 'Wide leg',
};
export const LENGTH_WORDS = {
  YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good length', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short', FULL_TOSS: 'Full toss',
};
export const KIND_WORDS = { 'pace bowler': 'pace', 'spin bowler': 'spin', 'mixture/unknown': 'unknown' };
export const PHASE_WORDS = { powerplay: 'Powerplay', middle: 'Middle overs', death: 'Death overs' };
export const ZONE_WORDS = { 1: 'Fine leg', 2: 'Square leg', 3: 'Midwicket', 4: 'Long on', 5: 'Long off', 6: 'Cover', 7: 'Point', 8: 'Third man' };
const SHOT = (s) => (s || '').toLowerCase().replace(/_/g, ' ');

/** The group-bys offered as quick chips: label, the API's group_by. */
export const GROUP_CHIPS = [
  ['By year', ['year']],
  ['By phase', ['phase']],
  ['Pace v spin', ['bowl_kind']],
  ['Line & length', ['line', 'length']],
  ['Scoring zones', ['wagon_zone']],
  ['By venue', ['venue']],
  ['By batter', ['batter']],
  ['By bowler', ['bowler']],
];

export const GROUP_WORDS = {
  year: 'year', season: 'season', phase: 'phase', bowl_kind: 'pace or spin', bowl_style: 'bowling type', line: 'line', length: 'length',
  wagon_zone: 'scoring zone', venue: 'venue', batter: 'batter', bowler: 'bowler', batting_team: 'batting team', bowling_team: 'bowling team',
  competition: 'competition', country: 'country', shot: 'shot', bat_hand: 'batting hand', innings: 'innings', match_id: 'match',
  dismissal: 'dismissal', partnership: 'partnership', non_striker: 'partner', match_outcome: 'result', batting_position: 'batting position',
  over: 'over', crease_combo: 'batting pair', toss_decision: 'toss',
};

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const dateWords = (s, e) => {
  const d = (x) => { const t = new Date(`${x}T00:00:00`); return `${MONTHS[t.getMonth()]} ${t.getFullYear()}`; };
  if (s && e) {
    if (s.slice(5) === '01-01' && e.slice(5) === '12-31' && s.slice(0, 4) === e.slice(0, 4)) return s.slice(0, 4);
    return `${d(s)} to ${d(e)}`;
  }
  if (s) return s.slice(5) === '01-01' ? `since ${s.slice(0, 4)}` : `since ${d(s)}`;
  return `to ${d(e)}`;
};

/** A value in plain words, by its filter key. */
export const valueWords = (key, v) => {
  if (key === 'line') return LINE_WORDS[v] || v;
  if (key === 'length') return LENGTH_WORDS[v] || v;
  if (key === 'bowl_kind') return `v ${KIND_WORDS[v] || v}`;
  if (key === 'phase') return PHASE_WORDS[v] || v;
  if (key === 'wagon_zone') return ZONE_WORDS[v] || `zone ${v}`;
  if (key === 'shot') return SHOT(v);
  if (key === 'bat_hand') return v === 'LHB' ? 'left-handers' : 'right-handers';
  return String(v);
};

/**
 * The chips that state a query, in reading order: who, against whom, where, when, the ball, the situation, how it's
 * shown. Each is {key, label, values?}: removing a chip clears its key (or one value of a list).
 */
export const queryChips = (filters, groupBy) => {
  const f = filters || {};
  const out = [];
  const list = (key, words = (v) => valueWords(key, v)) => (f[key] || []).forEach((v) => out.push({ key, value: v, label: words(v) }));
  list('batters'); list('players'); list('bowlers');
  list('batting_teams', (v) => `${v} batting`); list('bowling_teams', (v) => `${v} bowling`); list('teams');
  if (f.venue) out.push({ key: 'venue', label: f.venue });
  (f.leagues || []).forEach((v) => out.push({ key: 'leagues', value: v, label: v }));
  if (f.include_international) out.push({ key: 'include_international', label: f.top_teams ? `T20Is, top ${f.top_teams}` : 'internationals' });
  if (f.start_date || f.end_date) out.push({ key: 'dates', label: dateWords(f.start_date, f.end_date) });
  list('bowl_kind'); list('bowl_style', (v) => `v ${v}`); list('line'); list('length'); list('shot'); list('shot_family', (v) => SHOT(v));
  list('wagon_zone'); list('dismissal', (v) => `out ${String(v).toLowerCase()}`);
  if (f.bat_hand) out.push({ key: 'bat_hand', label: valueWords('bat_hand', f.bat_hand) });
  if (f.over_min != null || f.over_max != null) {
    const a = f.over_min != null ? Number(f.over_min) + 1 : 1; const b = f.over_max != null ? Number(f.over_max) + 1 : null;
    out.push({ key: 'overs', label: b ? `overs ${a}-${b}` : `from over ${a}` });
  }
  if (f.innings) out.push({ key: 'innings', label: f.innings === 1 || f.innings === '1' ? '1st innings' : '2nd innings' });
  if (f.is_chase != null && f.is_chase !== '') out.push({ key: 'is_chase', label: f.is_chase === true || f.is_chase === 'true' ? 'chasing' : 'setting a target' });
  list('match_outcome', (v) => (v === 'win' ? 'in wins' : v === 'loss' ? 'in defeats' : v));
  list('toss_decision', (v) => `chose to ${v}`);
  if (f.control != null && f.control !== '') out.push({ key: 'control', label: Number(f.control) === 1 ? 'in control' : 'false shots' });
  (groupBy || []).length && out.push({ key: 'group_by', label: `by ${groupBy.map((g) => GROUP_WORDS[g] || g).join(' & ')}` });
  if (f.min_balls) out.push({ key: 'min_balls', label: `${f.min_balls}+ balls` });
  return out;
};

/** The query in one line of words: the follow-up box sends it as the context of a refinement. */
export const queryInWords = (filters, groupBy) => queryChips(filters, groupBy).map((c) => c.label).join(', ');

/** Clear a chip from the query. */
export const removeChip = (filters, groupBy, chip) => {
  const f = { ...filters };
  let g = [...(groupBy || [])];
  if (chip.key === 'group_by') g = [];
  else if (chip.key === 'dates') { f.start_date = null; f.end_date = null; }
  else if (chip.key === 'overs') { f.over_min = null; f.over_max = null; }
  else if (chip.key === 'include_international') { f.include_international = false; f.top_teams = null; }
  else if (Array.isArray(f[chip.key])) f[chip.key] = f[chip.key].filter((v) => v !== chip.value);
  else f[chip.key] = Array.isArray(filters[chip.key]) ? [] : null;
  return { filters: f, groupBy: g };
};
