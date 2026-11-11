import { bestFromDeal, deal, profile, rng, seasonResults, SLOTS } from '../draftEngine';

const roles = [{ key: 'openers', lower: false }, { key: 'top', lower: false }, { key: 'finishers', lower: false },
  { key: 'pp_pace', lower: false }, { key: 'mid_spin', lower: false }, { key: 'death_pace', lower: true }];
const card = (name, rolesR, overseas = false) => ({ name, season: '2020', overseas,
  roles: Object.fromEntries(Object.entries(rolesR).map(([k, r]) => [k, { r, v: r, balls: 200 }])) });
const cards = [];
for (let i = 0; i < 12; i += 1) {
  cards.push(card(`O${i}`, { openers: 0.8 + i * 0.05 }, i % 3 === 0));
  cards.push(card(`T${i}`, { top: 0.8 + i * 0.05 }));
  cards.push(card(`F${i}`, { finishers: 0.8 + i * 0.05 }, i % 2 === 0));
  cards.push(card(`P${i}`, { pp_pace: 0.8 + i * 0.05, death_pace: 1.2 - i * 0.03 }, i % 2 === 1));
  cards.push(card(`S${i}`, { mid_spin: 0.8 + i * 0.05 }));
}

test('the deal is the same for the same day, three cards a slot, no player twice', () => {
  const a = deal(cards, '2026-11-12'); const b = deal(cards, '2026-11-12'); const c = deal(cards, '2026-11-13');
  expect(a.map((s) => s.map((x) => x.name))).toEqual(b.map((s) => s.map((x) => x.name)));
  expect(a.map((s) => s.map((x) => x.name))).not.toEqual(c.map((s) => s.map((x) => x.name)));
  expect(a.every((s) => s.length === 3)).toBe(true);
  const names = a.flat().map((x) => x.name);
  expect(new Set(names).size).toBe(names.length);
  expect(a.length).toBe(SLOTS.length);
});

test('a stronger XI makes the playoffs in more seasons', () => {
  const seasons = [1, 2, 3].map((n) => ({ season: `${n}`, playoff: ['a', 'b', 'c', 'd'], teams: Object.fromEntries(
    'abcdefgh'.split('').map((t, i) => [t, { openers: 1 + (4 - i) * 0.03, top: 1, finishers: 1, pp_pace: 1, mid_spin: 1, death_pace: 1 }])) }));
  const weak = seasonResults({ openers: 0.8, top: 0.9, finishers: 0.9, pp_pace: 0.9, mid_spin: 0.9, death_pace: 1.1 }, seasons, roles);
  const strong = seasonResults({ openers: 1.3, top: 1.2, finishers: 1.2, pp_pace: 1.2, mid_spin: 1.2, death_pace: 0.85 }, seasons, roles);
  expect(strong.filter((r) => r.made).length).toBeGreaterThan(weak.filter((r) => r.made).length);
  expect(strong.every((r) => r.topped)).toBe(true);
});

test('the best XI from a deal keeps to four overseas', () => {
  const d = deal(cards, 'x');
  const best = bestFromDeal(d, roles);
  expect(best.filter((c) => c.overseas).length).toBeLessThanOrEqual(4);
  expect(profile(best).openers).toBeGreaterThan(0);
  expect(rng('a')()).toBe(rng('a')());
});
