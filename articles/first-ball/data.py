"""
Refresh the first-ball numbers from the query builder (production, read only) into data/*.json, so cards.py rebuilds
the deck from the latest data:

    python articles/first-ball/data.py          # then: prepare.py --write (re-saves the bench pack)

"First ball" = batter_ball_number 1, the first legal ball a batter faces. All men's T20s = leagues [] and
include_international False (the query builder's "everything").
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
SINCE = date(2023, 1, 1)
THREE = ["Abhishek Sharma", "Sanju Samson", "Vaibhav Sooryavanshi"]
KEEP = ("balls", "boundaries", "fours", "sixes", "wickets", "runs", "dots")


def main() -> int:
    from database import get_session
    from services.query_builder_v2 import run_deliveries_query

    db = next(get_session())
    ALL = {"fmt": "T20", "gender": "male", "metrics_perspective": "batting", "leagues": [], "include_international": False}
    first = ["batter_ball_number:eq:1"]

    def q(**kw):
        return run_deliveries_query(db, **{**ALL, **kw}, limit=10000)["data"]

    def slim(rows, *keys):
        return [{**{k: r[k] for k in keys}, **{k: r[k] or 0 for k in KEEP}} for r in rows]

    out = {
        "curve": slim(q(group_by=["batter_ball_number"], dimension_filters=["batter_ball_number:lte:20"]), "batter_ball_number"),
        "trend_all": slim(q(group_by=["year"], dimension_filters=first, start_date=date(2015, 1, 1)), "year"),
        "trend_ipl": slim(q(group_by=["year"], dimension_filters=first, start_date=date(2015, 1, 1), leagues=["IPL"]), "year"),
        "field": slim(q(group_by=["batter"], dimension_filters=first, start_date=SINCE, min_balls=60), "batter"),
        "three": slim(q(group_by=["batter"], dimension_filters=first, start_date=SINCE, batters=THREE), "batter"),
        "as_of": date.today().isoformat(),
    }
    out["curve"] = [r for r in out["curve"] if 1 <= r["batter_ball_number"] <= 20]
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "first_ball.json").write_text(json.dumps(out, indent=1))
    t = {r["batter"]: r for r in out["three"]}
    print(f"field {len(out['field'])} · " + " · ".join(f"{n}: {t[n]['sixes']} sixes, {t[n]['boundaries']} boundaries in "
                                                         f"{t[n]['balls']}" for n in THREE if n in t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
