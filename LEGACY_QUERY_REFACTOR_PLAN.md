# Refactor `query_legacy_grouped()` to single-CTE pattern

## Context

The query-builder route runs `handle_grouped_query()` (against
`delivery_details`, 2015+) AND `query_legacy_grouped()` (against the legacy
`deliveries` table, pre-2015) and merges the results. In the previous
session we refactored the *new* path from 5 sequential queries down to one
combined CTE + tiny fallback (commit `80c25ab`). The legacy path still uses
the old N-query pattern.

After deploying the new-path refactor, the heavy query
(`innings=2&match_outcome=win&group_by=batter,venue&min_runs=800`) returns
on the live API in **~24–28s** — under Heroku's 30s budget but close. Local
benchmarks of the new path alone are ~2s; the remaining ~20s is the legacy
path. Refactoring legacy to match should take total query time well under
5s.

## Differences from `handle_grouped_query()` to keep in mind

These are the gotchas — handle them or the refactor will silently corrupt
results.

1. **Table & joins.** Use `deliveries d JOIN matches m ON d.match_id = m.id
   LEFT JOIN players p ON p.name = d.bowler`. The `LEFT JOIN players p` is
   always present (not conditional on `join_matches`).
2. **Column names.**
   - runs: `d.runs_off_bat` (use_runs_off_bat_only=True) or
     `d.runs_off_bat + d.extras` (else)
   - wickets: `SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END)`
   - dots: `SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END)`
   - boundaries / fours / sixes: same shape, on `d.runs_off_bat`
   - **No `control` column** — `query_legacy_grouped` omits
     `control_percentage` from the result rows. Don't add it.
3. **No HAVING, no LIMIT, no OFFSET.** Legacy returns **all** groups
   sorted by `COUNT(*) DESC`. The route merges with new-path results, then
   applies HAVING / LIMIT downstream. So **two-pass with Stage-2 LIMIT
   doesn't apply here**; the only win is collapsing the 3 queries into 1.
4. **Return signature.** `query_legacy_grouped()` returns a 2-tuple
   `(formatted_results, total_balls)`, not a dict. Callers depend on this.
5. **`total_balls_override`.** Caller can pre-supply `total_balls` to skip
   the count query. The refactor must keep this short-circuit working.
6. **Empty-group safety.** If `valid_group_columns` is empty (all requested
   group_by cols unavailable in legacy), the function returns `([], 0)`
   immediately. Preserve that early return.
7. **`percent_balls` semantics.** Same as new path — relative to parent
   group for multi-level, relative to total for single-level. Use window
   functions like the new path does.

## Approach (mirrors the new-path refactor)

Replace the three sequential queries (`total_balls_query`, `parent_query`,
`aggregation_query`) with **one combined CTE** that:

- Aggregates per-group cheap + rich metrics in a single CTE pass (no
  Stage 2 — see point 3 above; one scan of `deliveries` is the floor).
- Uses window functions to compute `universe_balls` and `parent_balls` in
  the same scan.

```sql
WITH all_groups AS (
    SELECT
        {select_group_clause},
        COUNT(*) as balls,
        COUNT(DISTINCT (d.match_id, d.innings)) as innings_count,
        {runs_calculation} as runs,
        SUM(CASE WHEN d.wicket_type IS NOT NULL THEN 1 ELSE 0 END) as wickets,
        SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
        SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
        SUM(CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END) as fours,
        SUM(CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END) as sixes
    FROM deliveries d
    JOIN matches m ON d.match_id = m.id
    LEFT JOIN players p ON p.name = d.bowler
    {where_clause}
    GROUP BY {group_by_clause}
)
SELECT
    {final_select_groups},
    g.balls, g.innings_count, g.runs, g.wickets,
    g.dots, g.boundaries, g.fours, g.sixes,
    SUM(g.balls) OVER () as universe_balls,
    {parent_partition_sql} as parent_balls
FROM all_groups g
ORDER BY g.balls DESC
```

`parent_partition_sql` follows the same pattern used in
`handle_grouped_query`:

```python
if len(group_by) > 1:
    parent_partition_sql = f"SUM(g.balls) OVER (PARTITION BY g.{group_by[0]})"
else:
    parent_partition_sql = "NULL::bigint"
```

Then in Python:

- Pull `universe_balls` and `parent_balls` from each row.
- If `total_balls_override` is provided, **use it instead of
  `universe_balls`** (preserve the existing short-circuit semantics —
  caller may have a different denominator they want used).
- Compute `percent_balls` per row exactly as today (parent-relative for
  multi-level, total-relative otherwise).
- Build the result dicts unchanged (same shape, same omission of
  `control_percentage`).
- Return `(formatted_results, total_balls)` — same 2-tuple, where
  `total_balls = total_balls_override if total_balls_override is not None
  else universe_balls`.

### Empty-result fallback

If the combined CTE returns 0 rows (no rows match WHERE), `universe_balls`
won't be available from the rows. Mirror the new-path fallback: a tiny
follow-up query that just returns `COUNT(*)` from the same WHERE. Skip if
`total_balls_override is not None`.

```python
if not formatted_results and total_balls_override is None:
    fallback_query = f\"\"\"
        SELECT COUNT(*) FROM deliveries d
        JOIN matches m ON d.match_id = m.id
        LEFT JOIN players p ON p.name = d.bowler
        {where_clause}
    \"\"\"
    total_balls = db.execute(text(fallback_query), query_params).scalar() or 0
```

## Critical files

- `services/query_builder_v2.py:746` — `query_legacy_grouped()` (the
  function to rewrite). Function ends at line 879.
- `services/query_builder_v2.py:2718` — `handle_grouped_query()` to crib
  the CTE-with-window-functions pattern from. Treat it as the reference
  implementation; the legacy version is a stripped-down variant (no
  HAVING, no LIMIT, no Stage 2, no count/innings_total queries).
- No model/schema changes. No new indexes (existing `idx_deliveries_*`
  serve the same access patterns).

## Reused utilities

- `get_legacy_grouping_columns_map()` at `services/query_builder_v2.py:426`
  — the existing column-expression map. Don't touch it.
- `_match_context_warning()` etc. — unaffected.
- `get_legacy_total_balls()` at `services/query_builder_v2.py:882` —
  separate helper, leave alone (callers use it independently).

## Verification

1. **Unit-style equivalence.** Pick three representative inputs and run
   both the old and new function side-by-side, asserting the result lists
   are equal:
   - `(group_by=['venue'], where: leagues=IPL, players=Virat Kohli, innings=2)`
     — single-level grouping, narrow filter.
   - `(group_by=['batter','venue'], where: innings=2, match_outcome=win)`
     — multi-level, the heavy unfiltered case.
   - `(group_by=['phase'], where: leagues=BBL)` — uses a CASE expression
     in the group column.
   Compare both `formatted_results` (every dict) and `total_balls`.
2. **Empty case.** Call with a WHERE that matches zero rows. Confirm
   `([], 0)` (or `total_balls_override` value).
3. **`total_balls_override`.** Pass a sentinel value (e.g. `12345`).
   Confirm the returned `total_balls` is exactly `12345` and that
   `percent_balls` math uses it.
4. **End-to-end live timing.** After deploy, hit
   `/api/query/deliveries?innings=2&match_outcome=win&group_by=batter&group_by=venue&min_runs=800`
   from cold. Expect <10s (down from current 24-28s). Warm should be
   ~3-5s.
5. **GROUP BY consolidation still works.** Confirm RCB / DC / PBKS rows
   appear once each in `?group_by=batting_team&leagues=IPL` (the team-
   standardization migration from the previous session is what makes this
   true; the refactor shouldn't change that).

## Out of scope

- Adding HAVING / LIMIT to the legacy query. The route applies these
  downstream on the merged result; that's deliberate so post-merge groups
  (which combine new + legacy counts for the same key) get filtered
  consistently. Don't push them into legacy.
- `query_legacy_ungrouped()` (if it exists) — separate function, separate
  refactor.
- Adding `control_percentage` to legacy results. The legacy `deliveries`
  table genuinely doesn't have control data; do not fabricate it.

## Handoff notes for next session

The new-path refactor is on `main` at commit `80c25ab` and live as Heroku
v350. The team + venue standardization migrations have already run on the
live DB; the code in `services/query_builder_v2.py` already reflects the
simplified `get_team_canonical_sql()`. Nothing in the legacy refactor
depends on those changes — but the perf benefit will compound: the
simplified `get_team_canonical_sql()` already shrunk `match_outcome`
filter from 8.7K to 480 chars, so legacy queries with `match_outcome`
are already faster than they were before this refactor; the CTE collapse
removes the redundant scans on top.
