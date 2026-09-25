"""
Runs and wickets above average -- Primer section 3.

    RAA = runs off the ball - expected runs          (eq. 5a)
    WAA = expected wickets  - wicket on the ball     (eq. 5b)

Expectations come from gradient-boosted models on the Primer's four game-state features:
balls left, wickets down, par-or-target (the match par in the first innings, the target in the
second) and innings number. As the Primer stresses, the model is an averaging device over game
states, not a forecaster, so it is fit on (and applied to) the whole dataset.

Wides are excluded from training and get no RAA/WAA, as in the Primer. "Runs" is what the ball
added to the team total (team_runs, extras included), the same quantity Impact uses, so the two
are directly comparable; a batter's leg-byes therefore count toward their RAA, a known and small
simplification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

FEATURES = ["balls_before", "wkts_before", "par_or_target", "inns"]
MODEL_VERSION = "v1"


def feature_frame(states: pd.DataFrame) -> pd.DataFrame:
    frame = pd.DataFrame(index=states.index)
    frame["balls_before"] = states["balls_before"].astype(float)
    frame["wkts_before"] = states["wkts_before"].astype(float)
    frame["par_or_target"] = np.where(states["inns"] == 1, states["par"], states["chase_target"]).astype(float)
    frame["inns"] = states["inns"].astype(float)
    return frame


def _training_mask(states: pd.DataFrame) -> pd.Series:
    return (states["wide"].fillna(0) == 0) & states["par"].notna()


def fit_models(states: pd.DataFrame, seed: int = 7) -> Tuple[object, object]:
    from xgboost import XGBClassifier, XGBRegressor

    mask = _training_mask(states)
    X = feature_frame(states[mask])
    common = dict(n_estimators=400, max_depth=8, learning_rate=0.08, subsample=0.9, tree_method="hist", random_state=seed, n_jobs=-1)
    runs_model = XGBRegressor(objective="reg:squarederror", **common)
    runs_model.fit(X, states.loc[mask, "team_runs"].astype(float))
    wkts_model = XGBClassifier(objective="binary:logistic", eval_metric="logloss", **common)
    wkts_model.fit(X, states.loc[mask, "wicket"].astype(int))
    return runs_model, wkts_model


def apply_models(states: pd.DataFrame, runs_model, wkts_model) -> pd.DataFrame:
    mask = _training_mask(states)
    exp_runs = pd.Series(np.nan, index=states.index)
    exp_wkts = pd.Series(np.nan, index=states.index)
    if mask.any():
        X = feature_frame(states[mask])
        exp_runs[mask] = runs_model.predict(X)
        exp_wkts[mask] = wkts_model.predict_proba(X)[:, 1]
    out = pd.DataFrame({"exp_runs": exp_runs, "exp_wkts": exp_wkts}, index=states.index)
    out["raa"] = states["team_runs"].where(mask) - out["exp_runs"]
    out["waa"] = out["exp_wkts"] - states["wicket"].where(mask)
    return out


def save_models(runs_model, wkts_model, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    runs_model.save_model(directory / f"raa_runs_{MODEL_VERSION}.ubj")
    wkts_model.save_model(directory / f"waa_wickets_{MODEL_VERSION}.ubj")


def load_models(directory: Path):
    from xgboost import XGBClassifier, XGBRegressor

    runs_model = XGBRegressor()
    runs_model.load_model(directory / f"raa_runs_{MODEL_VERSION}.ubj")
    wkts_model = XGBClassifier()
    wkts_model.load_model(directory / f"waa_wickets_{MODEL_VERSION}.ubj")
    return runs_model, wkts_model
