# Query builder metrics: control, coverage, shot families, partnerships

What the query builder (`services/query_builder_v2.py`) counts for the metrics people share, and the
rules that keep a ranking honest when the underlying tags are incomplete. Written after an audit of
three shared stats in October 2026 found leaderboards that were correct for the query but
misleading.

## Balls

A row's `balls` follow the row's perspective (`services/metrics/sql_defs.py`):

| Perspective | When | Balls | Runs | Wickets |
|---|---|---|---|---|
| batter | grouped by batter, or a batters filter | every ball except wides (no-balls are faced) | runs off the bat | the batter's own dismissals |
| bowler | grouped by bowler (no batter) | legal balls (no wides, no no-balls) | runs minus byes and leg-byes | bowler's wickets |
| team | anything else, partnerships included | legal balls | every run, extras included | every real dismissal, run-outs included |

## control_percentage

```
control_percentage = controlled balls / control-tagged balls * 100
```

* **Numerator:** balls with `control = 1`.
* **Denominator:** balls with a control tag (`control` is 0 or 1).
* **Both counted over the row's own balls** (the legal-ball rule above). Wides are never in it for a
  batter.

Until 2026-10-05 the denominator counted every tagged delivery row, wides included. A wide often
carries a control tag, so control % disagreed with `group_by=control`. Gill (ODI) read 87.64%
(3,183 of 3,632) against 3,156 of 3,587 = **87.98%** from the control split; Kohli 86.43% against
13,894 of 15,989 = **86.90%**. Both now match, and `tests/test_tag_coverage.py` checks them.
`having=control_percentage:...` thresholds use the same definition.

## Tag coverage

Five columns are tagged ball by ball by the feed: `control`, `line`, `length`, `shot` and
`wagon_zone`. Not every ball carries them, and how many do depends on the match, the competition
and the era. A wagon zone of 0 means no direction was recorded.

* Every grouped row carries **`control_tagged`** and **`control_coverage_pct`**: control-tagged
  balls / the row's balls.
* A **tag filter** (line, length, shot, shot_family, control, wagon_zone) keeps only the tagged
  balls, so the row's own count can't show what's missing. The query runs a second pass without the
  tag filters and returns **`<tag>_coverage_pct`**: the share of the group's balls, before the tag
  filter, that carry the tag. `metadata.coverage` names the tags.
* Merged pre-2015 T20 rows (legacy table, no tags) add balls but no tagged balls, so they lower
  coverage, as they should.

### Ranking by a tagged metric

`services/coverage.py`. When the ranking metric is built on a tag (today `control_percentage`),
rows whose coverage is below **`min_coverage` (default 90%)**:

* stay in the result, with their values;
* rank after every row that qualifies;
* are flagged `coverage_excluded`;
* are left out of the denominator.

The query builder table shows them greyed, with a tooltip. The "Min control data %" box beside the
sort chip changes the floor; 0 turns it off.

Example (ODI partnerships, 1,000+ balls, by control %): MacLeod & Berrington (93.4%, but only 34.2%
of balls tagged) and Milind Kumar & Mukkamalla (90.4%, 58.4% tagged) used to top it. With the floor,
155 of 211 partnerships qualified (before stands, below, which changed the order).

## Shot families

`services/shot_families.py`. The feed's shot labels changed:

* **Older tagging** (ODIs 2001–2018, T20s 2015–2024) splits by foot, e.g.
  `PULL_HOOK_ON_BACK_FOOT`, `CUT_SHOT_ON_FRONT_FOOT`, `OFF_SIDE_DRIVE_ON_FRONT_FOOT`.
* **Newer tagging** splits by shot: `PULL`, `HOOK`, `CUT_SHOT`, `COVER_DRIVE`.

A `PULL`/`HOOK` filter therefore missed every older pull. ODI pull and hook sixes read Rohit 152, not
170, and left AB de Villiers out.

A family holds every label either scheme used for the same shot. Where the older scheme had one wide
label (`SWEEP`), the family is that wide one, so a family means the same thing in 2005 and 2025.

| Family | Labels |
|---|---|
| PULL_HOOK | PULL, HOOK, PULL_HOOK_ON_BACK_FOOT, PULL_HOOK_ON_FRONT_FOOT |
| CUT | CUT_SHOT, CUT_SHOT_ON_BACK_FOOT, CUT_SHOT_ON_FRONT_FOOT, LATE_CUT, UPPER_CUT |
| DRIVE | COVER_DRIVE, SQUARE_DRIVE, STRAIGHT_DRIVE, ON_DRIVE, OFF/ON_SIDE_DRIVE_ON_BACK/FRONT_FOOT, VERTICAL_FORWARD_ATTACK |
| FLICK_GLANCE | FLICK, LEG_GLANCE |
| SWEEP | SWEEP, SWEEP_SHOT, SLOG_SWEEP, PADDLE_SWEEP |
| REVERSE | REVERSE_SWEEP, REVERSE_SCOOP, REVERSE_PULL |
| RAMP_SCOOP | RAMP, PADDLE_AWAY |
| SLOG | SLOG_SHOT |
| WORK_PUSH | PUSH, PUSH_SHOT, DAB, STEERED, DROP_AND_RUN |
| DEFENCE | DEFENDED, FORWARD_DEFENCE, BACK_DEFENCE |
| LEAVE | LEFT_ALONE, NO_SHOT, PADDED_AWAY |

* `shot_family` is a filter (OR'd with `shot`) and a `group_by` column.
* "Make a graphic" groups by family instead of shot, and turns a shot filter into its families, with
  the definition in the footer.
* With families, ODI pull and hook sixes give Rohit 170, Afridi 72, Gayle 70 and de Villiers 69 (all-time; the
  first card, read from 2005, had Gayle 57 and no Afridi).

## Partnerships

`group_by=partnership` is the two batters at the crease, either way round. It uses the team
perspective:

* **runs:** every run while the pair batted, **extras included**.
* **balls:** legal balls bowled to the pair (wides and no-balls excluded), whichever of them faced.
* **wickets:** dismissals while the pair batted, run-outs included. Retirements aren't dismissals.
* **average:** runs per dismissal (runs / wickets).
* **control_percentage:** controlled / control-tagged balls over the pair's legal balls.

`metadata.definitions` carries these on every partnership result.

### Who was at the crease: `partnership_stands`

`delivery_details.non_striker` is unreliable around wickets. On 45% of ODI wicket balls the feed
names the incoming batter as non-striker on the dismissal ball, or the dismissed one just after. A
stand's closing wicket was then credited to a pair that never batted together. Rohit & Gill read 22
dismissals; they had 46.

Strikers are reliable, so the pair comes from them (migration 016,
`scripts/build_partnership_stands.py`):

* **A stand** is the balls between two dismissals. Any `out = 'true'` ends one, retirements
  included.
* **Its batters** are the distinct strikers in the stand.
* **When only one batter faced,** the partner is the most common non-striker in the stand.
* **If that still leaves no pair** (0.3% of stands), the ball falls back to the feed's
  striker/non-striker.

`group_by=partnership`, `group_by=non_striker` and `partnership_players` read the stand. Pre-2015
T20 rows (legacy table) still use the feed. The nightly refresh builds stands for new matches.
`--full` rebuilds the lot in about 20 s; run it after renaming players through the alias scripts.

With stands, the ODI control ranking (1,000+ balls, 90%+ control data, since 2005, 154
partnerships) is led by Mathews & Sangakkara 88.78%. Gill & Kohli are 6th at 88.22%: 1,232 balls,
24 dismissals, average 53.7, strike rate 104.5.

**Date range:** until 2026-10-05 (LOGIC_VERSION c), a query with no `start_date` read from
2005-01-01, the men's T20 legacy table's start. That left out every ODI from 2000–04. Now
`delivery_details` has no floor, so ODI and cross-format queries read from the first match. All-time,
174 ODI partnerships qualify, and the same five beat Gill & Kohli on both axes.

**Partnerships involving a player:** `partnership_players=[...]` keeps every ball either batter of a
stand faced. A `batters` filter used to count only the named batter's balls of each stand, and in
the batter perspective (runs off the bat). Grouped by partnership, a `batters` filter is now read as
`partnership_players`, and the response says so in `metadata.warnings`.

## "Make a graphic"

`services/content_ideas.attempt`:

* **The denominator is the population actually ranked:** rows with a value and, for a tagged metric,
  at or above the coverage floor. For example: "1st of 155 ODI partnerships (1,000+ balls, 90%+
  control data)", not the raw 211.
* **The footer**, next to "Data as of", carries:
  * the filters;
  * the subject's coverage ("control data: 99.9% of Rayudu and Kohli's balls (90% min)");
  * any shot-family definition.
* **It refuses to rank a subject below the coverage floor**, with a message saying so.
* **It warns, in the picker,** when a tag filter's leader, or anyone above the subject, has less
  tagged data than the floor.
* **A scatter** (`chart: {type: scatter, x_axis, y_axis}`) plots every qualifying row, up to 400.
  It numbers the rows that beat the subject on both axes and lists them under the chart. The title
  counts them ("5 of 153 ODI partnerships beat … on both average and strike rate").
