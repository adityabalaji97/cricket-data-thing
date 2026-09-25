"""
Par (expected first-innings) scores by nested Bayesian shrinkage -- Primer section 2.

Leagues:  global -> league -> year -> ground
T20Is:    global -> year -> country

At every level the bucket mean is pulled toward its (already shrunk) parent:
    mu_l = w_l * xbar_l + (1 - w_l) * mu_parent            (eq. 3)
    w_l  = n_l / (n_l + k),  k = var_within / var_between   (eq. 4)
where var_within is the variance of innings scores inside the parent and var_between the variance
of the child buckets' raw means. A parent with fewer than two children has no between-bucket
spread to measure, so it borrows the level-wide k (all parents at that depth pooled).

Only complete first innings feed the means (full allotted balls bowled, or all out), because a
rain-cut total is not a first-innings score. Every match still gets a par from its bucket, and a
bucket with no qualifying innings inherits its parent.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

INTERNATIONAL_COMPETITION = "T20I"
LEAGUE_LEVELS = ["competition", "year", "ground"]
INTERNATIONAL_LEVELS = ["year", "country"]


def _k_for(parent_scores: pd.Series, child_means: pd.Series) -> Optional[float]:
    if len(child_means) < 2 or len(parent_scores) < 2:
        return None
    between = float(np.var(child_means, ddof=1))
    within = float(np.var(parent_scores, ddof=1))
    if not np.isfinite(between) or between <= 1e-9:
        return None
    return within / between


def _shrink_levels(innings: pd.DataFrame, levels: List[str], global_mean: float) -> Dict[tuple, float]:
    """Shrunk mean for every bucket key (tuple of level values, any depth)."""
    shrunk: Dict[tuple, float] = {(): global_mean}
    for depth in range(1, len(levels) + 1):
        parent_cols = levels[: depth - 1]
        child_cols = levels[:depth]
        grouped = innings.groupby(child_cols, dropna=False)["total"]
        child_stats = grouped.agg(["mean", "size"]).reset_index()

        # k per parent, with a pooled fallback for parents that have a single child.
        per_parent_k: Dict[tuple, Optional[float]] = {}
        pooled_within, pooled_between = [], []
        parent_groups = innings.groupby(parent_cols, dropna=False) if parent_cols else [((), innings)]
        for parent_key, parent_df in parent_groups:
            parent_key = parent_key if isinstance(parent_key, tuple) else (parent_key,)
            if not parent_cols:
                parent_key = ()
            child_means = parent_df.groupby(levels[depth - 1], dropna=False)["total"].mean()
            k = _k_for(parent_df["total"], child_means)
            per_parent_k[parent_key] = k
            if k is not None:
                pooled_within.append(float(np.var(parent_df["total"], ddof=1)))
                pooled_between.append(float(np.var(child_means, ddof=1)))
        pooled_k = (
            float(np.mean(pooled_within) / np.mean(pooled_between))
            if pooled_between and np.mean(pooled_between) > 1e-9
            else 1.0
        )

        for row in child_stats.itertuples(index=False):
            key = tuple(getattr(row, c) for c in child_cols)
            parent_key = key[:-1]
            k = per_parent_k.get(parent_key) or pooled_k
            n = float(row.size)
            weight = n / (n + k)
            shrunk[key] = weight * float(row.mean) + (1.0 - weight) * shrunk[parent_key]
    return shrunk


def _lookup(shrunk: Dict[tuple, float], key: tuple) -> float:
    """Deepest shrunk mean available for a key (a bucket with no qualifying innings -> parent)."""
    for depth in range(len(key), -1, -1):
        if key[:depth] in shrunk:
            return shrunk[key[:depth]]
    return shrunk[()]


def compute_par_scores(matches: pd.DataFrame) -> pd.DataFrame:
    """
    matches: one row per match with columns
        p_match, competition, year, ground, country, first_total (NaN if not a complete innings)
    Returns p_match, par, par_source ('league' | 'international').
    """
    matches = matches[["p_match", "competition", "year", "ground", "country", "first_total"]].copy()
    complete = matches.dropna(subset=["first_total"]).rename(columns={"first_total": "total"})
    global_mean = float(complete["total"].mean())

    is_intl = matches["competition"] == INTERNATIONAL_COMPETITION
    leagues = complete[complete["competition"] != INTERNATIONAL_COMPETITION]
    intl = complete[complete["competition"] == INTERNATIONAL_COMPETITION]

    league_shrunk = _shrink_levels(leagues, LEAGUE_LEVELS, global_mean) if len(leagues) else {(): global_mean}
    intl_shrunk = _shrink_levels(intl, INTERNATIONAL_LEVELS, global_mean) if len(intl) else {(): global_mean}

    pars = []
    for row, international in zip(matches.itertuples(index=False), is_intl):
        if international:
            pars.append(_lookup(intl_shrunk, (row.year, row.country)))
        else:
            pars.append(_lookup(league_shrunk, (row.competition, row.year, row.ground)))
    return pd.DataFrame({
        "p_match": matches["p_match"].values,
        "par": np.round(np.asarray(pars, dtype=float), 2),
        "par_source": np.where(is_intl, "international", "league"),
    })
