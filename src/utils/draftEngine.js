// The Season Draft (XI_BUILDER_PLAN.md X10): eleven picks from IPL player-seasons, five cards dealt per slot (each
// draft its own deal, from a seed in the URL), slots filled in any order under a budget and four overseas, scored
// against all 19 IPL seasons. Every number is era-adjusted: a ratio to that
// season's league rate for the role (scripts/build_season_draft.py), so seasons compare.
//
// Scoring is a game rule, not a prediction (XI_SCORE_CHECK.md): each season is simulated. The XI joins that season's
// real sides; every side's strength is its role profile against the season's (mean z-score over the roles, economy the
// other way round, a missing role -1.5); each pair plays twice, a win drawn with probability 1/(1+e^(-K·gap)); top
// four on wins "made the playoffs", top "topped it". Seeded by the deal alone: every XI on a deal faces the same luck, so a draft always scores the
// same. K and the budget were tuned together (12 Nov 2026, see BUDGET); ranking alone was all-or-nothing (a standout
// XI topped every season).

export const SLOTS = [
  { key: 'openers', label: 'Opener', roles: ['openers'] }, { key: 'openers', label: 'Opener', roles: ['openers'] },
  { key: 'top', label: 'No. 3-4', roles: ['top'] }, { key: 'top', label: 'No. 3-4', roles: ['top'] },
  { key: 'finishers', label: 'No. 5-7', roles: ['finishers'] }, { key: 'finishers', label: 'No. 5-7', roles: ['finishers'] },
  { key: 'finishers', label: 'No. 5-7', roles: ['finishers'] },
  { key: 'pace', label: 'Pace', roles: ['pp_pace', 'death_pace'] }, { key: 'pace', label: 'Pace', roles: ['pp_pace', 'death_pace'] },
  { key: 'spin', label: 'Spin', roles: ['mid_spin'] }, { key: 'spin', label: 'Spin', roles: ['mid_spin'] },
];
export const OVERSEAS_MAX = 4;  // the IPL's; a league's own comes in its data (rules.overseas_max: the BBL's 3)

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

/** A card's ratio to its season, pulled toward 1 (the league average) by SHRINK balls: a short burst isn't scored or
 * priced like a full great season. Wickets are noisier than runs, so they're pulled harder. Used by the score and
 * the price alike. 12 Nov 2026 (a 78-ball powerplay burst at 2.1x was costing more than Malinga 2015). */
const SHRINK = { openers: 300, top: 300, finishers: 300, pp_pace: 600, mid_spin: 600, death_pace: 300 };
export const adjRatio = (x, r) => (x.r * x.balls + SHRINK[r]) / (x.balls + SHRINK[r]);
const good = (c, r) => {
  const x = c.roles[r];
  if (!x) return null;
  return LOWER[r] ? 1 / adjRatio(x, r) : adjRatio(x, r);
};
/** What a card costs is based on: in a batting slot, his batting there plus any bowling above average (an
 * all-rounder costs more); in a bowling slot, his phases balls-weighted (a pace bowler on both powerplay and death). */
const priceValue = (c, slot) => {
  const own = slot.roles.filter((r) => c.roles[r]);
  if (!own.length) return 0;
  const w = own.reduce((a, r) => a + c.roles[r].balls, 0);
  const base = own.reduce((a, r) => a + good(c, r) * c.roles[r].balls, 0) / w;
  if (!['openers', 'top', 'finishers'].includes(slot.key)) return base;
  return base + ['pp_pace', 'mid_spin', 'death_pace'].reduce((a, r) => a + Math.max(0, (good(c, r) ?? 1) - 1), 0);
};

export const PER_SLOT = 5;

/** Keepers a deal must hold across the batting slots, so an XI with a wicketkeeper (the rule to lock in) is always
 * possible: a deal short of them is redealt from the next seed (`seed#1`, `seed#2`, ...), deterministically. */
export const DEAL_KEEPERS = 2;

export const deal = (cards, seed, perSlot = PER_SLOT) => {
  for (let k = 0; k < 50; k += 1) {
    const d = dealOnce(cards, k ? `${seed}#${k}` : seed, perSlot);
    if (d.slice(0, 7).flat().filter((c) => c.wk).length >= DEAL_KEEPERS) return d;
  }
  return dealOnce(cards, seed, perSlot);
};

const dealOnce = (cards, seed, perSlot) => {
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

// Which picks fill each role (12 Nov 2026, the squad grade's rule, services/squad_grade.py): the batting slots bat
// 1-7 in their bands; every pick's bowling counts, batters' too (Russell at 5-7 also bowls), and each bowling role is
// held by its busiest HOLDERS among the XI, as a captain would use them. Bowlers bat 8-11, which isn't scored.
const BAT_ROLES = ['openers', 'top', 'finishers'];
const HOLDERS = { openers: 2, top: 2, finishers: 3, pp_pace: 2, mid_spin: 2, death_pace: 2 };
export const isBatSlot = (slotIndex) => BAT_ROLES.includes(SLOTS[slotIndex].key);

/** The roles a pick can fill: his slot's band (a batting slot) and all his bowling. */
export const rolesFilled = (card, slotIndex) => {
  const bowl = Object.keys(card.roles).filter((r) => !BAT_ROLES.includes(r));
  return isBatSlot(slotIndex) ? [...SLOTS[slotIndex].roles.filter((r) => card.roles[r]), ...bowl] : bowl;
};

/** The XI's role profile: each role's (sample-adjusted) ratio, balls-weighted over its holders. */
export const profile = (picks) => {
  const cands = {};
  picks.forEach((card, i) => {
    if (!card) return;
    rolesFilled(card, i).forEach((r) => { (cands[r] = cands[r] || []).push(card.roles[r]); });  // ratios adjusted below
  });
  return Object.fromEntries(Object.entries(cands).map(([r, xs]) => {
    const held = xs.slice().sort((a, b) => b.balls - a.balls).slice(0, HOLDERS[r] || 2);
    const w = held.reduce((a, x) => a + x.balls, 0);
    return [r, held.reduce((a, x) => a + adjRatio(x, r) * x.balls, 0) / w];
  }));
};

export const K = 1.5;

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

/** What won and lost the seasons: each role's mean z-score for the XI across the 19 seasons (the strengths the
 * simulation used), with the strongest and weakest role. For the result's "why" line (13 Nov 2026). */
export const ROLE_NAMES = { openers: 'openers', top: 'No. 3-4', finishers: 'No. 5-7 hitting', pp_pace: 'powerplay pace',
  mid_spin: 'middle-overs spin', death_pace: 'death bowling' };
export const roleEdges = (prof, seasons, roles) => {
  const z = Object.fromEntries(roles.map((r) => [r.key, 0]));
  seasons.forEach((season) => {
    const ents = [...Object.values(season.teams), prof];
    roles.forEach((r) => {
      const vals = ents.map((p) => p[r.key]).filter((v) => v != null);
      const m = vals.reduce((a, b) => a + b, 0) / vals.length;
      const sd = Math.sqrt(vals.reduce((a, b) => a + (b - m) ** 2, 0) / vals.length) || 1;
      const v = prof[r.key];
      z[r.key] += v == null ? -1.5 : Math.max(-3, Math.min(3, (r.lower ? m - v : v - m) / sd));
    });
  });
  const ranked = Object.entries(z).map(([k, v]) => [k, v / seasons.length]).sort((a, b) => b[1] - a[1]);
  return { z: Object.fromEntries(ranked), strongest: ranked[0][0], weakest: ranked[ranked.length - 1][0] };
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

export const BUDGET = 100;           // credits for eleven (costs 4-12). Tuned 13 Nov 2026 with K and the keeper rule: the best a deal allows ~13 of 19 (10-15), a random legal XI ~5 (2-10)
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

/** A set of picks (a card or null per slot) against the rules: the budget, the overseas cap, no player twice; and
 * whether it can be locked in (eleven picks, one of them a wicketkeeper). */
export const checkPicks = (picks, table, overseasMax = OVERSEAS_MAX) => {
  const chosen = picks.map((c, i) => (c ? { c, i } : null)).filter(Boolean);
  const spent = chosen.reduce((a, { c, i }) => a + costOf(c, i, table), 0);
  const overseas = chosen.filter(({ c }) => c.overseas).length;
  const names = chosen.map(({ c }) => c.name);
  const keeper = chosen.some(({ c }) => c.wk);
  const ok = spent <= BUDGET && overseas <= overseasMax && new Set(names).size === names.length;
  return { spent, left: BUDGET - spent, overseas, keeper, ok, complete: ok && keeper && chosen.length === SLOTS.length };
};

/** The best XI the deal allowed under the rules (budget, overseas cap, a wicketkeeper): the most total value (what
 * prices are based on), by dynamic programming over (slot, credits spent, overseas used, keeper yet). */
export const bestFromDeal = (dealt, roles, table, overseasMax = OVERSEAS_MAX) => {
  const half = (x) => Math.round(x * 2);
  const B = half(BUDGET);
  let states = new Map([['0,0,0', { score: 0, picks: [] }]]);
  dealt.forEach((cards, i) => {
    const next = new Map();
    states.forEach((st, key) => {
      const [sp, ov, wk] = key.split(',').map(Number);
      cards.forEach((c) => {
        if (st.picks.some((p) => p.name === c.name)) return;
        const cost = half(costOf(c, i, table)); const o = ov + (c.overseas ? 1 : 0);
        if (sp + cost > B || o > overseasMax) return;
        const k = `${sp + cost},${o},${wk || (c.wk ? 1 : 0)}`; const sc = st.score + priceValue(c, SLOTS[i]);
        if (!next.has(k) || next.get(k).score < sc) next.set(k, { score: sc, picks: [...st.picks, c] });
      });
    });
    states = next;
  });
  let best = null;
  states.forEach((st, key) => { if (key.endsWith(',1') && (!best || st.score > best.score)) best = st; });
  return best ? best.picks : [];
};
