#!/usr/bin/env python3
"""
Compute the T20 Primer metrics (par, Impact, RAA/WAA, win probability, WPA, leverage) for men's
T20 and load them into metric_models / match_par / ball_metrics (migration 003).

    # Refit everything from scratch and print the validation summary (no writes):
    python scripts/compute_primer_metrics.py full
    # ...and replace the stored metrics with the result:
    python scripts/compute_primer_metrics.py full --write
    # Nightly: score matches that have no ball_metrics yet with the stored models:
    python scripts/compute_primer_metrics.py incremental --write

`full` fits the DL curve, par shrinkage and the RAA/WAA models, writes the models to
ml/models/primer/ (commit them: incremental runs need them) and, with --write, truncates and
reloads the three tables. `incremental` never refits; it uses the stored version, so historical
numbers do not drift as new matches arrive. Refitting is a deliberate `full` run with a bumped
--version.

Reads use one READ ONLY COPY; writes go through COPY FROM STDIN, never row-by-row UPDATEs of
delivery_details. DATABASE_URL comes from the environment / .env like every other script.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.metrics.ball_metrics import (  # noqa: E402
    WP_EXPONENT,
    calibration,
    impact,
    prepare_states,
    win_prob_and_leverage,
)
from services.metrics.dl_curve import DLParams, fit_dl_standard, r_std, solve_lambda  # noqa: E402
from services.metrics.par_scores import compute_par_scores  # noqa: E402
from services.metrics.raa_waa import apply_models, fit_models, load_models, save_models  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("primer")

FORMAT, GENDER = "T20", "male"
# The Hundred is 100 balls a side: a different game for these curves.
EXCLUDED_COMPETITIONS = ("Men's Hundred",)
MODELS_DIR = ROOT / "ml" / "models" / "primer"
EXPORT_COLUMNS = (
    "id,p_match,inns,over,ball,score,out,wide,noball,inns_runs,inns_wkts,inns_balls,target,"
    "max_balls,year,ground,country,competition,team_bat,bat,bowl,win_prob,winner"
)
BALL_COLUMNS = ["delivery_id", "p_match", "inns", "exp_runs", "exp_wkts", "raa", "waa", "impact",
                "wp_before", "wp_after", "wpa", "leverage", "version"]


def _engine():
    from database import engine

    return engine


def export_deliveries(match_ids=None) -> pd.DataFrame:
    """Men's T20 deliveries (optionally only some matches) via one READ ONLY COPY."""
    where = f"format = '{FORMAT}' AND gender = '{GENDER}'"
    excluded = ", ".join("'" + c.replace("'", "''") + "'" for c in EXCLUDED_COMPETITIONS)
    where += f" AND competition NOT IN ({excluded})"
    if match_ids is not None:
        if not len(match_ids):
            return pd.DataFrame(columns=EXPORT_COLUMNS.split(","))
        ids = ", ".join("'" + str(m).replace("'", "''") + "'" for m in match_ids)
        where += f" AND p_match IN ({ids})"
    raw = _engine().raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        buf = io.StringIO()
        cur.copy_expert(f"COPY (SELECT {EXPORT_COLUMNS} FROM delivery_details WHERE {where}) TO STDOUT WITH CSV HEADER", buf)
        raw.rollback()
    finally:
        raw.close()
    buf.seek(0)
    df = pd.read_csv(buf, low_memory=False, dtype={"p_match": str})
    df["out"] = df["out"].astype(str).str.lower().isin(["true", "t", "1"])
    return df


def first_innings_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per match: bucket keys and the first-innings total if it was a complete innings."""
    allot = np.where(df["max_balls"].fillna(0) > 0, df["max_balls"], 120)
    first = df.assign(allot=allot)[df["inns"] == 1]
    inn = first.groupby("p_match").agg(
        total=("inns_runs", "max"), wk=("inns_wkts", "max"), balls=("inns_balls", "max"), allot=("allot", "max"),
        competition=("competition", "first"), year=("year", "first"), ground=("ground", "first"),
        country=("country", "first"),
    ).reset_index()
    complete = (inn["allot"] == 120) & ((inn["balls"] >= 120) | (inn["wk"] >= 10))
    inn["first_total"] = np.where(complete, inn["total"], np.nan)
    # Matches with no first innings in the data still need a bucket for their par.
    missing = df[~df["p_match"].isin(inn["p_match"])].groupby("p_match").agg(
        competition=("competition", "first"), year=("year", "first"), ground=("ground", "first"),
        country=("country", "first"),
    ).reset_index()
    return pd.concat([inn, missing], ignore_index=True)


def fit_dl(df: pd.DataFrame) -> tuple:
    """Fit the standard curve on runs-to-come cell means from complete full-length first innings."""
    inn = first_innings_table(df)
    complete = inn.dropna(subset=["first_total"])[["p_match", "first_total"]].rename(columns={"first_total": "complete_total"})
    states = prepare_states(df[df["inns"] == 1], pd.DataFrame({"p_match": [], "par": []}), pd.DataFrame({"p_match": [], "lam": []}))
    states = states.merge(complete, on="p_match")
    states["to_come"] = states["complete_total"] - states["runs_before"]
    cells = states.groupby(["balls_before", "wkts_before"]).agg(y=("to_come", "mean"), n=("to_come", "size")).reset_index()
    cells = cells[(cells.balls_before > 0) & (cells.balls_before <= 120) & (cells.wkts_before < 10) & (cells.n >= 20)]
    result = fit_dl_standard(cells.balls_before, cells.wkts_before, cells.y, cells.n)
    return result.params, {"rmse": round(result.rmse, 3), "cells": result.cells, "innings": int(len(complete)),
                           "r_std_120_0": round(float(r_std(120, 0, result.params)), 2)}


def compute(df: pd.DataFrame, params: DLParams, par: pd.DataFrame, runs_model, wkts_model, version: int) -> pd.DataFrame:
    states = prepare_states(df, par, par)
    states["impact"] = impact(states, params)
    states = states.join(win_prob_and_leverage(states, params))
    states = states.join(apply_models(states, runs_model, wkts_model))
    out = states.rename(columns={"id": "delivery_id"})
    out["version"] = version
    return out


def validation_summary(states: pd.DataFrame) -> dict:
    won = (states["winner"] == states["team_bat"]).astype(float)
    decided = states["winner"].notna()
    feed = decided & states["win_prob"].notna() & (states["win_prob"] >= 0)
    no_wide = states["wide"].fillna(0) == 0
    return {
        "balls": int(len(states)),
        "matches": int(states["p_match"].nunique()),
        "wp_model": calibration(states.loc[decided, "wp_before"], won[decided]),
        "wp_model_on_feed_rows": calibration(states.loc[feed, "wp_after"], won[feed]),
        "wp_feed": calibration(states.loc[feed, "win_prob"] / 100.0, won[feed]),
        "mean_raa": round(float(states.loc[no_wide, "raa"].mean()), 5),
        "mean_waa": round(float(states.loc[no_wide, "waa"].mean()), 5),
    }


def _copy_into(table: str, frame: pd.DataFrame, columns: list, cursor) -> None:
    buf = io.StringIO()
    frame[columns].to_csv(buf, index=False, header=False, na_rep="\\N", float_format="%.5g")
    buf.seek(0)
    cursor.copy_expert(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')", buf)


def write_full(params: DLParams, par: pd.DataFrame, balls: pd.DataFrame, validation: dict, version: int) -> None:
    migration = (ROOT / "scripts" / "migrations" / "003_primer_metrics.sql").read_text()
    raw = _engine().raw_connection()
    try:
        cur = raw.cursor()
        cur.execute(migration)
        cur.execute("DELETE FROM metric_models WHERE version = %s AND format = %s AND gender = %s", (version, FORMAT, GENDER))
        cur.execute(
            "INSERT INTO metric_models (version, format, gender, params, validation) VALUES (%s, %s, %s, %s, %s)",
            (version, FORMAT, GENDER, json.dumps({"dl": params.to_dict(), "wp_exponent": WP_EXPONENT,
                                                   "excluded_competitions": list(EXCLUDED_COMPETITIONS)}),
             json.dumps(validation)),
        )
        cur.execute("DELETE FROM match_par WHERE format = %s AND gender = %s", (FORMAT, GENDER))
        par_rows = par.assign(format=FORMAT, gender=GENDER, version=version)
        _copy_into("match_par", par_rows, ["p_match", "format", "gender", "par", "lam", "par_source", "version"], cur)
        # TRUNCATE rather than DELETE: no dead tuples for 2.4M rows, and this table is men's T20
        # only for now. (Add a format column and a per-format delete when ODI metrics arrive.)
        cur.execute("TRUNCATE ball_metrics")
        _copy_into("ball_metrics", balls, BALL_COLUMNS, cur)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def run_full(args) -> None:
    t0 = time.time()
    df = pd.read_parquet(args.cache) if args.cache and Path(args.cache).exists() else export_deliveries()
    if args.cache and not Path(args.cache).exists():
        df.to_parquet(args.cache, index=False)
    log.info("deliveries: %s (%.0fs)", len(df), time.time() - t0)

    params, dl_summary = fit_dl(df)
    log.info("DL fit: %s", dl_summary)
    par = compute_par_scores(first_innings_table(df))
    par["lam"] = solve_lambda(par["par"].values, params)

    states = prepare_states(df, par, par)
    runs_model, wkts_model = fit_models(states)
    save_models(runs_model, wkts_model, MODELS_DIR)
    (MODELS_DIR / f"dl_params_v{args.version}.json").write_text(json.dumps(params.to_dict(), indent=2))

    balls = compute(df, params, par, runs_model, wkts_model, args.version)
    validation = {"dl": dl_summary, **validation_summary(balls)}
    log.info("validation: %s", json.dumps(validation))
    if args.write:
        write_full(params, par, balls, validation, args.version)
        log.info("wrote %s balls, %s match pars (%.0fs)", len(balls), len(par), time.time() - t0)


def run_incremental(args) -> None:
    engine = _engine()
    with engine.connect() as conn:
        from sqlalchemy import text

        stored = conn.execute(text(
            "SELECT params FROM metric_models WHERE format = :f AND gender = :g ORDER BY version DESC LIMIT 1"
        ), {"f": FORMAT, "g": GENDER}).scalar()
        version = conn.execute(text("SELECT max(version) FROM metric_models WHERE format = :f AND gender = :g"),
                               {"f": FORMAT, "g": GENDER}).scalar()
        todo = [r[0] for r in conn.execute(text("""
            SELECT DISTINCT dd.p_match FROM delivery_details dd
            WHERE dd.format = :f AND dd.gender = :g
              AND dd.competition <> ALL(:excluded)
              AND NOT EXISTS (SELECT 1 FROM ball_metrics bm WHERE bm.p_match = dd.p_match)
        """), {"f": FORMAT, "g": GENDER, "excluded": list(EXCLUDED_COMPETITIONS)})]
    if stored is None:
        raise SystemExit("No stored metric model: run `full --write` first.")
    params = DLParams.from_dict(stored["dl"] if isinstance(stored, dict) else json.loads(stored)["dl"])
    log.info("matches without metrics: %s", len(todo))
    if not todo:
        return

    # Par needs the whole bucket history, so recompute it over everything; only the new matches'
    # pars are written -- stored pars for older matches stay fixed for this model version.
    history = export_deliveries()
    par = compute_par_scores(first_innings_table(history))
    par["lam"] = solve_lambda(par["par"].values, params)
    new_par = par[par["p_match"].isin(todo)]

    df = history[history["p_match"].isin(todo)]
    runs_model, wkts_model = load_models(MODELS_DIR)
    balls = compute(df, params, new_par, runs_model, wkts_model, version)
    log.info("scored %s balls in %s matches", len(balls), balls["p_match"].nunique())
    if not args.write:
        return
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        ids = tuple(new_par["p_match"].astype(str))
        cur.execute("DELETE FROM match_par WHERE p_match IN %s", (ids,))
        _copy_into("match_par", new_par.assign(format=FORMAT, gender=GENDER, version=version),
                   ["p_match", "format", "gender", "par", "lam", "par_source", "version"], cur)
        _copy_into("ball_metrics", balls, BALL_COLUMNS, cur)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["full", "incremental"])
    parser.add_argument("--write", action="store_true", help="write to the database (default: compute and report only)")
    parser.add_argument("--version", type=int, default=1, help="model version for a full run")
    parser.add_argument("--cache", help="parquet path to cache the full export between runs")
    args = parser.parse_args()
    (run_full if args.mode == "full" else run_incremental)(args)


if __name__ == "__main__":
    main()
