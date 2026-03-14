"""
Global T20 rankings engine for batting and bowling across competitions.

Implements:
- Length-bucket normalization
- Leave-one-out baselines for intent/reliability style metrics
- Variation penalty across length buckets
- Cross-league competition weights (MixedLM with fallback)
- Logistic squashing to 0-100
- In-memory TTL caches for rankings, weights, and trajectories
"""

from __future__ import annotations

import calendar
import copy
import logging
import math
import time
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.player_aliases import get_player_names

try:
    import pandas as pd
    import statsmodels.formula.api as smf

    HAS_STATSMODELS = True
except Exception:  # pragma: no cover - fallback path
    pd = None
    smf = None
    HAS_STATSMODELS = False


logger = logging.getLogger(__name__)


VARIATION_ALPHA = 0.5

# Cell-level filters
MIN_CELL_BALLS = 10

# Final qualification gates
MIN_BALLS_PER_LENGTH_BATTING = 50
MIN_BALLS_PER_LENGTH_BOWLING = 50

LENGTH_BUCKETS_ALL = ("FULL", "GOOD_LENGTH", "SHORT_OF_GOOD", "SHORT")
LENGTH_BUCKETS_SPIN_BOWLING = ("FULL", "GOOD_LENGTH", "SHORT_OF_GOOD")

# Cache TTLs
RANKINGS_CACHE_TTL_SECONDS = 60 * 60      # 1 hour
COMP_WEIGHTS_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
TRAJECTORY_CACHE_TTL_SECONDS = 6 * 60 * 60     # 6 hours
DELIVERY_SCHEMA_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


DEFAULT_COMPETITION_WEIGHTS: Dict[str, float] = {
    "Indian Premier League": 1.21,
    "International Twenty20": 1.18,
    "Big Bash League": 1.11,
    "Pakistan Super League": 1.08,
    "SA20": 1.08,
    "Caribbean Premier League": 1.05,
    "International League T20": 1.03,
    "Vitality Blast": 1.00,
    "Bangladesh Premier League": 0.97,
    "Lanka Premier League": 0.95,
}


_RANKINGS_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
_COMP_WEIGHTS_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
_TRAJECTORY_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
_DELIVERY_SCHEMA_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


LENGTH_BUCKET_SQL = """
CASE
  WHEN UPPER(TRIM(dd.length)) IN ('FULL_TOSS', 'YORKER', 'FULL') THEN 'FULL'
  WHEN UPPER(TRIM(dd.length)) = 'GOOD_LENGTH' THEN 'GOOD_LENGTH'
  WHEN UPPER(TRIM(dd.length)) IN ('SHORT_OF_A_GOOD_LENGTH', 'SHORT_OF_GOOD_LENGTH') THEN 'SHORT_OF_GOOD'
  WHEN UPPER(TRIM(dd.length)) = 'SHORT' THEN 'SHORT'
  ELSE NULL
END
"""


BOWL_KIND_BUCKET_SQL = """
CASE
  WHEN dd.bowl_kind IS NULL THEN NULL
  WHEN LOWER(dd.bowl_kind) LIKE '%pace%'
    OR LOWER(dd.bowl_kind) LIKE '%fast%'
    OR LOWER(dd.bowl_kind) LIKE '%seam%'
    OR LOWER(dd.bowl_kind) LIKE '%medium%'
  THEN 'pace'
  WHEN LOWER(dd.bowl_kind) LIKE '%spin%'
    OR LOWER(dd.bowl_kind) LIKE '%slow%'
    OR LOWER(dd.bowl_kind) LIKE '%offbreak%'
    OR LOWER(dd.bowl_kind) LIKE '%legbreak%'
    OR LOWER(dd.bowl_kind) LIKE '%orthodox%'
    OR LOWER(dd.bowl_kind) LIKE '%chinaman%'
  THEN 'spin'
  ELSE NULL
END
"""


def _now() -> float:
    return time.time()


def _cache_get(cache: Dict[Tuple[Any, ...], Dict[str, Any]], key: Tuple[Any, ...], ttl_seconds: int) -> Optional[Any]:
    entry = cache.get(key)
    if not entry:
        return None
    age = _now() - entry["ts"]
    if age > ttl_seconds:
        cache.pop(key, None)
        return None
    return copy.deepcopy(entry["payload"])


def _cache_set(cache: Dict[Tuple[Any, ...], Dict[str, Any]], key: Tuple[Any, ...], payload: Any) -> None:
    cache[key] = {
        "ts": _now(),
        "payload": copy.deepcopy(payload),
    }


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den in (None, 0):
        return None
    return float(num) / float(den)


def _normalize_bowl_kind(value: Optional[str]) -> str:
    if not value:
        return "all"
    normalized = value.strip().lower()
    if normalized in {"pace", "pace bowler", "pacers"}:
        return "pace"
    if normalized in {"spin", "spin bowler", "spinners"}:
        return "spin"
    return "all"


def _resolve_date_range(start_date: Optional[date], end_date: Optional[date]) -> Tuple[date, date]:
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=730))
    if start > end:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
    return start, end


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_vals = sorted(float(v) for v in values)
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return sorted_vals[low]
    frac = rank - low
    return sorted_vals[low] + (sorted_vals[high] - sorted_vals[low]) * frac


def _population_std(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _weighted_mean(values: Sequence[float], weights: Sequence[float]) -> Optional[float]:
    if not values or not weights or len(values) != len(weights):
        return None
    total_w = sum(weights)
    if total_w <= 0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / total_w


def _weighted_std(values: Sequence[float], weights: Sequence[float]) -> float:
    if not values or len(values) <= 1:
        return 0.0
    avg = _weighted_mean(values, weights)
    if avg is None:
        return 0.0
    total_w = sum(weights)
    if total_w <= 0:
        return 0.0
    variance = sum(w * ((v - avg) ** 2) for v, w in zip(values, weights)) / total_w
    return math.sqrt(max(0.0, variance))


def _variation_adjust(values: Sequence[float], weights: Sequence[float], weight_mode: str = "occurrence") -> Optional[float]:
    if not values:
        return None
    if weight_mode == "equal":
        eff_weights = [1.0 for _ in values]
    else:
        eff_weights = [max(0.0, float(w)) for w in weights]

    avg = _weighted_mean(values, eff_weights)
    if avg is None:
        return None

    if avg <= 0:
        cv = 0.0
    else:
        std = _weighted_std(values, eff_weights)
        cv = std / avg

    penalty_factor = max(0.0, 1.0 - VARIATION_ALPHA * cv)
    return avg * penalty_factor


def _sigmoid(z: float) -> float:
    if z >= 60:
        return 1.0
    if z <= -60:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def _logistic_squash(values: Sequence[float]) -> List[float]:
    if not values:
        return []

    vals = [float(v) for v in values]
    med = _percentile(vals, 50)
    p95 = _percentile(vals, 95)

    if p95 <= med:
        k = 1.0
    else:
        # logit(0.9) ~= 2.197 so 95th percentile maps near 90.
        k = 2.1972245773362196 / (p95 - med)

    return [100.0 * _sigmoid(k * (v - med)) for v in vals]


def _coalesced_trim_expr(table_alias: str, columns: Sequence[str]) -> str:
    parts = [f"NULLIF(TRIM({table_alias}.{col}), '')" for col in columns]
    if len(parts) == 1:
        return parts[0]
    return f"COALESCE({', '.join(parts)})"


def _get_delivery_schema_config(db: Session) -> Dict[str, Any]:
    cache_key = ("delivery_details_schema",)
    cached = _cache_get(_DELIVERY_SCHEMA_CACHE, cache_key, DELIVERY_SCHEMA_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'delivery_details'
              AND table_schema = ANY(current_schemas(false))
            """
        )
    ).fetchall()
    columns = {str(row[0]) for row in rows}

    batter_cols = [col for col in ("batter", "bat") if col in columns]
    bowler_cols = [col for col in ("bowler", "bowl") if col in columns]
    date_cols = [col for col in ("date", "match_date") if col in columns]
    has_year = "year" in columns

    if not batter_cols:
        raise HTTPException(
            status_code=500,
            detail="delivery_details schema missing batter/bat column required for rankings",
        )
    if not bowler_cols:
        raise HTTPException(
            status_code=500,
            detail="delivery_details schema missing bowler/bowl column required for rankings",
        )
    if not date_cols and not has_year:
        raise HTTPException(
            status_code=500,
            detail="delivery_details schema missing date/match_date/year required for rankings",
        )

    if len(date_cols) == 2:
        date_expr = "COALESCE(dd.date, dd.match_date)"
    elif len(date_cols) == 1:
        date_expr = f"dd.{date_cols[0]}"
    else:
        date_expr = None

    payload = {
        "batter_expr": _coalesced_trim_expr("dd", batter_cols),
        "bowler_expr": _coalesced_trim_expr("dd", bowler_cols),
        "date_expr": date_expr,
        "has_year": has_year,
    }
    _cache_set(_DELIVERY_SCHEMA_CACHE, cache_key, payload)
    return payload


def _build_delivery_date_filter(
    schema_cfg: Dict[str, Any],
    start: date,
    end: date,
) -> Tuple[str, Dict[str, Any]]:
    date_expr = schema_cfg.get("date_expr")
    has_year = bool(schema_cfg.get("has_year"))

    if date_expr and has_year:
        return (
            f"""(
                ({date_expr} IS NOT NULL AND {date_expr} >= :start_date AND {date_expr} <= :end_date)
                OR ({date_expr} IS NULL AND dd.year >= :start_year AND dd.year <= :end_year)
            )""",
            {
                "start_date": start,
                "end_date": end,
                "start_year": int(start.year),
                "end_year": int(end.year),
            },
        )

    if date_expr:
        return (
            f"{date_expr} >= :start_date AND {date_expr} <= :end_date",
            {"start_date": start, "end_date": end},
        )

    if has_year:
        return (
            "dd.year >= :start_year AND dd.year <= :end_year",
            {"start_year": int(start.year), "end_year": int(end.year)},
        )

    raise HTTPException(status_code=500, detail="Unable to build date filter for delivery_details")


def _month_end(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def _add_months(d: date, months: int) -> date:
    month_idx = (d.month - 1) + months
    year = d.year + month_idx // 12
    month = (month_idx % 12) + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _fetch_batting_cells(db: Session, start: date, end: date) -> List[Dict[str, Any]]:
    schema_cfg = _get_delivery_schema_config(db)
    date_filter_sql, date_filter_params = _build_delivery_date_filter(schema_cfg, start, end)

    query = text(
        f"""
        WITH normalized AS (
            SELECT
                {schema_cfg["batter_expr"]} AS batter_name,
                dd.competition,
                {LENGTH_BUCKET_SQL} AS length_bucket,
                {BOWL_KIND_BUCKET_SQL} AS bowl_kind_bucket,
                COALESCE(dd.score, 0)::float AS runs_scored,
                CASE WHEN COALESCE(dd.control, 0) = 1 THEN 1 ELSE 0 END::float AS controlled_ball
            FROM delivery_details dd
            WHERE {date_filter_sql}
              AND dd.length IS NOT NULL
              AND {schema_cfg["batter_expr"]} IS NOT NULL
              AND dd.competition IS NOT NULL
              AND TRIM(dd.competition) <> ''
              AND (dd.wide IS NULL OR dd.wide = 0)
        )
        SELECT
            batter_name AS player,
            competition,
            length_bucket,
            bowl_kind_bucket,
            COUNT(*)::int AS balls,
            SUM(runs_scored)::float AS runs,
            SUM(controlled_ball)::float AS controlled
        FROM normalized
        WHERE length_bucket IS NOT NULL
          AND bowl_kind_bucket IS NOT NULL
        GROUP BY batter_name, competition, length_bucket, bowl_kind_bucket
        HAVING COUNT(*) >= :min_cell_balls
        """
    )

    params = {
        **date_filter_params,
        "min_cell_balls": MIN_CELL_BALLS,
    }
    rows = db.execute(query, params).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        r = row._mapping
        out.append(
            {
                "player": r["player"],
                "competition": r["competition"],
                "length_bucket": r["length_bucket"],
                "bowl_kind": r["bowl_kind_bucket"],
                "balls": int(r["balls"] or 0),
                "runs": float(r["runs"] or 0.0),
                "controlled": float(r["controlled"] or 0.0),
            }
        )
    return out


def _fetch_batting_totals(db: Session, start: date, end: date) -> Dict[Tuple[str, str, str], Dict[str, float]]:
    schema_cfg = _get_delivery_schema_config(db)
    date_filter_sql, date_filter_params = _build_delivery_date_filter(schema_cfg, start, end)

    query = text(
        f"""
        WITH normalized AS (
            SELECT
                dd.competition,
                {LENGTH_BUCKET_SQL} AS length_bucket,
                {BOWL_KIND_BUCKET_SQL} AS bowl_kind_bucket,
                COALESCE(dd.score, 0)::float AS runs_scored,
                CASE WHEN COALESCE(dd.control, 0) = 1 THEN 1 ELSE 0 END::float AS controlled_ball
            FROM delivery_details dd
            WHERE {date_filter_sql}
              AND dd.length IS NOT NULL
              AND dd.competition IS NOT NULL
              AND TRIM(dd.competition) <> ''
              AND (dd.wide IS NULL OR dd.wide = 0)
        )
        SELECT
            competition,
            length_bucket,
            bowl_kind_bucket,
            COUNT(*)::int AS balls,
            SUM(runs_scored)::float AS runs,
            SUM(controlled_ball)::float AS controlled
        FROM normalized
        WHERE length_bucket IS NOT NULL
          AND bowl_kind_bucket IS NOT NULL
        GROUP BY competition, length_bucket, bowl_kind_bucket
        """
    )

    rows = db.execute(query, date_filter_params).fetchall()
    totals: Dict[Tuple[str, str, str], Dict[str, float]] = {}
    for row in rows:
        r = row._mapping
        key = (r["competition"], r["length_bucket"], r["bowl_kind_bucket"])
        totals[key] = {
            "balls": float(r["balls"] or 0.0),
            "runs": float(r["runs"] or 0.0),
            "controlled": float(r["controlled"] or 0.0),
        }
    return totals


def _fetch_bowling_cells(db: Session, start: date, end: date) -> List[Dict[str, Any]]:
    schema_cfg = _get_delivery_schema_config(db)
    date_filter_sql, date_filter_params = _build_delivery_date_filter(schema_cfg, start, end)

    query = text(
        f"""
        WITH normalized AS (
            SELECT
                {schema_cfg["bowler_expr"]} AS bowler_name,
                dd.competition,
                {LENGTH_BUCKET_SQL} AS length_bucket,
                {BOWL_KIND_BUCKET_SQL} AS bowl_kind_bucket,
                COALESCE(dd.score, 0)::float AS runs_conceded,
                CASE WHEN COALESCE(dd.score, 0) = 0 THEN 1 ELSE 0 END::float AS dot_ball
            FROM delivery_details dd
            WHERE {date_filter_sql}
              AND dd.length IS NOT NULL
              AND {schema_cfg["bowler_expr"]} IS NOT NULL
              AND dd.competition IS NOT NULL
              AND TRIM(dd.competition) <> ''
              AND (dd.wide IS NULL OR dd.wide = 0)
        )
        SELECT
            bowler_name AS player,
            competition,
            length_bucket,
            bowl_kind_bucket,
            COUNT(*)::int AS balls,
            SUM(runs_conceded)::float AS runs,
            SUM(dot_ball)::float AS dots
        FROM normalized
        WHERE length_bucket IS NOT NULL
          AND bowl_kind_bucket IS NOT NULL
        GROUP BY bowler_name, competition, length_bucket, bowl_kind_bucket
        HAVING COUNT(*) >= :min_cell_balls
        """
    )

    params = {
        **date_filter_params,
        "min_cell_balls": MIN_CELL_BALLS,
    }
    rows = db.execute(query, params).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        r = row._mapping
        out.append(
            {
                "player": r["player"],
                "competition": r["competition"],
                "length_bucket": r["length_bucket"],
                "bowl_kind": r["bowl_kind_bucket"],
                "balls": int(r["balls"] or 0),
                "runs": float(r["runs"] or 0.0),
                "dots": float(r["dots"] or 0.0),
            }
        )
    return out


def _fetch_bowling_totals(db: Session, start: date, end: date) -> Dict[Tuple[str, str, str], Dict[str, float]]:
    schema_cfg = _get_delivery_schema_config(db)
    date_filter_sql, date_filter_params = _build_delivery_date_filter(schema_cfg, start, end)

    query = text(
        f"""
        WITH normalized AS (
            SELECT
                dd.competition,
                {LENGTH_BUCKET_SQL} AS length_bucket,
                {BOWL_KIND_BUCKET_SQL} AS bowl_kind_bucket,
                COALESCE(dd.score, 0)::float AS runs_conceded,
                CASE WHEN COALESCE(dd.score, 0) = 0 THEN 1 ELSE 0 END::float AS dot_ball
            FROM delivery_details dd
            WHERE {date_filter_sql}
              AND dd.length IS NOT NULL
              AND dd.competition IS NOT NULL
              AND TRIM(dd.competition) <> ''
              AND (dd.wide IS NULL OR dd.wide = 0)
        )
        SELECT
            competition,
            length_bucket,
            bowl_kind_bucket,
            COUNT(*)::int AS balls,
            SUM(runs_conceded)::float AS runs,
            SUM(dot_ball)::float AS dots
        FROM normalized
        WHERE length_bucket IS NOT NULL
          AND bowl_kind_bucket IS NOT NULL
        GROUP BY competition, length_bucket, bowl_kind_bucket
        """
    )

    rows = db.execute(query, date_filter_params).fetchall()
    totals: Dict[Tuple[str, str, str], Dict[str, float]] = {}
    for row in rows:
        r = row._mapping
        key = (r["competition"], r["length_bucket"], r["bowl_kind_bucket"])
        totals[key] = {
            "balls": float(r["balls"] or 0.0),
            "runs": float(r["runs"] or 0.0),
            "dots": float(r["dots"] or 0.0),
        }
    return totals


def _build_comp_weight_rows(
    batting_cells: Sequence[Dict[str, Any]],
    batting_totals: Dict[Tuple[str, str, str], Dict[str, float]],
) -> List[Dict[str, Any]]:
    player_comp_cells: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for cell in batting_cells:
        if cell["balls"] < MIN_CELL_BALLS:
            continue
        player_comp_cells[cell["player"]][cell["competition"]].append(cell)

    rows: List[Dict[str, Any]] = []

    for player, comp_map in player_comp_cells.items():
        valid_competitions = [
            comp
            for comp, cells in comp_map.items()
            if sum(float(c["balls"] or 0.0) for c in cells) >= MIN_CELL_BALLS
        ]
        if len(valid_competitions) < 2:
            continue

        for competition in valid_competitions:
            cells = comp_map[competition]
            total_balls = sum(float(c["balls"] or 0.0) for c in cells)
            if total_balls <= 0:
                continue

            player_skill_components: List[float] = []
            baseline_skill_components: List[float] = []
            weights: List[float] = []

            for cell in cells:
                balls = float(cell["balls"] or 0.0)
                if balls <= 0:
                    continue

                sr = _safe_div(cell["runs"] * 100.0, balls)
                control_pct = _safe_div(cell["controlled"], balls)
                if sr is None or control_pct is None:
                    continue

                skill = sr * control_pct

                total_key = (competition, cell["length_bucket"], cell["bowl_kind"])
                total_cell = batting_totals.get(total_key)
                if not total_cell:
                    continue

                t_balls = float(total_cell["balls"] or 0.0)
                if t_balls <= 0:
                    continue

                baseline_sr = _safe_div(float(total_cell["runs"] or 0.0) * 100.0, t_balls)
                baseline_control = _safe_div(float(total_cell["controlled"] or 0.0), t_balls)
                if baseline_sr is None or baseline_control is None:
                    continue

                baseline_skill = baseline_sr * baseline_control
                if baseline_skill <= 0:
                    continue

                player_skill_components.append(skill)
                baseline_skill_components.append(baseline_skill)
                weights.append(balls)

            if not weights:
                continue

            player_skill = _weighted_mean(player_skill_components, weights)
            baseline_skill = _weighted_mean(baseline_skill_components, weights)
            if player_skill is None or baseline_skill is None or baseline_skill <= 0:
                continue

            ratio = player_skill / baseline_skill
            if ratio <= 0:
                continue

            rows.append(
                {
                    "player": player,
                    "competition": competition,
                    "log_deviation": math.log(ratio),
                    "balls": total_balls,
                }
            )

    return rows


def _fit_competition_weights_mixedlm(rows: Sequence[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not HAS_STATSMODELS or not rows:
        return None

    if pd is None or smf is None:
        return None

    df = pd.DataFrame(rows)
    if df.empty:
        return None

    if df["competition"].nunique() < 2:
        return None

    # Need enough cross-league points and enough players for a stable fit.
    if len(df) < 24 or df["player"].nunique() < 12:
        return None

    try:
        model = smf.mixedlm("log_deviation ~ C(competition)", data=df, groups=df["player"])
        result = model.fit(reml=False, method="lbfgs", maxiter=200, disp=False)
        params = result.params.to_dict()

        intercept = float(params.get("Intercept", 0.0))
        competitions = sorted(df["competition"].dropna().unique().tolist())

        raw_weights: Dict[str, float] = {}
        for comp in competitions:
            key = f"C(competition)[T.{comp}]"
            effect = intercept + float(params.get(key, 0.0))
            raw_weights[comp] = math.exp(effect)

        if not raw_weights:
            return None

        med = median(raw_weights.values())
        if med <= 0:
            med = 1.0

        normalized = {
            comp: _clamp(weight / med, 0.70, 1.40)
            for comp, weight in raw_weights.items()
        }
        return normalized

    except Exception as exc:  # pragma: no cover - data-dependent
        logger.warning("MixedLM competition weights failed, using fallback: %s", exc)
        return None


def _merge_competition_weights(computed: Optional[Dict[str, float]]) -> Dict[str, float]:
    merged = dict(DEFAULT_COMPETITION_WEIGHTS)

    if computed:
        for comp, weight in computed.items():
            merged[comp] = float(weight)

    return {comp: _round(weight, 3) for comp, weight in sorted(merged.items(), key=lambda kv: kv[0])}


def _get_competition_weights(
    db: Session,
    start: date,
    end: date,
    force_refresh: bool = False,
    batting_cells: Optional[Sequence[Dict[str, Any]]] = None,
    batting_totals: Optional[Dict[Tuple[str, str, str], Dict[str, float]]] = None,
) -> Dict[str, Any]:
    key = (start.isoformat(), end.isoformat())
    if not force_refresh:
        cached = _cache_get(_COMP_WEIGHTS_CACHE, key, COMP_WEIGHTS_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

    cells = list(batting_cells) if batting_cells is not None else _fetch_batting_cells(db, start, end)
    totals = dict(batting_totals) if batting_totals is not None else _fetch_batting_totals(db, start, end)

    comp_rows = _build_comp_weight_rows(cells, totals)
    computed = _fit_competition_weights_mixedlm(comp_rows)

    payload = {
        "weights": _merge_competition_weights(computed),
        "source": "mixedlm" if computed else ("fallback_statsmodels_missing" if not HAS_STATSMODELS else "fallback_insufficient_cross_league"),
        "cross_league_samples": len(comp_rows),
    }

    _cache_set(_COMP_WEIGHTS_CACHE, key, payload)
    return payload


def _filter_cells_by_bowl_kind(cells: Sequence[Dict[str, Any]], bowl_kind: str) -> List[Dict[str, Any]]:
    if bowl_kind == "all":
        return list(cells)
    return [cell for cell in cells if cell.get("bowl_kind") == bowl_kind]


def _qualifies_by_length(
    length_totals: Dict[str, float],
    required_lengths: Sequence[str],
    min_balls_per_length: int,
) -> bool:
    return all(float(length_totals.get(length, 0.0)) >= float(min_balls_per_length) for length in required_lengths)


def _aggregate_param_bundle(
    cells: Sequence[Dict[str, Any]],
    param_keys: Sequence[str],
    weight_mode: str,
) -> Dict[str, Any]:
    if not cells:
        return {}

    balls = [float(cell.get("balls", 0.0) or 0.0) for cell in cells]
    total_balls = sum(balls)
    if total_balls <= 0:
        return {}

    result: Dict[str, Any] = {"balls": total_balls}

    for param in param_keys:
        vals: List[float] = []
        weights: List[float] = []
        for cell in cells:
            value = cell.get(param)
            b = float(cell.get("balls", 0.0) or 0.0)
            if value is None or b <= 0:
                continue
            vals.append(float(value))
            weights.append(b)

        result[param] = _variation_adjust(vals, weights, weight_mode=weight_mode) if vals else None

    return result


def _finalize_scores_with_logistic(rows: List[Dict[str, Any]]) -> None:
    quality_raw = [float(r.get("quality_raw", 0.0) or 0.0) for r in rows]
    strike_raw = [float(r.get("strike_raw", 0.0) or 0.0) for r in rows]
    control_raw = [float(r.get("control_raw", 0.0) or 0.0) for r in rows]

    quality_scaled = _logistic_squash(quality_raw)
    strike_scaled = _logistic_squash(strike_raw)
    control_scaled = _logistic_squash(control_raw)

    for idx, row in enumerate(rows):
        row["quality_score"] = _round(quality_scaled[idx], 1)
        row["strike_factor"] = _round(strike_scaled[idx], 1)
        row["control_factor"] = _round(control_scaled[idx], 1)

    rows.sort(
        key=lambda r: (
            float(r.get("quality_score", 0.0) or 0.0),
            float(r.get("strike_factor", 0.0) or 0.0),
            float(r.get("control_factor", 0.0) or 0.0),
        ),
        reverse=True,
    )

    for index, row in enumerate(rows, start=1):
        row["rank"] = index
        row.pop("quality_raw", None)
        row.pop("strike_raw", None)
        row.pop("control_raw", None)


def _build_batting_rows(
    cells: Sequence[Dict[str, Any]],
    totals: Dict[Tuple[str, str, str], Dict[str, float]],
    competition_weights: Dict[str, float],
    bowl_kind: str,
    min_balls_per_length: int,
    weight_mode: str,
) -> List[Dict[str, Any]]:
    filtered_cells = _filter_cells_by_bowl_kind(cells, bowl_kind)

    player_comp_kind_cells: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    player_length_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for cell in filtered_cells:
        balls = float(cell["balls"] or 0.0)
        if balls <= 0:
            continue

        total_key = (cell["competition"], cell["length_bucket"], cell["bowl_kind"])
        total_cell = totals.get(total_key)
        if not total_cell:
            continue

        t_balls = float(total_cell["balls"] or 0.0)
        if t_balls <= 0:
            continue

        # Leave-one-out baselines.
        other_balls = t_balls - balls
        if other_balls > 0:
            baseline_sr = ((float(total_cell["runs"] or 0.0) - float(cell["runs"] or 0.0)) / other_balls) * 100.0
            baseline_control = (float(total_cell["controlled"] or 0.0) - float(cell["controlled"] or 0.0)) / other_balls
        else:
            baseline_sr = (float(total_cell["runs"] or 0.0) / t_balls) * 100.0
            baseline_control = float(total_cell["controlled"] or 0.0) / t_balls

        if baseline_sr <= 0:
            baseline_sr = (float(total_cell["runs"] or 0.0) / t_balls) * 100.0
        if baseline_control <= 0:
            baseline_control = float(total_cell["controlled"] or 0.0) / t_balls

        if baseline_sr <= 0 or baseline_control <= 0:
            continue

        sr = (float(cell["runs"] or 0.0) / balls) * 100.0
        control_pct = float(cell["controlled"] or 0.0) / balls

        intent = _clamp(sr / baseline_sr, 0.0, 3.0)
        reliability = _clamp(control_pct / baseline_control, 0.0, 3.0)

        player_comp_kind_cells[cell["player"]][cell["competition"]][cell["bowl_kind"]].append(
            {
                "length_bucket": cell["length_bucket"],
                "balls": balls,
                "sr": sr,
                "control": control_pct,
                "intent": intent,
                "reliability": reliability,
            }
        )

        player_length_totals[cell["player"]][cell["length_bucket"]] += balls

    rows: List[Dict[str, Any]] = []
    required_lengths = list(LENGTH_BUCKETS_ALL)

    for player, competition_map in player_comp_kind_cells.items():
        if not _qualifies_by_length(player_length_totals[player], required_lengths, min_balls_per_length):
            continue

        per_competition: Dict[str, Dict[str, Any]] = {}

        for competition, kind_map in competition_map.items():
            kind_aggregates: Dict[str, Dict[str, Any]] = {}
            for kind, kind_cells in kind_map.items():
                agg = _aggregate_param_bundle(
                    kind_cells,
                    param_keys=("sr", "control", "intent", "reliability"),
                    weight_mode=weight_mode,
                )
                if agg:
                    kind_aggregates[kind] = agg

            if not kind_aggregates:
                continue

            kind_weights = [float(v["balls"]) for v in kind_aggregates.values()]
            competition_total_balls = sum(kind_weights)
            if competition_total_balls <= 0:
                continue

            comp_params: Dict[str, Optional[float]] = {}
            for param in ("sr", "control", "intent", "reliability"):
                vals = [float(v[param]) for v in kind_aggregates.values() if v.get(param) is not None]
                weights = [float(v["balls"]) for v in kind_aggregates.values() if v.get(param) is not None]
                comp_params[param] = _weighted_mean(vals, weights) if vals else None

            per_competition[competition] = {
                "weight": float(competition_weights.get(competition, 1.0)),
                "balls": competition_total_balls,
                "sr": comp_params["sr"],
                "control": comp_params["control"],
                "intent": comp_params["intent"],
                "reliability": comp_params["reliability"],
                "kind_breakdown": {
                    kind: {
                        "balls": _round(float(bundle.get("balls", 0.0)), 1),
                        "sr": _round(bundle.get("sr")),
                        "control": _round(bundle.get("control")),
                        "intent": _round(bundle.get("intent")),
                        "reliability": _round(bundle.get("reliability")),
                    }
                    for kind, bundle in kind_aggregates.items()
                },
            }

        if not per_competition:
            continue

        final_params: Dict[str, float] = {}
        for param in ("sr", "control", "intent", "reliability"):
            values = [
                float(entry[param]) * float(entry["weight"])
                for entry in per_competition.values()
                if entry.get(param) is not None
            ]
            if not values:
                final_params[param] = 0.0
                continue
            final_mean = mean(values)
            final_std = _population_std(values)
            final_params[param] = max(0.0, final_mean * (1.0 - VARIATION_ALPHA * final_std))

        quality_raw = (
            (final_params["sr"] ** 2)
            * final_params["control"]
            * (final_params["intent"] ** 2)
            * final_params["reliability"]
        )
        strike_raw = final_params["intent"] * final_params["sr"]
        control_raw = final_params["reliability"] * final_params["control"]

        rows.append(
            {
                "player": player,
                "quality_raw": quality_raw,
                "strike_raw": strike_raw,
                "control_raw": control_raw,
                "competitions_played": sorted(per_competition.keys()),
                "base_params": {
                    "sr": _round(final_params["sr"]),
                    "control": _round(final_params["control"]),
                    "intent": _round(final_params["intent"]),
                    "reliability": _round(final_params["reliability"]),
                },
                "per_competition": {
                    comp: {
                        "weight": _round(float(entry["weight"]), 3),
                        "balls": int(round(float(entry["balls"]))),
                        "sr": _round(entry.get("sr")),
                        "control": _round(entry.get("control")),
                        "intent": _round(entry.get("intent")),
                        "reliability": _round(entry.get("reliability")),
                        "kind_breakdown": entry.get("kind_breakdown", {}),
                    }
                    for comp, entry in per_competition.items()
                },
                "length_coverage": {
                    length: int(round(float(player_length_totals[player].get(length, 0.0))))
                    for length in LENGTH_BUCKETS_ALL
                },
                "total_balls": int(round(sum(player_length_totals[player].values()))),
            }
        )

    _finalize_scores_with_logistic(rows)
    return rows


def _build_bowling_rows(
    cells: Sequence[Dict[str, Any]],
    totals: Dict[Tuple[str, str, str], Dict[str, float]],
    competition_weights: Dict[str, float],
    bowl_kind: str,
    min_balls_per_length: int,
    weight_mode: str,
) -> List[Dict[str, Any]]:
    filtered_cells = _filter_cells_by_bowl_kind(cells, bowl_kind)

    player_comp_kind_cells: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    player_length_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    player_kind_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for cell in filtered_cells:
        balls = float(cell["balls"] or 0.0)
        if balls <= 0:
            continue

        total_key = (cell["competition"], cell["length_bucket"], cell["bowl_kind"])
        total_cell = totals.get(total_key)
        if not total_cell:
            continue

        t_balls = float(total_cell["balls"] or 0.0)
        if t_balls <= 0:
            continue

        other_balls = t_balls - balls
        if other_balls > 0:
            baseline_economy = ((float(total_cell["runs"] or 0.0) - float(cell["runs"] or 0.0)) / other_balls) * 6.0
            baseline_dot = (float(total_cell["dots"] or 0.0) - float(cell["dots"] or 0.0)) / other_balls
        else:
            baseline_economy = (float(total_cell["runs"] or 0.0) / t_balls) * 6.0
            baseline_dot = float(total_cell["dots"] or 0.0) / t_balls

        if baseline_economy <= 0:
            baseline_economy = (float(total_cell["runs"] or 0.0) / t_balls) * 6.0
        if baseline_dot <= 0:
            baseline_dot = float(total_cell["dots"] or 0.0) / t_balls

        if baseline_economy <= 0 or baseline_dot <= 0:
            continue

        economy = (float(cell["runs"] or 0.0) / balls) * 6.0
        dot_pct = float(cell["dots"] or 0.0) / balls
        econ_inv = 100.0 / economy if economy > 0 else 0.0

        restriction = _clamp(baseline_economy / economy, 0.0, 3.0) if economy > 0 else 0.0
        consistency = _clamp(dot_pct / baseline_dot, 0.0, 3.0)

        player_comp_kind_cells[cell["player"]][cell["competition"]][cell["bowl_kind"]].append(
            {
                "length_bucket": cell["length_bucket"],
                "balls": balls,
                "econ_inv": econ_inv,
                "dot_pct": dot_pct,
                "restriction": restriction,
                "consistency": consistency,
            }
        )

        player_length_totals[cell["player"]][cell["length_bucket"]] += balls
        player_kind_totals[cell["player"]][cell["bowl_kind"]] += balls

    rows: List[Dict[str, Any]] = []

    for player, competition_map in player_comp_kind_cells.items():
        if bowl_kind == "spin":
            required_lengths = list(LENGTH_BUCKETS_SPIN_BOWLING)
        else:
            # pace/all defaults to all four length buckets.
            required_lengths = list(LENGTH_BUCKETS_ALL)

        if not _qualifies_by_length(player_length_totals[player], required_lengths, min_balls_per_length):
            continue

        per_competition: Dict[str, Dict[str, Any]] = {}

        for competition, kind_map in competition_map.items():
            kind_aggregates: Dict[str, Dict[str, Any]] = {}
            for kind, kind_cells in kind_map.items():
                agg = _aggregate_param_bundle(
                    kind_cells,
                    param_keys=("econ_inv", "dot_pct", "restriction", "consistency"),
                    weight_mode=weight_mode,
                )
                if agg:
                    kind_aggregates[kind] = agg

            if not kind_aggregates:
                continue

            competition_total_balls = sum(float(v["balls"]) for v in kind_aggregates.values())
            if competition_total_balls <= 0:
                continue

            comp_params: Dict[str, Optional[float]] = {}
            for param in ("econ_inv", "dot_pct", "restriction", "consistency"):
                vals = [float(v[param]) for v in kind_aggregates.values() if v.get(param) is not None]
                weights = [float(v["balls"]) for v in kind_aggregates.values() if v.get(param) is not None]
                comp_params[param] = _weighted_mean(vals, weights) if vals else None

            per_competition[competition] = {
                "weight": float(competition_weights.get(competition, 1.0)),
                "balls": competition_total_balls,
                "econ_inv": comp_params["econ_inv"],
                "dot_pct": comp_params["dot_pct"],
                "restriction": comp_params["restriction"],
                "consistency": comp_params["consistency"],
                "kind_breakdown": {
                    kind: {
                        "balls": _round(float(bundle.get("balls", 0.0)), 1),
                        "econ_inv": _round(bundle.get("econ_inv")),
                        "dot_pct": _round(bundle.get("dot_pct")),
                        "restriction": _round(bundle.get("restriction")),
                        "consistency": _round(bundle.get("consistency")),
                    }
                    for kind, bundle in kind_aggregates.items()
                },
            }

        if not per_competition:
            continue

        final_params: Dict[str, float] = {}
        for param in ("econ_inv", "dot_pct", "restriction", "consistency"):
            values = [
                float(entry[param]) * float(entry["weight"])
                for entry in per_competition.values()
                if entry.get(param) is not None
            ]
            if not values:
                final_params[param] = 0.0
                continue
            final_mean = mean(values)
            final_std = _population_std(values)
            final_params[param] = max(0.0, final_mean * (1.0 - VARIATION_ALPHA * final_std))

        quality_raw = (
            (final_params["econ_inv"] ** 2)
            * final_params["dot_pct"]
            * (final_params["restriction"] ** 2)
            * final_params["consistency"]
        )
        strike_raw = final_params["restriction"] * final_params["econ_inv"]
        control_raw = final_params["consistency"] * final_params["dot_pct"]

        rows.append(
            {
                "player": player,
                "quality_raw": quality_raw,
                "strike_raw": strike_raw,
                "control_raw": control_raw,
                "competitions_played": sorted(per_competition.keys()),
                "base_params": {
                    "econ_inv": _round(final_params["econ_inv"]),
                    "dot_pct": _round(final_params["dot_pct"]),
                    "restriction": _round(final_params["restriction"]),
                    "consistency": _round(final_params["consistency"]),
                },
                "per_competition": {
                    comp: {
                        "weight": _round(float(entry["weight"]), 3),
                        "balls": int(round(float(entry["balls"]))),
                        "econ_inv": _round(entry.get("econ_inv")),
                        "dot_pct": _round(entry.get("dot_pct")),
                        "restriction": _round(entry.get("restriction")),
                        "consistency": _round(entry.get("consistency")),
                        "kind_breakdown": entry.get("kind_breakdown", {}),
                    }
                    for comp, entry in per_competition.items()
                },
                "length_coverage": {
                    length: int(round(float(player_length_totals[player].get(length, 0.0))))
                    for length in LENGTH_BUCKETS_ALL
                },
                "total_balls": int(round(sum(player_length_totals[player].values()))),
                "bowl_kind_coverage": {
                    kind: int(round(float(value)))
                    for kind, value in player_kind_totals[player].items()
                },
            }
        )

    _finalize_scores_with_logistic(rows)
    return rows


def _build_rankings_payload(
    db: Session,
    mode: str,
    start: date,
    end: date,
    bowl_kind: str,
    force_refresh: bool = False,
    variation_mode: str = "occurrence",
) -> Dict[str, Any]:
    cache_key = (mode, start.isoformat(), end.isoformat(), bowl_kind, variation_mode)

    if not force_refresh:
        cached = _cache_get(_RANKINGS_CACHE, cache_key, RANKINGS_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

    try:
        batting_cells = _fetch_batting_cells(db, start, end)
        batting_totals = _fetch_batting_totals(db, start, end)
        comp_weight_payload = _get_competition_weights(
            db,
            start,
            end,
            force_refresh=force_refresh,
            batting_cells=batting_cells,
            batting_totals=batting_totals,
        )
        comp_weights = comp_weight_payload["weights"]

        if mode == "batting":
            rows = _build_batting_rows(
                cells=batting_cells,
                totals=batting_totals,
                competition_weights=comp_weights,
                bowl_kind=bowl_kind,
                min_balls_per_length=MIN_BALLS_PER_LENGTH_BATTING,
                weight_mode=variation_mode,
            )
            qualification = {
                "min_balls_per_length": MIN_BALLS_PER_LENGTH_BATTING,
                "required_lengths": list(LENGTH_BUCKETS_ALL),
            }
        elif mode == "bowling":
            bowling_cells = _fetch_bowling_cells(db, start, end)
            bowling_totals = _fetch_bowling_totals(db, start, end)
            rows = _build_bowling_rows(
                cells=bowling_cells,
                totals=bowling_totals,
                competition_weights=comp_weights,
                bowl_kind=bowl_kind,
                min_balls_per_length=MIN_BALLS_PER_LENGTH_BOWLING,
                weight_mode=variation_mode,
            )
            qualification = {
                "min_balls_per_length": MIN_BALLS_PER_LENGTH_BOWLING,
                "required_lengths": list(LENGTH_BUCKETS_SPIN_BOWLING if bowl_kind == "spin" else LENGTH_BUCKETS_ALL),
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported ranking mode: {mode}")

        payload = {
            "rankings": rows,
            "total": len(rows),
            "date_range": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "bowl_kind": bowl_kind,
            "competition_weights": comp_weights,
            "competition_weight_source": comp_weight_payload.get("source"),
            "cross_league_samples": comp_weight_payload.get("cross_league_samples", 0),
            "qualification": qualification,
        }

        _cache_set(_RANKINGS_CACHE, cache_key, payload)
        return payload

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute {mode} rankings: {exc}")


def _paginate_rankings(payload: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
    all_rows = payload.get("rankings", [])

    if offset < 0:
        offset = 0
    if limit < 0:
        limit = 0

    page_rows = all_rows[offset: offset + limit] if limit else all_rows[offset:]

    return {
        **payload,
        "rankings": page_rows,
    }


def _normalize_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def _find_player_row(rankings: Sequence[Dict[str, Any]], candidates: Iterable[str]) -> Optional[Dict[str, Any]]:
    candidate_set = {_normalize_name(c) for c in candidates if c}
    if not candidate_set:
        return None

    for row in rankings:
        row_player = row.get("player")
        if _normalize_name(str(row_player)) in candidate_set:
            return row

    return None


def _build_player_trajectory(
    db: Session,
    player_candidates: Sequence[str],
    mode: str,
    end_date: date,
    bowl_kind: str,
    snapshots: int,
    force_refresh: bool,
) -> List[Dict[str, Any]]:
    snapshots = max(1, min(36, int(snapshots)))

    key = (
        mode,
        tuple(sorted({c for c in player_candidates if c})),
        end_date.isoformat(),
        bowl_kind,
        snapshots,
    )

    if not force_refresh:
        cached = _cache_get(_TRAJECTORY_CACHE, key, TRAJECTORY_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

    timeline: List[Dict[str, Any]] = []
    anchor_end = _month_end(end_date)

    for idx in range(snapshots):
        month_end = _add_months(anchor_end, -(snapshots - 1 - idx))
        month_end = _month_end(month_end)

        window_start = _add_months(month_end, -24) + timedelta(days=1)

        payload = _build_rankings_payload(
            db=db,
            mode=mode,
            start=window_start,
            end=month_end,
            bowl_kind=bowl_kind,
            force_refresh=False,
        )

        row = _find_player_row(payload.get("rankings", []), player_candidates)
        if row:
            timeline.append(
                {
                    "date": month_end.isoformat(),
                    "rank": row.get("rank"),
                    "quality_score": row.get("quality_score"),
                    "strike_factor": row.get("strike_factor"),
                    "control_factor": row.get("control_factor"),
                }
            )
        else:
            timeline.append(
                {
                    "date": month_end.isoformat(),
                    "rank": None,
                    "quality_score": None,
                    "strike_factor": None,
                    "control_factor": None,
                }
            )

    _cache_set(_TRAJECTORY_CACHE, key, timeline)
    return timeline


def get_batting_rankings_service(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    bowl_kind: str = "all",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    start, end = _resolve_date_range(start_date, end_date)
    normalized_bowl_kind = _normalize_bowl_kind(bowl_kind)

    payload = _build_rankings_payload(
        db=db,
        mode="batting",
        start=start,
        end=end,
        bowl_kind=normalized_bowl_kind,
        force_refresh=force_refresh,
    )

    return _paginate_rankings(payload, limit=limit, offset=offset)


def get_bowling_rankings_service(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    bowl_kind: str = "all",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    start, end = _resolve_date_range(start_date, end_date)
    normalized_bowl_kind = _normalize_bowl_kind(bowl_kind)

    payload = _build_rankings_payload(
        db=db,
        mode="bowling",
        start=start,
        end=end,
        bowl_kind=normalized_bowl_kind,
        force_refresh=force_refresh,
    )

    return _paginate_rankings(payload, limit=limit, offset=offset)


def get_player_rankings_service(
    player_name: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    bowl_kind: str = "all",
    snapshots: int = 24,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    if not player_name or not player_name.strip():
        raise HTTPException(status_code=400, detail="player name is required")

    start, end = _resolve_date_range(start_date, end_date)
    normalized_bowl_kind = _normalize_bowl_kind(bowl_kind)

    names = get_player_names(player_name.strip(), db)
    player_candidates = [
        player_name.strip(),
        names.get("legacy_name", ""),
        names.get("details_name", ""),
    ]

    batting_payload = _build_rankings_payload(
        db=db,
        mode="batting",
        start=start,
        end=end,
        bowl_kind=normalized_bowl_kind,
        force_refresh=force_refresh,
    )
    bowling_payload = _build_rankings_payload(
        db=db,
        mode="bowling",
        start=start,
        end=end,
        bowl_kind=normalized_bowl_kind,
        force_refresh=force_refresh,
    )

    batting_row = _find_player_row(batting_payload.get("rankings", []), player_candidates)
    bowling_row = _find_player_row(bowling_payload.get("rankings", []), player_candidates)

    batting_trajectory = _build_player_trajectory(
        db=db,
        player_candidates=player_candidates,
        mode="batting",
        end_date=end,
        bowl_kind=normalized_bowl_kind,
        snapshots=snapshots,
        force_refresh=force_refresh,
    )

    bowling_trajectory = _build_player_trajectory(
        db=db,
        player_candidates=player_candidates,
        mode="bowling",
        end_date=end,
        bowl_kind=normalized_bowl_kind,
        snapshots=snapshots,
        force_refresh=force_refresh,
    )

    return {
        "player": {
            "requested": player_name,
            "legacy_name": names.get("legacy_name", player_name),
            "details_name": names.get("details_name", player_name),
        },
        "date_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "bowl_kind": normalized_bowl_kind,
        "batting": {
            "found": batting_row is not None,
            "ranking": batting_row,
            "trajectory": batting_trajectory,
        },
        "bowling": {
            "found": bowling_row is not None,
            "ranking": bowling_row,
            "trajectory": bowling_trajectory,
        },
        "competition_weights": batting_payload.get("competition_weights", {}),
    }


def get_competition_weights_service(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    start, end = _resolve_date_range(start_date, end_date)
    payload = _get_competition_weights(db, start, end, force_refresh=force_refresh)

    return {
        "date_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "source": payload.get("source"),
        "cross_league_samples": payload.get("cross_league_samples", 0),
        "weights": payload.get("weights", {}),
    }
