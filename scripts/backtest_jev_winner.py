"""
Backtest: can Jev pick T20 winners from our preview facts better than our own lean and Elo?

For a seeded sample of completed men's T20s (IPL and T20Is), builds the preview context as it
stood before the match (history windows end the day before; Elo from earlier matches only),
then scores three predictors of "team1 wins":

  elo   1 / (1 + 10^(-(elo1 - elo2) / 400))
  lean  score_preview_lean total mapped through a logistic, slope fitted on the sample
        (flagged: in-sample, so it slightly flatters the lean)
  jev   a Jev Choice between "Team A" and "Team B" over the typed-preview facts, anonymised:
        team and venue names replaced, and player/date facts dropped because they identify the
        teams -- otherwise Jev could simply remember famous results.

Reports accuracy, Brier and log loss per predictor and per season. Jev runs only with --jev and
TYPESAFE_API_KEY set. Read-only against the database; one match at a time, ~30s each (the
preview context is heavy), so 300 matches is a ~2.5h background run.

    python scripts/backtest_jev_winner.py --n 40               # baselines only (harness check)
    python scripts/backtest_jev_winner.py --n 300 --out $S/jev_backtest.jsonl     # contexts, once
    python scripts/backtest_jev_winner.py --rescore $S/jev_backtest.jsonl         # Jev over saved facts
"""
import argparse
import json
import math
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from database import get_session  # noqa: E402
from services import jev_client  # noqa: E402
from services.daily_games import TOP_T20I_TEAMS  # noqa: E402
from services.match_preview import gather_preview_context, score_preview_lean  # noqa: E402
from services.typed_preview import build_candidate_facts  # noqa: E402

# Player and date facts identify the teams; the lean is our own verdict, which Jev must not see.
IDENTIFYING_KINDS = {"edge", "threat", "fantasy", "last_meeting", "lean"}


def sample_matches(db, n, since, seed):
    rows = db.execute(text("""
        SELECT id, date, venue, team1, team2, winner, competition
        FROM matches
        WHERE format = 'T20' AND gender = 'male' AND date >= :since
          AND winner IS NOT NULL AND winner IN (team1, team2)
          AND (competition = 'Indian Premier League'
               OR (competition = 'T20I' AND team1 = ANY(:teams) AND team2 = ANY(:teams)))
        ORDER BY id
    """), {"since": since, "teams": list(TOP_T20I_TEAMS)}).mappings().all()
    rng = random.Random(seed)
    return rng.sample(list(rows), min(n, len(rows)))


def anonymise(text_, team1, team2, venue):
    for name, alias in ((team1, "Team A"), (team2, "Team B"), (venue, "the ground")):
        if name:
            text_ = text_.replace(name, alias)
    return text_


def jev_state(context):
    team1, team2, venue = context["team1"], context["team2"], context.get("venue")
    facts = [f for f in build_candidate_facts(context) if f["kind"] not in IDENTIFYING_KINDS]
    return {
        "match": "Team A vs Team B, men's T20",
        "facts": [anonymise(f["text"], team1, team2, venue) for f in facts],
    }


def jev_probability(state):
    answers = jev_client.ask(state, {
        "winner": {
            "type": "choice",
            "instructions": "Based only on these pre-match facts, which team is more likely to win?",
            "criteria": {"team_a": "Team A wins", "team_b": "Team B wins"},
        }
    }, timeout=10.0)
    probs = ((answers or {}).get("winner") or {}).get("probabilities") or {}
    return probs.get("team_a")


def brier(p, y):
    return (p - y) ** 2


def logloss(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def fit_lean_slope(rows):
    """Slope k for p = 1/(1+e^(-k*score)) minimising log loss on the sample (grid search)."""
    best = (None, float("inf"))
    for k in [i / 100 for i in range(0, 201, 2)]:
        loss = sum(logloss(1 / (1 + math.exp(-k * r["lean_score"])), r["y"]) for r in rows)
        if loss < best[1]:
            best = (k, loss)
    return best[0]


def summarise(rows, key):
    scored = [r for r in rows if r.get(key) is not None]
    if not scored:
        return None
    return {
        "n": len(scored),
        "accuracy": round(sum((r[key] > 0.5) == bool(r["y"]) for r in scored if r[key] != 0.5) / max(1, sum(r[key] != 0.5 for r in scored)), 3),
        "brier": round(sum(brier(r[key], r["y"]) for r in scored) / len(scored), 4),
        "logloss": round(sum(logloss(r[key], r["y"]) for r in scored) / len(scored), 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--since", default="2023-01-01")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--jev", action="store_true")
    parser.add_argument("--out", default=None, help="JSONL of per-match rows")
    parser.add_argument("--rescore", default=None,
                        help="JSONL from an earlier run: ask Jev over its saved facts, no DB work")
    args = parser.parse_args()
    if (args.jev or args.rescore) and not jev_client.enabled():
        sys.exit("Jev needs TYPESAFE_API_KEY")

    if args.rescore:
        rows = [json.loads(line) for line in open(args.rescore)]
        for r in rows:
            r["jev"] = jev_probability(r["jev_state"])
        report(rows, args.out)
        return

    db = next(get_session())
    rows = []
    for i, m in enumerate(sample_matches(db, args.n, args.since, args.seed), 1):
        match_date = m["date"] if isinstance(m["date"], date) else date.fromisoformat(str(m["date"]))
        started = time.monotonic()
        try:
            ctx = gather_preview_context(
                venue=m["venue"], team1_identifier=m["team1"], team2_identifier=m["team2"], db=db,
                start_date=date(match_date.year - 4, 1, 1), end_date=match_date - timedelta(days=1),
                fmt="T20", gender="male", elo_as_of=match_date,
            )
        except Exception as exc:
            db.rollback()
            print(f"[{i}] {m['id']} skipped: {exc!r}", file=sys.stderr)
            continue
        elo = ctx.get("elo") or {}
        e1, e2 = elo.get(ctx["team1"]), elo.get(ctx["team2"])
        row = {
            "match_id": m["id"], "date": str(match_date), "season": match_date.year,
            "competition": m["competition"], "team1": ctx["team1"], "team2": ctx["team2"],
            "y": 1 if m["winner"] == m["team1"] else 0,
            "lean_score": score_preview_lean(ctx).get("score_total", 0),
            "elo": 1 / (1 + 10 ** (-(e1 - e2) / 400)) if e1 and e2 else None,
        }
        row["jev_state"] = jev_state(ctx)
        if args.jev:
            row["jev"] = jev_probability(row["jev_state"])
        row["seconds"] = round(time.monotonic() - started, 1)
        rows.append(row)
        print(f"[{i}/{args.n}] {row['date']} {row['team1']} v {row['team2']}: y={row['y']} lean={row['lean_score']} "
              f"elo={row['elo'] and round(row['elo'], 2)} jev={row.get('jev')} ({row['seconds']}s)", file=sys.stderr)

    report(rows, args.out)


def report(rows, out):
    k = fit_lean_slope(rows)
    for r in rows:
        r["lean"] = 1 / (1 + math.exp(-k * r["lean_score"]))
    if out:
        with open(out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    result = {"sample": len(rows), "lean_slope_in_sample": k, "overall": {}, "by_season": {}}
    for key in ("elo", "lean", "jev"):
        result["overall"][key] = summarise(rows, key)
    for season in sorted({r["season"] for r in rows}):
        subset = [r for r in rows if r["season"] == season]
        result["by_season"][season] = {key: summarise(subset, key) for key in ("elo", "lean", "jev")}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
