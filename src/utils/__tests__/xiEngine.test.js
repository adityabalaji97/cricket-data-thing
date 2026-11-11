import { limitsState, score } from '../xiEngine';
import cases from './xi_vectors.json';

// The browser's scorer against the server's (services/xi_engine.py) on real squads (scripts/xi_engine_vectors.py).
describe('xiEngine matches the server', () => {
  cases.forEach((c) => {
    test(c.label, () => {
      const s = score(c.players, c.roles, c.bench);
      expect(s.at_level).toBe(c.expect.at_level);
      s.roles.forEach((r, i) => {
        const e = c.expect.roles[i];
        expect(r.key).toBe(e.key);
        expect(r.status).toBe(e.status);
        expect(r.holders).toEqual(e.holders);
        if (e.value == null) expect(r.value).toBeNull(); else expect(r.value).toBeCloseTo(e.value, 5);
      });
      const l = limitsState(c.players, c.limits);
      expect(l.can_save).toBe(c.expect_limits.can_save);
      expect(l.spent).toBeCloseTo(c.expect_limits.spent, 2);
    });
  });

  test('a pin puts a player into a role ahead of the busiest', () => {
    const c = cases[0];
    const role = c.roles.find((r) => r.key === 'death_pace');
    const cands = c.players.filter((p) => p.roles.death_pace && p.roles.death_pace.balls >= 60);
    const last = cands.sort((a, b) => a.roles.death_pace.w - b.roles.death_pace.w)[0];
    const s = score(c.players, [role], c.bench, { death_pace: [last.name] });
    expect(s.roles[0].holders[0]).toBe(last.name);
  });
});

describe('the XI tab', () => {
  const { scoreXI, defaultXI, allocateOvers, elevens } = require('../xiEngine');
  const c = cases.find((x) => x.label.endsWith('as is'));
  const players = Object.fromEntries(c.players.map((p) => [p.name, p]));

  test('elevens follow the sub rule', () => {
    const t = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 's'];
    const bowlIn = elevens(t, { name: 's', for: 'g', bats: false });
    expect(bowlIn.batting).not.toContain('s');
    expect(bowlIn.bowling).toContain('s');
    expect(bowlIn.bowling).not.toContain('g');
  });

  test('20 overs, at most 4 a bowler', () => {
    const bowlers = c.players.filter((p) => p.bowl_all && p.bowl_all.balls > 200).slice(0, 6);
    const { overs, unassigned } = allocateOvers(bowlers);
    const per = Object.values(overs).map((o) => o.powerplay + o.middle + o.death);
    expect(per.every((n) => n <= 4)).toBe(true);
    expect(per.reduce((a, b) => a + b, 0) + unassigned).toBe(20);
  });

  test('a default XI scores, and a batter out of his slot is flagged', () => {
    const xi = defaultXI(c.players, c.roles, c.bench);
    expect(xi.twelve.length).toBe(12);
    const s = scoreXI(xi, players, c.roles, c.bench);
    expect(s.roles.length).toBe(7);
    // Move the best opener to 7: if he has under 60 balls at 5-7, he's flagged.
    const moved = { ...xi, twelve: [...xi.twelve.slice(1, 7), xi.twelve[0], ...xi.twelve.slice(7)] };
    const s2 = scoreXI(moved, players, c.roles, c.bench);
    const p = players[xi.twelve[0]];
    if (!p.bat?.middle || p.bat.middle.balls < 60) expect(s2.flags[xi.twelve[0]]).toBe('out of his usual role');
  });
});
