"""
The teams in the piece, as (label, team, start, end) date windows over data/xi_teams.csv, and their XIs averaged
against the IPL's own average in the same seasons (so the impact-player 12 is compared with other 12s).

    python articles/gambhir/regimes.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
IPL = ("Indian Premier League", "IPL")
KKR, LSG, CSK, MI = "Kolkata Knight Riders", "Lucknow Super Giants", "Chennai Super Kings", "Mumbai Indians"

#: (group, label, team, start, end). Dates inclusive.
REGIMES = [
    ("Gambhir", "KKR, captain 2011–17", KKR, "2011-01-01", "2017-12-31"),
    ("Gambhir", "Delhi, captain 2018 (6 games)", None, "2018-01-01", "2018-04-25"),
    ("Gambhir", "LSG, mentor 2022–23", LSG, "2022-01-01", "2023-12-31"),
    ("Gambhir", "KKR, mentor 2024", KKR, "2024-01-01", "2024-12-31"),
    ("Gambhir", "India, coach Jul 2024–", "India", "2024-07-27", "2030-12-31"),
    ("After", "KKR 2018–23", KKR, "2018-01-01", "2023-12-31"),
    ("After", "LSG 2024–26", LSG, "2024-01-01", "2030-12-31"),
    ("After", "KKR 2025–26", KKR, "2025-01-01", "2030-12-31"),
    ("Before", "India under Dravid, Nov 2021–Jun 2024", "India", "2021-11-17", "2024-06-29"),
    ("Others", "CSK under Dhoni 2008–23", CSK, "2008-01-01", "2023-12-31"),
    ("Others", "MI under Rohit 2013–23", MI, "2013-04-24", "2023-12-31"),
    ("Others", "England, Jul 2024–", "England", "2024-07-27", "2030-12-31"),
    ("Others", "Australia, Jul 2024–", "Australia", "2024-07-27", "2030-12-31"),
    ("Others", "South Africa, Jul 2024–", "South Africa", "2024-07-27", "2030-12-31"),
    ("Others", "New Zealand, Jul 2024–", "New Zealand", "2024-07-27", "2030-12-31"),
]
#: CSK in 2022 before Dhoni took the captaincy back from Jadeja.
EXCLUDE = [(CSK, "2022-03-26", "2022-04-30")]
METRICS = ["all_rounders", "bat_options", "bowl_options", "lhb_bat_options", "spec_batters", "spec_bowlers", "players"]


def load() -> pd.DataFrame:
    t = pd.read_csv(HERE / "data" / "xi_teams.csv", parse_dates=["date"])
    t["ipl"] = t["competition"].isin(IPL)
    t["season"] = t["date"].dt.year
    for team, a, b in EXCLUDE:
        t = t[~((t.team == team) & t.date.between(a, b))]
    return t


def delhi_2018(t: pd.DataFrame) -> str:
    names = t[t.ipl & (t.season == 2018) & t.team.str.contains("Delhi")].team.unique()
    return names[0]


def rows(t: pd.DataFrame) -> pd.DataFrame:
    league = t[t.ipl].groupby("season")[METRICS].mean()
    out = []
    for group, label, team, a, b in REGIMES:
        team = team or delhi_2018(t)
        x = t[(t.team == team) & t.date.between(a, b)]
        if team != "India" and team not in ("England", "Australia", "South Africa", "New Zealand"):
            x = x[x.ipl]
        else:
            x = x[x.competition == "T20I"]
        if x.empty:
            continue
        row = {"group": group, "label": label, "matches": len(x), **x[METRICS].mean().round(2).to_dict()}
        if x.ipl.all():  # against the IPL's average in the same seasons, match-weighted
            base = league.loc[x.season].mean()
            row.update({f"{m}_vs_ipl": round(row[m] - base[m], 2) for m in METRICS})
        out.append(row)
    return pd.DataFrame(out)


def extras(t: pd.DataFrame) -> pd.DataFrame:
    """Per regime: left-right share of legal balls at the crease, win %, and what the all-rounders did."""
    data = HERE / "data"
    lr = pd.read_csv(data / "lr_innings.csv", dtype={"match_id": str})
    res = pd.read_csv(data / "results.csv", dtype={"match_id": str}).set_index("match_id")
    pl = pd.read_csv(data / "xi_players.csv", dtype={"match_id": str}, parse_dates=["date"])
    t = t.assign(match_id=t.match_id.astype(str))
    opp = t.groupby("match_id")["team"].apply(list).to_dict()

    def theirs(df, team, col):
        """Rows for `team` where a name may be spelled differently: anything that isn't the opponent's."""
        o = df.match_id.map(lambda m: [x for x in opp.get(m, []) if x != team])
        return df[[v == team or (v not in os_ and pd.notna(v)) for v, os_ in zip(df[col], o)]]

    ipl_ids = set(t[t.ipl].match_id)
    lr_ipl = lr[lr.match_id.isin(ipl_ids)].merge(t[["match_id", "season"]].drop_duplicates(), on="match_id")
    lr_league = lr_ipl.groupby("season")[["mixed", "known"]].sum()
    out = []
    for group, label, team, a, b in REGIMES:
        team = team or delhi_2018(t)
        x = t[(t.team == team) & t.date.between(a, b)]
        x = x[x.ipl] if x.ipl.any() and team != "India" else x[x.competition == "T20I"]
        if x.empty:
            continue
        ids = set(x.match_id)
        l = theirs(lr[lr.match_id.isin(ids)], team, "batting_team")
        r = res.loc[res.index.intersection(list(ids))].reset_index()
        decided = r[r.winner.notna()]
        wins = theirs(decided.rename(columns={"winner": "w"}), team, "w")
        p = pl[pl.match_id.isin(ids) & (pl.team == team)]
        ar = p[p.role == "all-rounder"]
        row = {"label": label, "lr_share": round(100 * l.mixed.sum() / max(l.known.sum(), 1), 1),
               "win_pct": round(100 * len(wins) / max(len(decided), 1), 1), "decided": len(decided),
               "ar_bowled_pct": round(100 * (ar.overs > 0).mean(), 1),
               "ar_share_overs": round(100 * ar.overs.sum() / max(p.overs.sum(), 1), 1),
               "ar_share_runs": round(100 * ar.runs.sum() / max(p.runs.sum(), 1), 1)}
        if x.ipl.all():
            base = lr_league.loc[x.season]
            row["lr_vs_ipl"] = round(row["lr_share"] - 100 * (base.mixed / base.known).mean(), 1)
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    r = rows(load())
    print(r[["group", "label", "matches", "players", "all_rounders", "bat_options", "bowl_options", "lhb_bat_options",
             "spec_batters", "spec_bowlers"]].to_string(index=False))
    print()
    print(r.dropna(subset=["all_rounders_vs_ipl"])[["label", "all_rounders_vs_ipl", "bat_options_vs_ipl",
                                                    "bowl_options_vs_ipl", "lhb_bat_options_vs_ipl"]].to_string(index=False))
    e = extras(load())
    print()
    print(e.to_string(index=False))
    r.merge(e, on="label").to_csv(HERE / "data" / "regimes.csv", index=False)
