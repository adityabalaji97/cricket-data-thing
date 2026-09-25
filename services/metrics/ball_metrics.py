"""
Per-ball contextual metrics from the Primer: Impact (sec. 5), win probability, WPA (sec. 6) and
leverage (sec. 7). RAA/WAA live in raa_waa.py because they need a fitted baseline model.

Input is one row per delivery from delivery_details. Its running columns are recorded AFTER the
ball (inns_runs, inns_wkts, inns_balls include it). The state before a ball is the previous
ball's recorded state, not "after minus this ball": in ~0.3% of rows (mostly 2015-16) `score`
disagrees with the change in inns_runs, a wicket is flagged without inns_wkts moving, or a rain
revision changes max_balls mid-innings. Chaining the recorded states makes every ball's runs the
actual change in the team total, makes Impact telescope exactly over an innings, and applies a
mid-innings allotment cut between balls instead of charging it to whoever faced the next one:
    balls_before(i) = allotted(i) - inns_balls(i-1),   balls_after(i) = allotted(i) - inns_balls(i)
All values are from the batting side's perspective; bowling figures are the negation.

Wides are kept: they change the score and the chase equation, so skipping them would break the
win-probability path. Consumers that follow the Primer in ignoring wides for player figures
(RAA/WAA, batter Impact) filter them out when aggregating.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from services.metrics.dl_curve import FULL_INNINGS_BALLS, MAX_WICKETS, DLParams, r_pro

WP_EXPONENT = 6  # Primer eq. 12: P = r^n / (1 + r^n), best fit n = 6


def prepare_states(deliveries: pd.DataFrame, par_by_match: pd.DataFrame, lam_by_match: pd.DataFrame) -> pd.DataFrame:
    """Add pre/post-ball state columns. Keeps only innings 1 and 2 (super overs are not modelled)."""
    df = deliveries[deliveries["inns"].isin([1, 2])].copy()
    df = df.merge(par_by_match[["p_match", "par"]], on="p_match", how="left")
    df = df.merge(lam_by_match[["p_match", "lam"]], on="p_match", how="left")
    df["lam"] = df["lam"].fillna(1.0)

    df = df.sort_values(["p_match", "inns", "over", "ball"], kind="mergesort").reset_index(drop=True)
    legal = ((df["wide"].fillna(0) == 0) & (df["noball"].fillna(0) == 0)).astype(int)
    allot = pd.Series(np.where(df["max_balls"].fillna(0) > 0, df["max_balls"], FULL_INNINGS_BALLS), index=df.index)

    grouped = df.groupby(["p_match", "inns"], sort=False)
    prev_runs = grouped["inns_runs"].shift(1).fillna(0)
    prev_wkts = grouped["inns_wkts"].shift(1).fillna(0)
    prev_balls = grouped["inns_balls"].shift(1).fillna(0)

    df["legal"] = legal
    df["wicket"] = df["out"].astype(bool).astype(int)  # the flag, for player figures (RAA/WAA)
    df["allot"] = allot
    df["runs_before"] = prev_runs
    df["wkts_before"] = prev_wkts.clip(upper=MAX_WICKETS)
    df["balls_before"] = (allot - prev_balls).clip(lower=0)
    df["runs_after"] = df["inns_runs"]
    df["wkts_after"] = df["inns_wkts"].clip(upper=MAX_WICKETS)
    df["balls_after"] = (allot - df["inns_balls"]).clip(lower=0)
    df["team_runs"] = df["runs_after"] - df["runs_before"]  # what the ball added to the total

    # Chase target: the recorded one (it carries DLS revisions), else first-innings total + 1.
    first_totals = (
        df[df["inns"] == 1].groupby("p_match")["inns_runs"].max().rename("first_total").reset_index()
    )
    df = df.merge(first_totals, on="p_match", how="left")
    df["chase_target"] = np.where(df["target"].notna() & (df["target"] > 0), df["target"], df["first_total"] + 1)
    return df


def impact(df: pd.DataFrame, params: DLParams) -> np.ndarray:
    """Primer eq. 9: I = s + R_pro(b - 1, w + wkt, lam) - R_pro(b, w, lam)."""
    before = r_pro(df["balls_before"].values, df["wkts_before"].values, df["lam"].values, params)
    after = r_pro(df["balls_after"].values, df["wkts_after"].values, df["lam"].values, params)
    return df["team_runs"].values + after - before


def _pythag(r: np.ndarray, n: float = WP_EXPONENT) -> np.ndarray:
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        rn = np.power(np.clip(r, 0, None), n)
        p = rn / (1.0 + rn)
    return np.where(np.isinf(rn), 1.0, np.nan_to_num(p, nan=0.0))


def win_probability(inns, runs, balls, wkts, lam, allot, chase_target, params: DLParams, n: float = WP_EXPONENT) -> np.ndarray:
    """
    Batting side's win probability at a state (Primer eq. 11-12).
      1st innings: r = (S + R_pro(b, w) + 1) / R_pro(allotted, 0)
      2nd innings: r = R_pro(b, w) / N,  N = runs still needed
    A finished chase is 1 (won), 0 (lost) or 0.5 (tied).
    """
    inns = np.asarray(inns)
    runs = np.asarray(runs, dtype=float)
    balls = np.asarray(balls, dtype=float)
    wkts = np.asarray(wkts, dtype=float)
    lam = np.asarray(lam, dtype=float)
    allot = np.asarray(allot, dtype=float)
    target = np.asarray(chase_target, dtype=float)

    to_come = r_pro(balls, wkts, lam, params)
    full = r_pro(allot, np.zeros_like(allot), lam, params)
    with np.errstate(divide="ignore", invalid="ignore"):
        r_first = (runs + to_come + 1.0) / full
        needed = target - runs
        r_second = np.where(needed > 0, to_come / needed, np.inf)
    p = np.where(inns == 1, _pythag(r_first, n), _pythag(r_second, n))

    # A chase that is over is not a probability any more.
    chase_over = (inns == 2) & ((balls <= 0) | (wkts >= MAX_WICKETS)) & (target - runs > 0)
    tied = chase_over & (target - runs == 1)
    p = np.where(chase_over, 0.0, p)
    p = np.where(tied, 0.5, p)
    p = np.where((inns == 2) & (target - runs <= 0), 1.0, p)
    return p


def win_prob_and_leverage(df: pd.DataFrame, params: DLParams, n: float = WP_EXPONENT) -> pd.DataFrame:
    common = dict(lam=df["lam"].values, allot=df["allot"].values, chase_target=df["chase_target"].values, params=params, n=n)
    inns = df["inns"].values
    wp_before = win_probability(inns, df["runs_before"].values, df["balls_before"].values, df["wkts_before"].values, **common)
    wp_after = win_probability(inns, df["runs_after"].values, df["balls_after"].values, df["wkts_after"].values, **common)

    # Leverage (sec. 7.1): best case (a six off a legal ball) minus worst case (a wicket).
    next_balls = (df["balls_before"].values - 1).clip(min=0)
    p_six = win_probability(inns, df["runs_before"].values + 6, next_balls, df["wkts_before"].values, **common)
    p_wkt = win_probability(
        inns, df["runs_before"].values, next_balls, np.minimum(df["wkts_before"].values + 1, MAX_WICKETS), **common
    )
    return pd.DataFrame({
        "wp_before": wp_before,
        "wp_after": wp_after,
        "wpa": wp_after - wp_before,
        "leverage": p_six - p_wkt,
    }, index=df.index)


def calibration(prob: np.ndarray, outcome: np.ndarray, bins: int = 10) -> dict:
    """Brier score, log loss and expected calibration error of probabilities against 0/1 outcomes."""
    prob = np.clip(np.asarray(prob, dtype=float), 1e-6, 1 - 1e-6)
    outcome = np.asarray(outcome, dtype=float)
    brier = float(np.mean((prob - outcome) ** 2))
    logloss = float(-np.mean(outcome * np.log(prob) + (1 - outcome) * np.log(1 - prob)))
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(prob, edges) - 1, 0, bins - 1)
    ece = 0.0
    for b in range(bins):
        mask = idx == b
        if mask.any():
            ece += mask.mean() * abs(prob[mask].mean() - outcome[mask].mean())
    return {"brier": round(brier, 4), "log_loss": round(logloss, 4), "ece": round(float(ece), 4), "n": int(len(prob))}
