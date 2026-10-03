# Hypothesis lab

One script per hypothesis, all through the query-builder engine, so every chart has a `/query`
link that reproduces it. Definitions, thresholds, minimum samples and verdict rules were committed
in [`preregistration/`](preregistration/) **before** any analysis ran.

| Script | Hypothesis |
|---|---|
| `h0_varun_first_over.py` | Varun Chakravarthy: 10+ first over vs rest of match (vs five IPL spinners); powerplay vs middle entry; previous-over pressure with a next-over placebo |
| `h1_impact_player.py` | Impact Player rule and IPL scoring, difference-in-differences vs BBL/PSL/CPL |
| `h2_varun_figured_out.py` | Has Varun been figured out: by season, half-season, hand, length, shot, dismissal |
| `h3_iyer_anchor.py` | Shreyas Iyer in the middle overs vs Suryakumar Yadav, Tilak Varma, Rinku Singh; short balls |
| `h4_india_openers.py` | Spread of Impact per innings for India's T20I openers; win rate when they fail vs fire |
| `h5_anchor_dead.py` | 30+ ball innings by strike rate: WPA and win %, 2015-19 vs 2023-26 |
| `h6_bumrah_death.py` | Leverage-weighted death-overs RAA for all bowlers since 2015; Bumrah's rank and gap |
| `h7_toss_india.py` | Toss-winner win % at Indian venues, 2023-26 |
| `h8_matchups.py` | Leg-spin to LHB, left-arm pace to RHB in the powerplay: within-bowler RAA |

Shared: `common.py` (engine access with paging, bootstrap/Welch/Fisher, verdict rules, result and
chart model), `credits.py` (credit lines for notes and cards).

## Running

The findings need the full men's T20 history (2015 onward). `hindsight_local` holds 2024 onward
only, so build a separate analysis database from production once (read-only on production):

```bash
scripts/dev/setup_analysis_db.sh                      # -> hindsight_analysis, ~3-4 GB
export DATABASE_URL=postgresql://localhost:5432/hindsight_analysis
python -m analysis.hypotheses.run_all                 # writes results/<slug>.json
HINDSIGHT_FULL_DATA=1 pytest -s tests/test_validation_first_over.py
```

To check the scripts run without touching `results/`:

```bash
DATABASE_URL=postgresql://localhost:5432/hindsight_local HYPOTHESIS_BOOTSTRAP=300 \
  HYPOTHESIS_RESULTS_DIR=/tmp/dryrun python -m analysis.hypotheses.run_all
```

Each result JSON holds the verdict, headline, every effect (estimate, 95% CI, p, n), tables, chart
definitions with their `/query` URLs, caveats and the database it came from. Phase 3
(`scripts/notes/build_hypothesis_notes.py`) turns them into /notes drafts and share cards.
