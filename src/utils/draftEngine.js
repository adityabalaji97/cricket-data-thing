// The Season Draft (XI_BUILDER_PLAN.md X10): eleven picks from IPL player-seasons, five cards dealt per slot (each
// draft its own deal, from a seed in the URL), slots filled in any order under a budget and four overseas, scored
// against all 19 IPL seasons. Every number is era-adjusted: a ratio to that
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

/** A small seeded random generator (mulberry32) from a string: a draft's deal and its simulated seasons. */
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

/** Cards per slot (PER_SLOT), no player twice in a deal. Weighted toward recognisable seasons: how much he played, and
 * (gently: square root) how far above his season he was, so standout seasons come up often but not every card. */
const LOWER = { death_pace: true };
const quality = (c, slot) => Math.max(...slot.roles.map((r) => {
  const x = c.roles[r];
  if (!x) return 0;
  const good = LOWER[r] ? 1 / x.r : x.r;
  return Math.sqrt(x.balls) * Math.sqrt(Math.max(0.35, good));
}));

/** How far above his season a card was in the slot's role (economy the other way): what wins the simulated seasons. */
const goodness = (c, slot) => Math.max(...slot.roles.map((r) => {
  const x = c.roles[r];
  if (!x) return 0;
  return LOWER[r] ? 1 / x.r : x.r;
}));

/** What a card costs is based on: his ratio to the season, pulled toward 1 (the league average) by PRICE_SHRINK
 * balls, so a short hot streak isn't priced like a full great season. */
const PRICE_SHRINK = 300;
const priceValue = (c, slot) => Math.max(...slot.roles.map((r) => {
  const x = c.roles[r];
  if (!x) return 0;
  const g = LOWER[r] ? 1 / x.r : x.r;
  return (g * x.balls + PRICE_SHRINK) / (x.balls + PRICE_SHRINK);
}));

export const PER_SLOT = 5;

export const deal = (cards, seed, perSlot = PER_SLOT) => {
  const rand = rng(seed);
  const used = new Set();
  return SLOTS.map((slot) => {
    const pool = cards.filter((c) => eligible(c, slot) && !used.has(c.name));
    const out = [];
    for (let k = 0; k < perSlot && pool.length; k += 1) {
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

// ---- the budget (12 Nov 2026: tight; a card's cost from the data, one scale for all 19 seasons) -------------------

export const BUDGET = 100;           // credits for eleven (costs 4-12). Tuned 12 Nov 2026: the best a deal allows ~14 of 19 (10-17), a random legal XI ~9 (4-14)
export const COST_MIN = 4;
export const COST_MAX = 12;

/** For each slot kind, every card's price value sorted, so a cost is the card's place among the cards of its kind. */
export const costTable = (cards) => {
  const t = {};
  SLOTS.forEach((slot) => {
    if (t[slot.key]) return;
    t[slot.key] = cards.filter((c) => slot.roles.some((r) => c.roles[r])).map((c) => priceValue(c, slot)).sort((a, b) => a - b);
  });
  return t;
};

/** A card's cost in credits for a slot: 4 for the weakest of its kind to 12 for the best (by price value), in halves. */
export const costOf = (card, slotIndex, table) => {
  const slot = SLOTS[slotIndex];
  const vals = table[slot.key];
  const q = priceValue(card, slot);
  let lo = 0; let hi = vals.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (vals[mid] < q) lo = mid + 1; else hi = mid; }
  const pct = vals.length > 1 ? lo / (vals.length - 1) : 0.5;
  return Math.round(2 * (COST_MIN + (COST_MAX - COST_MIN) * Math.min(1, pct))) / 2;
};

/** A set of picks (a card or null per slot) against the rules: the budget, the overseas cap, no player twice. */
export const checkPicks = (picks, table) => {
  const chosen = picks.map((c, i) => (c ? { c, i } : null)).filter(Boolean);
  const spent = chosen.reduce((a, { c, i }) => a + costOf(c, i, table), 0);
  const overseas = chosen.filter(({ c }) => c.overseas).length;
  const names = chosen.map(({ c }) => c.name);
  return { spent, left: BUDGET - spent, overseas, ok: spent <= BUDGET && overseas <= OVERSEAS_MAX && new Set(names).size === names.length };
};

/** The best XI the deal allowed under the budget and the overseas cap: the most total goodness, by dynamic programming
 * over (slot, credits spent, overseas used). */
export const bestFromDeal = (dealt, roles, table) => {
  const half = (x) => Math.round(x * 2);
  const B = half(BUDGET);
  // state key: `${spent},${overseas}` -> {score, picks}
  let states = new Map([['0,0', { score: 0, picks: [] }]]);
  dealt.forEach((cards, i) => {
    const next = new Map();
    states.forEach((st, key) => {
      const [sp, ov] = key.split(',').map(Number);
      cards.forEach((c) => {
        if (st.picks.some((p) => p.name === c.name)) return;
        const cost = half(costOf(c, i, table)); const o = ov + (c.overseas ? 1 : 0);
        if (sp + cost > B || o > OVERSEAS_MAX) return;
        const k = `${sp + cost},${o}`; const sc = st.score + goodness(c, SLOTS[i]);
        if (!next.has(k) || next.get(k).score < sc) next.set(k, { score: sc, picks: [...st.picks, c] });
      });
    });
    states = next;
  });
  let best = null;
  states.forEach((st) => { if (!best || st.score > best.score) best = st; });
  return best ? best.picks : [];
};
