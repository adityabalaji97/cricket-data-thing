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
