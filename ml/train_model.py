"""Train foresight/hindsight ML models from historical match data.

Trains three models:
- Match winner classifier (with isotonic calibration)
- 1st innings score predictor (independent XGBRegressor)
- 2nd innings score predictor (independent XGBRegressor, uses 1st innings score)
- Player fantasy points regressor
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

try:
    from xgboost import XGBClassifier, XGBRegressor
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "xgboost is required to train Chunk 9 models. Install dependencies from requirements.txt first."
    ) from exc

# Ensure repo root import path when running as `python ml/train_model.py`.
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import SessionLocal
from ml import config
from ml.feature_engineering import FeatureEngineer


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def _default_version() -> str:
    return f"{config.MODEL_VERSION_PREFIX}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def _resolve_tscv(n_samples: int, desired_splits: int) -> Optional[TimeSeriesSplit]:
    if n_samples < 8:
        return None
    n_splits = min(desired_splits, n_samples - 1)
    if n_splits < 2:
        return None
    return TimeSeriesSplit(n_splits=n_splits)


def _prepare_features(
    df: pd.DataFrame,
    candidate_features: Sequence[str],
    drop_columns: Sequence[str],
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    available = [c for c in candidate_features if c in df.columns]
    if not available:
        available = [c for c in df.columns if c not in drop_columns]

    X = df[available].copy()

    bool_cols = list(X.select_dtypes(include=["bool"]).columns)
    for col in bool_cols:
        X[col] = X[col].astype(int)

    obj_cols = list(X.select_dtypes(include=["object", "category"]).columns)
    for col in obj_cols:
        X[col] = X[col].fillna("unknown").astype(str)

    if obj_cols:
        X = pd.get_dummies(X, columns=obj_cols, dummy_na=True)

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    medians = X.median(numeric_only=True)
    X = X.fillna(medians)
    X = X.fillna(0.0)

    return X, list(X.columns), available


def _prune_zero_importance_features(
    model: Any,
    X: pd.DataFrame,
    feature_cols: List[str],
) -> Tuple[pd.DataFrame, List[str], int]:
    """Drop features with zero importance. Returns pruned X, pruned feature list, count pruned."""
    if not hasattr(model, "feature_importances_"):
        return X, feature_cols, 0

    importances = np.asarray(model.feature_importances_, dtype=float)
    if len(importances) != len(feature_cols):
        return X, feature_cols, 0

    keep_mask = importances > 0
    pruned_count = int((~keep_mask).sum())

    if pruned_count == 0:
        return X, feature_cols, 0

    kept_cols = [c for c, keep in zip(feature_cols, keep_mask) if keep]
    return X[kept_cols], kept_cols, pruned_count


# ---------------------------------------------------------------------------
# CV metrics helpers
# ---------------------------------------------------------------------------

def _classifier_cv_metrics(
    X: pd.DataFrame,
    y: pd.Series,
    sample_weight: Optional[np.ndarray],
    params: Dict[str, Any],
    desired_splits: int,
) -> Dict[str, Any]:
    splitter = _resolve_tscv(len(X), desired_splits)
    if splitter is None:
        return {"cv_available": False}

    fold_metrics: List[Dict[str, float]] = []
    # Also track Elo baseline per fold.
    elo_fold_metrics: List[Dict[str, float]] = []

    for train_idx, val_idx in splitter.split(X):
        model = XGBClassifier(**params)
        fit_kwargs: Dict[str, Any] = {}
        if sample_weight is not None:
            fit_kwargs["sample_weight"] = sample_weight[train_idx]

        model.fit(X.iloc[train_idx], y.iloc[train_idx], **fit_kwargs)

        # Calibrate with isotonic regression.
        calibrated = CalibratedClassifierCV(model, method="isotonic", cv=3)
        calib_kwargs: Dict[str, Any] = {}
        if sample_weight is not None:
            calib_kwargs["sample_weight"] = sample_weight[train_idx]
        calibrated.fit(X.iloc[train_idx], y.iloc[train_idx], **calib_kwargs)

        probs = calibrated.predict_proba(X.iloc[val_idx])[:, 1]
        preds = (probs >= 0.5).astype(int)

        fold_metrics.append(
            {
                "accuracy": float(accuracy_score(y.iloc[val_idx], preds)),
                "log_loss": float(log_loss(y.iloc[val_idx], probs, labels=[0, 1])),
            }
        )

        # Elo baseline: predict team1 wins if elo_delta > 0.
        if "elo_delta" in X.columns:
            elo_preds = (X.iloc[val_idx]["elo_delta"] > 0).astype(int)
            # Simple Elo probability: sigmoid of elo_delta / 400.
            elo_delta_vals = X.iloc[val_idx]["elo_delta"].values
            elo_probs = 1.0 / (1.0 + 10.0 ** (-elo_delta_vals / 400.0))
            elo_probs = np.clip(elo_probs, 0.001, 0.999)
            elo_fold_metrics.append(
                {
                    "accuracy": float(accuracy_score(y.iloc[val_idx], elo_preds)),
                    "log_loss": float(log_loss(y.iloc[val_idx], elo_probs, labels=[0, 1])),
                }
            )

    result = {
        "cv_available": True,
        "folds": fold_metrics,
        "mean_accuracy": float(np.mean([m["accuracy"] for m in fold_metrics])),
        "mean_log_loss": float(np.mean([m["log_loss"] for m in fold_metrics])),
    }
    if elo_fold_metrics:
        result["elo_baseline"] = {
            "mean_accuracy": float(np.mean([m["accuracy"] for m in elo_fold_metrics])),
            "mean_log_loss": float(np.mean([m["log_loss"] for m in elo_fold_metrics])),
        }
    return result


def _score_regressor_cv_metrics(
    X: pd.DataFrame,
    y: pd.Series,
    sample_weight: Optional[np.ndarray],
    params: Dict[str, Any],
    desired_splits: int,
    innings_label: str = "innings",
) -> Dict[str, Any]:
    """CV metrics for a single-target score regressor (1st or 2nd innings)."""
    splitter = _resolve_tscv(len(X), desired_splits)
    if splitter is None:
        return {"cv_available": False}

    fold_metrics: List[Dict[str, float]] = []
    for train_idx, val_idx in splitter.split(X):
        reg = XGBRegressor(**params)
        fit_kwargs: Dict[str, Any] = {}
        if sample_weight is not None:
            fit_kwargs["sample_weight"] = sample_weight[train_idx]

        reg.fit(X.iloc[train_idx], y.iloc[train_idx], **fit_kwargs)
        preds = reg.predict(X.iloc[val_idx])

        y_true = y.iloc[val_idx].to_numpy()
        mae = mean_absolute_error(y_true, preds)
        rmse = mean_squared_error(y_true, preds) ** 0.5

        # Global mean baseline.
        mean_pred = y.iloc[train_idx].mean()
        baseline_mae = mean_absolute_error(y_true, np.full_like(y_true, mean_pred))
        baseline_rmse = mean_squared_error(y_true, np.full_like(y_true, mean_pred)) ** 0.5

        fold_metrics.append(
            {
                "mae": float(mae),
                "rmse": float(rmse),
                "baseline_mean_mae": float(baseline_mae),
                "baseline_mean_rmse": float(baseline_rmse),
            }
        )

    return {
        "cv_available": True,
        "folds": fold_metrics,
        f"mean_mae": float(np.mean([m["mae"] for m in fold_metrics])),
        f"mean_rmse": float(np.mean([m["rmse"] for m in fold_metrics])),
        "baseline_mean_mae": float(np.mean([m["baseline_mean_mae"] for m in fold_metrics])),
        "baseline_mean_rmse": float(np.mean([m["baseline_mean_rmse"] for m in fold_metrics])),
    }


def _regressor_cv_metrics(
    X: pd.DataFrame,
    y: pd.Series,
    sample_weight: Optional[np.ndarray],
    params: Dict[str, Any],
    desired_splits: int,
) -> Dict[str, Any]:
    splitter = _resolve_tscv(len(X), desired_splits)
    if splitter is None:
        return {"cv_available": False}

    fold_metrics: List[Dict[str, float]] = []
    for train_idx, val_idx in splitter.split(X):
        reg = XGBRegressor(**params)
        fit_kwargs: Dict[str, Any] = {}
        if sample_weight is not None:
            fit_kwargs["sample_weight"] = sample_weight[train_idx]

        reg.fit(X.iloc[train_idx], y.iloc[train_idx], **fit_kwargs)
        preds = reg.predict(X.iloc[val_idx])

        mae = mean_absolute_error(y.iloc[val_idx], preds)
        rmse = mean_squared_error(y.iloc[val_idx], preds) ** 0.5
        fold_metrics.append({"mae": float(mae), "rmse": float(rmse)})

    return {
        "cv_available": True,
        "folds": fold_metrics,
        "mean_mae": float(np.mean([m["mae"] for m in fold_metrics])),
        "mean_rmse": float(np.mean([m["rmse"] for m in fold_metrics])),
    }


def _extract_feature_importance(model: Any) -> Optional[np.ndarray]:
    # Unwrap CalibratedClassifierCV to get the base estimator.
    if isinstance(model, CalibratedClassifierCV):
        # After fitting, calibrated_classifiers_ contains the calibrated estimators.
        # Try to get importances from the base estimator.
        if hasattr(model, "estimator") and hasattr(model.estimator, "feature_importances_"):
            return np.asarray(model.estimator.feature_importances_, dtype=float)
        # Fallback: average across calibrated classifiers.
        importances: List[np.ndarray] = []
        for cc in getattr(model, "calibrated_classifiers_", []):
            base = getattr(cc, "estimator", None) or getattr(cc, "base_estimator", None)
            if base is not None and hasattr(base, "feature_importances_"):
                importances.append(np.asarray(base.feature_importances_, dtype=float))
        if importances:
            return np.mean(np.vstack(importances), axis=0)
        return None

    if hasattr(model, "feature_importances_"):
        return np.asarray(model.feature_importances_, dtype=float)

    return None


def _save_feature_importance(
    model: Any,
    feature_names: Sequence[str],
    output_csv: Path,
    top_k: int = 40,
) -> List[Dict[str, Any]]:
    importances = _extract_feature_importance(model)
    if importances is None or len(importances) != len(feature_names):
        return []

    fi_df = pd.DataFrame({"feature": list(feature_names), "importance": importances})
    fi_df = fi_df.sort_values("importance", ascending=False).reset_index(drop=True)
    fi_df.to_csv(output_csv, index=False)

    top_rows = fi_df.head(top_k).to_dict(orient="records")
    for row in top_rows:
        row["importance"] = float(row["importance"])
    return top_rows


# ---------------------------------------------------------------------------
# Model training functions
# ---------------------------------------------------------------------------

def _get_feature_columns(fast_mode: bool) -> List[str]:
    return list(config.FAST_MODE_FEATURES if fast_mode else config.MATCH_FEATURE_COLUMNS)


def _train_match_winner(
    match_df: pd.DataFrame,
    fast_mode: bool = False,
) -> Tuple[Any, Dict[str, Any], List[str], pd.DataFrame]:
    dataset = match_df.dropna(subset=["winner_label"]).copy()
    if len(dataset) < config.MIN_MATCH_ROWS:
        raise ValueError(
            f"Not enough rows for winner model: {len(dataset)} < {config.MIN_MATCH_ROWS}."
        )

    drop_cols = [
        "match_id",
        "match_date",
        "team1",
        "team2",
        "actual_winner",
        "winner_label",
        "score_1st_actual",
        "score_2nd_actual",
        "sample_weight",
    ]
    feature_cols_config = _get_feature_columns(fast_mode)
    X, feature_cols, source_cols = _prepare_features(dataset, feature_cols_config, drop_cols)
    y = dataset["winner_label"].astype(int)
    weights = dataset["sample_weight"].astype(float).to_numpy()

    # Initial train + feature pruning.
    initial_model = XGBClassifier(**config.MATCH_WINNER_PARAMS)
    initial_model.fit(X, y, sample_weight=weights)

    X_pruned, feature_cols_pruned, pruned_count = _prune_zero_importance_features(
        initial_model, X, feature_cols
    )
    if pruned_count > 0:
        print(f"[train_model] Pruned {pruned_count} zero-importance features from winner model.")
        feature_cols = feature_cols_pruned
        X = X_pruned

    # CV with calibration.
    cv = _classifier_cv_metrics(X, y, weights, config.MATCH_WINNER_PARAMS, config.TIME_SERIES_SPLITS)

    # Final model: XGBClassifier wrapped in isotonic calibration.
    base_model = XGBClassifier(**config.MATCH_WINNER_PARAMS)
    base_model.fit(X, y, sample_weight=weights)
    model = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    model.fit(X, y, sample_weight=weights)

    metadata = {
        "rows": int(len(dataset)),
        "features": int(len(feature_cols)),
        "features_pruned": pruned_count,
        "feature_source_columns": source_cols,
        "cv": cv,
    }
    return model, metadata, feature_cols, dataset


def _train_score_models(
    match_df: pd.DataFrame,
    fast_mode: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Train separate 1st and 2nd innings score models.

    Returns:
        (models_dict, metadata_dict) where models_dict has keys
        'score_1st' and 'score_2nd', each containing {model, feature_columns, cv, ...}.
    """
    dataset = match_df.dropna(subset=["score_1st_actual", "score_2nd_actual"]).copy()
    if len(dataset) < config.MIN_MATCH_ROWS:
        raise ValueError(
            f"Not enough rows for score model: {len(dataset)} < {config.MIN_MATCH_ROWS}."
        )

    drop_cols = [
        "match_id",
        "match_date",
        "team1",
        "team2",
        "actual_winner",
        "winner_label",
        "score_1st_actual",
        "score_2nd_actual",
        "sample_weight",
    ]
    feature_cols_config = _get_feature_columns(fast_mode)
    X, feature_cols, source_cols = _prepare_features(dataset, feature_cols_config, drop_cols)
    weights = dataset["sample_weight"].astype(float).to_numpy()

    results: Dict[str, Any] = {}

    # --- 1st innings model ---
    y_1st = dataset["score_1st_actual"].astype(float)

    initial_1st = XGBRegressor(**config.SCORE_REGRESSOR_PARAMS)
    initial_1st.fit(X, y_1st, sample_weight=weights)
    X_1st, feat_1st, pruned_1st = _prune_zero_importance_features(initial_1st, X, feature_cols)
    if pruned_1st > 0:
        print(f"[train_model] Pruned {pruned_1st} zero-importance features from 1st innings model.")

    cv_1st = _score_regressor_cv_metrics(
        X_1st, y_1st, weights, config.SCORE_REGRESSOR_PARAMS, config.TIME_SERIES_SPLITS,
        innings_label="1st",
    )

    model_1st = XGBRegressor(**config.SCORE_REGRESSOR_PARAMS)
    model_1st.fit(X_1st, y_1st, sample_weight=weights)

    results["score_1st"] = {
        "model": model_1st,
        "feature_columns": feat_1st,
        "source_columns": source_cols,
        "cv": cv_1st,
        "rows": int(len(dataset)),
        "features": int(len(feat_1st)),
        "features_pruned": pruned_1st,
    }

    # --- 2nd innings model: add 1st innings score as input feature ---
    y_2nd = dataset["score_2nd_actual"].astype(float)

    X_2nd = X.copy()
    X_2nd["score_1st_actual_input"] = y_1st.values
    feat_2nd_all = feature_cols + ["score_1st_actual_input"]

    initial_2nd = XGBRegressor(**config.SCORE_REGRESSOR_PARAMS)
    initial_2nd.fit(X_2nd, y_2nd, sample_weight=weights)
    X_2nd_pruned, feat_2nd, pruned_2nd = _prune_zero_importance_features(
        initial_2nd, X_2nd, feat_2nd_all
    )
    if pruned_2nd > 0:
        print(f"[train_model] Pruned {pruned_2nd} zero-importance features from 2nd innings model.")

    cv_2nd = _score_regressor_cv_metrics(
        X_2nd_pruned, y_2nd, weights, config.SCORE_REGRESSOR_PARAMS, config.TIME_SERIES_SPLITS,
        innings_label="2nd",
    )

    model_2nd = XGBRegressor(**config.SCORE_REGRESSOR_PARAMS)
    model_2nd.fit(X_2nd_pruned, y_2nd, sample_weight=weights)

    results["score_2nd"] = {
        "model": model_2nd,
        "feature_columns": feat_2nd,
        "source_columns": source_cols + ["score_1st_actual_input"],
        "cv": cv_2nd,
        "rows": int(len(dataset)),
        "features": int(len(feat_2nd)),
        "features_pruned": pruned_2nd,
    }

    return results, {"dataset": dataset}


def _train_player_model(
    player_df: pd.DataFrame,
) -> Tuple[Any, Dict[str, Any], List[str], pd.DataFrame]:
    dataset = player_df.dropna(subset=["target_player_points"]).copy()
    if len(dataset) < config.MIN_PLAYER_ROWS:
        raise ValueError(
            f"Not enough rows for player model: {len(dataset)} < {config.MIN_PLAYER_ROWS}."
        )

    drop_cols = [
        "match_id",
        "match_date",
        "player",
        "team",
        "team1",
        "team2",
        "competition",
        "target_player_points",
        "sample_weight",
    ]
    X, feature_cols, source_cols = _prepare_features(dataset, config.PLAYER_FEATURE_COLUMNS, drop_cols)
    y = dataset["target_player_points"].astype(float)
    weights = dataset["sample_weight"].astype(float).to_numpy()

    cv = _regressor_cv_metrics(X, y, weights, config.PLAYER_REGRESSOR_PARAMS, config.TIME_SERIES_SPLITS)

    model = XGBRegressor(**config.PLAYER_REGRESSOR_PARAMS)
    model.fit(X, y, sample_weight=weights)

    metadata = {
        "rows": int(len(dataset)),
        "features": int(len(feature_cols)),
        "feature_source_columns": source_cols,
        "cv": cv,
    }
    return model, metadata, feature_cols, dataset


# ---------------------------------------------------------------------------
# Promotion gates
# ---------------------------------------------------------------------------

def _compute_promotion_gates(
    winner_cv: Dict[str, Any],
    score_1st_cv: Dict[str, Any],
    score_2nd_cv: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], int]:
    """Evaluate promotion gates. Returns (gates_list, passes_count)."""
    gates: List[Dict[str, Any]] = []

    # Gate 1: Winner accuracy > Elo accuracy
    model_acc = winner_cv.get("mean_accuracy")
    elo_baseline = winner_cv.get("elo_baseline", {})
    elo_acc = elo_baseline.get("mean_accuracy")
    gates.append({
        "gate": "Winner accuracy > Elo accuracy",
        "model": model_acc,
        "baseline": elo_acc,
        "pass": model_acc is not None and elo_acc is not None and model_acc > elo_acc,
    })

    # Gate 2: Winner log loss < Elo log loss
    model_ll = winner_cv.get("mean_log_loss")
    elo_ll = elo_baseline.get("mean_log_loss")
    gates.append({
        "gate": "Winner log loss < Elo log loss",
        "model": model_ll,
        "baseline": elo_ll,
        "pass": model_ll is not None and elo_ll is not None and model_ll < elo_ll,
    })

    # Gate 3: 1st innings MAE < global mean MAE
    model_mae_1st = score_1st_cv.get("mean_mae")
    baseline_mae_1st = score_1st_cv.get("baseline_mean_mae")
    gates.append({
        "gate": "Score MAE (1st) < global mean MAE",
        "model": model_mae_1st,
        "baseline": baseline_mae_1st,
        "pass": model_mae_1st is not None and baseline_mae_1st is not None and model_mae_1st < baseline_mae_1st,
    })

    # Gate 4: 2nd innings MAE < global mean MAE
    model_mae_2nd = score_2nd_cv.get("mean_mae")
    baseline_mae_2nd = score_2nd_cv.get("baseline_mean_mae")
    gates.append({
        "gate": "Score MAE (2nd) < global mean MAE",
        "model": model_mae_2nd,
        "baseline": baseline_mae_2nd,
        "pass": model_mae_2nd is not None and baseline_mae_2nd is not None and model_mae_2nd < baseline_mae_2nd,
    })

    # Gate 5: 1st innings RMSE < global mean RMSE
    model_rmse_1st = score_1st_cv.get("mean_rmse")
    baseline_rmse_1st = score_1st_cv.get("baseline_mean_rmse")
    gates.append({
        "gate": "Score RMSE (1st) < global mean RMSE",
        "model": model_rmse_1st,
        "baseline": baseline_rmse_1st,
        "pass": model_rmse_1st is not None and baseline_rmse_1st is not None and model_rmse_1st < baseline_rmse_1st,
    })

    # Gate 6: 2nd innings RMSE < global mean RMSE
    model_rmse_2nd = score_2nd_cv.get("mean_rmse")
    baseline_rmse_2nd = score_2nd_cv.get("baseline_mean_rmse")
    gates.append({
        "gate": "Score RMSE (2nd) < global mean RMSE",
        "model": model_rmse_2nd,
        "baseline": baseline_rmse_2nd,
        "pass": model_rmse_2nd is not None and baseline_rmse_2nd is not None and model_rmse_2nd < baseline_rmse_2nd,
    })

    passes = sum(1 for g in gates if g["pass"])
    return gates, passes


def _print_promotion_gates(gates: List[Dict[str, Any]], passes: int, threshold: int) -> None:
    print("\n" + "=" * 72)
    print("PROMOTION GATES")
    print("=" * 72)
    print(f"{'Gate':<42} {'Model':>10} {'Baseline':>10} {'Result':>8}")
    print("-" * 72)
    for g in gates:
        model_val = f"{g['model']:.4f}" if g["model"] is not None else "N/A"
        baseline_val = f"{g['baseline']:.4f}" if g["baseline"] is not None else "N/A"
        result = "PASS" if g["pass"] else "FAIL"
        print(f"{g['gate']:<42} {model_val:>10} {baseline_val:>10} {result:>8}")
    print("-" * 72)
    print(f"Result: {passes}/6 gates passed (threshold: {threshold}/6)")
    if passes >= threshold:
        print(">>> MODEL PROMOTED — artifacts will be saved.")
    else:
        print(">>> MODEL REJECTED — artifacts will NOT be saved (use --force-save to override).")
    print("=" * 72 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _league_slug(league_name: str) -> str:
    """Convert a league name to a filesystem-safe slug."""
    return league_name.lower().replace(" ", "_").replace("'", "")


def _resolve_competitions(competitions: Optional[List[str]]) -> Optional[List[str]]:
    """Resolve competition aliases — includes BOTH original and canonical names.

    Different tables may use different competition names (e.g. matches has
    "Indian Premier League" while delivery_details has "IPL"), so we keep
    all variants to ensure filters work across tables.
    """
    if not competitions:
        return None
    resolved: List[str] = []
    for c in competitions:
        if c not in resolved:
            resolved.append(c)
        canonical = config.LEAGUE_ALIASES.get(c)
        if canonical and canonical not in resolved:
            resolved.append(canonical)
        # Also add reverse lookup: if c is a canonical name, include its aliases.
        for alias, canon in config.LEAGUE_ALIASES.items():
            if canon == c and alias not in resolved:
                resolved.append(alias)
    return resolved


def _train_single_league(
    session: Session,
    competitions: Optional[List[str]],
    model_version: str,
    mode: str,
    fast_mode: bool,
    gate_threshold: int,
    force_save: bool,
    skip_player_model: bool,
    limit_matches: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Train models for a single league (or all competitions if competitions is None).

    Returns a result dict with keys: league, matches, gates, passes, status.
    """
    from sqlalchemy.orm import Session as _Session

    out_dir = output_dir or config.MODEL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    league_label = ", ".join(competitions) if competitions else "all"
    print(f"\n{'='*72}")
    print(f"TRAINING: {league_label}")
    print(f"{'='*72}")

    engineer = FeatureEngineer(session, fast_mode=fast_mode)

    print("[train_model] Building match-level dataset...")
    match_df = engineer.build_match_training_frame(
        limit=limit_matches,
        start_date=start_date,
        end_date=end_date,
        competitions=competitions,
        verbose=True,
    )

    if match_df.empty:
        print(f"[train_model] No match rows for {league_label}. Skipping.")
        return {"league": league_label, "matches": 0, "gates": "N/A", "passes": 0, "status": "SKIPPED (no data)"}

    if len(match_df) < config.MIN_LEAGUE_MATCHES:
        print(f"[train_model] Only {len(match_df)} matches for {league_label} (min: {config.MIN_LEAGUE_MATCHES}). Skipping.")
        return {"league": league_label, "matches": len(match_df), "gates": "N/A", "passes": 0, "status": "SKIPPED (too few)"}

    artifacts: Dict[str, Any] = {
        "model_version": model_version,
        "generated_at_utc": datetime.utcnow().isoformat(),
        "mode": mode,
        "competitions": competitions,
        "match_rows_total": int(len(match_df)),
    }

    # --- Match winner model ---
    print("[train_model] Training match winner model...")
    winner_model, winner_meta, winner_features, _ = _train_match_winner(match_df, fast_mode=fast_mode)
    winner_fi_path = out_dir / f"match_winner_feature_importance_{model_version}.csv"
    winner_top = _save_feature_importance(winner_model, winner_features, winner_fi_path)

    # --- Score models ---
    print("[train_model] Training score models...")
    score_results, _ = _train_score_models(match_df, fast_mode=fast_mode)
    score_1st_info = score_results["score_1st"]
    score_2nd_info = score_results["score_2nd"]

    score_1st_fi_path = out_dir / f"score_1st_feature_importance_{model_version}.csv"
    score_2nd_fi_path = out_dir / f"score_2nd_feature_importance_{model_version}.csv"
    score_1st_top = _save_feature_importance(score_1st_info["model"], score_1st_info["feature_columns"], score_1st_fi_path)
    score_2nd_top = _save_feature_importance(score_2nd_info["model"], score_2nd_info["feature_columns"], score_2nd_fi_path)

    artifacts["match_winner"] = {
        **winner_meta,
        "feature_importance_csv": str(winner_fi_path),
        "top_feature_importance": winner_top,
    }
    artifacts["score_1st_innings"] = {
        "rows": score_1st_info["rows"],
        "features": score_1st_info["features"],
        "features_pruned": score_1st_info["features_pruned"],
        "cv": score_1st_info["cv"],
        "feature_importance_csv": str(score_1st_fi_path),
        "top_feature_importance": score_1st_top,
    }
    artifacts["score_2nd_innings"] = {
        "rows": score_2nd_info["rows"],
        "features": score_2nd_info["features"],
        "features_pruned": score_2nd_info["features_pruned"],
        "cv": score_2nd_info["cv"],
        "feature_importance_csv": str(score_2nd_fi_path),
        "top_feature_importance": score_2nd_top,
    }

    # --- Promotion gates ---
    winner_cv = winner_meta.get("cv", {})
    score_1st_cv = score_1st_info.get("cv", {})
    score_2nd_cv = score_2nd_info.get("cv", {})

    gates, passes = _compute_promotion_gates(winner_cv, score_1st_cv, score_2nd_cv)
    _print_promotion_gates(gates, passes, gate_threshold)

    artifacts["promotion_gates"] = {
        "gates": gates,
        "passes": passes,
        "threshold": gate_threshold,
        "promoted": passes >= gate_threshold or force_save,
    }

    should_save = passes >= gate_threshold or force_save

    if should_save:
        if force_save and passes < gate_threshold:
            print("[train_model] Force-saving despite gate failure.")

        winner_model_path = out_dir / f"match_winner_{model_version}.joblib"
        joblib.dump(
            {"model": winner_model, "feature_columns": winner_features, "version": model_version, "mode": mode},
            winner_model_path,
        )
        artifacts["match_winner"]["artifact"] = str(winner_model_path)

        score_1st_path = out_dir / f"score_1st_innings_{model_version}.joblib"
        joblib.dump(
            {"model": score_1st_info["model"], "feature_columns": score_1st_info["feature_columns"], "version": model_version, "mode": mode},
            score_1st_path,
        )
        artifacts["score_1st_innings"]["artifact"] = str(score_1st_path)

        score_2nd_path = out_dir / f"score_2nd_innings_{model_version}.joblib"
        joblib.dump(
            {"model": score_2nd_info["model"], "feature_columns": score_2nd_info["feature_columns"], "version": model_version, "mode": mode},
            score_2nd_path,
        )
        artifacts["score_2nd_innings"]["artifact"] = str(score_2nd_path)
    else:
        print("[train_model] Model artifacts NOT saved (gates failed).")

    # --- Player model ---
    if not skip_player_model:
        print("[train_model] Building player-level dataset...")
        player_df = engineer.build_player_training_frame(match_df)
        if player_df.empty:
            print("[train_model] Player frame empty. Skipping player model.")
            artifacts["player_performance"] = {"skipped": True, "reason": "no_player_rows"}
        else:
            print("[train_model] Training player performance model...")
            player_model, player_meta, player_features, _ = _train_player_model(player_df)

            if should_save:
                player_model_path = out_dir / f"player_performance_{model_version}.joblib"
                joblib.dump(
                    {"model": player_model, "feature_columns": player_features, "version": model_version},
                    player_model_path,
                )
                player_fi_path = out_dir / f"player_performance_feature_importance_{model_version}.csv"
                player_top = _save_feature_importance(player_model, player_features, player_fi_path)

                artifacts["player_performance"] = {
                    **player_meta,
                    "artifact": str(player_model_path),
                    "feature_importance_csv": str(player_fi_path),
                    "top_feature_importance": player_top,
                }
            else:
                artifacts["player_performance"] = {**player_meta, "saved": False}
    else:
        artifacts["player_performance"] = {"skipped": True, "reason": "flag_skip_player_model"}

    metadata_path = out_dir / f"training_metadata_{model_version}.json"
    with metadata_path.open("w", encoding="utf-8") as fp:
        json.dump(artifacts, fp, indent=2)

    status = "PROMOTED" if should_save else "REJECTED"
    return {
        "league": league_label,
        "matches": int(len(match_df)),
        "gates": f"{passes}/6",
        "passes": passes,
        "status": status,
    }


def _print_league_summary(results: List[Dict[str, Any]]) -> None:
    """Print a summary table of per-league training results."""
    print("\n" + "=" * 72)
    print("PER-LEAGUE TRAINING SUMMARY")
    print("=" * 72)
    print(f"{'League':<35} {'Matches':>8} {'Gates':>8} {'Status':>12}")
    print("-" * 72)
    for r in results:
        print(f"{r['league']:<35} {r['matches']:>8} {str(r['gates']):>8} {r['status']:>12}")
    print("=" * 72)

    promoted = sum(1 for r in results if r["status"] == "PROMOTED")
    total = len(results)
    print(f"\n{promoted}/{total} leagues promoted.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train foresight/hindsight models.")
    parser.add_argument("--version", default=None, help="Model version tag (default: timestamped).")
    parser.add_argument("--limit-matches", type=int, default=None, help="Optional limit for training matches.")
    parser.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD inclusive.")
    parser.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD inclusive.")
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        default="fast",
        help="Feature mode: 'fast' uses lightweight features only, 'full' uses all 174+ features.",
    )
    parser.add_argument(
        "--competitions",
        nargs="+",
        default=None,
        help="Filter to specific competition names (e.g. 'Indian Premier League' 'IPL').",
    )
    parser.add_argument(
        "--league",
        nargs="+",
        default=None,
        help="Alias for --competitions. Filter to specific league names.",
    )
    parser.add_argument(
        "--train-all-leagues",
        action="store_true",
        help="Auto-discover all leagues from cache and train a model per league.",
    )
    parser.add_argument(
        "--skip-player-model",
        action="store_true",
        help="Skip player model training if you only want match-level models.",
    )
    parser.add_argument(
        "--force-save",
        action="store_true",
        help="Save model artifacts even if promotion gates fail.",
    )
    parser.add_argument(
        "--gate-threshold",
        type=int,
        default=None,
        help=f"Number of gates to pass for auto-save (default: {config.PROMOTION_GATE_THRESHOLD}).",
    )
    parser.add_argument(
        "--local-cache",
        type=str,
        default=None,
        help="Path to local SQLite cache file to avoid remote DB latency (e.g. ml/ipl_cache.db).",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Refresh local cache from remote DB before training.",
    )
    args = parser.parse_args()

    # Merge --league into --competitions.
    competitions = args.competitions or args.league
    competitions = _resolve_competitions(competitions)

    fast_mode = args.mode == "fast"
    model_version = args.version or _default_version()
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)
    gate_threshold = args.gate_threshold if args.gate_threshold is not None else config.PROMOTION_GATE_THRESHOLD

    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # --- Refresh cache if requested ---
    if args.refresh_cache and args.local_cache:
        from ml.cache_manager import get_last_refresh, refresh_cache as _refresh_cache
        import time as _time

        last_ts = get_last_refresh(args.local_cache)
        skip_refresh = False
        if last_ts:
            try:
                last_dt = datetime.fromisoformat(last_ts)
                age_hours = (datetime.utcnow() - last_dt).total_seconds() / 3600
                if age_hours < 1.0:
                    print(f"[train_model] Cache refreshed {age_hours:.1f}h ago. Skipping refresh.")
                    skip_refresh = True
            except (ValueError, TypeError):
                pass

        if not skip_refresh:
            print("[train_model] Refreshing cache from remote DB...")
            remote_session = SessionLocal()
            try:
                _refresh_cache(remote_session, args.local_cache)
            finally:
                remote_session.close()

    # --- Create session ---
    if args.local_cache:
        from sqlalchemy import create_engine as _ce
        from sqlalchemy.orm import sessionmaker as _sm
        _local_engine = _ce(f"sqlite:///{args.local_cache}")
        _LocalSession = _sm(autocommit=False, autoflush=False, bind=_local_engine)
        session = _LocalSession()
        print(f"[train_model] Using local cache: {args.local_cache}")
    else:
        session = SessionLocal()

    try:
        if args.train_all_leagues:
            # --- Per-league training loop ---
            from ml.cache_manager import list_leagues as _list_leagues

            cache_path = args.local_cache or "ml/all_cache.db"
            all_leagues = _list_leagues(cache_path)
            if not all_leagues:
                # Fall back to querying session directly.
                rows = session.execute(
                    text(
                        "SELECT DISTINCT competition FROM matches WHERE winner IS NOT NULL AND competition IS NOT NULL ORDER BY competition"
                    )
                ).fetchall()
                all_leagues = [str(r[0]) for r in rows]

            print(f"[train_model] Discovered {len(all_leagues)} leagues: {', '.join(all_leagues)}")

            results: List[Dict[str, Any]] = []
            for league in all_leagues:
                league_dir = config.MODEL_DIR / _league_slug(league)
                result = _train_single_league(
                    session=session,
                    competitions=[league],
                    model_version=model_version,
                    mode=args.mode,
                    fast_mode=fast_mode,
                    gate_threshold=gate_threshold,
                    force_save=args.force_save,
                    skip_player_model=args.skip_player_model,
                    limit_matches=args.limit_matches,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=league_dir,
                )
                results.append(result)

            _print_league_summary(results)

        else:
            # --- Single-league (or all-competition) training ---
            # Determine output directory.
            if competitions and config.MODEL_DIR_STRUCTURE == "per_league":
                # Use the first competition name as the league slug for output dir.
                out_dir = config.MODEL_DIR / _league_slug(competitions[0])
            else:
                out_dir = config.MODEL_DIR

            print(f"[train_model] Mode: {args.mode} | Competitions: {competitions or 'all'}")

            result = _train_single_league(
                session=session,
                competitions=competitions,
                model_version=model_version,
                mode=args.mode,
                fast_mode=fast_mode,
                gate_threshold=gate_threshold,
                force_save=args.force_save,
                skip_player_model=args.skip_player_model,
                limit_matches=args.limit_matches,
                start_date=start_date,
                end_date=end_date,
                output_dir=out_dir,
            )

            print(f"\n[train_model] Training complete. Version: {model_version}")
            print(f"[train_model] Result: {result['status']} ({result['gates']} gates)")

    finally:
        session.close()


if __name__ == "__main__":
    main()
