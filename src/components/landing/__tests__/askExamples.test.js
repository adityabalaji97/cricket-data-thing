import { EXAMPLES, examplesFor } from '../AskHero';

// react-router-dom 7 ships ES modules Jest can't resolve; only the pure helpers are tested here.
jest.mock('react-router-dom', () => ({ Link: () => null, useNavigate: () => () => {} }), { virtual: true });

test('every chip opens a stored query, never a model call, labelled with its own question', () => {
  for (const ex of EXAMPLES) {
    expect(ex.to.startsWith('/query?')).toBe(true);
    const params = new URLSearchParams(ex.to.slice('/query?'.length));
    expect(params.has('nl')).toBe(false);
    expect(params.get('q')).toBe(ex.q);
    expect(params.getAll('group_by').length).toBeGreaterThan(0);
    expect(params.get('fmt')).toBeTruthy();
  }
});

test('two a day, different from each other, changing at IST midnight', () => {
  const day = (iso) => examplesFor(Date.parse(iso)).map((e) => e.q);
  const today = day('2026-11-24T12:00:00Z');
  expect(today).toHaveLength(2);
  expect(today[0]).not.toBe(today[1]);
  // 18:29 UTC is 23:59 IST the same day; 18:31 UTC is past midnight IST.
  expect(day('2026-11-24T18:29:00Z')).toEqual(today);
  expect(day('2026-11-24T18:31:00Z')).not.toEqual(today);
});

test('the six cycle over three days', () => {
  const seen = new Set();
  for (let d = 0; d < 3; d += 1) examplesFor(Date.parse('2026-11-24T06:00:00Z') + d * 864e5).forEach((e) => seen.add(e.q));
  expect(seen.size).toBe(EXAMPLES.length);
});
