// The XI Builder's scorer in the browser (XI_BUILDER_PLAN.md X5/X6): the same rules as services/xi_engine.py
// (score, limits), checked against the server's own output on shared cases (src/utils/__tests__/xiEngine.test.js,
// written by scripts/xi_engine_vectors.py), so a swap is scored instantly without a server call.
//
// One addition the server doesn't need: pins. A reader can put a player into a role "instead of" a holder; pinned
// holders fill the role first, then the busiest by recent usage, as the grade does.

const SQUAD_MIN_BALLS = 60;   // services/squad_grade.SQUAD_MIN
const REGULAR = 120;          // a season's balls for a regular bowler

/** 0-100: the share of team-seasons this value beats (services/squad_grade.place). */
export const place = (values, v, lower) => {
  const beaten = values.reduce((n, x) => n + ((lower ? x > v : x < v) ? 1 : x === v ? 0.5 : 0), 0);
  return (100 * beaten) / values.length;
};

const measureOf = (measure, t) => {
  if (measure === 'average') return t.wickets ? t.runs / t.wickets : null;
  if (measure === 'strike_rate') return t.balls ? (100 * t.runs) / t.balls : null;
  if (measure === 'wickets_per_24') return t.balls ? (24 * t.wickets) / t.balls : null;
  return t.balls ? (6 * t.runs) / t.balls : null;
};

/** The template rows for these players. roles: [{key, label, side, measure, n, lower}]; bench: {key: {values, playoff,
 * rest}}; pins: {roleKey: [names]} chosen to hold a role first. */
export const score = (players, roles, bench, pins = {}) => {
  const rows = roles.map((r) => {
    const b = bench[r.key];
    let v = null; let holders = [];
    if (r.side === 'depth') {
      holders = players.filter((p) => (p.best_season_balls || 0) >= REGULAR).map((p) => p.name);
      v = holders.length;
    } else {
      const cands = players.filter((p) => p.roles[r.key] && p.roles[r.key].balls >= SQUAD_MIN_BALLS);
      const pinned = (pins[r.key] || []).map((n) => cands.find((p) => p.name === n)).filter(Boolean);
      const rest = cands.filter((p) => !pinned.includes(p)).sort((a, c) => c.roles[r.key].w - a.roles[r.key].w);
      const held = [...pinned, ...rest].slice(0, r.n);
      holders = held.map((p) => p.name);
      if (held.length) {
        const t = ['balls', 'runs', 'wickets'].reduce((o, k) => ({ ...o, [k]: held.reduce((s, p) => s + p.roles[r.key][k], 0) }), {});
        v = measureOf(r.measure, t);
      }
    }
    let status = 'gap'; let pl = 0;
    if (v != null) {
      pl = place(b.values, v, r.lower);
      const better = r.lower ? (a, c) => a <= c : (a, c) => a >= c;
      status = better(v, b.playoff) ? 'playoff level' : better(v, b.rest) ? 'short' : 'gap';
    }
    return { key: r.key, label: r.label, measure: r.measure, value: v, holders, place: pl, status, playoff: b.playoff };
  });
  return { roles: rows, at_level: rows.filter((r) => r.status === 'playoff level').length, of: rows.length };
};

/** Purse, overseas and size; over a limit the squad still scores but can't be saved (the agreed rule). */
export const limitsState = (squad, lim) => {
  const spent = Math.round(squad.reduce((s, p) => s + (p.price || 0), 0) * 100) / 100;
  const overseas = squad.filter((p) => p.overseas).length;
  const problems = [];
  if (spent > lim.purse) problems.push(`₹${(spent - lim.purse).toFixed(2)} crore over the purse`);
  if (overseas > lim.overseas_max) problems.push(`${overseas - lim.overseas_max} overseas too many`);
  if (squad.length > lim.squad_max) problems.push(`${squad.length - lim.squad_max} over the squad limit`);
  if (squad.length < lim.squad_min) problems.push(`${lim.squad_min - squad.length} short of a full squad`);
  return { spent, left: Math.round((lim.purse - spent) * 100) / 100, overseas, size: squad.length, problems, can_save: !problems.length };
};
