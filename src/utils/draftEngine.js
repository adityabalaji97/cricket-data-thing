// The Season Draft (XI_BUILDER_PLAN.md X10): eleven picks from IPL player-seasons, three cards dealt per slot (the
// same deal for everyone each day), scored against all 19 IPL seasons. Every number is era-adjusted: a ratio to that
// season's league rate for the role (scripts/build_season_draft.py), so seasons compare.
//
// Scoring is a game rule, not a prediction (XI_SCORE_CHECK.md): in each season, the XI's role profile is ranked among
// that season's real sides (the mean of its percentile on each role); top four "made the playoffs", top "topped it".

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

/** Three cards per slot, no player twice in a deal. Weighted toward recognisable seasons: how much he played and how
 * far above his season he was (squared), so standout seasons come up often and an ordinary one now and then. */
const LOWER = { death_pace: true };
const quality = (c, slot) => Math.max(...slot.roles.map((r) => {
  const x = c.roles[r];
  if (!x) return 0;
  const good = LOWER[r] ? 1 / x.r : x.r;
  return Math.sqrt(x.balls) * Math.max(0.35, good) ** 3;
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

/** In each season: where the XI's profile ranks among that season's sides. */
export const seasonResults = (prof, seasons, roles) => seasons.map((s) => {
  const entries = [...Object.entries(s.teams).map(([team, p]) => ({ team, p })), { team: 'XI', p: prof }];
  const score = Object.fromEntries(entries.map((e) => [e.team, 0]));
  roles.forEach((r) => {
    const vals = entries.map((e) => e.p[r.key]).filter((v) => v != null);
    entries.forEach((e) => {
      const v = e.p[r.key];
      if (v == null) return;  // nobody in the role: no credit
      const beaten = vals.filter((x) => (r.lower ? x > v : x < v)).length + 0.5 * (vals.filter((x) => x === v).length - 1);
      score[e.team] += beaten / Math.max(1, vals.length - 1);
    });
  });
  const ranked = Object.entries(score).sort((a, b) => b[1] - a[1]).map(([t]) => t);
  const rank = ranked.indexOf('XI') + 1;
  const cut = Math.max(4, Math.min(4, (s.playoff || []).length || 4));
  return { season: s.season, rank, of: entries.length, made: rank <= cut, topped: rank === 1, champion: s.champion };
});

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
