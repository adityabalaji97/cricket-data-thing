"""Configuration for foresight/hindsight ML training."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_ROOT = PROJECT_ROOT / "ml"
MODEL_DIR = ML_ROOT / "models"

MODEL_VERSION_PREFIX = "v"
RECENCY_HALF_LIFE_DAYS = 240.0
TIME_SERIES_SPLITS = 5
RANDOM_STATE = 42

# Defensive training thresholds to avoid fitting on tiny slices.
MIN_MATCH_ROWS = 120
MIN_PLAYER_ROWS = 300
MIN_LEAGUE_MATCHES = 120  # Minimum completed matches to train a per-league model.

# Per-league model output: models saved under models/<league_slug>/.
MODEL_DIR_STRUCTURE = "per_league"

# Aliases for competition names — maps short/common names to canonical names.
LEAGUE_ALIASES = {
    "IPL": "Indian Premier League",
    "BBL": "Big Bash League",
    "PSL": "Pakistan Super League",
    "CPL": "Caribbean Premier League",
    "T20I": "T20 International",
    "T20 Intl": "T20 International",
    "SA20": "SA20",
    "ILT20": "International League T20",
    "MLC": "Major League Cricket",
    "BPL": "Bangladesh Premier League",
    "LPL": "Lanka Premier League",
    "The Hundred": "The Hundred",
    "T20 Blast": "Vitality Blast",
}

# Optional shortlist for styles where we export dedicated style-level features.
BOWL_STYLE_FEATURES = ["RF", "RFM", "RM", "LF", "LFM", "LM", "SLO", "OB", "LB"]

MATCH_FEATURE_COLUMNS = [
    # Context
    "competition",
    "venue_cluster_type",
    "venue_total_matches",
    # Venue profile
    "venue_bat_first_win_pct",
    "venue_avg_1st_innings_score",
    "venue_avg_2nd_innings_score",
    "venue_avg_winning_score",
    "venue_avg_chasing_score",
    # Team and form
    "team1_elo",
    "team2_elo",
    "elo_delta",
    "team1_recent_form",
    "team2_recent_form",
    "h2h_team1_wins",
    "h2h_team2_wins",
    # Team phase behavior
    "team1_pp_avg_runs",
    "team1_middle_avg_runs",
    "team1_death_avg_runs",
    "team2_pp_avg_runs",
    "team2_middle_avg_runs",
    "team2_death_avg_runs",
    "team1_pp_avg_wickets_lost",
    "team1_middle_avg_wickets_lost",
    "team1_death_avg_wickets_lost",
    "team2_pp_avg_wickets_lost",
    "team2_middle_avg_wickets_lost",
    "team2_death_avg_wickets_lost",
    # Toss context
    "toss_winner_is_team1",
    "toss_decision_bat",
    "toss_aligns_with_venue_bias",
    # Template alignment
    "team1_bat_first_template_alignment",
    "team1_chase_template_alignment",
    "team2_bat_first_template_alignment",
    "team2_chase_template_alignment",
    # Pace/spin venue profile
    "venue_pace_economy",
    "venue_spin_economy",
    "venue_pace_wickets_per_match",
    "venue_spin_wickets_per_match",
    "venue_pace_dot_pct",
    "venue_spin_dot_pct",
    "venue_pace_boundary_pct",
    "venue_spin_boundary_pct",
    "venue_pace_spin_economy_ratio",
    "venue_pp_pace_economy",
    "venue_middle_spin_economy",
    "venue_death_pace_economy",
    "venue_death_spin_economy",
    # Team bowling composition
    "team1_pace_overs_pct",
    "team1_spin_overs_pct",
    "team2_pace_overs_pct",
    "team2_spin_overs_pct",
    "team1_spin_attack_economy",
    "team2_spin_attack_economy",
    "team1_pace_attack_economy",
    "team2_pace_attack_economy",
    "team1_spin_attack_vs_venue_delta",
    "team2_spin_attack_vs_venue_delta",
    # Handedness / crease combos
    "venue_lhb_sr",
    "venue_rhb_sr",
    "venue_lhb_boundary_pct",
    "venue_rhb_boundary_pct",
    "venue_lhb_vs_spin_sr",
    "venue_rhb_vs_spin_sr",
    "venue_lhb_vs_pace_sr",
    "venue_rhb_vs_pace_sr",
    "venue_RHB_RHB_sr",
    "venue_RHB_LHB_sr",
    "venue_LHB_RHB_sr",
    "venue_LHB_LHB_sr",
    "venue_middle_RHB_LHB_vs_spin_sr",
    "venue_middle_LHB_RHB_vs_spin_sr",
    "team1_lhb_count",
    "team1_rhb_count",
    "team2_lhb_count",
    "team2_rhb_count",
    "team1_crease_combo_diversity",
    "team2_crease_combo_diversity",
    # Line and length
    "venue_good_length_runs_pct",
    "venue_short_boundary_pct",
    "venue_yorker_dot_pct",
    "venue_full_scoring_rate",
    "venue_dominant_length_runs_share",
    "venue_spin_good_length_economy",
    "venue_pace_good_length_economy",
    # WPA and direction
    "venue_avg_wpa_per_delivery",
    "team1_avg_wpa_batting",
    "team2_avg_wpa_batting",
    "team1_avg_wpa_bowling",
    "team2_avg_wpa_bowling",
    "venue_into_batter_boundary_pct",
    "venue_away_batter_dot_pct",
    "team1_into_batter_sr",
    "team1_away_batter_sr",
    "team2_into_batter_sr",
    "team2_away_batter_sr",
    # Team performance context
    "team1_avg_entry_overs_top3",
    "team2_avg_entry_overs_top3",
    "team1_avg_batting_position_weighted_sr",
    "team2_avg_batting_position_weighted_sr",
    "team1_avg_sr_diff",
    "team2_avg_sr_diff",
    "team1_avg_economy_diff",
    "team2_avg_economy_diff",
    "team1_player_sr_diff_consistency",
    "team2_player_sr_diff_consistency",
    "team1_rotation_pct",
    "team2_rotation_pct",
    "venue_rotation_vs_boundary_winners",
    "team1_scoring_style_venue_fit",
    "team2_scoring_style_venue_fit",
    # Wagon zones
    "venue_zone_0_boundary_pct",
    "venue_zone_1_boundary_pct",
    "venue_zone_2_boundary_pct",
    "venue_zone_3_boundary_pct",
    "venue_zone_4_boundary_pct",
    "venue_zone_5_boundary_pct",
    "venue_zone_6_boundary_pct",
    "venue_zone_7_boundary_pct",
    "venue_zone_8_boundary_pct",
    "venue_scoring_zone_concentration",
    "team1_zone_fit_score",
    "team2_zone_fit_score",
    # Granular team at venue
    "team1_control_pct_at_venue",
    "team2_control_pct_at_venue",
    "team1_boundary_pct_at_venue",
    "team2_boundary_pct_at_venue",
    "team1_dot_pct_at_venue",
    "team2_dot_pct_at_venue",
    # Precomputed baseline features
    "team1_top3_batter_baseline_sr",
    "team2_top3_batter_baseline_sr",
    "team1_bowling_baseline_economy",
    "team2_bowling_baseline_economy",
    "team1_top3_batter_avg_xpoints",
    "team2_top3_batter_avg_xpoints",
    "team1_key_matchup_edge_score",
    "team2_key_matchup_edge_score",
]

# Fast mode: lightweight features that don't require delivery_details queries.
# Covers venue averages, Elo, recent form, H2H, team phase stats, toss context.
FAST_MODE_FEATURES = [
    # Context
    "competition",
    "venue_cluster_type",
    "venue_total_matches",
    # Venue profile
    "venue_bat_first_win_pct",
    "venue_avg_1st_innings_score",
    "venue_avg_2nd_innings_score",
    "venue_avg_winning_score",
    "venue_avg_chasing_score",
    # Team and form
    "team1_elo",
    "team2_elo",
    "elo_delta",
    "team1_recent_form",
    "team2_recent_form",
    "h2h_team1_wins",
    "h2h_team2_wins",
    # Team phase behavior
    "team1_pp_avg_runs",
    "team1_middle_avg_runs",
    "team1_death_avg_runs",
    "team2_pp_avg_runs",
    "team2_middle_avg_runs",
    "team2_death_avg_runs",
    "team1_pp_avg_wickets_lost",
    "team1_middle_avg_wickets_lost",
    "team1_death_avg_wickets_lost",
    "team2_pp_avg_wickets_lost",
    "team2_middle_avg_wickets_lost",
    "team2_death_avg_wickets_lost",
    # Toss context
    "toss_winner_is_team1",
    "toss_decision_bat",
    "toss_aligns_with_venue_bias",
    # Template alignment
    "team1_bat_first_template_alignment",
    "team1_chase_template_alignment",
    "team2_bat_first_template_alignment",
    "team2_chase_template_alignment",
    # Elo confidence
    "elo_confidence_weight",
]

# Feature extraction methods to skip in fast mode (these hit delivery_details).
FAST_MODE_SKIP_METHODS = {
    "_compute_venue_pace_spin_features",
    "_compute_bowler_style_features",
    "_compute_handedness_combo_features",
    "_compute_line_length_features",
    "_compute_ball_direction_features",
    "_compute_wagon_zone_features",
    "_compute_team_bowling_attack_features",
    "_compute_team_hand_combo_features",
    "_compute_team_venue_granular_features",
    "_compute_wpa_features",
    "_compute_team_context_features",
    "_compute_team_baseline_features",
}

# Elo confidence: if more than this fraction of features are null, lean on Elo.
ELO_CONFIDENCE_THRESHOLD = 0.5

# Promotion gates: model must pass at least this many gates to auto-save.
PROMOTION_GATE_THRESHOLD = 4

PLAYER_FEATURE_COLUMNS = [
    "player_recent_fantasy_avg",
    "player_recent_fantasy_std",
    "player_recent_batting_points_avg",
    "player_recent_bowling_points_avg",
    "player_recent_fielding_points_avg",
    "player_recent_sr",
    "player_recent_runs",
    "player_recent_balls",
    "player_sr_diff_mean",
    "player_sr_diff_std",
    "player_matches_seen",
    "batting_position",
    "entry_overs",
    # Precomputed player baseline
    "player_baseline_avg_runs",
    "player_baseline_avg_sr",
    "player_baseline_avg_balls",
    "player_baseline_boundary_pct",
    "player_baseline_dot_pct",
    # Match context passthrough
    "team_elo",
    "opponent_elo",
    "elo_delta",
    "venue_bat_first_win_pct",
    "venue_avg_1st_innings_score",
    "venue_avg_2nd_innings_score",
    "team_rotation_pct",
    "team_avg_sr_diff",
    "team_avg_economy_diff",
]

MATCH_WINNER_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "reg_lambda": 1.0,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": RANDOM_STATE,
    "n_jobs": 4,
}

SCORE_REGRESSOR_PARAMS = {
    "n_estimators": 400,
    "max_depth": 6,
    "learning_rate": 0.04,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "random_state": RANDOM_STATE,
    "n_jobs": 4,
}

PLAYER_REGRESSOR_PARAMS = {
    "n_estimators": 320,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "random_state": RANDOM_STATE,
    "n_jobs": 4,
}
