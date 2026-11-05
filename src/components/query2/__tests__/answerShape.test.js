import { shapeAnswer } from '../answerShape';
import { queryChips, removeChip } from '../qbWords';

const years = [
  { year: 2023, balls: 208, runs: 235, strike_rate: 113, wickets: 5, dot_percentage: 27 },
  { year: 2024, balls: 275, runs: 368, strike_rate: 134, wickets: 6, dot_percentage: 29 },
];

test('a by-year result is a line, read from first to last year', () => {
  const a = shapeAnswer(years, { batters: ['Virat Kohli'] }, ['year']);
  expect(a.type).toBe('time');
  expect(a.chart.visual).toBe('metric_lines');
  expect(a.sentence.map(([t]) => t).join('')).toContain('134 in 2024, from 113 in 2023');
});

test('a group with one value is dropped (by batter when one batter is named)', () => {
  const rows = years.map((r) => ({ ...r, batter: 'Virat Kohli' }));
  expect(shapeAnswer(rows, { batters: ['Virat Kohli'] }, ['batter', 'year']).type).toBe('time');
});

test('bowlers rank by economy, cheapest first, unless the question asks for wickets', () => {
  const rows = [
    { bowler: 'A', balls: 60, runs: 90, wickets: 2 },
    { bowler: 'B', balls: 60, runs: 70, wickets: 5 },
    { bowler: 'C', balls: 10, runs: 5, wickets: 0 },
  ];
  const econ = shapeAnswer(rows, { leagues: ['IPL'] }, ['bowler']);
  expect(econ.type).toBe('ranked');
  expect(econ.rows.map((r) => r.label)).toEqual(['B', 'A']);   // C under the 30-ball floor
  const wkts = shapeAnswer(rows, { leagues: ['IPL'] }, ['bowler'], 'wickets');
  expect(wkts.rows[0].label).toBe('B');
});

test('chips read the query in words, and removing one clears it', () => {
  const f = { batters: ['Virat Kohli'], bowl_kind: ['spin bowler'], start_date: '2023-01-01', over_min: 0, over_max: 5 };
  const chips = queryChips(f, ['year']);
  expect(chips.map((c) => c.label)).toEqual(['Virat Kohli', 'since 2023', 'v spin', 'overs 1-6', 'by year']);
  const n = removeChip(f, ['year'], chips.find((c) => c.key === 'overs'));
  expect(n.filters.over_min).toBeNull();
});
