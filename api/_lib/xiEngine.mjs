// A copy of src/utils/xiEngine.js for the link previews (Vercel functions can't import the app's src as ESM).
// Keep in step: scripts/dev/check_engine_copies.mjs fails if the two differ.
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

// ---- the XI tab (XI_BUILDER_PLAN.md stage 2b) ----------------------------------------------------------------------
// Twelve players: a batting order and an impact sub who comes in for a named player. Batting roles come from the order
// (slots 1-2, 3-4, 5-7), each player on his record at those slots if 60+ balls, else his overall batting (flagged).
// The 20 overs go to the bowling eleven by where each has bowled (6 powerplay, 9 middle, 5 death; 4 each).

const SLOT_OF = (i) => (i < 2 ? 'openers' : i < 4 ? 'top' : i < 7 ? 'middle' : 'lower');
const BAT_ROLE = { openers: 'openers', top: 'top', middle: 'finishers' };
const PHASE_OVERS = [['death', 5], ['powerplay', 6], ['middle', 9]];
const PHASE_ROLE = { 'powerplay|pace': 'pp_pace', 'middle|spin': 'mid_spin', 'death|pace': 'death_pace' };
const MIN_ROLE = 60;

/** A bowler's kind (pace or spin): where most of his balls were. */
export const kindOf = (p) => {
  const tot = { pace: 0, spin: 0 };
  Object.entries(p.bowl || {}).forEach(([slot, r]) => { const k = slot.split('|')[1]; if (k in tot) tot[k] += r.balls; });
  return tot.pace || tot.spin ? (tot.spin > tot.pace ? 'spin' : 'pace') : null;
};

/** The elevens: who bats and who bowls, from the twelve and the sub. sub = {name, for, bats}: if the sub comes in to
 * bat, the man he replaces bowled (and the sub didn't); if he comes in to bowl, the reverse. */
export const elevens = (twelve, sub) => {
  if (!sub?.name || !sub.for) return { batting: twelve.slice(0, 11), bowling: twelve.slice(0, 11) };
  return sub.bats
    ? { batting: twelve.filter((n) => n !== sub.for), bowling: twelve.filter((n) => n !== sub.name) }
    : { batting: twelve.filter((n) => n !== sub.name), bowling: twelve.filter((n) => n !== sub.for) };
};

/** The 20 overs: each over to the bowler with the most history in that phase for the overs he already has there,
 * 4 at most each; `force` {name: phase} puts a bowler's overs in a phase first. Returns {name: {powerplay, middle, death}}. */
export const allocateOvers = (bowlers, force = {}) => {
  const left = Object.fromEntries(bowlers.map((p) => [p.name, 4]));
  const out = Object.fromEntries(bowlers.map((p) => [p.name, { powerplay: 0, middle: 0, death: 0 }]));
  const hist = (p, ph) => Object.entries(p.bowl || {}).filter(([s]) => s.startsWith(`${ph}|`)).reduce((n, [, r]) => n + r.balls, 0);
  const need = Object.fromEntries(PHASE_OVERS);
  // Forced phases first, as many overs as the phase still needs.
  Object.entries(force).forEach(([name, ph]) => {
    while (left[name] > 0 && need[ph] > 0) { out[name][ph] += 1; left[name] -= 1; need[ph] -= 1; }
  });
  PHASE_OVERS.forEach(([ph]) => {
    while (need[ph] > 0) {
      const best = bowlers.filter((p) => left[p.name] > 0 && !(force[p.name] && force[p.name] !== ph))
        .map((p) => ({ p, s: hist(p, ph) / (out[p.name][ph] + 1) })).sort((a, b) => b.s - a.s)[0];
      if (!best) break;
      out[best.p.name][ph] += 1; left[best.p.name] -= 1; need[ph] -= 1;
    }
  });
  return { overs: out, unassigned: Object.values(need).reduce((a, b) => a + b, 0) };
};

/** The template rows for an XI: {twelve: [names, batting order first], sub, force}. players: name -> payload player. */
export const scoreXI = (xi, players, roles, bench) => {
  const { batting, bowling } = elevens(xi.twelve, xi.sub);
  const order = xi.twelve.filter((n) => batting.includes(n));
  const flags = {};
  const pooled = {};
  order.slice(0, 7).forEach((name, i) => {
    const p = players[name]; const role = BAT_ROLE[SLOT_OF(i)];
    if (!p || !role) return;
    const own = p.bat?.[SLOT_OF(i)];
    let rec = own;
    if (!own || own.balls < MIN_ROLE) { rec = p.bat_all; flags[name] = rec ? 'out of his usual role' : 'no IPL batting'; }
    if (!rec) return;
    const t = (pooled[role] = pooled[role] || { balls: 0, runs: 0, wickets: 0, holders: [] });
    t.balls += rec.balls; t.runs += rec.runs; t.wickets += rec.wickets; t.holders.push(name);
  });
  const bowlers = bowling.map((n) => players[n]).filter((p) => p && p.bowl_all && p.bowl_all.balls > 0);
  const { overs, unassigned } = allocateOvers(bowlers, xi.force || {});
  bowlers.forEach((p) => {
    const kind = kindOf(p);
    ['powerplay', 'middle', 'death'].forEach((ph) => {
      const n = overs[p.name][ph]; const role = PHASE_ROLE[`${ph}|${kind}`];
      if (!n || !role) return;
      const own = p.bowl?.[`${ph}|${kind}`];
      let rec = own;
      if (!own || own.balls < MIN_ROLE) { rec = p.bowl_all; flags[p.name] = flags[p.name] || `bowling out of his usual phase`; }
      const balls = 6 * n; const per = { runs: rec.runs / rec.balls, wickets: rec.wickets / rec.balls };
      const t = (pooled[role] = pooled[role] || { balls: 0, runs: 0, wickets: 0, holders: [] });
      t.balls += balls; t.runs += per.runs * balls; t.wickets += per.wickets * balls;
      if (!t.holders.includes(p.name)) t.holders.push(p.name);
    });
  });
  const rows = roles.map((r) => {
    const b = bench[r.key];
    let v = null; let holders = [];
    if (r.side === 'depth') {
      holders = bowling.filter((n) => (players[n]?.best_season_balls || 0) >= REGULAR); v = holders.length;
    } else if (pooled[r.key]) {
      holders = pooled[r.key].holders; v = measureOf(r.measure, pooled[r.key]);
    }
    let status = 'gap'; let pl = 0;
    if (v != null) {
      pl = place(b.values, v, r.lower);
      const better = r.lower ? (a, c) => a <= c : (a, c) => a >= c;
      status = better(v, b.playoff) ? 'playoff level' : better(v, b.rest) ? 'short' : 'gap';
    }
    return { key: r.key, label: r.label, measure: r.measure, value: v, holders, place: pl, status, playoff: b.playoff };
  });
  const overseas = xi.twelve.filter((n) => players[n]?.overseas).length;
  return { roles: rows, at_level: rows.filter((r) => r.status === 'playoff level').length, of: rows.length,
    flags, overs, unassigned, order, overseas };
};

/** A sensible starting XI from a squad: the squad view's role holders (openers, 3-4, 5-7, then the bowling roles),
 * filled with the busiest bowlers, at most four overseas; the next bowler is the sub, in for the last batter. */
export const defaultXI = (squad, roles, bench) => {
  const s = score(squad, roles, bench);
  const holders = (k) => (s.roles.find((r) => r.key === k)?.holders || []);
  const pick = []; const over = (n) => squad.find((p) => p.name === n)?.overseas;
  const add = (n) => { if (n && !pick.includes(n) && (!over(n) || pick.filter(over).length < 4)) pick.push(n); };
  holders('openers').slice(0, 2).forEach(add); holders('top').slice(0, 2).forEach(add); holders('finishers').slice(0, 3).forEach(add);
  ['pp_pace', 'death_pace', 'mid_spin'].forEach((k) => holders(k).forEach(add));
  squad.slice().sort((a, b) => (b.best_season_balls || 0) - (a.best_season_balls || 0)).forEach((p) => { if (pick.length < 11) add(p.name); });
  squad.forEach((p) => { if (pick.length < 11) add(p.name); });
  const twelve = pick.slice(0, 11);
  const subName = squad.slice().sort((a, b) => (b.best_season_balls || 0) - (a.best_season_balls || 0)).map((p) => p.name)
    .find((n) => !twelve.includes(n) && (!over(n) || twelve.filter(over).length < 4));
  if (subName) twelve.push(subName);
  return { twelve, sub: subName ? { name: subName, for: twelve[6], bats: false } : null, force: {} };
};
