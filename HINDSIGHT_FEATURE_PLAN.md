# Hindsight Feature Plan - April 2026

> **Working Directory**: `/Users/adityabalaji/cdt/cricket-data-thing`
> **IMPORTANT FOR ALL LLM AGENTS**: Always `cd /Users/adityabalaji/cdt/cricket-data-thing` before running any commands. All file paths below are relative to this directory unless otherwise noted.

> **Auto-Update Instruction**: After each chunk is completed, committed, pushed to git, and deployed to Heroku, update the status tracker below by changing `[ ]` to `[x]` and adding the completion date. This keeps the plan in sync with actual progress.

---

## Status Tracker

| Chunk | Description | Status | Completed |
|-------|-------------|--------|-----------|
| 1 | Name Condensing + Tooltips | [x] | 2026-04-21 |
| 2 | Scatter Plot Zoom | [ ] | — |
| 3 | xPoints Balls Fix | [x] | 2026-04-21 |
| 4 | NL Query Logging | [ ] | — |
| 5 | Enhanced AI Interpretation | [ ] | — |
| 6 | Intelligent Columns | [ ] | — |
| 7 | Auto-Chart from NL | [ ] | — |
| 8 | LLM Upgrade + Fallback | [ ] | — |
| 9 | ML Training Pipeline | [ ] | — |
| 10 | Hindsight Batch Job | [ ] | — |
| 11 | Foresight/Hindsight UI | [ ] | — |
| 12 | ML Preview Integration | [ ] | — |

---

## Context
The Hindsight cricket analytics app needs several enhancements across three areas: (1) NL query builder improvements, (2) a foresight/hindsight ML learning mechanism for match previews, and (3) fantasy points algorithm fixes. This plan is structured as self-contained chunks that can be independently implemented and committed.

**Key decisions made during brainstorming**:
- ML model: XGBoost/LightGBM (trained locally, no API cost), three separate models for match winner, score prediction, player performance
- Training data: All available matches with recency weighting (hybrid approach)
- LLM: GPT-4o primary with 4o-mini fallback at $15/mo spend threshold
- Scatter zoom: Pinch-to-zoom via `react-zoom-pan-pinch` on all scatter plots
- xPoints fix: Cap batter balls using avg balls per innings from `batting_stats`
- Hindsight UI: Side-by-side foresight/hindsight comparison
- Hindsight batch: Automatic nightly job

---

## Chunk 1: Name Condensing Fix + Hover Tooltips (Quick Win)
**Goal**: Ensure `condenseName()` and `getTeamAbbr()` are applied consistently site-wide, and add hover tooltips with full names.

**Files to modify**:
- `src/utils/playerNameUtils.js` — export a `PlayerNameTooltip` component or add a helper
- `src/utils/teamAbbreviations.js` — export a `TeamNameTooltip` component or helper
- `src/components/QueryResults.jsx` — apply condenseName to all player name columns, getTeamAbbr to team columns, wrap in Tooltip
- `src/components/Matchups.jsx` — same treatment for player/team names
- `src/components/FantasyPlanner.jsx` — same
- `src/components/MatchPreviewCard.jsx` — same
- Any other components displaying player/team names (search for raw name rendering)

**Implementation**:
1. Create a reusable `<CondensedName name={fullName} type="player|team" />` component in `src/components/common/CondensedName.jsx`
   - Renders condensed name with MUI `<Tooltip>` showing full name
   - For players: tooltip shows full name
   - For teams: tooltip shows full team name (reverse lookup from abbreviations)
2. Audit all components that display player/team names and replace raw text with `<CondensedName>`
3. Test on mobile and desktop

**Commit message**: `feat: apply name condensing site-wide with hover tooltips`

---

## Chunk 2: Scatter Plot Autoscaling + Pinch-to-Zoom (Quick Win)
**Goal**: Add intelligent axis autoscaling and pinch-to-zoom/pan on all scatter plots.

**Files to modify**:
- `package.json` — add `react-zoom-pan-pinch` dependency
- `src/components/InningsScatter.jsx` — wrap chart in zoom container, improve axis domains
- `src/components/ComparisonInningsScatter.jsx` — same
- `src/components/BattingScatterChart.jsx` — same (already has some padding logic at lines 154-179)
- `src/components/ChartPanel.jsx` — if it renders scatter plots from query builder

**Implementation**:
1. `npm install react-zoom-pan-pinch`
2. Create a reusable `<ZoomableChart>` wrapper component in `src/components/common/ZoomableChart.jsx`:
   - Wraps children in `<TransformWrapper>` / `<TransformComponent>` from react-zoom-pan-pinch
   - Adds a floating reset-zoom button (MUI IconButton with ZoomOutMap icon)
   - Supports pinch-to-zoom and drag-to-pan on mobile
   - Double-tap to reset on mobile
3. For each scatter plot component, improve axis autoscaling:
   - Calculate data range (min/max for X and Y)
   - Remove outliers (>2 std deviations) from domain calculation
   - Add 10% padding to the trimmed domain
   - Set Recharts `<XAxis domain={[min, max]}/>` and `<YAxis domain={[min, max]}/>`
4. Wrap each scatter plot's `<ResponsiveContainer>` with `<ZoomableChart>`
5. Test on mobile (pinch gestures) and desktop (scroll wheel / drag)

**Commit message**: `feat: add autoscaling and pinch-to-zoom to all scatter plots`

---

## Chunk 3: xPoints Balls-Faced Fix (Quick Win)
**Goal**: Cap batter's projected balls faced using their average balls per innings instead of unrealistic balls-per-dismissal from matchup data.

**Files to modify**:
- `services/matchups.py` — modify consolidated batter row calculation (lines 627-698) and xPoints batting calculation (lines 122-161)
- `fantasy_points_v2.py` — modify `calculate_expected_batting_points_from_matchup` (lines 424-526) to accept and use avg_balls_per_innings cap

**Implementation**:
1. In `matchups.py`, when building the consolidated batter row:
   - Query `batting_stats` for the batter's average `balls_faced` per innings in the relevant time period:
     ```sql
     SELECT AVG(balls_faced) as avg_balls_per_innings
     FROM batting_stats
     WHERE striker = :batter AND match_id IN (relevant matches)
     ```
   - Store as `avg_balls_per_innings` in the consolidated stats
2. In `calculate_expected_batting_points_from_matchup`:
   - After computing `balls` from matchup data, cap it: `balls = min(matchup_balls, avg_balls_per_innings)`
   - If `avg_balls_per_innings` is not available, fall back to a default cap of 30 balls
3. This mirrors the 24-ball normalization already used for bowlers
4. Update the fantasy points display to show the capped balls value

**Commit message**: `fix: cap batter xPoints balls using avg balls per innings`

---

## Chunk 4: NL Query Logging & Learning (1a)
**Goal**: Implement persistent query logging and use successful queries as few-shot examples to improve the LLM prompt.

**Files to modify**:
- `models.py` — add `NLQueryLog` model
- `services/nl2query.py` — add logging after each query, implement few-shot example retrieval
- `routers/nl2query.py` — add feedback endpoint
- New migration SQL file for the table

**Implementation**:
1. Create `nl_query_log` table:
   ```sql
   CREATE TABLE nl_query_log (
     id SERIAL PRIMARY KEY,
     query_text TEXT NOT NULL,
     parsed_filters JSONB,
     query_mode VARCHAR(50),
     group_by JSONB,
     explanation TEXT,
     confidence VARCHAR(20),
     model_used VARCHAR(50),
     execution_success BOOLEAN,
     result_row_count INTEGER,
     user_feedback VARCHAR(20), -- 'good', 'bad', 'refined'
     refined_query_text TEXT,   -- if user refined their search
     ip_hash VARCHAR(64),       -- hashed IP for analytics
     created_at TIMESTAMP DEFAULT NOW(),
     execution_time_ms INTEGER
   );
   ```
2. In `nl2query.py`, log every query after execution (async, non-blocking)
3. Add `POST /nl2query/feedback` endpoint for thumbs up/down on results
4. Implement few-shot example selection:
   - Query `nl_query_log` for top 5 queries with `user_feedback='good'` that are semantically similar (same query_mode or similar filters)
   - Include these as examples in the system prompt before the user's query
5. Track execution success: after query runs, update the log with `execution_success` and `result_row_count`

**Commit message**: `feat: add NL query logging with feedback and few-shot learning`

---

## Chunk 5: Enhanced AI Interpretation + Smart Suggestions (1b)
**Goal**: Replace the plain text AI interpretation with a rich, structured display that includes confidence, parsed filter highlights, and refinement suggestions.

**Depends on**: Chunk 4 (logging table exists)

**Files to modify**:
- `services/nl2query.py` — enhance the prompt to return richer interpretation data
- `src/components/NLQueryInput.jsx` or `src/components/QueryBuilder.jsx` — replace Alert with structured card
- New component: `src/components/NLInterpretation.jsx`

**Implementation**:
1. Update the OpenAI system prompt to also return:
   ```json
   {
     "interpretation": {
       "summary": "Showing Kohli's batting stats against spin bowling since 2023",
       "parsed_entities": [
         {"type": "player", "value": "Virat Kohli", "matched_from": "kohli"},
         {"type": "bowl_kind", "value": "spin bowler", "matched_from": "spin"},
         {"type": "date_range", "value": "2023-present", "matched_from": "since 2023"}
       ],
       "suggestions": [
         "Try adding 'in powerplay' to see phase-specific stats",
         "Add 'grouped by venue' to see ground-wise breakdown"
       ]
     }
   }
   ```
2. Create `NLInterpretation.jsx`:
   - Card with parsed entities as colored chips (player=blue, team=green, filter=orange)
   - Confidence badge (high=green, medium=yellow, low=red)
   - Clickable suggestion chips that modify the query
   - Collapsible "Show raw filters" section
3. Replace the current `<Alert>` in `QueryBuilder.jsx` with `<NLInterpretation>`

**Commit message**: `feat: enhanced AI interpretation with entity highlights and suggestions`

---

## Chunk 6: Intelligent Column Selection (1c)
**Goal**: LLM selects the most relevant columns to display based on the query context, instead of defaulting to balls/runs/strike_rate.

**Depends on**: Chunk 5 (enhanced prompt structure)

**Files to modify**:
- `services/nl2query.py` — extend prompt to return `recommended_columns`
- `src/components/QueryResults.jsx` — use recommended columns for initial display
- `src/components/QueryBuilder.jsx` — pass recommended columns to results

**Implementation**:
1. Add to the OpenAI system prompt:
   ```
   Also return "recommended_columns": a list of 4-6 metric columns most relevant to this query.
   Available metrics: balls, runs, strike_rate, average, wickets, dots, boundaries, fours, sixes,
   dot_percentage, boundary_percentage, economy, control_percentage, percent_balls.
   Choose columns that best answer the user's question.
   ```
2. Pass `recommended_columns` from the NL parse response through to `QueryResults.jsx`
3. In `QueryResults.jsx`, when `recommended_columns` is provided:
   - Use them as the initial visible columns instead of the default `['balls', 'runs', 'strike_rate']`
   - Still allow the user to toggle columns via the existing metric chip selector
4. Examples:
   - "kohli boundaries" → `['balls', 'runs', 'boundaries', 'fours', 'sixes', 'boundary_percentage']`
   - "bumrah economy death overs" → `['balls', 'runs_conceded', 'wickets', 'economy', 'dots', 'dot_percentage']`

**Commit message**: `feat: LLM-driven intelligent column selection for query results`

---

## Chunk 7: Auto-Chart from NL Queries (1d)
**Goal**: LLM suggests an appropriate chart type and axis mapping when the query result is suitable for visualization.

**Depends on**: Chunk 6 (prompt already extended)

**Files to modify**:
- `services/nl2query.py` — extend prompt to return `recommended_chart`
- `src/components/QueryBuilder.jsx` — auto-open chart panel with recommended config
- `src/components/ChartPanel.jsx` — accept initial config from NL recommendation

**Implementation**:
1. Add to the OpenAI system prompt:
   ```
   If the query groups data and would benefit from a chart, return:
   "recommended_chart": {
     "type": "bar" | "scatter" | null,
     "x_axis": "column_name",
     "y_axis": "column_name",
     "reason": "brief explanation"
   }
   Return null if the data isn't suitable for charting (e.g., ungrouped, single row).
   Bar charts work well for comparing categories. Scatter plots work for showing relationships between two metrics.
   ```
2. When `recommended_chart` is returned and result set has 3-50 rows:
   - Auto-expand the chart panel
   - Pre-configure with the recommended chart type and axes
   - Show a dismissible note: "AI suggested this chart because: {reason}"
3. User can still change chart type/axes manually

**Commit message**: `feat: auto-suggest charts from NL query context`

---

## Chunk 8: LLM Model Upgrade + Cost Fallback
**Goal**: Upgrade NL query LLM to GPT-4o with automatic fallback to 4o-mini when approaching monthly spend cap.

**Files to modify**:
- `services/nl2query.py` — add model selection logic and spend tracking
- `models.py` — add `LLMUsageLog` table (or extend `nl_query_log`)
- New migration SQL for usage tracking

**Implementation**:
1. Add usage tracking columns to `nl_query_log` (from Chunk 4):
   ```sql
   ALTER TABLE nl_query_log ADD COLUMN model_used VARCHAR(50);
   ALTER TABLE nl_query_log ADD COLUMN prompt_tokens INTEGER;
   ALTER TABLE nl_query_log ADD COLUMN completion_tokens INTEGER;
   ALTER TABLE nl_query_log ADD COLUMN estimated_cost_usd DECIMAL(8,6);
   ```
2. In `nl2query.py`, implement model selection:
   ```python
   MONTHLY_COST_CAP = 15.0  # USD, leaves $5 buffer
   MODEL_PRIMARY = "gpt-4o"
   MODEL_FALLBACK = "gpt-4o-mini"

   def select_model():
       month_start = datetime.now().replace(day=1)
       total_spend = db.query(func.sum(NLQueryLog.estimated_cost_usd))
           .filter(NLQueryLog.created_at >= month_start).scalar() or 0
       return MODEL_PRIMARY if total_spend < MONTHLY_COST_CAP else MODEL_FALLBACK
   ```
3. After each API call, log token usage from the OpenAI response and compute estimated cost
4. Add an admin endpoint `GET /nl2query/usage` to check current month spend

**Commit message**: `feat: GPT-4o primary with 4o-mini cost fallback`

---

## Chunk 9: Foresight/Hindsight ML Model - Training Pipeline
**Goal**: Build a gradient boosting model trained on historical match data to predict match outcomes, score ranges, and player performance.

**This is the largest chunk. It introduces new files and a training pipeline.**

**New files**:
- `ml/feature_engineering.py` — feature extraction from DB
- `ml/train_model.py` — model training script
- `ml/models/` — directory for saved model files (.joblib)
- `ml/config.py` — model hyperparameters, feature lists
- `requirements.txt` update — add `xgboost`, `scikit-learn`, `joblib`

**Existing files to modify**:
- `models.py` — add `MatchPrediction` and `HindsightComparison` tables
- New migration SQL for new tables

**Implementation**:

### 9a. Database Tables
```sql
CREATE TABLE match_predictions (
  id SERIAL PRIMARY KEY,
  match_id VARCHAR(255) REFERENCES matches(id),
  prediction_date TIMESTAMP DEFAULT NOW(),
  model_version VARCHAR(50),
  -- Match winner prediction
  predicted_winner VARCHAR(255),
  win_probability DECIMAL(5,3),
  -- Score predictions
  predicted_1st_innings_score_low INTEGER,
  predicted_1st_innings_score_high INTEGER,
  predicted_1st_innings_score_mean DECIMAL(6,2),
  predicted_2nd_innings_score_low INTEGER,
  predicted_2nd_innings_score_high INTEGER,
  predicted_2nd_innings_score_mean DECIMAL(6,2),
  -- Phase predictions (JSONB: {powerplay: {runs: X, wickets: Y}, ...})
  predicted_phase_performance JSONB,
  -- Player predictions (JSONB: [{player, predicted_runs, predicted_wickets, predicted_xpoints}, ...])
  predicted_player_performance JSONB,
  -- Feature snapshot (for debugging/analysis)
  feature_snapshot JSONB,
  -- Decision score from existing preview system
  preview_lean_score INTEGER,
  preview_lean_direction VARCHAR(50),
  UNIQUE(match_id, model_version)
);

CREATE TABLE hindsight_comparisons (
  id SERIAL PRIMARY KEY,
  match_id VARCHAR(255) REFERENCES matches(id),
  prediction_id INTEGER REFERENCES match_predictions(id),
  computed_at TIMESTAMP DEFAULT NOW(),
  -- Outcome accuracy
  winner_correct BOOLEAN,
  score_1st_innings_actual INTEGER,
  score_1st_innings_error DECIMAL(6,2),
  score_2nd_innings_actual INTEGER,
  score_2nd_innings_error DECIMAL(6,2),
  -- Phase accuracy (JSONB: {powerplay: {predicted: X, actual: Y, error: Z}, ...})
  phase_accuracy JSONB,
  -- Player accuracy (JSONB: [{player, predicted_xpoints, actual_points, error}, ...])
  player_accuracy JSONB,
  -- Metric-level accuracy for learning
  metric_accuracies JSONB,
  -- Overall calibration score (0-1, how well-calibrated were predictions)
  calibration_score DECIMAL(5,3),
  UNIQUE(match_id, prediction_id)
);
```

### 9b. Feature Engineering (`ml/feature_engineering.py`)
Extract features for a given match using ONLY data available before match date:

**Venue features**:
- `venue_bat_first_win_pct` — from matches table
- `venue_avg_1st_innings_score`, `venue_avg_2nd_innings_score`
- `venue_avg_winning_score`, `venue_avg_chasing_score`
- `venue_cluster_type` — from venue_clusters table
- `venue_total_matches` — sample size indicator

**Team features**:
- `team1_elo`, `team2_elo`, `elo_delta`
- `team1_recent_form` (wins in last 5), `team2_recent_form`
- `h2h_team1_wins`, `h2h_team2_wins` (last 10 H2H)
- `team1_pp_avg_runs`, `team1_middle_avg_runs`, `team1_death_avg_runs` (and for team2)
- `team1_pp_avg_wickets_lost`, etc.

**Toss features**:
- `toss_winner_is_team1` (binary)
- `toss_decision` (bat=1, bowl=0)
- `toss_aligns_with_venue_bias` (binary)

**Phase template features** (from `team_phase_stats` or computed):
- `team1_bat_first_template_alignment` — how closely team1's batting profile matches the venue's bat-first-winning template
- `team2_chase_template_alignment` — same for chasing
- (and vice versa for the other scenario)

**Pace vs Spin venue features** (from `delivery_details` where `bowl_kind` is available):
- `venue_pace_economy` — avg economy of pace bowlers at this venue
- `venue_spin_economy` — avg economy of spin bowlers at this venue
- `venue_pace_wickets_per_match` — avg pace wickets per match
- `venue_spin_wickets_per_match` — avg spin wickets per match
- `venue_pace_dot_pct` — dot ball % for pace at this venue
- `venue_spin_dot_pct` — dot ball % for spin at this venue
- `venue_pace_boundary_pct` — boundary % conceded by pace
- `venue_spin_boundary_pct` — boundary % conceded by spin
- `venue_pace_spin_economy_ratio` — pace_economy / spin_economy (>1 = spin-friendly, <1 = pace-friendly)
- Phase-wise pace/spin splits: `venue_pp_pace_economy`, `venue_death_spin_economy`, etc. (pace dominates PP, spin matters in middle — capture these patterns)

**Individual bowler type features** (RF, LM, SLO, etc. from `bowl_style`):
- Per bowler type at venue: `venue_{bowl_style}_economy`, `venue_{bowl_style}_wickets_per_match`
- Per bowler type per phase: `venue_pp_{bowl_style}_economy`, `venue_death_{bowl_style}_economy`
- Team bowling attack composition: `team1_pace_overs_pct`, `team1_spin_overs_pct` (what % of overs does each team bowl pace vs spin?)
- Team bowling type matchup vs venue: `team1_spin_attack_economy` vs `venue_spin_economy` (does this team's spinners suit this venue?)

**Batter handedness & crease combo features** (from `delivery_details` — `bat_hand`, `crease_combo`):
- `venue_lhb_sr` vs `venue_rhb_sr` — strike rate by batter handedness at this venue
- `venue_lhb_boundary_pct` vs `venue_rhb_boundary_pct` — boundary % by handedness
- `venue_lhb_vs_spin_sr`, `venue_rhb_vs_spin_sr` — handedness vs bowling type at venue
- `venue_lhb_vs_pace_sr`, `venue_rhb_vs_pace_sr` — same for pace
- Crease combo overall: `venue_RHB_RHB_sr`, `venue_RHB_LHB_sr`, `venue_LHB_RHB_sr`, `venue_LHB_LHB_sr` — strike rates by crease combo at venue
- Crease combo vs bowling type: `venue_RHB_LHB_vs_spin_sr`, `venue_LHB_RHB_vs_pace_sr`, etc.
- Phase-wise crease combo: `venue_middle_RHB_LHB_vs_spin_sr` — e.g., left-right combos vs spin in middle overs (captures the insight that mixed combos disrupt spin bowling lines, possibly due to uneven boundaries)
- Per bowler style: `venue_RHB_LHB_vs_SLO_sr`, `venue_LHB_LHB_vs_RF_sr` — crease combo effectiveness against specific bowler types
- Team crease composition: `team1_lhb_count`, `team1_rhb_count` — how many LHB/RHB in the lineup (teams with more LHB may have an edge at certain venues)
- `team1_crease_combo_diversity` — how frequently does this team create mixed crease combos (higher = more disruptive to bowlers)

**Line and length venue features** (post-2015 from `delivery_details`):
- `venue_good_length_runs_pct` — % of runs scored off good length at this venue
- `venue_short_boundary_pct` — boundary % off short balls (indicates small ground / true bounce)
- `venue_yorker_dot_pct` — effectiveness of yorkers at this venue
- `venue_full_scoring_rate` — runs per ball off full deliveries
- Dominant length profile: which lengths are most/least effective at this venue
- Length effectiveness by pace vs spin: `venue_spin_good_length_economy` vs `venue_pace_good_length_economy`

**WPA-derived features** (from `deliveries.wpa_batter`, `deliveries.wpa_bowler`):
- `venue_avg_wpa_per_delivery` — overall match impact density at this venue
- `venue_pace_avg_wpa` vs `venue_spin_avg_wpa` — which bowling type creates more impact at this venue
- `team1_avg_wpa_batting` — team's avg batting WPA contribution (measures clutch ability)
- `team1_avg_wpa_bowling` — team's bowling impact
- `player_avg_wpa` — for top players, individual WPA signature (for player performance model)

**Ball direction features** (from `deliveries.ball_direction` — intoBatter/awayFromBatter):
- `venue_into_batter_boundary_pct` — how punishing is bowling into the batter at this venue
- `venue_away_batter_dot_pct` — how effective is bowling away from the batter
- `team1_into_batter_sr` vs `team1_away_batter_sr` — how the team's batters handle different lines

**Batting position & match situation features** (from `batting_stats`):
- `team1_avg_entry_overs_top3` — how early do the top 3 typically bat (stability indicator)
- `team1_avg_batting_position_weighted_sr` — position-weighted strike rates
- `player_typical_entry_overs` — when does this player usually come in
- `player_avg_sr_by_entry_phase` — how does entry timing affect performance

**Performance context features** (from `batting_stats.sr_diff`, `bowling_stats.economy_diff`):
- `team1_avg_sr_diff` — team's batters' avg strike rate vs team context (impact players have high positive sr_diff)
- `team1_avg_economy_diff` — team's bowlers' avg economy diff vs team (negative = better than team)
- `player_sr_diff_consistency` — std deviation of sr_diff (low = reliable, high = volatile)

**Scoring pattern features** (from `batting_stats.ones`, `twos`, `threes`):
- `team1_rotation_pct` — % of runs from 1s, 2s, 3s (vs boundaries). Rotation-heavy teams may suit slower venues
- `venue_rotation_vs_boundary_winners` — do teams that rotate or hit boundaries tend to win here?
- `team1_scoring_style_venue_fit` — how well does team's scoring style match venue winners' profile

**Wagon zone venue profiles** (from `delivery_details.wagon_zone`):
- `venue_zone_X_boundary_pct` (for zones 0-8) — which zones score boundaries most (proxy for boundary dimensions)
- `venue_scoring_zone_concentration` — are runs concentrated in specific zones? (flatter grounds have more even distribution)
- `team1_strong_zones_vs_venue_profitable_zones` — overlap between team's preferred scoring zones and venue's high-scoring zones

**General granular features (post-2015 only, nullable for older matches)**:
- `team1_control_pct_at_venue` — from delivery_details
- `team1_boundary_pct_at_venue`
- `team1_dot_pct_at_venue`
- Shot selection profile similarity to venue winners

**Player-level features** (leveraging precomputed `player_baselines` table directly):
- Use `player_baselines` at venue_specific → cluster → league → global fallback levels
- `team1_top3_batter_baseline_sr` — from player_baselines for top 3 batters
- `team1_bowling_baseline_economy` — from player_baselines for bowling attack
- `team1_top3_batter_avg_xpoints` — predicted fantasy contribution
- `team1_key_matchup_edge_score` — from consolidated matchup data
- `player_batting_points_avg`, `player_bowling_points_avg`, `player_fielding_points_avg` — from batting_stats/bowling_stats fantasy breakdown (separate prediction targets for player model)

**Team-level features** (leveraging precomputed `team_phase_stats` table directly):
- Use `team_phase_stats` at venue_specific → cluster → league → global fallback
- `team1_pp_avg_runs`, `team1_middle_avg_runs`, `team1_death_avg_runs` per innings type
- `team1_boundary_rate`, `team1_dot_rate` per phase
- Delta between team1 and team2 phase stats at this venue type

**Sparsity management note**: Features at individual bowler style level (`SLO`, `RF`, `LM`, etc.) should be computed at **cluster or league level**, not venue level, to avoid sparse features. Only pace vs spin splits should be venue-level. XGBoost handles NaN natively so missing features for older matches are fine.

**Recency weighting**: All features that aggregate historical data use exponential decay weighting:
```python
weight = exp(-lambda * days_since_match)  # lambda tuned per feature
```

### 9c. Model Training (`ml/train_model.py`)
1. **Data preparation**:
   - For each match in DB: extract features using only pre-match data (temporal split)
   - Label: actual winner (binary), actual scores (regression), actual player points (regression)
   - Handle missing features for pre-2015 matches (XGBoost handles NaN natively)
   - Apply recency weighting to training samples

2. **Model architecture** — Three separate XGBoost models:
   - `match_winner_model` — XGBClassifier for binary win prediction
   - `score_predictor_model` — XGBRegressor for 1st/2nd innings score
   - `player_performance_model` — XGBRegressor for per-player xPoints

3. **Training procedure**:
   ```python
   from xgboost import XGBClassifier, XGBRegressor
   from sklearn.model_selection import TimeSeriesSplit

   # Temporal cross-validation (no future data leakage)
   tscv = TimeSeriesSplit(n_splits=5)

   winner_model = XGBClassifier(
       n_estimators=200, max_depth=6, learning_rate=0.1,
       subsample=0.8, colsample_bytree=0.8,
       eval_metric='logloss', early_stopping_rounds=20
   )
   ```

4. **Feature importance output**: After training, export feature importance rankings to understand which metrics matter most at each venue type.

5. **Model serialization**: Save to `ml/models/match_winner_v{version}.joblib`, etc.

**Commit message**: `feat: ML training pipeline for match outcome, score, and player predictions`

---

## Chunk 10: Hindsight Batch Job + Nightly Automation
**Goal**: Automated nightly job that computes hindsight comparisons for completed matches and retrains models.

**Depends on**: Chunk 9

**New files**:
- `ml/hindsight_batch.py` — batch processing script
- `ml/retrain.py` — retraining orchestrator

**Existing files to modify**:
- `services/match_preview.py` — integrate model predictions into preview generation
- Cron/scheduler config (Vercel cron or system crontab)

**Implementation**:
1. `hindsight_batch.py`:
   - Query matches completed since last batch run that have predictions but no hindsight comparison
   - For each match:
     a. Retrieve the stored `match_predictions` row
     b. Compute actual outcomes from `matches`, `batting_stats`, `bowling_stats`
     c. Compare predicted vs actual for each metric
     d. Insert into `hindsight_comparisons`
   - Log results summary

2. `retrain.py`:
   - After hindsight batch completes, check if retraining is needed:
     - New matches since last training > threshold (e.g., 10 matches)
     - OR calibration score has drifted below threshold
   - If retraining needed:
     a. Extract full training set
     b. Train new model version
     c. Evaluate on holdout set
     d. If performance >= previous model, promote to production
     e. Save model with version tag

3. Schedule via Vercel cron (if supported) or system crontab:
   ```
   0 6 * * * cd /Users/adityabalaji/cdt/cricket-data-thing && python ml/hindsight_batch.py && python ml/retrain.py
   ```

**Commit message**: `feat: nightly hindsight batch job with auto-retraining`

---

## Chunk 11: Foresight/Hindsight UI — Match Preview + Review Views
**Goal**: Side-by-side foresight (pre-match prediction) and hindsight (post-match comparison) views.

**Depends on**: Chunk 10

**Files to modify**:
- `src/components/MatchPreviewCard.jsx` — add "View Hindsight" button for completed matches
- New: `src/components/MatchHindsightCard.jsx` — the review view
- New: `src/components/ForesightHindsightComparison.jsx` — side-by-side comparison
- `routers/match_preview.py` — add hindsight endpoint
- `services/match_preview.py` — add hindsight data retrieval

**Implementation**:
1. Backend endpoint: `GET /match-hindsight/{match_id}`
   - Returns the stored prediction + actual outcomes + comparison metrics
   - Returns accuracy scores per metric category

2. `ForesightHindsightComparison.jsx`:
   - Two-column layout (mobile: stacked tabs)
   - Left: Foresight (predicted metrics)
   - Right: Hindsight (actual outcomes)
   - Color coding: green = prediction accurate, red = prediction missed, yellow = partial

   Sections:
   | Section | Foresight | Hindsight |
   |---------|-----------|-----------|
   | Winner | Predicted winner + probability | Actual winner + margin |
   | 1st Innings | Predicted score range | Actual score |
   | 2nd Innings | Predicted score range | Actual score |
   | Phase Breakdown | Predicted phase template | Actual phase performance |
   | Top Performers | xPoints predictions | Actual fantasy points |
   | Key Matchups | Edge predictions | Actual outcomes |

3. Add navigation from match preview to hindsight view (for completed matches)
4. Add a "Model Accuracy" summary card showing the model's overall track record

**Commit message**: `feat: foresight/hindsight comparison UI with side-by-side view`

---

## Chunk 12: Integrate ML Predictions into Match Preview
**Goal**: Replace raw average-based predictions in the match preview with ML model predictions.

**Depends on**: Chunks 9 + 10

**Files to modify**:
- `services/match_preview.py` — use model predictions alongside or instead of rule-based predictions
- `routers/match_preview.py` — serve model predictions in preview response

**Implementation**:
1. At preview generation time:
   - Extract features for the upcoming match (same as training pipeline)
   - Run through the three models to get predictions
   - Store predictions in `match_predictions` table
2. In the preview sections, blend model predictions with existing deterministic logic:
   - Score predictions: show model's predicted range alongside venue average
   - Phase strategy: weight by model's learned feature importances
   - Fantasy picks: use model-adjusted xPoints instead of raw matchup calculation
3. Display model confidence alongside predictions
4. Keep the existing deterministic logic as a fallback when model confidence is low

**Commit message**: `feat: integrate ML predictions into match preview generation`

---

## Implementation Order & Dependencies

```
Chunk 1 (names)        ─── no deps ───┐
Chunk 2 (scatter zoom) ─── no deps ───┤
Chunk 3 (xPoints fix)  ─── no deps ───┼── Can all be done in parallel
Chunk 4 (query logging) ── no deps ───┤
Chunk 8 (LLM upgrade)  ── no deps ────┘

Chunk 5 (AI interpret) ── depends on Chunk 4 (logging table exists)
Chunk 6 (smart columns) ─ depends on Chunk 5 (enhanced prompt structure)
Chunk 7 (auto-chart)   ── depends on Chunk 6 (prompt already extended)

Chunk 9 (ML pipeline)  ── no deps (new code) ──┐
Chunk 10 (batch job)   ── depends on Chunk 9 ───┤
Chunk 11 (UI)          ── depends on Chunk 10 ──┤
Chunk 12 (integration) ── depends on Chunk 9+10 ┘
```

**Recommended execution order**:
1. First: Chunks 1, 2, 3 (quick wins, immediate UX improvements)
2. Second: Chunks 4, 8 (infrastructure for NL improvements)
3. Third: Chunks 5, 6, 7 (NL query builder enhancements, sequential)
4. Fourth: Chunk 9 (ML training pipeline — largest single chunk)
5. Fifth: Chunks 10, 11, 12 (hindsight system completion)

---

## Verification

After each chunk, verify by:
- **Chunks 1-3**: Manual testing in browser (mobile + desktop)
- **Chunk 4**: Check `nl_query_log` table populates after NL queries
- **Chunks 5-7**: Submit NL queries and verify enhanced interpretation, smart columns, auto-charts
- **Chunk 8**: Check model selection switches based on spend tracking
- **Chunk 9**: Run `python ml/train_model.py`, verify model files created, check feature importance output
- **Chunk 10**: Run `python ml/hindsight_batch.py` on historical data, verify `hindsight_comparisons` table
- **Chunk 11**: Navigate to a completed match and verify side-by-side comparison renders
- **Chunk 12**: Generate a preview and verify ML predictions appear alongside deterministic ones

---

## Key Database Tables Reference

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `matches` | Match metadata | venue, team1, team2, winner, toss_decision, team1_elo, team2_elo |
| `batting_stats` | Per-innings batting | runs, balls_faced, fours, sixes, pp/middle/death phase breakdowns, sr_diff |
| `bowling_stats` | Per-innings bowling | overs, runs_conceded, wickets, economy, pp/middle/death phase breakdowns |
| `delivery_details` | Ball-by-ball (post-2015) | line, length, shot, control, wagon_zone, bat_hand, bowl_style, bowl_kind |
| `deliveries` | Ball-by-ball (all) | runs_off_bat, extras, wicket_type, crease_combo |
| `player_baselines` | Precomputed player metrics | avg_runs, avg_strike_rate, avg_balls_faced per venue/phase |
| `team_phase_stats` | Precomputed team metrics | avg_runs, avg_wickets, avg_run_rate per team/venue/phase |
| `venue_clusters` | Venue groupings | cluster_type: high_scoring, balanced, bowling_friendly |
| `wpa_outcomes` | Win probability | target_bucket, over_bucket, wickets_lost, win_probability |
