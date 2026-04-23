"""Generate pre-match ML predictions and store them in RDS.

Usage:
    # Predict a specific match
    python ml/predict.py \
      --venue "Wankhede Stadium" \
      --team1 "Mumbai Indians" --team2 "Chennai Super Kings" \
      --date 2026-04-23 --competition IPL \
      --cache ml/all_cache.db

    # Predict all upcoming matches (reads from matches table)
    python ml/predict.py --upcoming --cache ml/all_cache.db
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

# Ensure repo root import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml import config
from ml.feature_engineering import FeatureEngineer
from ml.train_model import _prepare_features, _resolve_competitions, _league_slug


# Human-readable labels for raw feature names.
_FEATURE_LABELS: Dict[str, str] = {
    "elo_delta": "Elo rating gap",
    "team1_elo": "Team 1 Elo rating",
    "team2_elo": "Team 2 Elo rating",
    "team1_recent_form": "Team 1 recent form",
    "team2_recent_form": "Team 2 recent form",
    "h2h_team1_wins": "H2H wins (team 1)",
    "h2h_team2_wins": "H2H wins (team 2)",
    "venue_bat_first_win_pct": "Venue bat-first win %",
    "venue_avg_1st_innings_score": "Venue avg 1st innings score",
    "venue_avg_2nd_innings_score": "Venue avg 2nd innings score",
    "venue_avg_winning_score": "Venue avg winning score",
    "venue_avg_chasing_score": "Venue avg chasing score",
    "venue_pace_spin_economy_ratio": "Venue pace/spin economy ratio",
    "venue_pace_economy": "Venue pace economy",
    "venue_spin_economy": "Venue spin economy",
    "venue_pace_wickets_per_match": "Venue pace wickets/match",
    "venue_spin_wickets_per_match": "Venue spin wickets/match",
    "team1_death_avg_runs": "Team 1 death-overs runs",
    "team2_death_avg_runs": "Team 2 death-overs runs",
    "team1_pp_avg_runs": "Team 1 powerplay runs",
    "team2_pp_avg_runs": "Team 2 powerplay runs",
    "team1_middle_avg_runs": "Team 1 middle-overs runs",
    "team2_middle_avg_runs": "Team 2 middle-overs runs",
    "team1_death_avg_wickets_lost": "Team 1 death-overs discipline",
    "team2_death_avg_wickets_lost": "Team 2 death-overs discipline",
    "team1_pp_avg_wickets_lost": "Team 1 powerplay discipline",
    "team2_pp_avg_wickets_lost": "Team 2 powerplay discipline",
    "team1_spin_attack_economy": "Team 1 spin attack economy",
    "team2_spin_attack_economy": "Team 2 spin attack economy",
    "team1_pace_attack_economy": "Team 1 pace attack economy",
    "team2_pace_attack_economy": "Team 2 pace attack economy",
    "team1_spin_attack_vs_venue_delta": "Team 1 spin attack vs venue",
    "team2_spin_attack_vs_venue_delta": "Team 2 spin attack vs venue",
    "team1_control_pct_at_venue": "Team 1 control % at venue",
    "team2_control_pct_at_venue": "Team 2 control % at venue",
    "team1_boundary_pct_at_venue": "Team 1 boundary % at venue",
    "team2_boundary_pct_at_venue": "Team 2 boundary % at venue",
    "toss_aligns_with_venue_bias": "Toss aligns with venue bias",
    "venue_total_matches": "Venue total matches",
    "team1_scoring_style_venue_fit": "Team 1 scoring style venue fit",
    "team2_scoring_style_venue_fit": "Team 2 scoring style venue fit",
}


def _humanize_feature(name: str) -> str:
    """Convert a raw feature column name into a human-readable label."""
    if name in _FEATURE_LABELS:
        return _FEATURE_LABELS[name]
    # Strip one-hot suffixes and format
    return name.replace("_", " ").replace("  ", " ").strip().capitalize()


def _curate_feature_snapshot(
    feature_snapshot: Dict[str, Any],
    team1: str,
    team2: str,
) -> Dict[str, str]:
    """Select the most interpretable features from the snapshot and label them."""
    curated = {}
    _CURATED_KEYS = [
        # Phase stats
        ("team1_pp_avg_runs", f"{team1} avg powerplay runs"),
        ("team2_pp_avg_runs", f"{team2} avg powerplay runs"),
        ("team1_middle_avg_runs", f"{team1} avg middle-overs runs"),
        ("team2_middle_avg_runs", f"{team2} avg middle-overs runs"),
        ("team1_death_avg_runs", f"{team1} avg death-overs runs"),
        ("team2_death_avg_runs", f"{team2} avg death-overs runs"),
        ("team1_pp_avg_wickets_lost", f"{team1} avg powerplay wickets lost"),
        ("team2_pp_avg_wickets_lost", f"{team2} avg powerplay wickets lost"),
        ("team1_death_avg_wickets_lost", f"{team1} avg death-overs wickets lost"),
        ("team2_death_avg_wickets_lost", f"{team2} avg death-overs wickets lost"),
        # Venue
        ("venue_bat_first_win_pct", "Venue bat-first win %"),
        ("venue_avg_1st_innings_score", "Venue avg 1st innings score"),
        ("venue_avg_2nd_innings_score", "Venue avg 2nd innings score"),
        ("venue_pace_spin_economy_ratio", "Venue pace/spin economy ratio"),
        # H2H
        ("h2h_team1_wins", f"H2H wins for {team1}"),
        ("h2h_team2_wins", f"H2H wins for {team2}"),
        # Elo
        ("team1_elo", f"{team1} Elo rating"),
        ("team2_elo", f"{team2} Elo rating"),
        ("elo_delta", "Elo rating gap"),
        # Bowling
        ("team1_spin_attack_economy", f"{team1} spin attack economy"),
        ("team2_spin_attack_economy", f"{team2} spin attack economy"),
        ("team1_pace_attack_economy", f"{team1} pace attack economy"),
        ("team2_pace_attack_economy", f"{team2} pace attack economy"),
        # Form
        ("team1_recent_form", f"{team1} recent form (win %)"),
        ("team2_recent_form", f"{team2} recent form (win %)"),
        # Venue-specific
        ("team1_control_pct_at_venue", f"{team1} control % at this venue"),
        ("team2_control_pct_at_venue", f"{team2} control % at this venue"),
        ("team1_boundary_pct_at_venue", f"{team1} boundary % at this venue"),
        ("team2_boundary_pct_at_venue", f"{team2} boundary % at this venue"),
    ]
    for key, label in _CURATED_KEYS:
        val = feature_snapshot.get(key)
        if val is not None and val != 0:
            curated[label] = round(float(val), 2) if isinstance(val, (int, float)) else val
    return curated


def _generate_narrative_insights(
    team1: str,
    team2: str,
    venue: str,
    team1_win_prob: float,
    team2_win_prob: float,
    predicted_1st: float,
    predicted_2nd: float,
    top_features: List[Dict],
    feature_snapshot: Dict,
) -> List[str]:
    """Generate natural cricket commentary for a prediction using GPT-4o-mini.

    Falls back to template-based insights if the OpenAI call fails.
    """
    curated = _curate_feature_snapshot(feature_snapshot, team1, team2)

    predicted_winner = team1 if team1_win_prob > 0.5 else team2
    win_pct = max(team1_win_prob, team2_win_prob) * 100

    # Build the prompt
    system_msg = (
        "You are a cricket analyst writing concise pre-match insights for a data-driven cricket app. "
        "Write 5-7 short bullet points (one sentence each) explaining WHY the ML model predicts this outcome. "
        "Use the feature data provided. Be specific with numbers. No preamble."
    )
    user_msg = (
        f"Prediction: {predicted_winner} to win ({win_pct:.1f}% probability) at {venue}.\n"
        f"Predicted 1st innings score: {predicted_1st:.0f}. Predicted 2nd innings score: {predicted_2nd:.0f}.\n\n"
        f"Top model features (by importance):\n"
    )
    for f in top_features[:10]:
        user_msg += f"  - {f['feature']}: value={f['value']}, importance={f['importance']}\n"
    user_msg += f"\nDetailed stats:\n"
    for label, val in curated.items():
        user_msg += f"  - {label}: {val}\n"

    try:
        from openai import OpenAI
        client = OpenAI()  # uses OPENAI_API_KEY env var
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        raw = response.choices[0].message.content.strip()
        # Parse bullet points — lines starting with - or * or numbered
        insights = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip leading bullet markers
            for prefix in ("- ", "* ", "• "):
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    break
            # Strip numbered prefixes like "1. " or "1) "
            if len(line) > 2 and line[0].isdigit() and line[1] in (".", ")"):
                line = line[2:].strip()
            elif len(line) > 3 and line[:2].isdigit() and line[2] in (".", ")"):
                line = line[3:].strip()
            if line:
                insights.append(line)
        if insights:
            print(f"[predict] Generated {len(insights)} narrative insights via GPT-4o-mini")
            return insights[:7]
    except Exception as e:
        print(f"[predict] OpenAI narrative generation failed ({e}), using template fallback")

    # Template fallback
    return _template_insights(
        team1, team2, venue, team1_win_prob, team2_win_prob,
        predicted_1st, predicted_2nd, top_features, feature_snapshot,
    )


def _template_insights(
    team1: str, team2: str, venue: str,
    team1_win_prob: float, team2_win_prob: float,
    predicted_1st: float, predicted_2nd: float,
    top_features: List[Dict], feature_snapshot: Dict,
) -> List[str]:
    """Simple f-string templates for the top features when LLM is unavailable."""
    predicted_winner = team1 if team1_win_prob > 0.5 else team2
    win_pct = max(team1_win_prob, team2_win_prob) * 100
    insights = [
        f"Model gives {predicted_winner} a {win_pct:.0f}% chance of winning at {venue}.",
    ]

    elo1 = feature_snapshot.get("team1_elo")
    elo2 = feature_snapshot.get("team2_elo")
    if elo1 and elo2:
        stronger = team1 if elo1 > elo2 else team2
        insights.append(f"{stronger} hold the higher Elo rating ({max(elo1, elo2):.0f} vs {min(elo1, elo2):.0f}).")

    form1 = feature_snapshot.get("team1_recent_form")
    form2 = feature_snapshot.get("team2_recent_form")
    if form1 is not None and form2 is not None:
        better = team1 if form1 > form2 else team2
        insights.append(f"{better} come in with stronger recent form ({max(form1, form2)*100:.0f}% win rate).")

    bat_first_pct = feature_snapshot.get("venue_bat_first_win_pct")
    if bat_first_pct is not None:
        side = "batting first" if bat_first_pct > 0.5 else "chasing"
        insights.append(f"This venue favours {side} (bat-first win rate: {bat_first_pct*100:.0f}%).")

    insights.append(f"Predicted 1st innings score: {predicted_1st:.0f}, 2nd innings: {predicted_2nd:.0f}.")

    return insights[:5]


def _infer_team(feature_name: str) -> Optional[str]:
    """Infer which team a feature belongs to, or None for venue/neutral features."""
    if feature_name.startswith("team1_"):
        return "team1"
    if feature_name.startswith("team2_"):
        return "team2"
    return None


def _find_latest_model_version(league_dir: Path) -> Optional[str]:
    """Find the latest promoted model version in a league directory."""
    metadata_files = sorted(league_dir.glob("training_metadata_v*.json"), reverse=True)
    for mf in metadata_files:
        version = mf.stem.replace("training_metadata_", "")
        # Check that all 3 model artifacts exist
        winner = league_dir / f"match_winner_{version}.joblib"
        score1 = league_dir / f"score_1st_innings_{version}.joblib"
        score2 = league_dir / f"score_2nd_innings_{version}.joblib"
        if winner.exists() and score1.exists() and score2.exists():
            return version
    return None


def _load_models(league_dir: Path, version: str) -> Dict[str, Any]:
    """Load the 3 model artifacts + metadata for a given version."""
    winner = joblib.load(league_dir / f"match_winner_{version}.joblib")
    score1 = joblib.load(league_dir / f"score_1st_innings_{version}.joblib")
    score2 = joblib.load(league_dir / f"score_2nd_innings_{version}.joblib")

    metadata_path = league_dir / f"training_metadata_{version}.json"
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

    return {
        "winner": winner,
        "score_1st": score1,
        "score_2nd": score2,
        "metadata": metadata,
        "version": version,
    }


def _compute_top_features(
    model_dict: Dict[str, Any],
    feature_values: pd.DataFrame,
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Compute per-prediction feature contributions.

    Multiplies each feature's model importance by its z-score in this prediction
    to get a contribution score. Returns top N features.
    """
    model_obj = model_dict["model"]
    feature_cols = model_dict["feature_columns"]

    # Get feature importances from the underlying model
    importances = None
    if hasattr(model_obj, "feature_importances_"):
        importances = model_obj.feature_importances_
    elif hasattr(model_obj, "calibrated_classifiers_"):
        # CalibratedClassifierCV wraps the real model
        base = model_obj.calibrated_classifiers_[0].estimator
        if hasattr(base, "feature_importances_"):
            importances = base.feature_importances_

    if importances is None or len(importances) != len(feature_cols):
        return []

    # Get feature values for this prediction (already prepared)
    values = feature_values[feature_cols].iloc[0].values if len(feature_values) > 0 else np.zeros(len(feature_cols))

    # Rank by model importance alone (the old importance * |value| formula was broken —
    # Elo's large magnitude always dominated regardless of actual predictive contribution)
    top_indices = np.argsort(importances)[::-1][:n]

    results = []
    for idx in top_indices:
        fname = feature_cols[idx]
        val = float(values[idx])
        results.append({
            "feature": _humanize_feature(fname),
            "raw_feature": fname,
            "team": _infer_team(fname),
            "direction": "positive" if val > 0 else "negative",
            "importance": round(float(importances[idx]), 6),
            "value": round(val, 4),
            "contribution": round(float(importances[idx]), 6),
        })

    return results


def _generate_match_id(venue: str, team1: str, team2: str, match_date: str) -> str:
    """Generate a deterministic match ID for prediction storage."""
    # Normalize: lowercase, replace spaces with underscores
    v = venue.lower().replace(" ", "_")[:20]
    t1 = team1.lower().replace(" ", "_")[:10]
    t2 = team2.lower().replace(" ", "_")[:10]
    d = match_date.replace("-", "")
    return f"pred_{t1}_{t2}_{d}_{v}"


def predict_match(
    venue: str,
    team1: str,
    team2: str,
    match_date: str,
    competition: str,
    cache_session,
    rds_session,
    models: Optional[Dict[str, Any]] = None,
    league_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate a prediction for a single match and store it in RDS.

    Args:
        venue: Venue name
        team1: Team 1 full name
        team2: Team 2 full name
        match_date: Date string (YYYY-MM-DD)
        competition: Competition name (e.g., "IPL")
        cache_session: SQLAlchemy session for the local SQLite cache (feature extraction)
        rds_session: SQLAlchemy session for RDS (storing predictions)
        models: Pre-loaded model dict (optional, will auto-load if not provided)
        league_dir: Path to league model directory (required if models not provided)

    Returns:
        Dict with prediction results.
    """
    from sqlalchemy import text

    # Resolve competitions for feature extraction
    competitions = _resolve_competitions([competition])

    # Load models if not provided
    if models is None:
        if league_dir is None:
            slug = _league_slug(competitions[0] if competitions else competition)
            league_dir = config.MODEL_DIR / slug
        version = _find_latest_model_version(league_dir)
        if version is None:
            raise ValueError(f"No trained models found in {league_dir}")
        models = _load_models(league_dir, version)

    version = models["version"]
    metadata = models["metadata"]
    gates_info = metadata.get("promotion_gates", {})
    gates_passed = f"{gates_info.get('passes', '?')}/{len(gates_info.get('gates', []))}"

    # Extract features using local cache
    engineer = FeatureEngineer(cache_session, fast_mode=False)
    engineer._league_competitions = competitions
    # Preload batch caches (delivery_details DataFrame, team phase stats, etc.)
    engineer._preload_batch_caches(competitions=competitions)

    match_row = {
        "date": match_date,
        "team1": team1,
        "team2": team2,
        "venue": venue,
        "competition": competitions[0] if competitions else competition,
        # No toss info for pre-match predictions
        "toss_winner": None,
        "toss_decision": None,
        "team1_elo": None,
        "team2_elo": None,
    }

    # Try to get Elo ratings from the cache
    try:
        elo_query = text("""
            SELECT team1, team2, team1_elo, team2_elo
            FROM matches
            WHERE (team1 = :t1 AND team2 = :t2) OR (team1 = :t2 AND team2 = :t1)
            ORDER BY date DESC LIMIT 1
        """)
        elo_row = cache_session.execute(elo_query, {"t1": team1, "t2": team2}).fetchone()
        if elo_row:
            if elo_row[0] == team1:
                match_row["team1_elo"] = elo_row[2]
                match_row["team2_elo"] = elo_row[3]
            else:
                match_row["team1_elo"] = elo_row[3]
                match_row["team2_elo"] = elo_row[2]
    except Exception:
        pass  # Elo columns may not exist in cache

    print(f"[predict] Extracting features for {team1} vs {team2} at {venue}...")
    features = engineer.extract_match_features(match_row)

    # Prepare feature DataFrame using the same pipeline as training
    feature_df = pd.DataFrame([features])
    candidate_features = models["winner"]["feature_columns"]

    # Use _prepare_features to match training pipeline exactly
    drop_cols = ["match_id", "team1", "team2", "winner", "target_team1_won",
                 "score_team1", "score_team2", "match_date", "date",
                 "sample_weight", "venue", "toss_winner", "toss_decision"]

    X, final_cols, _ = _prepare_features(feature_df, candidate_features, drop_cols)

    # Align columns with each model's expected features
    def _align_features(X_df: pd.DataFrame, model_cols: List[str]) -> pd.DataFrame:
        """Ensure X has exactly the columns the model expects, in the right order."""
        aligned = pd.DataFrame(0.0, index=X_df.index, columns=model_cols)
        for col in model_cols:
            if col in X_df.columns:
                aligned[col] = X_df[col].values
        return aligned

    # --- Winner prediction ---
    winner_model = models["winner"]
    X_winner = _align_features(X, winner_model["feature_columns"])
    win_prob = winner_model["model"].predict_proba(X_winner)[0]
    # The classifier predicts P(team1 wins) — class 1
    if len(win_prob) == 2:
        team1_win_prob = float(win_prob[1])
    else:
        team1_win_prob = float(win_prob[0])
    team2_win_prob = 1.0 - team1_win_prob
    predicted_winner = team1 if team1_win_prob > 0.5 else team2

    # --- Score predictions ---
    score1_model = models["score_1st"]
    X_score1 = _align_features(X, score1_model["feature_columns"])
    predicted_1st = float(score1_model["model"].predict(X_score1)[0])

    score2_model = models["score_2nd"]
    X_score2 = _align_features(X, score2_model["feature_columns"])
    predicted_2nd = float(score2_model["model"].predict(X_score2)[0])

    # --- Top contributing features ---
    top_features = _compute_top_features(winner_model, X_winner, n=10)

    # --- Generate narrative insights ---
    feature_snapshot_raw = {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v)
                            for k, v in features.items() if v is not None}
    narrative_insights = _generate_narrative_insights(
        team1=team1, team2=team2, venue=venue,
        team1_win_prob=team1_win_prob, team2_win_prob=team2_win_prob,
        predicted_1st=predicted_1st, predicted_2nd=predicted_2nd,
        top_features=top_features, feature_snapshot=feature_snapshot_raw,
    )

    # --- Look up match_id from matches table (if exists) ---
    match_id = None
    try:
        mid_query = text("""
            SELECT id FROM matches
            WHERE venue = :venue
            AND ((team1 = :t1 AND team2 = :t2) OR (team1 = :t2 AND team2 = :t1))
            AND date = :d
            LIMIT 1
        """)
        mid_row = rds_session.execute(mid_query, {
            "venue": venue, "t1": team1, "t2": team2, "d": match_date,
        }).fetchone()
        if mid_row:
            match_id = mid_row[0]
    except Exception:
        pass

    if match_id is None:
        match_id = _generate_match_id(venue, team1, team2, match_date)

    # --- Store in RDS ---
    feature_snapshot = feature_snapshot_raw

    upsert_sql = text("""
        INSERT INTO match_predictions (
            match_id, model_version, league,
            predicted_winner, win_probability,
            team1, team2, team1_win_prob, team2_win_prob,
            predicted_1st_innings_score_mean, predicted_2nd_innings_score_mean,
            top_features, feature_snapshot, gates_passed, narrative_insights
        ) VALUES (
            :match_id, :model_version, :league,
            :predicted_winner, :win_probability,
            :team1, :team2, :team1_win_prob, :team2_win_prob,
            :predicted_1st, :predicted_2nd,
            :top_features, :feature_snapshot, :gates_passed, :narrative_insights
        )
        ON CONFLICT ON CONSTRAINT uq_match_predictions_match_model
        DO UPDATE SET
            predicted_winner = EXCLUDED.predicted_winner,
            win_probability = EXCLUDED.win_probability,
            team1 = EXCLUDED.team1,
            team2 = EXCLUDED.team2,
            team1_win_prob = EXCLUDED.team1_win_prob,
            team2_win_prob = EXCLUDED.team2_win_prob,
            predicted_1st_innings_score_mean = EXCLUDED.predicted_1st_innings_score_mean,
            predicted_2nd_innings_score_mean = EXCLUDED.predicted_2nd_innings_score_mean,
            top_features = EXCLUDED.top_features,
            feature_snapshot = EXCLUDED.feature_snapshot,
            gates_passed = EXCLUDED.gates_passed,
            narrative_insights = EXCLUDED.narrative_insights,
            prediction_date = NOW()
    """)

    rds_session.execute(upsert_sql, {
        "match_id": match_id,
        "model_version": version,
        "league": competition,
        "predicted_winner": predicted_winner,
        "win_probability": max(team1_win_prob, team2_win_prob),
        "team1": team1,
        "team2": team2,
        "team1_win_prob": round(team1_win_prob, 4),
        "team2_win_prob": round(team2_win_prob, 4),
        "predicted_1st": round(predicted_1st, 1),
        "predicted_2nd": round(predicted_2nd, 1),
        "top_features": json.dumps(top_features),
        "feature_snapshot": json.dumps(feature_snapshot),
        "gates_passed": gates_passed,
        "narrative_insights": json.dumps(narrative_insights),
    })
    rds_session.commit()

    # Get the prediction ID
    pred_id_row = rds_session.execute(
        text("SELECT id FROM match_predictions WHERE match_id = :mid AND model_version = :v"),
        {"mid": match_id, "v": version},
    ).fetchone()
    pred_id = pred_id_row[0] if pred_id_row else "?"

    result = {
        "match_id": match_id,
        "prediction_id": pred_id,
        "team1": team1,
        "team2": team2,
        "team1_win_prob": round(team1_win_prob, 4),
        "team2_win_prob": round(team2_win_prob, 4),
        "predicted_winner": predicted_winner,
        "predicted_1st_innings_score": round(predicted_1st, 1),
        "predicted_2nd_innings_score": round(predicted_2nd, 1),
        "top_features": top_features,
        "narrative_insights": narrative_insights,
        "model_version": version,
        "gates_passed": gates_passed,
    }

    t1_abbr = team1[:3].upper()
    t2_abbr = team2[:3].upper()
    print(
        f"[predict] {t1_abbr} {team1_win_prob*100:.1f}% vs {t2_abbr} {team2_win_prob*100:.1f}% "
        f"| 1st: {predicted_1st:.0f} | 2nd: {predicted_2nd:.0f} "
        f"| Stored as prediction #{pred_id}"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Generate pre-match ML predictions.")
    parser.add_argument("--venue", type=str, help="Venue name")
    parser.add_argument("--team1", type=str, help="Team 1 full name")
    parser.add_argument("--team2", type=str, help="Team 2 full name")
    parser.add_argument("--date", type=str, help="Match date (YYYY-MM-DD)")
    parser.add_argument("--competition", type=str, default="IPL", help="Competition name")
    parser.add_argument("--cache", type=str, default="ml/all_cache.db",
                        help="Path to local SQLite cache for feature extraction")
    parser.add_argument("--upcoming", action="store_true",
                        help="Predict all upcoming matches from the matches/fixtures table")

    args = parser.parse_args()

    # --- Set up cache session (SQLite for feature extraction) ---
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm

    cache_path = Path(args.cache)
    if not cache_path.exists():
        print(f"[predict] Cache file not found: {cache_path}")
        print("[predict] Run: python ml/cache_manager.py build --cache ml/all_cache.db")
        sys.exit(1)

    _local_engine = _ce(f"sqlite:///{cache_path}")
    _LocalSession = _sm(autocommit=False, autoflush=False, bind=_local_engine)
    cache_session = _LocalSession()

    # --- Set up RDS session (for storing predictions) ---
    from database import SessionLocal
    rds_session = SessionLocal()

    try:
        if args.upcoming:
            # Find upcoming matches from the fixtures/matches table
            from sqlalchemy import text
            today = date.today().isoformat()

            # Try fixtures table first, then matches
            upcoming = []
            try:
                rows = rds_session.execute(text("""
                    SELECT venue, team1, team2, date, competition
                    FROM matches
                    WHERE date >= :today AND winner IS NULL
                    ORDER BY date ASC
                    LIMIT 20
                """), {"today": today}).fetchall()
                upcoming = [{"venue": r[0], "team1": r[1], "team2": r[2],
                             "date": str(r[3]), "competition": r[4]} for r in rows]
            except Exception as e:
                print(f"[predict] Could not query upcoming matches: {e}")

            if not upcoming:
                print("[predict] No upcoming matches found.")
                return

            print(f"[predict] Found {len(upcoming)} upcoming matches.")

            # Group by competition and load models once per league
            from collections import defaultdict
            by_league: Dict[str, List] = defaultdict(list)
            for m in upcoming:
                by_league[m["competition"] or "IPL"].append(m)

            for comp, matches in by_league.items():
                competitions = _resolve_competitions([comp])
                slug = _league_slug(competitions[0] if competitions else comp)
                league_dir = config.MODEL_DIR / slug
                version = _find_latest_model_version(league_dir)
                if version is None:
                    print(f"[predict] No models for {comp} (checked {league_dir}). Skipping {len(matches)} matches.")
                    continue

                models = _load_models(league_dir, version)
                print(f"[predict] Loaded {comp} models: {version}")

                for m in matches:
                    try:
                        predict_match(
                            venue=m["venue"],
                            team1=m["team1"],
                            team2=m["team2"],
                            match_date=m["date"],
                            competition=comp,
                            cache_session=cache_session,
                            rds_session=rds_session,
                            models=models,
                            league_dir=league_dir,
                        )
                    except Exception as e:
                        print(f"[predict] Error predicting {m['team1']} vs {m['team2']}: {e}")

        else:
            # Single match prediction
            if not all([args.venue, args.team1, args.team2, args.date]):
                parser.error("--venue, --team1, --team2, and --date are required for single-match prediction")

            competitions = _resolve_competitions([args.competition])
            slug = _league_slug(competitions[0] if competitions else args.competition)
            league_dir = config.MODEL_DIR / slug
            version = _find_latest_model_version(league_dir)
            if version is None:
                print(f"[predict] No trained models found in {league_dir}")
                sys.exit(1)

            models = _load_models(league_dir, version)
            print(f"[predict] Loaded models: {version} from {league_dir}")

            result = predict_match(
                venue=args.venue,
                team1=args.team1,
                team2=args.team2,
                match_date=args.date,
                competition=args.competition,
                cache_session=cache_session,
                rds_session=rds_session,
                models=models,
                league_dir=league_dir,
            )

            print(f"\n[predict] Full result: {json.dumps(result, indent=2)}")

    finally:
        cache_session.close()
        rds_session.close()


if __name__ == "__main__":
    main()
