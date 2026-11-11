// A copy of src/utils/draftEngine.js for the link previews (Vercel functions can't import the app's src as ESM).
// Keep in step: scripts/dev/check_draft_copy.mjs compares the two on a deal.
// The Season Draft (XI_BUILDER_PLAN.md X10): eleven picks from IPL player-seasons, three cards dealt per slot (the
// same deal for everyone each day), scored against all 19 IPL seasons. Every number is era-adjusted: a ratio to that
// season's league rate for the role (scripts/build_season_draft.py), so seasons compare.
//
// Scoring is a game rule, not a prediction (XI_SCORE_CHECK.md): each season is simulated. The XI joins that season's
// real sides; every side's strength is its role profile against the season's (mean z-score over the roles, economy the
// other way round, a missing role -1.5); each pair plays twice, a win drawn with probability 1/(1+e^(-K·gap)); top
// four on wins "made the playoffs", top "topped it". Seeded by the deal and the picks, so a draft always scores the
// same. K was tuned (12 Nov 2026) so a random draft makes ~10 of 19 (4-15), the best a deal allows ~16 (13-18), the
// worst ~2: ranking alone was all-or-nothing (a standout XI topped every season).

export const SLOTS = [
  { key: 'openers', label: 'Opener', roles: ['openers'] }, { key: 'openers', label: 'Opener', roles: ['openers'] },
  { key: 'top', label: 'Number 3-4', roles: ['top'] }, { key: 'top', label: 'Number 3-4', roles: ['top'] },
  { key: 'finishers', label: 'Number 5-7', roles: ['finishers'] }, { key: 'finishers', label: 'Number 5-7', roles: ['finishers'] },
  { key: 'finishers', label: 'Number 5-7', roles: ['finishers'] },
  { key: 'pace', label: 'Pace bowler', roles: ['pp_pace', 'death_pace'] }, { key: 'pace', label: 'Pace bowler', roles: ['pp_pace', 'death_pace'] },
  { key: 'spin', label: 'Spinner', roles: ['mid_spin'] }, { key: 'spin', label: 'Spinner', roles: ['mid_spin'] },
];
export const OVERSEAS_MAX = 4;

/** A small seeded random generator (mulberry32) from a string: the day's deal. */
export const rng = (seed) => {
  let h = 1779033703;
  for (let i = 0; i < seed.length; i += 1) { h = Math.imul(h ^ seed.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
  let a = h >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

const eligible = (card, slot) => slot.roles.some((r) => card.roles[r]);

/** Three cards per slot, no player twice in a deal. Weighted toward recognisable seasons: how much he played, and
 * (gently: square root) how far above his season he was, so standout seasons come up often but not every card. */
const LOWER = { death_pace: true };
const quality = (c, slot) => Math.max(...slot.roles.map((r) => {
  const x = c.roles[r];
  if (!x) return 0;
  const good = LOWER[r] ? 1 / x.r : x.r;
  return Math.sqrt(x.balls) * Math.sqrt(Math.max(0.35, good));
}));

export const deal = (cards, seed) => {
  const rand = rng(seed);
  const used = new Set();
  return SLOTS.map((slot) => {
    const pool = cards.filter((c) => eligible(c, slot) && !used.has(c.name));
    const out = [];
    for (let k = 0; k < 3 && pool.length; k += 1) {
      const w = pool.map((c) => quality(c, slot));
      let x = rand() * w.reduce((a, b) => a + b, 0);
      let i = 0;
      while (x > w[i] && i < w.length - 1) { x -= w[i]; i += 1; }
      out.push(pool[i]); used.add(pool[i].name); pool.splice(i, 1);
    }
    return out;
  });
};

/** The XI's role profile: each role's ratio, balls-weighted over the picks who did it. */
export const profile = (picks) => {
  const acc = {};
  picks.forEach((card, i) => {
    if (!card) return;
    SLOTS[i].roles.forEach((r) => {
      const x = card.roles[r];
      if (!x) return;
      const a = (acc[r] = acc[r] || { w: 0, s: 0 });
      a.w += x.balls; a.s += x.r * x.balls;
    });
  });
  return Object.fromEntries(Object.entries(acc).map(([r, a]) => [r, a.s / a.w]));
};

export const K = 0.4;

/** Every side's strength in a season: the mean over roles of its z-score among the season's sides (and the XI). */
const strengths = (season, prof, roles) => {
  const ents = [...Object.entries(season.teams), ['XI', prof]];
  const s = Object.fromEntries(ents.map(([t]) => [t, 0]));
  roles.forEach((r) => {
    const vals = ents.map(([, p]) => p[r.key]).filter((v) => v != null);
    const m = vals.reduce((a, b) => a + b, 0) / vals.length;
    const sd = Math.sqrt(vals.reduce((a, b) => a + (b - m) ** 2, 0) / vals.length) || 1;
    ents.forEach(([t, p]) => {
      const v = p[r.key];
      s[t] += v == null ? -1.5 : Math.max(-3, Math.min(3, (r.lower ? m - v : v - m) / sd));
    });
  });
  Object.keys(s).forEach((t) => { s[t] /= roles.length; });
  return s;
};

/** Each season simulated with the XI in it (see the note at the top): rank, wins, made the playoffs, topped it. */
export const seasonResults = (prof, seasons, roles, seed = 'draft') => {
  const rand = rng(`${seed}|sim`);
  return seasons.map((season) => {
    const s = strengths(season, prof, roles);
    const teams = Object.keys(s);
    const wins = Object.fromEntries(teams.map((t) => [t, 0]));
    for (let i = 0; i < teams.length; i += 1) {
      for (let j = i + 1; j < teams.length; j += 1) {
        for (let g = 0; g < 2; g += 1) {
          const p = 1 / (1 + Math.exp(-K * (s[teams[i]] - s[teams[j]])));
          if (rand() < p) wins[teams[i]] += 1; else wins[teams[j]] += 1;
        }
      }
    }
    const ranked = teams.slice().sort((a, b) => wins[b] - wins[a] || s[b] - s[a]);
    const rank = ranked.indexOf('XI') + 1;
    return { season: season.season, rank, of: teams.length, wins: wins.XI, games: 2 * (teams.length - 1),
      made: rank <= 4, topped: rank === 1, champion: season.champion };
  });
};

/** The best XI the deal allowed: the best card per slot on its role (ratio; economy the other way), overseas-capped. */
export const bestFromDeal = (dealt, roles) => {
  const lower = Object.fromEntries(roles.map((r) => [r.key, r.lower]));
  const value = (c, slot) => Math.max(...SLOTS[slot].roles.map((r) => (c.roles[r] ? (lower[r] ? 1 / c.roles[r].r : c.roles[r].r) : -1)));
  let picks = dealt.map((cards, i) => cards.slice().sort((a, b) => value(b, i) - value(a, i))[0]);
  // Over the overseas cap: swap the smallest losses to the slot's best local card.
  const swapsFor = (current) => current.map((c, i) => (c?.overseas ? { i, alt: dealt[i].filter((d) => !d.overseas).sort((a, b) => value(b, i) - value(a, i))[0] } : null))
    .filter((x) => x && x.alt).map((x) => ({ ...x, loss: value(current[x.i], x.i) - value(x.alt, x.i) })).sort((a, b) => a.loss - b.loss);
  while (picks.filter((c) => c?.overseas).length > OVERSEAS_MAX) {
    const swaps = swapsFor(picks);
    if (!swaps.length) break;
    const { i: at, alt } = swaps[0];
    picks = picks.map((c, i) => (i === at ? alt : c));
  }
  return picks;
};
