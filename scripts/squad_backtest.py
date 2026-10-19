"""
Does the squad score (services/squad_review.py) rank teams? Every SA20 and IPL season since 2023: each team's
squad (the players it used that season) scored on the two years before the season began, against the season's
win rate. The pre-season Elo rating is the benchmark to beat.

    python scripts/squad_backtest.py [--league SA20|IPL]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seasons(db, comps):
    """(start, end) per season: matches more than 120 days apart start a new one."""
    from sqlalchemy import text

    days = [r[0] for r in db.execute(text("SELECT DISTINCT date FROM matches WHERE competition = ANY(:c) AND date >= '2023-01-01' "
                                          "ORDER BY date"), {"c": comps})]
    out, start, prev = [], None, None
    for d in days:
        if start is None or (d - prev).days > 120:
            if start:
                out.append((start, prev))
            start = d
        prev = d
    if start:
        out.append((start, prev))
    return out


def rosters(db, comps, start, end):
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT mp.team, mp.player, COUNT(*) FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE m.competition = ANY(:c) AND m.date BETWEEN :a AND :b GROUP BY 1, 2
    """), {"c": comps, "a": start, "b": end}).all()
    out = {}
    for team, player, _n in rows:
        out.setdefault(team, []).append(player)
    return out


def results(db, comps, start, end):
    """{team: (won, played, elo at its first match)}."""
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT date, team1, team2, winner, team1_elo, team2_elo FROM matches
        WHERE competition = ANY(:c) AND date BETWEEN :a AND :b ORDER BY date
    """), {"c": comps, "a": start, "b": end}).all()
    out = {}
    for _d, t1, t2, w, e1, e2 in rows:
        for t, e in ((t1, e1), (t2, e2)):
            won, played, elo = out.get(t, (0, 0, None))
            if w:
                played += 1
                won += 1 if w == t else 0
            out[t] = (won, played, elo if elo is not None else e)
    return out


def local_players(db, league, players, end):
    """Players the data shows playing for the host country or in its domestic T20s: the rest are overseas."""
    from sqlalchemy import text
    from services.squad_review import LEAGUES

    cfg = LEAGUES[league]
    rows = db.execute(text("""
        SELECT DISTINCT p FROM (
            SELECT bat AS p FROM delivery_details WHERE match_date <= :e AND bat = ANY(:ps)
              AND ((competition IN ('T20I', 'ODI') AND team_bat = :h) OR competition = ANY(:dom))
            UNION
            SELECT bowl AS p FROM delivery_details WHERE match_date <= :e AND bowl = ANY(:ps)
              AND ((competition IN ('T20I', 'ODI') AND team_bowl = :h) OR competition = ANY(:dom))
        ) x
    """), {"e": str(end), "ps": players, "h": cfg["home"], "dom": cfg["home_domestic"]}).all()
    return {r[0] for r in rows}


def spearman(a, b):
    from scipy.stats import spearmanr

    r = spearmanr(a, b)
    return float(r.statistic if hasattr(r, "statistic") else r.correlation)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", choices=["SA20", "IPL"], default=None)
    args = ap.parse_args()

    from analysis.hypotheses.common import read_only_session
    from services import squad_review as S

    pooled = []
    with read_only_session() as db:
        for league in ([args.league] if args.league else ["SA20", "IPL"]):
            comps = S.LEAGUES[league]["comps"]
            for start, end in seasons(db, comps):
                ros = rosters(db, comps, start, end)
                res = results(db, comps, start, end)
                everyone = sorted({p for ps in ros.values() for p in ps})
                if not everyone:
                    continue
                values = S.player_values(db, everyone, start)
                slots = S.slot_balls(db, league, start)
                local = local_players(db, league, everyone, end)
                rows = []
                for team, squad in ros.items():
                    if team not in res or not res[team][1]:
                        continue
                    r = S.review(db, league, squad, start, overseas=[p for p in squad if p not in local],
                                 values=values, slots=slots, depth_n=0)
                    won, played, elo = res[team]
                    rows.append((team, r["score"], r["bat"], r["bowl"], won / played, elo))
                rows.sort(key=lambda x: -x[1])
                rho = spearman([x[1] for x in rows], [x[4] for x in rows])
                elos = [x for x in rows if x[5] is not None]
                rho_elo = spearman([x[5] for x in elos], [x[4] for x in elos]) if len(elos) == len(rows) else None
                print(f"\n{league} {start:%b %Y}: squad score v win rate rho {rho:+.2f}"
                      + (f" · pre-season Elo v win rate rho {rho_elo:+.2f}" if rho_elo is not None else ""))
                for team, sc, b, w, wr, elo in rows:
                    print(f"  {team:<32}{sc:+7.1f} (bat {b:+6.1f}, bowl {w:+6.1f})  won {100 * wr:4.0f}%  elo {elo}")
                pooled.append((league, start, rho, rho_elo, len(rows)))
    print("\nSeason by season:")
    for league, start, rho, rho_elo, n in pooled:
        print(f"  {league} {start:%Y-%m}  teams {n:2d}  squad {rho:+.2f}  elo {'' if rho_elo is None else f'{rho_elo:+.2f}'}")
    import statistics

    print(f"Mean rho: squad {statistics.mean(p[2] for p in pooled):+.2f}"
          + (f" · elo {statistics.mean(p[3] for p in pooled if p[3] is not None):+.2f}" if any(p[3] is not None for p in pooled) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
