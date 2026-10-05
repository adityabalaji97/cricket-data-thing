/**
 * Coverage-aware ranking for tagged metrics, the site's twin of services/coverage.py.
 *
 * Control (and line, length, shot, wagon zone) is tagged ball by ball, and how many balls carry the
 * tag varies. Ranked by a tagged metric, a row whose balls are mostly untagged is kept and shown, but
 * ranks after every row that qualifies, flagged `coverage_excluded` (the table greys it).
 */
export const TAGGED_METRICS = { control_percentage: 'control' };
export const DEFAULT_MIN_COVERAGE = 90;

export const coverageColumnFor = (metric) => (TAGGED_METRICS[metric] ? `${TAGGED_METRICS[metric]}_coverage_pct` : null);

/** Rows already in ranking order -> qualifying rows first, then the rest flagged. Summary rows stay put. */
export const rankWithCoverage = (rows, metric, minCoverage = DEFAULT_MIN_COVERAGE) => {
  const column = coverageColumnFor(metric);
  if (!column || !minCoverage) return rows;
  const flagged = rows.map((row) => ({
    ...row,
    coverage_excluded: !row.is_summary && !(Number(row[column]) >= minCoverage),
  }));
  return [...flagged.filter((r) => !r.coverage_excluded), ...flagged.filter((r) => r.coverage_excluded)];
};
