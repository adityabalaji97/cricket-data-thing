"""
Every men's T20 playing XI, each player classed by what the team could use him for on the day. Read-only against the
database DATABASE_URL points at (production by default, through .env).

A player is a BATTING OPTION if, in his previous 20 men's T20s (any competition), he batted in the top 7 in at least
40% of them, or he had 1,500+ career T20 runs before the match (reputation). He is a BOWLING OPTION if he bowled in at
least 40% of his previous 20, or had 150+ career T20 overs before the match. Both: an all-rounder. Players with fewer
than 5 previous T20s are judged on their first 10 (a debutant has no past, so his first games stand in for it).

Writes articles/gambhir/data/xi_players.csv (one row per player per XI) and xi_teams.csv (one row per team per match).

    python articles/gambhir/build_xi.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
OUT = HERE / "data"

WINDOW, MIN_PRIOR, FIRST = 20, 5, 10
BAT_RATE, BOWL_RATE = 0.40, 0.40
REP_RUNS, REP_OVERS = 1500, 150

#: Spellings with no word in common, which reconcile() can't pair.
EXTRA_ALIASES = {"M Muralitharan": "Muthiah Muralidaran"}

ALIAS = "(SELECT DISTINCT ON (player_name) player_name, alias_name FROM player_aliases ORDER BY player_name, id)"
SQL = {
    "apps": """
        SELECT mp.match_id, m.date, m.competition, mp.team, mp.player, mp.position
        FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE m.gender = 'male' AND m.format = 'T20'""",
    "bat": f"""
        SELECT b.match_id, COALESCE(al.alias_name, b.striker) AS player, MIN(b.batting_position) AS bat_pos,
               SUM(b.runs) AS runs
        FROM batting_stats b JOIN matches m ON m.id = b.match_id LEFT JOIN {ALIAS} al ON al.player_name = b.striker
        WHERE m.gender = 'male' AND m.format = 'T20' GROUP BY 1, 2""",
    "bowl": f"""
        SELECT w.match_id, COALESCE(al.alias_name, w.bowler) AS player, SUM(w.overs) AS overs
        FROM bowling_stats w JOIN matches m ON m.id = w.match_id LEFT JOIN {ALIAS} al ON al.player_name = w.bowler
        WHERE m.gender = 'male' AND m.format = 'T20' GROUP BY 1, 2""",
    "hand": f"""
        SELECT player, hand, SUM(n) AS n FROM (
            SELECT bat AS player, bat_hand AS hand, COUNT(*) AS n FROM delivery_details
            WHERE bat_hand IN ('LHB', 'RHB') GROUP BY 1, 2
            UNION ALL
            SELECT COALESCE(al.alias_name, d.batter), d.striker_batter_type, COUNT(*) FROM deliveries d
            LEFT JOIN {ALIAS} al ON al.player_name = d.batter
            WHERE d.striker_batter_type IN ('LHB', 'RHB') GROUP BY 1, 2) x
        GROUP BY 1, 2""",
}


def load(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """The raw tables, cached in data/raw.pkl (the pull takes minutes)."""
    cache = OUT / "raw.pkl"
    if cache.exists() and not refresh:
        return pd.read_pickle(cache)
    from database import engine

    with engine.connect() as conn:
        d = {k: pd.read_sql(q, conn) for k, q in SQL.items()}
    pd.to_pickle(d, cache)
    return d


def reconcile(apps: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    """Scorecard names the alias table misses ("CV Varun" for Varun Chakravarthy): within one match, a scorecard name
    no XI player has takes the name of the one leftover XI player it shares a word with (only when exactly one does)."""
    xi = apps[["match_id", "player"]]
    left_xi = xi.merge(stats[["match_id", "player"]], how="left", indicator=True).query("_merge == 'left_only'")
    left_sc = (stats.reset_index().merge(xi, how="left", on=["match_id", "player"], indicator=True)
               .query("_merge == 'left_only'").set_index("index"))  # keep stats' own row ids for the rename
    by_match = left_xi.groupby("match_id")["player"].apply(list).to_dict()
    rename = {}
    for i, row in left_sc.iterrows():
        words = {w for w in str(row["player"]).lower().replace(".", " ").split() if len(w) > 2}
        cands = [p for p in by_match.get(row["match_id"], []) if words & {w.lower() for w in str(p).split() if len(w) > 2}]
        if len(cands) == 1:
            rename[i] = cands[0]
    out = stats.copy()
    out.loc[list(rename), "player"] = list(rename.values())
    return out.groupby(["match_id", "player"], as_index=False).agg({c: ("min" if c == "bat_pos" else "sum")
                                                                     for c in stats.columns if c not in ("match_id", "player")})


def hands(h: pd.DataFrame, players) -> dict:
    """Batting hand by name; for an XI name the ball data spells differently ("AC Gilchrist" for Adam Gilchrist), the
    one ball-data name with the same surname whose initials include the XI name's first letter."""
    best = h.sort_values("n", ascending=False).drop_duplicates("player").set_index("player")["hand"].to_dict()
    by_surname: dict = {}
    for name in best:
        parts = str(name).split()
        if len(parts) >= 2:
            by_surname.setdefault(parts[-1].lower(), []).append(parts)
    out = {}
    for p in players:
        if p in best:
            out[p] = best[p]
            continue
        parts = str(p).split()
        if len(parts) < 2:
            continue
        cands = [c for c in by_surname.get(parts[-1].lower(), []) if c[0].isupper() and parts[0][0] in c[0]]
        if len(cands) == 1:
            out[p] = best[" ".join(cands[0])]
    return out


def classify(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    apps = d["apps"].copy()
    apps["date"] = pd.to_datetime(apps["date"])
    fix = lambda df: df.assign(player=df["player"].replace(EXTRA_ALIASES))  # noqa: E731
    bat, bowl = reconcile(apps, fix(d["bat"])), reconcile(apps, fix(d["bowl"]))
    apps = apps.merge(bat, on=["match_id", "player"], how="left").merge(bowl, on=["match_id", "player"], how="left")
    apps["top7"] = (apps["bat_pos"].fillna(99) <= 7).astype(int)
    apps["bowled"] = (apps["overs"].fillna(0) > 0).astype(int)
    apps["runs"] = apps["runs"].fillna(0)
    apps["overs"] = apps["overs"].fillna(0)
    apps = apps.sort_values(["player", "date", "match_id"]).reset_index(drop=True)

    g = apps.groupby("player", sort=False)
    apps["n_prior"] = g.cumcount()
    for col in ("top7", "bowled"):
        apps[f"{col}_prior"] = g[col].transform(lambda s: s.shift(1).rolling(WINDOW, min_periods=1).mean())
        apps[f"{col}_first"] = g[col].transform(lambda s: s.head(FIRST).mean())
    apps["runs_before"] = g["runs"].cumsum() - apps["runs"]
    apps["overs_before"] = g["overs"].cumsum() - apps["overs"]

    young = apps["n_prior"] < MIN_PRIOR
    bat_rate = np.where(young, apps["top7_first"], apps["top7_prior"])
    bowl_rate = np.where(young, apps["bowled_first"], apps["bowled_prior"])
    apps["bat_option"] = (bat_rate >= BAT_RATE) | (apps["runs_before"] >= REP_RUNS)
    apps["bowl_option"] = (bowl_rate >= BOWL_RATE) | (apps["overs_before"] >= REP_OVERS)
    apps["role"] = np.select([apps.bat_option & apps.bowl_option, apps.bat_option, apps.bowl_option],
                             ["all-rounder", "batter", "bowler"], "neither")

    apps["hand"] = apps["player"].map(hands(d["hand"], apps["player"].unique()))
    return apps


def teams(apps: pd.DataFrame) -> pd.DataFrame:
    a = apps.assign(lhb_bat=(apps.bat_option & (apps.hand == "LHB")).astype(int),
                    bat=apps.bat_option.astype(int), bowl=apps.bowl_option.astype(int),
                    ar=(apps.role == "all-rounder").astype(int), sbat=(apps.role == "batter").astype(int),
                    sbowl=(apps.role == "bowler").astype(int), xi=(apps.position <= 11).astype(int))
    return (a.groupby(["match_id", "date", "competition", "team"], as_index=False)
             .agg(players=("player", "size"), xi=("xi", "sum"), bat_options=("bat", "sum"), bowl_options=("bowl", "sum"),
                  all_rounders=("ar", "sum"), spec_batters=("sbat", "sum"), spec_bowlers=("sbowl", "sum"),
                  lhb_bat_options=("lhb_bat", "sum")))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    data = load()
    print({k: len(v) for k, v in data.items()})
    apps = classify(data)
    apps.to_csv(OUT / "xi_players.csv", index=False)
    t = teams(apps)
    t.to_csv(OUT / "xi_teams.csv", index=False)
    print(f"{len(apps):,} player-appearances, {len(t):,} team XIs")
    print(apps["role"].value_counts(normalize=True).round(3).to_dict())
