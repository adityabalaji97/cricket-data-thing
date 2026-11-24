import { FALLBACK_EXAMPLES, pickExamples } from '../AskHero';

// react-router-dom 7 ships ES modules Jest can't resolve; only the pure helpers are tested here.
jest.mock('react-router-dom', () => ({ Link: () => null, useNavigate: () => () => {} }), { virtual: true });

const recent = [
  { q: 'Sanju Samson … Batting at 3,4,5', search: '?q=x' },
  { q: 'India vs australia 2023', search: '?q=y' },
  { q: 'India vs australia', search: '?q=z' },
  { q: 'Tilak Varma batting at the death by line and length', search: '?q=long' },
  { q: 'Shubman Gill in ODIs since 2024 by phase', search: '?q=gill' },
  { q: 'Shubman Gill in ODIs since 2024 by phase', search: '?q=gill2' },
  { q: 'Hnry Stadium: pace or spin since 2023' },
];

test('picks two short, well-formed, distinct recent questions', () => {
  expect(pickExamples(recent)).toEqual([
    { q: 'Shubman Gill in ODIs since 2024 by phase', to: '/query?q=gill' },
    { q: 'Hnry Stadium: pace or spin since 2023', to: `/query?nl=${encodeURIComponent('Hnry Stadium: pace or spin since 2023')}` },
  ]);
});

test('a question and the same question with a year added count once', () => {
  const picked = pickExamples([{ q: 'Rohit Sharma vs spin' }, { q: 'Rohit Sharma vs spin 2024' }, { q: 'Bumrah at the death' }]);
  expect(picked.map((p) => p.q)).toEqual(['Rohit Sharma vs spin', 'Bumrah at the death']);
});

test('falls back to the curated pair when fewer than two qualify', () => {
  expect(pickExamples([{ q: 'india vs pak' }])).toBe(FALLBACK_EXAMPLES);
  expect(pickExamples(undefined)).toBe(FALLBACK_EXAMPLES);
});
