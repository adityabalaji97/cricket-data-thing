# Product Requirements Document (PRD): Player Impact and Win Probability Added (WPA) Engine for T20 Matches

---

## Overview

This PRD outlines the architecture and functionality of a Player Impact and Win Probability Added (WPA) Engine, designed to quantify the contextual impact of every ball, player performance, and match event in a T20 game using ball-by-ball data. It is tailored for use by large language models (LLMs) such as Claude or ChatGPT to assist in analysis and code generation.

The system must:

* Leverage a growing dataset of over 7000 T20 matches
* Respect chronological constraints to avoid data leakage
* Build venue-specific and phase-specific context models
* Enable WPA-based performance analysis
* Be modular, explainable, and extensible

---

## Key Modules & Components

### 1. Data Input Models

Data is available in SQLAlchemy ORM format from `models.py`. Relevant tables:

* `Match`
* `Delivery`
* `BattingStats`
* `BowlingStats`
* `Player`

Ensure the system reads from pre-processed and cleaned datasets.

### 2. Venue Context Model (DLS-style Resource Table Builder)

**Purpose:** Create historical par scores and resource curves for every venue, for each innings phase.

**Inputs:**

* All matches prior to the current match date at that venue
* League + innings split (optional)

**Outputs:**

* `venue_resource_table[venue][innings][over][wickets] -> %resource_remaining`
* `par_score_distribution[venue][innings][over]`

**Implementation Details:**

* Must support fallback hierarchy: venue > venue cluster > league > global average
* Future-proofing: should work with additional features like pitch type, toss decisions, or weather when available

### 3. Win Probability Model

**Purpose:** Compute WPA per delivery by comparing pre-ball and post-ball match states using venue-specific resource tables.

**Inputs per delivery:**

* Match ID, innings, over, ball, score, wickets
* Current and next state
* Venue-specific resource table

**Outputs:**

* `WPA_batter[delivery_id]`
* `WPA_bowler[delivery_id]`

**Notes:**

* WPA can be positive or negative
* Ignore or scale down WPA shifts in matches that are >95% decided

### 4. Player Impact Engine

**Purpose:** Aggregate impact metrics per player per match using WPA, RAR, and context leverage.

**Batting Metrics:**

* Raw runs, SR, RAR (vs team in same phase)
* WPA contribution
* Entry leverage (overs + wickets at entry)
* SR differential vs team

**Bowling Metrics:**

* Economy diff
* Key wickets (top-order, set batters)
* WPA prevention
* Dot ball pressure index (by phase)

**Fielding Metrics:**

* WPA-shift caused by fielder involvement
* Run-outs, catches, boundary saves (as available)

**Output Schema:**

```json
{
  "player_id": str,
  "match_id": str,
  "batting_impact_score": float,
  "bowling_impact_score": float,
  "fielding_impact_score": float,
  "total_impact_score": float,
  "submetrics": { ... detailed breakdowns ... }
}
```

### 5. WPA Curve Trainer

**Purpose:** Simulate win probability curves based on historical match states (esp. second innings).

**Approach:**

* Use all second innings chase data
* For each (score, over, wickets) tuple, compute historical win% at venue (prior to match date)
* Cache into `wpa_lookup_table[venue][score][over][wickets] -> win_probability`

**Future-Proofing:**

* Extendable with weather, toss, dew, or boundary size inputs
* Replaceable by ML-based win predictor

---

## System Constraints

* Chronological strictness: never use future data in any model for a given match
* Modular pipeline: each phase (context generation, WPA calc, aggregation) is isolated
* LLM-readable: Each function and data model must be clearly named, documented, and JSON serializable where possible

---

## Stretch Goals (Future Extensions)

* ML model for win prediction (gradient boosted trees or transformers)
* Player season-long impact normalization
* League-specific impact weighting (e.g., IPL > BBL)
* UI dashboards for per-match and career-level impact
* Integration with live match data for real-time WPA estimation

---

## Deliverables

* `context_model.py`: resource table builder
* `wpa_engine.py`: per-ball WPA calculator
* `impact_aggregator.py`: per-player match impact calculator
* `venue_utils.py`: venue clustering and fallback logic
* `tests/`: for each module using sample matches from different venues and years

---

## LLM Usage Notes

* LLMs can be used to:

  * Convert pseudocode into Python
  * Generate summary reports from raw WPA outputs
  * Test model behavior by generating mock Delivery sequences
  * Explain player impact deltas across matches

---

**End of PRD**
