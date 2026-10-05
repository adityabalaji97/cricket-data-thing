import { coverageColumnFor, rankWithCoverage } from '../coverage';

const rows = [ // sorted by control % descending, as the table sorts them
  { partnership: 'MacLeod & Berrington', control_percentage: 93.4, control_coverage_pct: 34.2 },
  { partnership: 'Kumar & Mukkamalla', control_percentage: 90.4, control_coverage_pct: 58.4 },
  { partnership: 'Rayudu & Kohli', control_percentage: 89.0, control_coverage_pct: 99.9 },
  { partnership: 'Gill & Kohli', control_percentage: 88.6, control_coverage_pct: 99.9 },
];

describe('rankWithCoverage', () => {
  it('ranks rows under the coverage floor last and flags them', () => {
    const ranked = rankWithCoverage(rows, 'control_percentage', 90);
    expect(ranked.map((r) => r.partnership)).toEqual(['Rayudu & Kohli', 'Gill & Kohli', 'MacLeod & Berrington', 'Kumar & Mukkamalla']);
    expect(ranked.map((r) => r.coverage_excluded)).toEqual([false, false, true, true]);
  });

  it('leaves untagged metrics and a zero floor alone', () => {
    expect(rankWithCoverage(rows, 'runs', 90)).toBe(rows);
    expect(rankWithCoverage(rows, 'control_percentage', 0)).toBe(rows);
    expect(coverageColumnFor('control_percentage')).toBe('control_coverage_pct');
  });
});
