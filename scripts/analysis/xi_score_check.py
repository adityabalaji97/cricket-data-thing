"""
XI_BUILDER_PLAN.md X2: does a squad score say anything about how the season goes?

Every IPL season 2015-26: each team's squad (the players it used that season), scored on its players' IPL numbers in
the three seasons before (at any side), against the season's win rate and whether it made the playoffs
(services/season_ledger.py). Two scores:
  grade    the winners' template (services/squad_grade.py): weighted share of roles at playoff level, and roles at level
  runs     services/squad_review.py: projected runs above average per match from the best XI (two years before, all T20s)
Benchmark: the pre-season Elo rating (as scripts/squad_backtest.py). The template was fitted on 2023-26 seasons, so
2015-22 is the fair test.

    python scripts/analysis/xi_score_check.py [--from 2015]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
logging.disable(logging.INFO)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="since", type=int, default=2015)
    ap.add_argument("--runs", action="store_true", help="also the squad_review score (slow)")
    ap.add_argument("--core", type=int, default=16, help="score each side's N most-used players (0: everyone it used)")
    args = ap.parse_args()

    from scipy.stats import spearmanr
    from sqlalchemy import text

    from database import get_session
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
    from squad_backtest import results, rosters
    from services import season_ledger
    from services.squad_grade import grade, load_template, squad_players

    db = next(get_session())
    comps = ["IPL", "Indian Premier League"]
    tmpl = load_template("IPL")
    led = {str(s["season"]): s for s in season_ledger.ledger(db, "IPL")}
    rows = []
    for year in range(args.since, 2027):
        r = db.execute(text("SELECT MIN(date), MAX(date) FROM matches WHERE competition = ANY(:c) AND EXTRACT(YEAR FROM date) = :y"),
                       {"c": comps, "y": year}).fetchone()
        if not r or not r[0]:
            continue
        start, end = r
        ros, res = rosters(db, comps, start, end), results(db, comps, start, end)
        if args.core:
            # Everyone a side used favours the sides that churned (losing sides try more players, and more players
            # fill more roles): score the core, its N most-used players.
            used = db.execute(text("""
                SELECT mp.team, mp.player, COUNT(*) FROM match_players mp JOIN matches m ON m.id = mp.match_id
                WHERE m.competition = ANY(:c) AND m.date BETWEEN :a AND :b GROUP BY 1, 2"""),
                {"c": comps, "a": start, "b": end}).all()
            by = {}
            for t, pl, n in used:
                by.setdefault(t, []).append((n, pl))
            ros = {t: [pl for _n, pl in sorted(v, reverse=True)[: args.core]] for t, v in by.items()}
        season = led.get(str(year)) or {}
        playoffs = {season_ledger.team_key(t) for t in (season.get("playoff") or [])}
        for team, players in ros.items():
            won, played, elo = res.get(team, (0, 0, None))
            if played < 8:
                continue
            g = grade(squad_players(db, "IPL", players, date(year - 3, 1, 1), start - timedelta(days=1)),
                      tmpl["benchmarks"], tmpl["weights"])
            row = {"year": year, "team": team, "win": won / played, "playoff": season_ledger.team_key(team) in playoffs,
                   "elo": elo, "fit": g["fit"], "at_level": g["at_level"]}
            if args.runs:
                from services.squad_review import review
                row["runs"] = review(db, "IPL", players, start)["score"]
            rows.append(row)
        print(year, len([x for x in rows if x["year"] == year]), "teams", "playoffs known" if playoffs else "NO PLAYOFF DATA")

    def report(label, sub):
        if len(sub) < 10:
            return
        out = [f"{label} (n={len(sub)})"]
        for k in ("fit", "at_level", "elo", "runs"):
            xs = [x for x in sub if x.get(k) is not None]
            if len(xs) < 10:
                continue
            rho = spearmanr([x[k] for x in xs], [x["win"] for x in xs]).correlation
            # Playoff rate in the top third of the score v the bottom third
            xs = sorted(xs, key=lambda x: x[k])
            third = max(1, len(xs) // 3)
            lo = sum(x["playoff"] for x in xs[:third]) / third
            hi = sum(x["playoff"] for x in xs[-third:]) / third
            out.append(f"{k}: rho v win% {rho:+.2f}, playoffs top third {hi:.0%} v bottom third {lo:.0%}")
        print("  " + " | ".join(out))

    # Within each season (the fair test: the template's levels are 2023-26's, so pooling seasons mixes eras): the rank
    # correlation per season, averaged, and how often the side ranked top by the score made the playoffs.
    def within(label, sub, k):
        rhos, hits, n = [], 0, 0
        for y in sorted({x["year"] for x in sub}):
            xs = [x for x in sub if x["year"] == y and x.get(k) is not None]
            if len(xs) < 6 or len({x[k] for x in xs}) < 2:
                continue
            rhos.append(spearmanr([x[k] for x in xs], [x["win"] for x in xs]).correlation)
            top4 = sorted(xs, key=lambda x: -x[k])[:4]
            hits += sum(x["playoff"] for x in top4)
            n += 4
        if rhos:
            print(f"  within-season {label} {k}: mean rho v win% {sum(rhos) / len(rhos):+.2f} over {len(rhos)} seasons; "
                  f"the score's top four made the playoffs {hits}/{n} ({hits / n:.0%}; chance is 4 of 8-10)")

    print()
    for k in ("fit", "at_level", "elo"):
        within("2015-22", [x for x in rows if x["year"] <= 2022], k)
        within("2023-26", [x for x in rows if x["year"] >= 2023], k)
    report("held out 2015-22", [x for x in rows if x["year"] <= 2022])
    report("fitted 2023-26", [x for x in rows if x["year"] >= 2023])
    report("all", rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
