"""Feature engineering pipeline for foresight/hindsight ML models.

This module extracts match-level and player-level features using only information
available before each match date (temporal-safe feature construction).
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ml import config


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _row_to_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)


def _normalize_style(style: Optional[str]) -> Optional[str]:
    if not style:
        return None
    return "".join(ch for ch in style.upper() if ch.isalnum())


class FeatureEngineer:
    """Builds feature matrices for match-level and player-level ML models."""

    def __init__(
        self,
        db: Session,
        recency_half_life_days: Optional[float] = None,
        fast_mode: bool = False,
    ):
        self.db = db
        self.fast_mode = fast_mode
        half_life = recency_half_life_days or config.RECENCY_HALF_LIFE_DAYS
        self.decay_lambda = math.log(2) / max(half_life, 1.0)
        self._table_columns_cache: Dict[str, set[str]] = {}
        # Batch caches — populated by _preload_batch_caches() before the match loop.
        self._team_phase_cache: Optional[Dict[tuple, Dict[str, Any]]] = None
        self._player_baseline_cache: Optional[Dict[str, Dict[str, Any]]] = None
        # In-memory delivery_details cache (all competitions for cross-league venue features).
        self._dd_df: Optional[pd.DataFrame] = None
        # Competition filter used during training (for league-specific team features).
        self._league_competitions: Optional[Sequence[str]] = None

    # ---------------------------------------------------------------------
    # Connection resilience
    # ---------------------------------------------------------------------
    def _ping_db(self) -> None:
        """Keep-alive ping to prevent connection from going stale."""
        try:
            self.db.execute(text("SELECT 1"))
        except OperationalError:
            self.db.rollback()
            self.db.execute(text("SELECT 1"))

    def _extract_with_retry(self, match: Dict[str, Any], max_retries: int = 2) -> Dict[str, Any]:
        """Extract features with retry on DB connection errors."""
        for attempt in range(max_retries + 1):
            try:
                return self.extract_match_features(match)
            except OperationalError as e:
                if attempt < max_retries:
                    print(f"[feature_engineering] DB error on match {match.get('id')}, retrying ({attempt + 1}/{max_retries})...")
                    self.db.rollback()
                    time.sleep(2 ** attempt)
                else:
                    print(f"[feature_engineering] DB error on match {match.get('id')} after {max_retries} retries, skipping: {e}")
                    return {}

    # ---------------------------------------------------------------------
    # Table/column capabilities
    # ---------------------------------------------------------------------
    def _table_columns(self, table_name: str) -> set[str]:
        if table_name in self._table_columns_cache:
            return self._table_columns_cache[table_name]

        cols: set[str] = set()
        try:
            rows = self.db.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            ).fetchall()
            cols = {str(r[0]) for r in rows}
        except Exception:
            # Non-Postgres fallback (best effort)
            try:
                rows = self.db.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
                cols = {str(r[1]) for r in rows}
            except Exception:
                cols = set()

        self._table_columns_cache[table_name] = cols
        return cols

    def _has_columns(self, table_name: str, required: Sequence[str]) -> bool:
        cols = self._table_columns(table_name)
        return all(col in cols for col in required)

    # ---------------------------------------------------------------------
    # Batch preloading for SQL optimization
    # ---------------------------------------------------------------------
    def _preload_batch_caches(self, competitions: Optional[Sequence[str]] = None) -> None:
        """Preload team_phase_stats, player_baselines, and delivery_details to avoid per-match queries.

        delivery_details are loaded WITHOUT competition filter so that venue
        features can use cross-league data.  The ``competitions`` argument is
        stored so that team-specific feature methods can filter in-memory via
        ``_dd_before_league()``.
        """
        self._league_competitions = list(competitions) if competitions else None
        self._preload_team_phase_stats()
        self._preload_player_baselines()
        if not self.fast_mode:
            # Load ALL delivery_details (cross-league) for venue features.
            self._preload_delivery_details(competitions=None)

    def _preload_team_phase_stats(self) -> None:
        if not self._table_columns("team_phase_stats"):
            self._team_phase_cache = {}
            return
        rows = self.db.execute(
            text(
                """
                SELECT
                    team, phase, innings, venue_type, venue_identifier,
                    league, avg_runs, avg_wickets, matches_played,
                    data_through_date
                FROM team_phase_stats
                """
            )
        ).fetchall()
        cache: Dict[tuple, list] = defaultdict(list)
        for row in rows:
            rec = _row_to_dict(row)
            key = (rec.get("team"), rec.get("phase"), rec.get("innings"))
            cache[key].append(rec)
        self._team_phase_cache = dict(cache)

    def _preload_delivery_details(self, competitions: Optional[Sequence[str]] = None) -> None:
        """Preload delivery_details into memory for fast in-memory aggregation."""
        if not self._table_columns("delivery_details"):
            self._dd_df = pd.DataFrame()
            return
        where = ""
        params: Dict[str, Any] = {}
        if competitions:
            placeholders = ", ".join(f":comp{i}" for i in range(len(competitions)))
            where = f"WHERE competition IN ({placeholders})"
            params = {f"comp{i}": c for i, c in enumerate(competitions)}
        # Check which column names exist to handle both raw DB and local cache schemas.
        dd_cols = self._table_columns("delivery_details")
        bat_team_expr = "COALESCE(batting_team, team_bat)" if "team_bat" in dd_cols else "batting_team"
        bowl_team_expr = "COALESCE(bowling_team, team_bowl)" if "team_bowl" in dd_cols else "bowling_team"
        batter_expr = "COALESCE(batter, bat)" if "bat" in dd_cols else "batter"
        sql = f"""
            SELECT match_date, ground,
                   {bat_team_expr} AS batting_team,
                   {bowl_team_expr} AS bowling_team,
                   match_id,
                   bowl_kind, bowl_style, bat_hand, crease_combo,
                   wagon_zone, line, length, over, score,
                   noball, wide, byes, legbyes, out, control,
                   competition,
                   {batter_expr} AS batter
            FROM delivery_details
            {where}
        """
        self._dd_df = pd.read_sql(text(sql), self.db.bind, params=params)
        # Pre-compute derived columns used by multiple feature methods.
        # Force numeric types for columns that may come back as TEXT from SQLite.
        for _num_col in ["score", "noball", "wide", "byes", "legbyes", "over", "wagon_zone", "control"]:
            if _num_col in self._dd_df.columns:
                self._dd_df[_num_col] = pd.to_numeric(self._dd_df[_num_col], errors="coerce")

        self._dd_df["ball_runs"] = (
            self._dd_df["score"].fillna(0)
            + self._dd_df["noball"].fillna(0)
            + self._dd_df["wide"].fillna(0)
            + self._dd_df["byes"].fillna(0)
            + self._dd_df["legbyes"].fillna(0)
        )
        self._dd_df["phase"] = pd.cut(
            self._dd_df["over"].fillna(0),
            bins=[-1, 5, 14, 50],
            labels=["pp", "middle", "death"],
        )
        self._dd_df["is_dot"] = (self._dd_df["ball_runs"] == 0).astype(int)
        self._dd_df["is_boundary"] = self._dd_df["score"].fillna(0).isin([4, 6]).astype(int)
        out_col = self._dd_df["out"].astype(str).str.lower().fillna("")
        self._dd_df["is_wicket"] = out_col.isin(["1", "true", "t", "yes", "y"]).astype(int)
        # Normalize bowl_kind into pace/spin/other — values are like "pace bowler", "spin bowler"
        bk = self._dd_df["bowl_kind"].fillna("").str.lower()
        self._dd_df["bowl_group"] = np.where(
            bk.str.contains("pace|medium|fast", regex=True), "pace",
            np.where(bk.str.contains("spin|orthodox|wrist", regex=True), "spin", "other")
        )

        # --- Performance optimization: sort by match_date for fast temporal filtering ---
        # Convert match_date to datetime for fast comparisons and sort.
        self._dd_df["_match_date_dt"] = pd.to_datetime(self._dd_df["match_date"], errors="coerce")
        self._dd_df = self._dd_df.sort_values("_match_date_dt").reset_index(drop=True)

        # Pre-build league-filtered subset for team features.
        if self._league_competitions:
            comp_set = set(self._league_competitions)
            self._dd_league_df: Optional[pd.DataFrame] = self._dd_df[
                self._dd_df["competition"].isin(comp_set)
            ].copy()
            print(f"[feature_engineering] League-filtered DD: {len(self._dd_league_df)} rows")
        else:
            self._dd_league_df = None

        print(f"[feature_engineering] Preloaded {len(self._dd_df)} delivery_details rows into memory")

    def _dd_before(self, match_date: str) -> pd.DataFrame:
        """Return delivery_details rows before the given match date (ALL competitions).

        Uses sorted datetime index with searchsorted for O(log n) cutoff.
        """
        if self._dd_df is None or self._dd_df.empty:
            return pd.DataFrame()
        cutoff = pd.Timestamp(match_date)
        idx = self._dd_df["_match_date_dt"].searchsorted(cutoff, side="left")
        return self._dd_df.iloc[:idx]

    def _dd_before_league(self, match_date: str) -> pd.DataFrame:
        """Return league-filtered delivery_details rows before the given match date.

        Uses pre-built league subset with sorted datetime index for fast cutoff.
        """
        source = self._dd_league_df if self._dd_league_df is not None else self._dd_df
        if source is None or source.empty:
            return self._dd_df.iloc[:0] if self._dd_df is not None else pd.DataFrame()
        cutoff = pd.Timestamp(match_date)
        idx = source["_match_date_dt"].searchsorted(cutoff, side="left")
        return source.iloc[:idx]

    def _preload_player_baselines(self) -> None:
        if not self._table_columns("player_baselines"):
            self._player_baseline_cache = {}
            return
        rows = self.db.execute(
            text(
                """
                SELECT
                    player_name, role, phase, venue_type, venue_identifier,
                    league, avg_runs, avg_strike_rate, avg_balls_faced,
                    boundary_percentage, dot_percentage, avg_economy,
                    matches_played, data_through_date
                FROM player_baselines
                """
            )
        ).fetchall()
        cache: Dict[str, list] = defaultdict(list)
        for row in rows:
            rec = _row_to_dict(row)
            cache[rec.get("player_name", "")].append(rec)
        self._player_baseline_cache = dict(cache)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def list_completed_matches(
        self,
        limit: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        competitions: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        sql = """
            SELECT
                id,
                date,
                venue,
                competition,
                team1,
                team2,
                toss_winner,
                toss_decision,
                winner,
                team1_elo,
                team2_elo
            FROM matches
            WHERE winner IS NOT NULL
              AND date IS NOT NULL
              AND team1 IS NOT NULL
              AND team2 IS NOT NULL
        """
        params: Dict[str, Any] = {}

        if start_date is not None:
            sql += " AND date >= :start_date"
            params["start_date"] = start_date
        if end_date is not None:
            sql += " AND date <= :end_date"
            params["end_date"] = end_date
        if competitions:
            placeholders = ", ".join(f":comp_{i}" for i in range(len(competitions)))
            sql += f" AND competition IN ({placeholders})"
            for i, c in enumerate(competitions):
                params[f"comp_{i}"] = c

        sql += " ORDER BY date ASC, id ASC"
        if limit:
            sql += " LIMIT :limit"
            params["limit"] = limit

        rows = self.db.execute(text(sql), params).fetchall()
        records = [_row_to_dict(r) for r in rows]
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df

    def build_match_training_frame(
        self,
        limit: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        competitions: Optional[Sequence[str]] = None,
        verbose: bool = True,
    ) -> pd.DataFrame:
        matches_df = self.list_completed_matches(
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            competitions=competitions,
        )
        if matches_df.empty:
            return pd.DataFrame()

        # Preload batch caches to reduce per-match SQL queries.
        if verbose:
            print("[feature_engineering] Preloading batch caches...")
        self._preload_batch_caches(competitions=competitions)

        feature_cols = config.FAST_MODE_FEATURES if self.fast_mode else config.MATCH_FEATURE_COLUMNS

        rows: List[Dict[str, Any]] = []
        total = len(matches_df)

        for idx, match in enumerate(matches_df.to_dict(orient="records"), start=1):
            # Periodically ping DB to keep connection alive on long runs.
            if idx % 100 == 1:
                self._ping_db()

            features = self._extract_with_retry(match)
            score_1, score_2 = self._get_match_scores(match["id"])

            row: Dict[str, Any] = {
                "match_id": match["id"],
                "match_date": match["date"],
                "team1": match["team1"],
                "team2": match["team2"],
                "actual_winner": match["winner"],
                "winner_label": 1 if match["winner"] == match["team1"] else 0,
                "score_1st_actual": score_1,
                "score_2nd_actual": score_2,
            }
            row.update(features)

            # Keep stable column availability for downstream training.
            for feature_name in feature_cols:
                row.setdefault(feature_name, None)

            rows.append(row)

            if verbose and idx % 200 == 0:
                print(f"[feature_engineering] processed matches: {idx}/{total}")

        out = pd.DataFrame(rows)
        if out.empty:
            return out

        max_date = pd.to_datetime(out["match_date"]).max().date()
        out["sample_weight"] = out["match_date"].apply(lambda d: self._recency_weight(d, max_date))
        out = out.sort_values(["match_date", "match_id"]).reset_index(drop=True)
        return out

    def build_player_training_frame(self, match_training_frame: pd.DataFrame) -> pd.DataFrame:
        """Build player-level regression frame for fantasy/xPoints learning."""
        if match_training_frame.empty:
            return pd.DataFrame()

        min_date = pd.to_datetime(match_training_frame["match_date"]).min().date()
        max_date = pd.to_datetime(match_training_frame["match_date"]).max().date()
        match_ids = set(match_training_frame["match_id"].astype(str))

        player_rows = self.db.execute(
            text(
                """
                SELECT
                    bs.match_id,
                    m.date AS match_date,
                    m.team1,
                    m.team2,
                    m.competition,
                    bs.striker AS player,
                    bs.batting_team AS team,
                    bs.runs,
                    bs.balls_faced,
                    bs.strike_rate,
                    bs.fantasy_points,
                    bs.batting_points,
                    bs.bowling_points,
                    bs.fielding_points,
                    bs.sr_diff,
                    bs.batting_position,
                    bs.entry_overs
                FROM batting_stats bs
                INNER JOIN matches m ON m.id = bs.match_id
                WHERE m.winner IS NOT NULL
                  AND m.date BETWEEN :min_date AND :max_date
                ORDER BY bs.striker, m.date, bs.match_id
                """
            ),
            {"min_date": min_date, "max_date": max_date},
        ).fetchall()

        if not player_rows:
            return pd.DataFrame()

        player_df = pd.DataFrame([_row_to_dict(r) for r in player_rows])
        player_df = player_df[player_df["match_id"].astype(str).isin(match_ids)].copy()
        if player_df.empty:
            return pd.DataFrame()

        player_df["match_date"] = pd.to_datetime(player_df["match_date"]).dt.date
        player_df = player_df.sort_values(["player", "match_date", "match_id"]).reset_index(drop=True)

        # Rolling player form features (shifted for temporal safety).
        grp = player_df.groupby("player", sort=False)
        player_df["player_matches_seen"] = grp.cumcount()

        rolling_window = 8
        player_df["player_recent_fantasy_avg"] = grp["fantasy_points"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_recent_fantasy_std"] = grp["fantasy_points"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=2).std()
        )
        player_df["player_recent_batting_points_avg"] = grp["batting_points"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_recent_bowling_points_avg"] = grp["bowling_points"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_recent_fielding_points_avg"] = grp["fielding_points"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_recent_sr"] = grp["strike_rate"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_recent_runs"] = grp["runs"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_recent_balls"] = grp["balls_faced"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_sr_diff_mean"] = grp["sr_diff"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=1).mean()
        )
        player_df["player_sr_diff_std"] = grp["sr_diff"].transform(
            lambda s: s.shift(1).rolling(rolling_window, min_periods=2).std()
        )

        # Merge match-level context features.
        context_cols = [
            "match_id",
            "team1",
            "team2",
            "team1_elo",
            "team2_elo",
            "elo_delta",
            "venue_bat_first_win_pct",
            "venue_avg_1st_innings_score",
            "venue_avg_2nd_innings_score",
            "team1_rotation_pct",
            "team2_rotation_pct",
            "team1_avg_sr_diff",
            "team2_avg_sr_diff",
            "team1_avg_economy_diff",
            "team2_avg_economy_diff",
        ]

        available_context_cols = [c for c in context_cols if c in match_training_frame.columns]
        context_df = match_training_frame[available_context_cols].drop_duplicates("match_id")
        player_df = player_df.merge(context_df, on="match_id", how="left")

        player_df["team_elo"] = np.where(
            player_df["team"] == player_df["team1"],
            player_df.get("team1_elo"),
            player_df.get("team2_elo"),
        )
        player_df["opponent_elo"] = np.where(
            player_df["team"] == player_df["team1"],
            player_df.get("team2_elo"),
            player_df.get("team1_elo"),
        )
        player_df["elo_delta"] = player_df["team_elo"] - player_df["opponent_elo"]

        player_df["team_rotation_pct"] = np.where(
            player_df["team"] == player_df["team1"],
            player_df.get("team1_rotation_pct"),
            player_df.get("team2_rotation_pct"),
        )
        player_df["team_avg_sr_diff"] = np.where(
            player_df["team"] == player_df["team1"],
            player_df.get("team1_avg_sr_diff"),
            player_df.get("team2_avg_sr_diff"),
        )
        player_df["team_avg_economy_diff"] = np.where(
            player_df["team"] == player_df["team1"],
            player_df.get("team1_avg_economy_diff"),
            player_df.get("team2_avg_economy_diff"),
        )

        # Global player baselines as lightweight fallback features.
        baseline_df = self._load_global_player_baselines()
        if not baseline_df.empty:
            player_df = player_df.merge(baseline_df, left_on="player", right_on="player_name", how="left")
            player_df = player_df.drop(columns=["player_name"], errors="ignore")

        player_df["target_player_points"] = player_df["fantasy_points"]

        max_player_date = pd.to_datetime(player_df["match_date"]).max().date()
        player_df["sample_weight"] = player_df["match_date"].apply(
            lambda d: self._recency_weight(d, max_player_date)
        )

        for feature_name in config.PLAYER_FEATURE_COLUMNS:
            if feature_name not in player_df.columns:
                player_df[feature_name] = np.nan

        return player_df

    def extract_match_features(self, match_row: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pre-match features for one match record."""
        raw_date = match_row["date"]
        # Convert to string for SQL params — works with both DATE and VARCHAR columns.
        match_date: str = str(raw_date) if not isinstance(raw_date, str) else raw_date
        team1 = match_row["team1"]
        team2 = match_row["team2"]
        venue = match_row.get("venue")
        competition = match_row.get("competition")

        features: Dict[str, Any] = {
            "competition": competition,
            "team1_elo": _safe_float(match_row.get("team1_elo")),
            "team2_elo": _safe_float(match_row.get("team2_elo")),
        }
        features["elo_delta"] = (
            None
            if features["team1_elo"] is None or features["team2_elo"] is None
            else features["team1_elo"] - features["team2_elo"]
        )

        cluster_name, cluster_type = self._get_venue_cluster(venue)
        features["venue_cluster_type"] = cluster_type

        venue_features = self._compute_venue_features(venue, match_date)
        features.update(venue_features)

        team1_phase = self._compute_team_phase_features(
            team=team1,
            match_date=match_date,
            venue=venue,
            competition=competition,
            cluster_name=cluster_name,
        )
        team2_phase = self._compute_team_phase_features(
            team=team2,
            match_date=match_date,
            venue=venue,
            competition=competition,
            cluster_name=cluster_name,
        )
        features.update({f"team1_{k}": v for k, v in team1_phase.items()})
        features.update({f"team2_{k}": v for k, v in team2_phase.items()})

        features.update(
            {
                "team1_recent_form": self._team_recent_form(team1, match_date, n_matches=5),
                "team2_recent_form": self._team_recent_form(team2, match_date, n_matches=5),
            }
        )
        h2h_team1, h2h_team2 = self._h2h_recent(team1, team2, match_date, n_matches=10)
        features["h2h_team1_wins"] = h2h_team1
        features["h2h_team2_wins"] = h2h_team2

        toss_decision_bat = 1 if str(match_row.get("toss_decision", "")).lower().startswith("bat") else 0
        toss_winner_is_team1 = 1 if match_row.get("toss_winner") == team1 else 0

        venue_bat_first_win_pct = _safe_float(features.get("venue_bat_first_win_pct"))
        toss_aligns = None
        if venue_bat_first_win_pct is not None:
            if toss_decision_bat == 1:
                toss_aligns = 1 if venue_bat_first_win_pct >= 0.5 else 0
            else:
                toss_aligns = 1 if venue_bat_first_win_pct < 0.5 else 0

        features["toss_winner_is_team1"] = toss_winner_is_team1
        features["toss_decision_bat"] = toss_decision_bat
        features["toss_aligns_with_venue_bias"] = toss_aligns

        features["team1_bat_first_template_alignment"] = self._template_alignment(
            team_total=self._sum_phase_runs(team1_phase),
            venue_target=_safe_float(features.get("venue_avg_1st_innings_score")),
        )
        features["team1_chase_template_alignment"] = self._template_alignment(
            team_total=self._sum_phase_runs(team1_phase),
            venue_target=_safe_float(features.get("venue_avg_2nd_innings_score")),
        )
        features["team2_bat_first_template_alignment"] = self._template_alignment(
            team_total=self._sum_phase_runs(team2_phase),
            venue_target=_safe_float(features.get("venue_avg_1st_innings_score")),
        )
        features["team2_chase_template_alignment"] = self._template_alignment(
            team_total=self._sum_phase_runs(team2_phase),
            venue_target=_safe_float(features.get("venue_avg_2nd_innings_score")),
        )

        # In fast mode, skip all expensive delivery_details-based features.
        if not self.fast_mode:
            # Venue delivery_details features.
            features.update(self._compute_venue_pace_spin_features(venue, match_date))
            features.update(self._compute_bowler_style_features(competition, match_date))
            features.update(self._compute_handedness_combo_features(venue, match_date))
            features.update(self._compute_line_length_features(venue, match_date))
            features.update(self._compute_ball_direction_features(venue, match_date, team1, team2))
            features.update(self._compute_wagon_zone_features(venue, match_date, team1, team2))

            # Team delivery composition features.
            team1_attack = self._compute_team_bowling_attack_features(team1, match_date)
            team2_attack = self._compute_team_bowling_attack_features(team2, match_date)
            features.update({f"team1_{k}": v for k, v in team1_attack.items()})
            features.update({f"team2_{k}": v for k, v in team2_attack.items()})
            venue_spin_econ = _safe_float(features.get("venue_spin_economy"))
            if venue_spin_econ is not None:
                t1_spin_attack_econ = _safe_float(features.get("team1_spin_attack_economy"))
                t2_spin_attack_econ = _safe_float(features.get("team2_spin_attack_economy"))
                features["team1_spin_attack_vs_venue_delta"] = (
                    None if t1_spin_attack_econ is None else t1_spin_attack_econ - venue_spin_econ
                )
                features["team2_spin_attack_vs_venue_delta"] = (
                    None if t2_spin_attack_econ is None else t2_spin_attack_econ - venue_spin_econ
                )

            team1_hand = self._compute_team_hand_combo_features(team1, match_date)
            team2_hand = self._compute_team_hand_combo_features(team2, match_date)
            features.update({f"team1_{k}": v for k, v in team1_hand.items()})
            features.update({f"team2_{k}": v for k, v in team2_hand.items()})

            team1_venue_context = self._compute_team_venue_granular_features(team1, venue, match_date)
            team2_venue_context = self._compute_team_venue_granular_features(team2, venue, match_date)
            features.update({f"team1_{k}": v for k, v in team1_venue_context.items()})
            features.update({f"team2_{k}": v for k, v in team2_venue_context.items()})

            # WPA-derived features (optional if columns exist).
            features.update(self._compute_wpa_features(venue, match_date, team1, team2))

            # Team context from batting/bowling tables.
            team1_context = self._compute_team_context_features(team1, match_date)
            team2_context = self._compute_team_context_features(team2, match_date)
            features.update({f"team1_{k}": v for k, v in team1_context.items()})
            features.update({f"team2_{k}": v for k, v in team2_context.items()})

            winner_rotation_share = self._venue_winner_rotation_share(venue, match_date)
            features["venue_rotation_vs_boundary_winners"] = winner_rotation_share
            features["team1_scoring_style_venue_fit"] = self._template_alignment(
                team_total=_safe_float(features.get("team1_rotation_pct")),
                venue_target=winner_rotation_share,
            )
            features["team2_scoring_style_venue_fit"] = self._template_alignment(
                team_total=_safe_float(features.get("team2_rotation_pct")),
                venue_target=winner_rotation_share,
            )

            # Player-baseline-assisted team strengths.
            team1_baselines = self._compute_team_baseline_features(
                team=team1,
                venue=venue,
                competition=competition,
                cluster_name=cluster_name,
                match_date=match_date,
            )
            team2_baselines = self._compute_team_baseline_features(
                team=team2,
                venue=venue,
                competition=competition,
                cluster_name=cluster_name,
                match_date=match_date,
            )
            features.update({f"team1_{k}": v for k, v in team1_baselines.items()})
            features.update({f"team2_{k}": v for k, v in team2_baselines.items()})

            team1_sr = _safe_float(features.get("team1_top3_batter_baseline_sr"))
            team2_sr = _safe_float(features.get("team2_top3_batter_baseline_sr"))
            team1_bowl = _safe_float(features.get("team1_bowling_baseline_economy"))
            team2_bowl = _safe_float(features.get("team2_bowling_baseline_economy"))

            features["team1_key_matchup_edge_score"] = _safe_div(team1_sr, team2_bowl)
            features["team2_key_matchup_edge_score"] = _safe_div(team2_sr, team1_bowl)

        # Elo confidence weight: high when many features are null (lean on Elo).
        feature_cols = config.FAST_MODE_FEATURES if self.fast_mode else config.MATCH_FEATURE_COLUMNS
        non_meta_features = [k for k in feature_cols if k not in ("competition", "venue_cluster_type")]
        null_count = sum(1 for k in non_meta_features if features.get(k) is None)
        null_frac = null_count / max(len(non_meta_features), 1)
        features["elo_confidence_weight"] = 1.0 if null_frac > config.ELO_CONFIDENCE_THRESHOLD else null_frac

        return features

    # ---------------------------------------------------------------------
    # Match labels and weights
    # ---------------------------------------------------------------------
    def _get_match_scores(self, match_id: str) -> Tuple[Optional[int], Optional[int]]:
        if self._has_columns("deliveries", ["match_id", "innings", "runs_off_bat", "extras"]):
            rows = self.db.execute(
                text(
                    """
                    SELECT
                        innings,
                        SUM(COALESCE(runs_off_bat, 0) + COALESCE(extras, 0)) AS runs
                    FROM deliveries
                    WHERE match_id = :match_id
                    GROUP BY innings
                    """
                ),
                {"match_id": match_id},
            ).fetchall()
            if rows:
                score_map = {int(r[0]): int(r[1]) for r in rows if r[1] is not None}
                return score_map.get(1), score_map.get(2)

        rows = self.db.execute(
            text(
                """
                SELECT innings, SUM(COALESCE(runs, 0)) AS runs
                FROM batting_stats
                WHERE match_id = :match_id
                GROUP BY innings
                """
            ),
            {"match_id": match_id},
        ).fetchall()
        score_map = {int(r[0]): int(r[1]) for r in rows if r[1] is not None}
        return score_map.get(1), score_map.get(2)

    def _recency_weight(self, sample_date: date, max_date: date) -> float:
        delta_days = max((max_date - sample_date).days, 0)
        return float(math.exp(-self.decay_lambda * delta_days))

    # ---------------------------------------------------------------------
    # Venue/team primitive feature builders
    # ---------------------------------------------------------------------
    def _get_venue_cluster(self, venue: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not venue or not self._table_columns("venue_clusters"):
            return None, None

        row = self.db.execute(
            text(
                """
                SELECT cluster_name, cluster_type
                FROM venue_clusters
                WHERE venue_name = :venue
                ORDER BY priority ASC
                LIMIT 1
                """
            ),
            {"venue": venue},
        ).fetchone()
        if not row:
            return None, None
        row_dict = _row_to_dict(row)
        return row_dict.get("cluster_name"), row_dict.get("cluster_type")

    def _compute_venue_features(self, venue: Optional[str], match_date) -> Dict[str, Any]:
        defaults = {
            "venue_total_matches": None,
            "venue_bat_first_win_pct": None,
            "venue_avg_1st_innings_score": None,
            "venue_avg_2nd_innings_score": None,
            "venue_avg_winning_score": None,
            "venue_avg_chasing_score": None,
        }
        if not venue:
            return defaults

        if self._has_columns(
            "deliveries",
            ["match_id", "innings", "runs_off_bat", "extras", "batting_team"],
        ):
            row = self.db.execute(
                text(
                    """
                    WITH past_matches AS (
                        SELECT id, winner, bat_first
                        FROM matches
                        WHERE venue = :venue
                          AND date < :match_date
                          AND winner IS NOT NULL
                    ),
                    inning_totals AS (
                        SELECT
                            d.match_id,
                            d.innings,
                            MAX(d.batting_team) AS batting_team,
                            SUM(COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS total_runs
                        FROM deliveries d
                        INNER JOIN past_matches pm ON pm.id = d.match_id
                        GROUP BY d.match_id, d.innings
                    )
                    SELECT
                        COUNT(DISTINCT pm.id) AS venue_total_matches,
                        AVG(CASE WHEN pm.winner = pm.bat_first THEN 1.0 ELSE 0.0 END) AS venue_bat_first_win_pct,
                        AVG(CASE WHEN it.innings = 1 THEN it.total_runs END) AS venue_avg_1st_innings_score,
                        AVG(CASE WHEN it.innings = 2 THEN it.total_runs END) AS venue_avg_2nd_innings_score,
                        AVG(CASE WHEN it.batting_team = pm.winner THEN it.total_runs END) AS venue_avg_winning_score,
                        AVG(CASE WHEN it.innings = 2 AND it.batting_team = pm.winner THEN it.total_runs END) AS venue_avg_chasing_score
                    FROM past_matches pm
                    LEFT JOIN inning_totals it ON it.match_id = pm.id
                    """
                ),
                {"venue": venue, "match_date": match_date},
            ).fetchone()
        else:
            row = self.db.execute(
                text(
                    """
                    WITH past_matches AS (
                        SELECT id, winner, bat_first
                        FROM matches
                        WHERE venue = :venue
                          AND date < :match_date
                          AND winner IS NOT NULL
                    ),
                    inning_totals AS (
                        SELECT
                            bs.match_id,
                            bs.innings,
                            MAX(bs.batting_team) AS batting_team,
                            SUM(COALESCE(bs.runs, 0)) AS total_runs
                        FROM batting_stats bs
                        INNER JOIN past_matches pm ON pm.id = bs.match_id
                        GROUP BY bs.match_id, bs.innings
                    )
                    SELECT
                        COUNT(DISTINCT pm.id) AS venue_total_matches,
                        AVG(CASE WHEN pm.winner = pm.bat_first THEN 1.0 ELSE 0.0 END) AS venue_bat_first_win_pct,
                        AVG(CASE WHEN it.innings = 1 THEN it.total_runs END) AS venue_avg_1st_innings_score,
                        AVG(CASE WHEN it.innings = 2 THEN it.total_runs END) AS venue_avg_2nd_innings_score,
                        AVG(CASE WHEN it.batting_team = pm.winner THEN it.total_runs END) AS venue_avg_winning_score,
                        AVG(CASE WHEN it.innings = 2 AND it.batting_team = pm.winner THEN it.total_runs END) AS venue_avg_chasing_score
                    FROM past_matches pm
                    LEFT JOIN inning_totals it ON it.match_id = pm.id
                    """
                ),
                {"venue": venue, "match_date": match_date},
            ).fetchone()

        if not row:
            return defaults

        record = _row_to_dict(row)
        out = defaults.copy()
        out.update({k: _safe_float(v) for k, v in record.items()})
        return out

    def _team_recent_form(self, team: str, match_date: date, n_matches: int) -> Optional[int]:
        rows = self.db.execute(
            text(
                """
                SELECT winner
                FROM matches
                WHERE date < :match_date
                  AND winner IS NOT NULL
                  AND (team1 = :team OR team2 = :team)
                ORDER BY date DESC, id DESC
                LIMIT :n_matches
                """
            ),
            {"team": team, "match_date": match_date, "n_matches": n_matches},
        ).fetchall()
        if not rows:
            return None
        return int(sum(1 for r in rows if r[0] == team))

    def _h2h_recent(self, team1: str, team2: str, match_date: date, n_matches: int) -> Tuple[Optional[int], Optional[int]]:
        rows = self.db.execute(
            text(
                """
                SELECT winner
                FROM matches
                WHERE date < :match_date
                  AND winner IS NOT NULL
                  AND ((team1 = :team1 AND team2 = :team2) OR (team1 = :team2 AND team2 = :team1))
                ORDER BY date DESC, id DESC
                LIMIT :n_matches
                """
            ),
            {
                "team1": team1,
                "team2": team2,
                "match_date": match_date,
                "n_matches": n_matches,
            },
        ).fetchall()
        if not rows:
            return None, None

        t1_wins = int(sum(1 for r in rows if r[0] == team1))
        t2_wins = int(sum(1 for r in rows if r[0] == team2))
        return t1_wins, t2_wins

    def _compute_team_phase_features(
        self,
        team: str,
        match_date: date,
        venue: Optional[str],
        competition: Optional[str],
        cluster_name: Optional[str],
        lookback_matches: int = 30,
    ) -> Dict[str, Any]:
        defaults = {
            "pp_avg_runs": None,
            "middle_avg_runs": None,
            "death_avg_runs": None,
            "pp_avg_wickets_lost": None,
            "middle_avg_wickets_lost": None,
            "death_avg_wickets_lost": None,
        }

        row = self.db.execute(
            text(
                """
                WITH recent_team_matches AS (
                    SELECT id
                    FROM matches
                    WHERE date < :match_date
                      AND (team1 = :team OR team2 = :team)
                    ORDER BY date DESC, id DESC
                    LIMIT :lookback_matches
                ),
                team_phase AS (
                    SELECT
                        bs.match_id,
                        SUM(COALESCE(bs.pp_runs, 0)) AS pp_runs,
                        SUM(COALESCE(bs.middle_runs, 0)) AS middle_runs,
                        SUM(COALESCE(bs.death_runs, 0)) AS death_runs,
                        SUM(COALESCE(bs.pp_wickets, 0)) AS pp_wickets,
                        SUM(COALESCE(bs.middle_wickets, 0)) AS middle_wickets,
                        SUM(COALESCE(bs.death_wickets, 0)) AS death_wickets
                    FROM batting_stats bs
                    INNER JOIN recent_team_matches rtm ON rtm.id = bs.match_id
                    WHERE bs.batting_team = :team
                    GROUP BY bs.match_id
                )
                SELECT
                    AVG(pp_runs) AS pp_avg_runs,
                    AVG(middle_runs) AS middle_avg_runs,
                    AVG(death_runs) AS death_avg_runs,
                    AVG(pp_wickets) AS pp_avg_wickets_lost,
                    AVG(middle_wickets) AS middle_avg_wickets_lost,
                    AVG(death_wickets) AS death_avg_wickets_lost
                FROM team_phase
                """
            ),
            {
                "team": team,
                "match_date": match_date,
                "lookback_matches": lookback_matches,
            },
        ).fetchone()

        record = _row_to_dict(row)
        out = defaults.copy()
        out.update({k: _safe_float(record.get(k)) for k in defaults.keys()})

        if any(v is None for v in out.values()):
            fallback = self._team_phase_fallback_from_precomputed(
                team=team,
                venue=venue,
                competition=competition,
                cluster_name=cluster_name,
                match_date=match_date,
            )
            for key, value in fallback.items():
                if out.get(key) is None:
                    out[key] = value

        return out

    def _team_phase_fallback_from_precomputed(
        self,
        team: str,
        venue: Optional[str],
        competition: Optional[str],
        cluster_name: Optional[str],
        match_date: date,
    ) -> Dict[str, Any]:
        # Use batch cache if available, otherwise fall back to per-query approach.
        if self._team_phase_cache is None:
            if not self._table_columns("team_phase_stats"):
                return {}
            return self._team_phase_fallback_from_precomputed_query(
                team, venue, competition, cluster_name, match_date
            )

        if not self._team_phase_cache:
            return {}

        phase_map = {
            "pp": "powerplay",
            "middle": "middle",
            "death": "death",
        }

        def _venue_priority(rec: Dict[str, Any]) -> int:
            vt = rec.get("venue_type")
            vi = rec.get("venue_identifier")
            lg = rec.get("league")
            if vt == "venue_specific" and vi == venue:
                return 1
            if vt == "cluster" and vi == cluster_name:
                return 2
            if vt == "league" and lg == competition:
                return 3
            if vt == "global":
                return 4
            return 99

        out: Dict[str, Any] = {}
        for short, phase_name in phase_map.items():
            key = (team, phase_name, 1)
            candidates = self._team_phase_cache.get(key, [])
            # Filter by temporal safety and venue relevance.
            valid = []
            for rec in candidates:
                dtd = rec.get("data_through_date")
                if dtd is not None and dtd >= match_date:
                    continue
                prio = _venue_priority(rec)
                if prio > 4:
                    continue
                valid.append((prio, -(rec.get("matches_played") or 0), rec))
            if not valid:
                continue
            valid.sort(key=lambda x: (x[0], x[1]))
            best = valid[0][2]
            out[f"{short}_avg_runs"] = _safe_float(best.get("avg_runs"))
            out[f"{short}_avg_wickets_lost"] = _safe_float(best.get("avg_wickets"))

        return out

    def _team_phase_fallback_from_precomputed_query(
        self,
        team: str,
        venue: Optional[str],
        competition: Optional[str],
        cluster_name: Optional[str],
        match_date: date,
    ) -> Dict[str, Any]:
        """Original per-query fallback (used when batch cache is not loaded)."""
        phase_map = {
            "pp": "powerplay",
            "middle": "middle",
            "death": "death",
        }

        out: Dict[str, Any] = {}
        for short, phase_name in phase_map.items():
            row = self.db.execute(
                text(
                    """
                    SELECT avg_runs, avg_wickets
                    FROM team_phase_stats
                    WHERE team = :team
                      AND phase = :phase_name
                      AND innings = 1
                      AND (
                        data_through_date IS NULL
                        OR data_through_date < :match_date
                      )
                      AND (
                        (venue_type = 'venue_specific' AND venue_identifier = :venue)
                        OR (venue_type = 'cluster' AND venue_identifier = :cluster_name)
                        OR (venue_type = 'league' AND league = :competition)
                        OR (venue_type = 'global')
                      )
                    ORDER BY
                        CASE
                            WHEN venue_type = 'venue_specific' AND venue_identifier = :venue THEN 1
                            WHEN venue_type = 'cluster' AND venue_identifier = :cluster_name THEN 2
                            WHEN venue_type = 'league' AND league = :competition THEN 3
                            ELSE 4
                        END,
                        matches_played DESC
                    LIMIT 1
                    """
                ),
                {
                    "team": team,
                    "phase_name": phase_name,
                    "venue": venue,
                    "cluster_name": cluster_name,
                    "competition": competition,
                    "match_date": match_date,
                },
            ).fetchone()
            if not row:
                continue
            record = _row_to_dict(row)
            out[f"{short}_avg_runs"] = _safe_float(record.get("avg_runs"))
            out[f"{short}_avg_wickets_lost"] = _safe_float(record.get("avg_wickets"))

        return out

    @staticmethod
    def _sum_phase_runs(team_phase: Dict[str, Any]) -> Optional[float]:
        vals = [
            _safe_float(team_phase.get("pp_avg_runs")),
            _safe_float(team_phase.get("middle_avg_runs")),
            _safe_float(team_phase.get("death_avg_runs")),
        ]
        valid = [v for v in vals if v is not None]
        if not valid:
            return None
        return float(sum(valid))

    @staticmethod
    def _template_alignment(team_total: Optional[float], venue_target: Optional[float]) -> Optional[float]:
        if team_total is None or venue_target in (None, 0):
            return None
        return max(0.0, 1.0 - abs(float(team_total) - float(venue_target)) / max(float(venue_target), 1.0))

    # ---------------------------------------------------------------------
    # delivery_details-derived features
    # ---------------------------------------------------------------------
    def _compute_venue_pace_spin_features(self, venue: Optional[str], match_date) -> Dict[str, Any]:
        if not venue:
            return {}

        dd = self._dd_before(match_date)
        dd = dd[dd["ground"] == venue]
        if dd.empty:
            return {}

        grouped: Dict[str, Dict[str, float]] = {
            "pace": defaultdict(float),
            "spin": defaultdict(float),
        }
        phase_econ: Dict[Tuple[str, str], Optional[float]] = {}

        # Aggregate using pandas groupby
        agg = dd.groupby(["bowl_group", "phase"], observed=True).agg(
            balls=("ball_runs", "size"),
            matches=("match_id", "nunique"),
            runs=("ball_runs", "sum"),
            dots=("is_dot", "sum"),
            boundaries=("is_boundary", "sum"),
            wickets=("is_wicket", "sum"),
        ).reset_index()

        for _, rec in agg.iterrows():
            bowl_group = rec["bowl_group"]
            phase = str(rec["phase"])
            if bowl_group not in grouped:
                continue

            balls = float(rec["balls"])
            runs = float(rec["runs"])
            dots = float(rec["dots"])
            boundaries = float(rec["boundaries"])
            wickets = float(rec["wickets"])
            matches = float(rec["matches"])

            grouped[bowl_group]["balls"] += balls
            grouped[bowl_group]["runs"] += runs
            grouped[bowl_group]["dots"] += dots
            grouped[bowl_group]["boundaries"] += boundaries
            grouped[bowl_group]["wickets"] += wickets
            grouped[bowl_group]["matches"] = max(grouped[bowl_group]["matches"], matches)

            phase_econ[(bowl_group, phase)] = _safe_div(runs * 6.0, balls)

        out: Dict[str, Any] = {}
        for kind in ["pace", "spin"]:
            balls = grouped[kind]["balls"]
            runs = grouped[kind]["runs"]
            dots = grouped[kind]["dots"]
            boundaries = grouped[kind]["boundaries"]
            wickets = grouped[kind]["wickets"]
            matches = grouped[kind]["matches"]

            out[f"venue_{kind}_economy"] = _safe_div(runs * 6.0, balls)
            out[f"venue_{kind}_wickets_per_match"] = _safe_div(wickets, matches)
            out[f"venue_{kind}_dot_pct"] = _safe_div(dots, balls)
            out[f"venue_{kind}_boundary_pct"] = _safe_div(boundaries, balls)

        out["venue_pace_spin_economy_ratio"] = _safe_div(
            _safe_float(out.get("venue_pace_economy")),
            _safe_float(out.get("venue_spin_economy")),
        )

        out["venue_pp_pace_economy"] = phase_econ.get(("pace", "pp"))
        out["venue_middle_spin_economy"] = phase_econ.get(("spin", "middle"))
        out["venue_death_pace_economy"] = phase_econ.get(("pace", "death"))
        out["venue_death_spin_economy"] = phase_econ.get(("spin", "death"))

        return out

    def _compute_bowler_style_features(self, competition: Optional[str], match_date) -> Dict[str, Any]:
        if not competition:
            return {}

        dd = self._dd_before_league(match_date)
        dd = dd[(dd["competition"] == competition) & dd["bowl_style"].notna()]
        if dd.empty:
            return {}

        dd_local = dd.copy()
        dd_local["norm_style"] = dd_local["bowl_style"].fillna("").str.upper().apply(_normalize_style)

        agg = dd_local.groupby(["norm_style", "phase"], observed=True).agg(
            balls=("ball_runs", "size"),
            matches=("match_id", "nunique"),
            runs=("ball_runs", "sum"),
            wickets=("is_wicket", "sum"),
        ).reset_index()

        accum: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        phase_accum: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for _, rec in agg.iterrows():
            style = rec["norm_style"]
            phase = str(rec["phase"])
            if not style or style not in config.BOWL_STYLE_FEATURES:
                continue

            balls = float(rec["balls"])
            runs = float(rec["runs"])
            wickets = float(rec["wickets"])
            matches = float(rec["matches"])

            accum[style]["balls"] += balls
            accum[style]["runs"] += runs
            accum[style]["wickets"] += wickets
            accum[style]["matches"] = max(accum[style]["matches"], matches)

            phase_accum[(style, phase)]["balls"] += balls
            phase_accum[(style, phase)]["runs"] += runs

        out: Dict[str, Any] = {}
        for style in config.BOWL_STYLE_FEATURES:
            balls = accum[style].get("balls", 0)
            runs = accum[style].get("runs", 0)
            wickets = accum[style].get("wickets", 0)
            matches = accum[style].get("matches", 0)

            out[f"venue_{style}_economy"] = _safe_div(runs * 6.0, balls)
            out[f"venue_{style}_wickets_per_match"] = _safe_div(wickets, matches)

            pp = phase_accum.get((style, "pp"), {})
            death = phase_accum.get((style, "death"), {})
            out[f"venue_pp_{style}_economy"] = _safe_div(pp.get("runs", 0) * 6.0, pp.get("balls", 0))
            out[f"venue_death_{style}_economy"] = _safe_div(death.get("runs", 0) * 6.0, death.get("balls", 0))

        return out

    def _compute_handedness_combo_features(self, venue: Optional[str], match_date) -> Dict[str, Any]:
        if not venue:
            return {}

        dd = self._dd_before(match_date)
        dd = dd[dd["ground"] == venue]
        if dd.empty:
            return {}

        # Derive hand and combo columns
        bh = dd["bat_hand"].fillna("").str.upper()
        hand = np.where(bh.str.contains("L"), "LHB", np.where(bh.str.contains("R"), "RHB", "UNK"))
        combo = dd["crease_combo"].fillna("UNK").str.upper()
        runs_bat = dd["score"].fillna(0)
        boundary = dd["is_boundary"]

        # Build aggregation in one pass using a temp frame
        tmp = pd.DataFrame({
            "hand": hand, "bowl_group": dd["bowl_group"].values,
            "phase": dd["phase"].values, "combo": combo.values,
            "runs": runs_bat.values, "boundary": boundary.values,
        })

        hand_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        hand_bowl: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        combo_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        combo_phase_spin: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        agg = tmp.groupby(["hand", "bowl_group", "phase", "combo"], observed=True).agg(
            balls=("runs", "size"), runs=("runs", "sum"), boundaries=("boundary", "sum")
        ).reset_index()

        for _, rec in agg.iterrows():
            h = str(rec["hand"])
            bg = str(rec["bowl_group"])
            ph = str(rec["phase"])
            cmb = str(rec["combo"])
            balls = float(rec["balls"])
            runs = float(rec["runs"])
            boundaries = float(rec["boundaries"])

            hand_totals[h]["balls"] += balls
            hand_totals[h]["runs"] += runs
            hand_totals[h]["boundaries"] += boundaries

            hand_bowl[(h, bg)]["balls"] += balls
            hand_bowl[(h, bg)]["runs"] += runs

            combo_totals[cmb]["balls"] += balls
            combo_totals[cmb]["runs"] += runs

            if bg == "spin":
                combo_phase_spin[(ph, cmb)]["balls"] += balls
                combo_phase_spin[(ph, cmb)]["runs"] += runs

        out = {
            "venue_lhb_sr": _safe_div(hand_totals["LHB"].get("runs"), hand_totals["LHB"].get("balls")),
            "venue_rhb_sr": _safe_div(hand_totals["RHB"].get("runs"), hand_totals["RHB"].get("balls")),
            "venue_lhb_boundary_pct": _safe_div(hand_totals["LHB"].get("boundaries"), hand_totals["LHB"].get("balls")),
            "venue_rhb_boundary_pct": _safe_div(hand_totals["RHB"].get("boundaries"), hand_totals["RHB"].get("balls")),
            "venue_lhb_vs_spin_sr": _safe_div(hand_bowl[("LHB", "spin")].get("runs"), hand_bowl[("LHB", "spin")].get("balls")),
            "venue_rhb_vs_spin_sr": _safe_div(hand_bowl[("RHB", "spin")].get("runs"), hand_bowl[("RHB", "spin")].get("balls")),
            "venue_lhb_vs_pace_sr": _safe_div(hand_bowl[("LHB", "pace")].get("runs"), hand_bowl[("LHB", "pace")].get("balls")),
            "venue_rhb_vs_pace_sr": _safe_div(hand_bowl[("RHB", "pace")].get("runs"), hand_bowl[("RHB", "pace")].get("balls")),
            "venue_RHB_RHB_sr": _safe_div(combo_totals["RHB_RHB"].get("runs"), combo_totals["RHB_RHB"].get("balls")),
            "venue_RHB_LHB_sr": _safe_div(combo_totals["RHB_LHB"].get("runs"), combo_totals["RHB_LHB"].get("balls")),
            "venue_LHB_RHB_sr": _safe_div(combo_totals["LHB_RHB"].get("runs"), combo_totals["LHB_RHB"].get("balls")),
            "venue_LHB_LHB_sr": _safe_div(combo_totals["LHB_LHB"].get("runs"), combo_totals["LHB_LHB"].get("balls")),
            "venue_middle_RHB_LHB_vs_spin_sr": _safe_div(
                combo_phase_spin[("middle", "RHB_LHB")].get("runs"),
                combo_phase_spin[("middle", "RHB_LHB")].get("balls"),
            ),
            "venue_middle_LHB_RHB_vs_spin_sr": _safe_div(
                combo_phase_spin[("middle", "LHB_RHB")].get("runs"),
                combo_phase_spin[("middle", "LHB_RHB")].get("balls"),
            ),
        }

        for sr_key in [
            "venue_lhb_sr",
            "venue_rhb_sr",
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
        ]:
            if out[sr_key] is not None:
                out[sr_key] = out[sr_key] * 100.0

        return out

    def _compute_line_length_features(self, venue: Optional[str], match_date) -> Dict[str, Any]:
        if not venue:
            return {}

        dd = self._dd_before(match_date)
        dd = dd[dd["ground"] == venue]
        if dd.empty:
            return {}

        length_key = dd["length"].fillna("").str.lower()
        tmp = pd.DataFrame({
            "length_key": length_key.values, "bowl_group": dd["bowl_group"].values,
            "ball_runs": dd["ball_runs"].values, "is_dot": dd["is_dot"].values,
            "is_boundary": dd["is_boundary"].values,
        })

        agg = tmp.groupby(["length_key", "bowl_group"]).agg(
            balls=("ball_runs", "size"), runs=("ball_runs", "sum"),
            dots=("is_dot", "sum"), boundaries=("is_boundary", "sum"),
        ).reset_index()

        total_runs = 0.0
        by_length: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        by_length_bowl: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for _, rec in agg.iterrows():
            lk = str(rec["length_key"])
            bg = str(rec["bowl_group"])
            balls = float(rec["balls"])
            runs = float(rec["runs"])
            dots = float(rec["dots"])
            boundaries = float(rec["boundaries"])

            total_runs += runs
            by_length[lk]["balls"] += balls
            by_length[lk]["runs"] += runs
            by_length[lk]["dots"] += dots
            by_length[lk]["boundaries"] += boundaries

            by_length_bowl[(lk, bg)]["balls"] += balls
            by_length_bowl[(lk, bg)]["runs"] += runs

        good_runs = sum(v["runs"] for k, v in by_length.items() if "good" in k)
        short = defaultdict(float)
        yorker = defaultdict(float)
        full = defaultdict(float)
        for key, values in by_length.items():
            if "short" in key:
                short["balls"] += values.get("balls", 0)
                short["boundaries"] += values.get("boundaries", 0)
            if "york" in key:
                yorker["balls"] += values.get("balls", 0)
                yorker["dots"] += values.get("dots", 0)
            if "full" in key:
                full["balls"] += values.get("balls", 0)
                full["runs"] += values.get("runs", 0)

        dominant_runs = max((v["runs"] for v in by_length.values()), default=None)

        spin_good = defaultdict(float)
        pace_good = defaultdict(float)
        for (length_key, bowl_group), values in by_length_bowl.items():
            if "good" not in length_key:
                continue
            if bowl_group == "spin":
                spin_good["balls"] += values.get("balls", 0)
                spin_good["runs"] += values.get("runs", 0)
            elif bowl_group == "pace":
                pace_good["balls"] += values.get("balls", 0)
                pace_good["runs"] += values.get("runs", 0)

        return {
            "venue_good_length_runs_pct": _safe_div(good_runs, total_runs),
            "venue_short_boundary_pct": _safe_div(short.get("boundaries"), short.get("balls")),
            "venue_yorker_dot_pct": _safe_div(yorker.get("dots"), yorker.get("balls")),
            "venue_full_scoring_rate": _safe_div(full.get("runs"), full.get("balls")),
            "venue_dominant_length_runs_share": _safe_div(dominant_runs, total_runs),
            "venue_spin_good_length_economy": _safe_div(spin_good.get("runs", 0) * 6.0, spin_good.get("balls", 0)),
            "venue_pace_good_length_economy": _safe_div(pace_good.get("runs", 0) * 6.0, pace_good.get("balls", 0)),
        }

    def _compute_ball_direction_features(
        self,
        venue: Optional[str],
        match_date,
        team1: str,
        team2: str,
    ) -> Dict[str, Any]:
        # ball_direction column does not exist in delivery_details — always empty.
        return {}

    def _compute_wagon_zone_features(
        self,
        venue: Optional[str],
        match_date,
        team1: str,
        team2: str,
    ) -> Dict[str, Any]:
        if not venue:
            return {}

        dd = self._dd_before(match_date)
        dd = dd[(dd["ground"] == venue) & dd["wagon_zone"].between(0, 8)]
        if dd.empty:
            return {}

        # Aggregate venue-level and team-level from the in-memory DataFrame.
        zone_map: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        team_zone_runs: Dict[str, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        total_runs = 0.0

        agg = dd.groupby(["wagon_zone", "batting_team"]).agg(
            balls=("score", "size"),
            runs=("score", lambda x: x.fillna(0).sum()),
            boundaries=("is_boundary", "sum"),
        ).reset_index()

        for _, rec in agg.iterrows():
            zone = int(rec["wagon_zone"])
            team = rec["batting_team"]
            balls = float(rec["balls"])
            runs = float(rec["runs"])
            boundaries = float(rec["boundaries"])
            zone_map[zone]["balls"] += balls
            zone_map[zone]["runs"] += runs
            zone_map[zone]["boundaries"] += boundaries
            total_runs += runs
            team_zone_runs[team][zone] += runs

        out: Dict[str, Any] = {}
        boundary_share_vector: Dict[int, float] = {}
        for zone in range(9):
            boundary_pct = _safe_div(zone_map[zone].get("boundaries"), zone_map[zone].get("balls"))
            out[f"venue_zone_{zone}_boundary_pct"] = boundary_pct
            boundary_share_vector[zone] = boundary_pct or 0.0

        # Normalize boundary profile for overlap scoring.
        boundary_norm = sum(boundary_share_vector.values())
        if boundary_norm > 0:
            for zone in range(9):
                boundary_share_vector[zone] /= boundary_norm

        zone_shares = [(_safe_div(zone_map[z].get("runs"), total_runs) or 0.0) for z in range(9)]
        out["venue_scoring_zone_concentration"] = float(sum(s * s for s in zone_shares)) if total_runs > 0 else None

        def team_zone_fit(team: str) -> Optional[float]:
            runs_by_zone = team_zone_runs.get(team, {})
            if not runs_by_zone:
                return None
            total = sum(runs_by_zone.values())
            if total <= 0:
                return None
            team_share = {z: runs_by_zone.get(z, 0.0) / total for z in range(9)}
            return float(sum(team_share[z] * boundary_share_vector[z] for z in range(9)))

        out["team1_zone_fit_score"] = team_zone_fit(team1)
        out["team2_zone_fit_score"] = team_zone_fit(team2)
        return out

    def _compute_team_bowling_attack_features(self, team: str, match_date) -> Dict[str, Any]:
        dd = self._dd_before_league(match_date)
        dd = dd[dd["bowling_team"] == team]
        if dd.empty:
            return {
                "pace_overs_pct": None,
                "spin_overs_pct": None,
                "spin_attack_economy": None,
                "pace_attack_economy": None,
                "spin_attack_vs_venue_delta": None,
            }

        agg = dd.groupby("bowl_group").agg(
            balls=("ball_runs", "size"), runs=("ball_runs", "sum"),
        ).reset_index()

        accum = defaultdict(lambda: defaultdict(float))
        total_balls = 0.0
        for _, rec in agg.iterrows():
            group = str(rec["bowl_group"])
            balls = float(rec["balls"])
            runs = float(rec["runs"])
            accum[group]["balls"] += balls
            accum[group]["runs"] += runs
            total_balls += balls

        return {
            "pace_overs_pct": _safe_div(accum["pace"].get("balls"), total_balls),
            "spin_overs_pct": _safe_div(accum["spin"].get("balls"), total_balls),
            "spin_attack_economy": _safe_div(accum["spin"].get("runs", 0) * 6.0, accum["spin"].get("balls", 0)),
            "pace_attack_economy": _safe_div(accum["pace"].get("runs", 0) * 6.0, accum["pace"].get("balls", 0)),
            # populated later when venue spin economy is available
            "spin_attack_vs_venue_delta": None,
        }

    def _compute_team_hand_combo_features(self, team: str, match_date) -> Dict[str, Any]:
        dd = self._dd_before_league(match_date)
        dd = dd[dd["batting_team"] == team]
        if dd.empty:
            return {
                "lhb_count": None,
                "rhb_count": None,
                "crease_combo_diversity": None,
            }

        # Hand classification
        bh = dd["bat_hand"].fillna("").str.upper()
        dd_local = dd.copy()
        dd_local["hand"] = np.where(bh.str.contains("L"), "LHB", np.where(bh.str.contains("R"), "RHB", "UNK"))

        # Count distinct batters per hand
        hand_agg = dd_local[dd_local["batter"].notna()].groupby("hand")["batter"].nunique().to_dict()
        lhb_count = float(hand_agg.get("LHB", 0))
        rhb_count = float(hand_agg.get("RHB", 0))

        # Crease combo diversity
        cc = dd[dd["crease_combo"].notna()]["crease_combo"].str.upper()
        combo_counts = cc.value_counts()
        total_combo_balls = float(combo_counts.sum())
        diversity = None
        if total_combo_balls > 0 and len(combo_counts) > 1:
            probs = (combo_counts / total_combo_balls).values
            entropy = -sum(p * math.log(p + 1e-12) for p in probs)
            max_entropy = math.log(len(combo_counts))
            diversity = entropy / max(max_entropy, 1e-9)

        return {
            "lhb_count": lhb_count if lhb_count > 0 else None,
            "rhb_count": rhb_count if rhb_count > 0 else None,
            "crease_combo_diversity": diversity,
        }

    def _compute_team_venue_granular_features(
        self,
        team: str,
        venue: Optional[str],
        match_date,
    ) -> Dict[str, Any]:
        if not venue:
            return {
                "control_pct_at_venue": None,
                "boundary_pct_at_venue": None,
                "dot_pct_at_venue": None,
            }

        dd = self._dd_before(match_date)
        dd = dd[(dd["batting_team"] == team) & (dd["ground"] == venue)]
        if dd.empty:
            return {
                "control_pct_at_venue": None,
                "boundary_pct_at_venue": None,
                "dot_pct_at_venue": None,
            }

        control_vals = pd.to_numeric(dd["control"], errors="coerce")
        control_pct = _safe_float(control_vals.mean()) if control_vals.notna().any() else None
        boundary_pct = _safe_float(dd["is_boundary"].mean())
        dot_pct = _safe_float(dd["is_dot"].mean())

        return {
            "control_pct_at_venue": control_pct,
            "boundary_pct_at_venue": boundary_pct,
            "dot_pct_at_venue": dot_pct,
        }

    # ---------------------------------------------------------------------
    # WPA + context/baseline features
    # ---------------------------------------------------------------------
    def _compute_wpa_features(
        self,
        venue: Optional[str],
        match_date: date,
        team1: str,
        team2: str,
    ) -> Dict[str, Any]:
        if not venue or not self._has_columns("deliveries", ["wpa_batter", "wpa_bowler", "match_id", "batting_team", "bowling_team"]):
            return {
                "venue_avg_wpa_per_delivery": None,
                "team1_avg_wpa_batting": None,
                "team2_avg_wpa_batting": None,
                "team1_avg_wpa_bowling": None,
                "team2_avg_wpa_bowling": None,
            }

        venue_row = self.db.execute(
            text(
                """
                SELECT AVG(ABS(COALESCE(d.wpa_batter, 0)) + ABS(COALESCE(d.wpa_bowler, 0))) AS venue_avg_wpa_per_delivery
                FROM deliveries d
                INNER JOIN matches m ON m.id = d.match_id
                WHERE m.venue = :venue
                  AND m.date < :match_date
                """
            ),
            {"venue": venue, "match_date": match_date},
        ).fetchone()

        team_wpa_bat_rows = self.db.execute(
            text(
                """
                SELECT
                    d.batting_team AS team,
                    AVG(COALESCE(d.wpa_batter, 0)) AS avg_wpa_batter
                FROM deliveries d
                INNER JOIN matches m ON m.id = d.match_id
                WHERE m.date < :match_date
                  AND (d.batting_team = :team1 OR d.batting_team = :team2)
                GROUP BY d.batting_team
                """
            ),
            {"team1": team1, "team2": team2, "match_date": match_date},
        ).fetchall()
        team_wpa_bowl_rows = self.db.execute(
            text(
                """
                SELECT
                    d.bowling_team AS team,
                    AVG(COALESCE(d.wpa_bowler, 0)) AS avg_wpa_bowler
                FROM deliveries d
                INNER JOIN matches m ON m.id = d.match_id
                WHERE m.date < :match_date
                  AND (d.bowling_team = :team1 OR d.bowling_team = :team2)
                GROUP BY d.bowling_team
                """
            ),
            {"team1": team1, "team2": team2, "match_date": match_date},
        ).fetchall()

        team_wpa_batting = {team1: None, team2: None}
        team_wpa_bowling = {team1: None, team2: None}
        for row in team_wpa_bat_rows:
            rec = _row_to_dict(row)
            team = rec.get("team")
            if team in team_wpa_batting:
                team_wpa_batting[team] = _safe_float(rec.get("avg_wpa_batter"))
        for row in team_wpa_bowl_rows:
            rec = _row_to_dict(row)
            team = rec.get("team")
            if team in team_wpa_bowling:
                team_wpa_bowling[team] = _safe_float(rec.get("avg_wpa_bowler"))

        return {
            "venue_avg_wpa_per_delivery": _safe_float(_row_to_dict(venue_row).get("venue_avg_wpa_per_delivery")),
            "team1_avg_wpa_batting": team_wpa_batting[team1],
            "team2_avg_wpa_batting": team_wpa_batting[team2],
            "team1_avg_wpa_bowling": team_wpa_bowling[team1],
            "team2_avg_wpa_bowling": team_wpa_bowling[team2],
        }

    def _compute_team_context_features(self, team: str, match_date: date, lookback_matches: int = 40) -> Dict[str, Any]:
        batting_row = self.db.execute(
            text(
                """
                WITH recent_matches AS (
                    SELECT id
                    FROM matches
                    WHERE date < :match_date
                      AND (team1 = :team OR team2 = :team)
                    ORDER BY date DESC, id DESC
                    LIMIT :lookback_matches
                )
                SELECT
                    AVG(CASE WHEN bs.batting_position <= 3 THEN bs.entry_overs END) AS avg_entry_overs_top3,
                    SUM(
                        CASE
                            WHEN bs.batting_position BETWEEN 1 AND 11 AND bs.strike_rate IS NOT NULL
                            THEN bs.strike_rate * (12 - bs.batting_position)
                            ELSE 0
                        END
                    )
                    / NULLIF(
                        SUM(
                            CASE
                                WHEN bs.batting_position BETWEEN 1 AND 11 AND bs.strike_rate IS NOT NULL
                                THEN (12 - bs.batting_position)
                                ELSE 0
                            END
                        ),
                        0
                    ) AS avg_batting_position_weighted_sr,
                    AVG(bs.sr_diff) AS avg_sr_diff,
                    NULL AS player_sr_diff_consistency,
                    SUM(COALESCE(bs.ones, 0) + 2 * COALESCE(bs.twos, 0) + 3 * COALESCE(bs.threes, 0))
                    / NULLIF(SUM(COALESCE(bs.runs, 0)), 0) AS rotation_pct,
                    AVG(CASE WHEN bs.batting_position <= 3 THEN bs.fantasy_points END) AS top3_avg_xpoints
                FROM batting_stats bs
                INNER JOIN recent_matches rm ON rm.id = bs.match_id
                WHERE bs.batting_team = :team
                """
            ),
            {"team": team, "match_date": match_date, "lookback_matches": lookback_matches},
        ).fetchone()

        bowling_row = self.db.execute(
            text(
                """
                WITH recent_matches AS (
                    SELECT id
                    FROM matches
                    WHERE date < :match_date
                      AND (team1 = :team OR team2 = :team)
                    ORDER BY date DESC, id DESC
                    LIMIT :lookback_matches
                )
                SELECT AVG(bw.economy_diff) AS avg_economy_diff
                FROM bowling_stats bw
                INNER JOIN recent_matches rm ON rm.id = bw.match_id
                WHERE bw.bowling_team = :team
                """
            ),
            {"team": team, "match_date": match_date, "lookback_matches": lookback_matches},
        ).fetchone()

        batting = _row_to_dict(batting_row)
        bowling = _row_to_dict(bowling_row)

        return {
            "avg_entry_overs_top3": _safe_float(batting.get("avg_entry_overs_top3")),
            "avg_batting_position_weighted_sr": _safe_float(batting.get("avg_batting_position_weighted_sr")),
            "avg_sr_diff": _safe_float(batting.get("avg_sr_diff")),
            "player_sr_diff_consistency": _safe_float(batting.get("player_sr_diff_consistency")),
            "rotation_pct": _safe_float(batting.get("rotation_pct")),
            "top3_batter_avg_xpoints": _safe_float(batting.get("top3_avg_xpoints")),
            "avg_economy_diff": _safe_float(bowling.get("avg_economy_diff")),
        }

    def _venue_winner_rotation_share(self, venue: Optional[str], match_date: date) -> Optional[float]:
        if not venue:
            return None

        row = self.db.execute(
            text(
                """
                WITH winner_batting AS (
                    SELECT
                        bs.match_id,
                        SUM(COALESCE(bs.ones, 0) + 2 * COALESCE(bs.twos, 0) + 3 * COALESCE(bs.threes, 0)) AS rotation_runs,
                        SUM(4 * COALESCE(bs.fours, 0) + 6 * COALESCE(bs.sixes, 0)) AS boundary_runs
                    FROM batting_stats bs
                    INNER JOIN matches m ON m.id = bs.match_id
                    WHERE m.venue = :venue
                      AND m.date < :match_date
                      AND bs.batting_team = m.winner
                    GROUP BY bs.match_id
                )
                SELECT AVG(rotation_runs / NULLIF(rotation_runs + boundary_runs, 0)) AS rotation_share
                FROM winner_batting
                """
            ),
            {"venue": venue, "match_date": match_date},
        ).fetchone()

        return _safe_float(_row_to_dict(row).get("rotation_share"))

    def _compute_team_baseline_features(
        self,
        team: str,
        venue: Optional[str],
        competition: Optional[str],
        cluster_name: Optional[str],
        match_date: date,
    ) -> Dict[str, Any]:
        if not self._table_columns("player_baselines"):
            return {
                "top3_batter_baseline_sr": None,
                "bowling_baseline_economy": None,
            }

        top3_batters = self._team_top_players(team, match_date, role="batting", limit=3)
        bowlers = self._team_top_players(team, match_date, role="bowling", limit=6)

        batter_srs: List[float] = []
        bowling_econs: List[float] = []

        for player in top3_batters:
            baseline = self._lookup_player_baseline(
                player=player,
                role="batting",
                venue=venue,
                competition=competition,
                cluster_name=cluster_name,
                match_date=match_date,
            )
            sr = _safe_float(baseline.get("avg_strike_rate"))
            if sr is not None:
                batter_srs.append(sr)

        for player in bowlers:
            baseline = self._lookup_player_baseline(
                player=player,
                role="bowling",
                venue=venue,
                competition=competition,
                cluster_name=cluster_name,
                match_date=match_date,
            )
            econ = _safe_float(baseline.get("avg_economy"))
            if econ is not None:
                bowling_econs.append(econ)

        return {
            "top3_batter_baseline_sr": float(np.mean(batter_srs)) if batter_srs else None,
            "bowling_baseline_economy": float(np.mean(bowling_econs)) if bowling_econs else None,
        }

    def _team_top_players(self, team: str, match_date: date, role: str, limit: int) -> List[str]:
        if role == "batting":
            rows = self.db.execute(
                text(
                    """
                    SELECT bs.striker AS player, COUNT(*) AS appearances
                    FROM batting_stats bs
                    INNER JOIN matches m ON m.id = bs.match_id
                    WHERE m.date < :match_date
                      AND bs.batting_team = :team
                      AND bs.batting_position <= 6
                    GROUP BY bs.striker
                    ORDER BY appearances DESC
                    LIMIT :limit
                    """
                ),
                {"team": team, "match_date": match_date, "limit": limit},
            ).fetchall()
        else:
            rows = self.db.execute(
                text(
                    """
                    SELECT bw.bowler AS player, COUNT(*) AS appearances
                    FROM bowling_stats bw
                    INNER JOIN matches m ON m.id = bw.match_id
                    WHERE m.date < :match_date
                      AND bw.bowling_team = :team
                    GROUP BY bw.bowler
                    ORDER BY appearances DESC
                    LIMIT :limit
                    """
                ),
                {"team": team, "match_date": match_date, "limit": limit},
            ).fetchall()

        return [str(r[0]) for r in rows if r[0]]

    def _lookup_player_baseline(
        self,
        player: str,
        role: str,
        venue: Optional[str],
        competition: Optional[str],
        cluster_name: Optional[str],
        match_date: date,
    ) -> Dict[str, Any]:
        # Use batch cache if available.
        if self._player_baseline_cache is not None:
            return self._lookup_player_baseline_from_cache(
                player, role, venue, competition, cluster_name, match_date
            )

        row = self.db.execute(
            text(
                """
                SELECT
                    avg_runs,
                    avg_strike_rate,
                    avg_balls_faced,
                    boundary_percentage,
                    dot_percentage,
                    avg_economy
                FROM player_baselines
                WHERE player_name = :player
                  AND role = :role
                  AND phase = 'overall'
                  AND (data_through_date IS NULL OR data_through_date < :match_date)
                  AND (
                    (venue_type = 'venue_specific' AND venue_identifier = :venue)
                    OR (venue_type = 'cluster' AND venue_identifier = :cluster_name)
                    OR (venue_type = 'league' AND league = :competition)
                    OR (venue_type = 'global')
                  )
                ORDER BY
                    CASE
                        WHEN venue_type = 'venue_specific' AND venue_identifier = :venue THEN 1
                        WHEN venue_type = 'cluster' AND venue_identifier = :cluster_name THEN 2
                        WHEN venue_type = 'league' AND league = :competition THEN 3
                        ELSE 4
                    END,
                    matches_played DESC
                LIMIT 1
                """
            ),
            {
                "player": player,
                "role": role,
                "venue": venue,
                "cluster_name": cluster_name,
                "competition": competition,
                "match_date": match_date,
            },
        ).fetchone()
        return _row_to_dict(row)

    def _lookup_player_baseline_from_cache(
        self,
        player: str,
        role: str,
        venue: Optional[str],
        competition: Optional[str],
        cluster_name: Optional[str],
        match_date: date,
    ) -> Dict[str, Any]:
        candidates = self._player_baseline_cache.get(player, [])
        if not candidates:
            return {}

        def _venue_priority(rec: Dict[str, Any]) -> int:
            vt = rec.get("venue_type")
            vi = rec.get("venue_identifier")
            lg = rec.get("league")
            if vt == "venue_specific" and vi == venue:
                return 1
            if vt == "cluster" and vi == cluster_name:
                return 2
            if vt == "league" and lg == competition:
                return 3
            if vt == "global":
                return 4
            return 99

        valid = []
        for rec in candidates:
            if rec.get("role") != role or rec.get("phase") != "overall":
                continue
            dtd = rec.get("data_through_date")
            if dtd is not None and dtd >= match_date:
                continue
            prio = _venue_priority(rec)
            if prio > 4:
                continue
            valid.append((prio, -(rec.get("matches_played") or 0), rec))

        if not valid:
            return {}
        valid.sort(key=lambda x: (x[0], x[1]))
        return valid[0][2]

    def _load_global_player_baselines(self) -> pd.DataFrame:
        if not self._table_columns("player_baselines"):
            return pd.DataFrame()

        rows = self.db.execute(
            text(
                """
                SELECT DISTINCT ON (player_name)
                    player_name,
                    avg_runs AS player_baseline_avg_runs,
                    avg_strike_rate AS player_baseline_avg_sr,
                    avg_balls_faced AS player_baseline_avg_balls,
                    boundary_percentage AS player_baseline_boundary_pct,
                    dot_percentage AS player_baseline_dot_pct
                FROM player_baselines
                WHERE role = 'batting'
                  AND phase = 'overall'
                  AND venue_type = 'global'
                ORDER BY player_name, data_through_date DESC NULLS LAST
                """
            )
        ).fetchall()

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([_row_to_dict(r) for r in rows])


__all__ = ["FeatureEngineer"]
