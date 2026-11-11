#!/usr/bin/env python3
"""
Pin the Season Draft's data (XI_BUILDER_PLAN.md X10) to services/pinned/season_draft_IPL.json: every IPL player-season
as a card, every team-season's role profile, each season era-adjusted.

Era adjustment: each role's number is a ratio to that season's league rate for the role (openers' average, the 3-4s'
and 5-7s' strike rate, powerplay pace and middle-overs spin wickets per four overs, death pace economy), so Kohli 2016
and a 2009 opener compare. A team-season's role ratio is its busiest holders' pooled number over the league rate
(services/squad_grade.role_value, the template's rule); a card's is his own.

    python scripts/build_season_draft.py
"""
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

CARD_MIN = {"bat": 60, "bowl": 48}   # balls in a role in the season for a card to be dealt for it


def measure(m, t):
    if not t or not t.get("balls"):
        return None
    if m == "average":
        return t["runs"] / t["wickets"] if t.get("wickets") else None
    if m == "strike_rate":
        return 100 * t["runs"] / t["balls"]
    if m == "wickets_per_24":
        return 24 * (t.get("wickets") or 0) / t["balls"]
    return 6 * t["runs"] / t["balls"]


def main() -> int:
    from sqlalchemy import text

    from database import get_session
    from services.squad_grade import ROLES, _slot_rows, main_bat_slot, role_value
    from services.team_roles import bat_slot, league_roles

    db = next(get_session())
    data = league_roles(db, "IPL")
    # Overseas: anyone who has played a men's international for a side other than India.
    overseas = set(db.execute(text("""
        SELECT DISTINCT bat FROM delivery_details WHERE competition IN ('T20I', 'ODI') AND team_bat <> 'India'
        UNION SELECT DISTINCT bowl FROM delivery_details WHERE competition IN ('T20I', 'ODI') AND team_bowl <> 'India'""")).scalars().all())
    roles = [r for r in ROLES if r[2] != "depth"]
    seasons, cards = [], []
    for s in data["seasons"]:
        everyone = [p for ps in s["teams"].values() for p in ps]
        # The league's rate per role this season: everyone's balls in it pooled.
        rate = {}
        for key, _l, side, slot, m, _n, _lo, _f in roles:
            tot = defaultdict(float)
            for p in everyone:
                if side == "bat" and main_bat_slot(p) != slot:
                    continue
                for k, v in _slot_rows(p, side, slot).items():
                    tot[k] += v or 0
            rate[key] = measure(m, tot)
        teams = {}
        for team, players in s["teams"].items():
            prof = {}
            for role in roles:
                v, _h = role_value(players, role, 30)
                prof[role[0]] = round(v / rate[role[0]], 4) if v is not None and rate[role[0]] else None
            teams[team] = prof
        seasons.append({"season": str(s["season"]), "playoff": s.get("playoff") or [], "champion": s.get("champion"),
                        "teams": teams, "rates": {k: round(v, 4) if v else None for k, v in rate.items()}})
        # Cards: one per player per season (his teams pooled), with a ratio for each role he did enough of.
        merged = defaultdict(lambda: {"bat": defaultdict(lambda: defaultdict(float)), "bowl": defaultdict(lambda: defaultdict(float)), "teams": []})
        for team, players in s["teams"].items():
            for p in players:
                m = merged[p["name"]]
                m["teams"].append(team)
                for pos, r in p["bat"].items():
                    for k in ("balls", "runs", "wickets"):
                        m["bat"][bat_slot(int(pos))][k] += r.get(k) or 0
                for slot, r in p["bowl"].items():
                    for k in ("balls", "runs", "wickets"):
                        m["bowl"][slot][k] += r.get(k) or 0
        for name, m in merged.items():
            ratios = {}
            for key, _l, side, slot, meas, _n, lower, _f in roles:
                t = m["bat"].get(slot) if side == "bat" else m["bowl"].get(slot)
                if not t or t["balls"] < CARD_MIN[side]:
                    continue
                v = measure(meas, t)
                if v is not None and rate[key]:
                    ratios[key] = {"r": round(v / rate[key], 4), "v": round(v, 2), "balls": int(t["balls"])}
            if ratios:
                bowled = sum(t["balls"] for t in m["bowl"].values())
                cards.append({"name": name, "season": str(s["season"]), "team": m["teams"][0], "overseas": name in overseas,
                              "roles": ratios, "regular": bowled >= 120})
        print(s["season"], len(teams), "teams,", sum(1 for c in cards if c["season"] == str(s["season"])), "cards")
    out = {"league": "IPL", "roles": [{"key": r[0], "label": r[1], "measure": r[4], "lower": r[6]} for r in roles],
           "seasons": seasons, "cards": cards}
    path = ROOT / "services/pinned/season_draft_IPL.json"
    path.write_text(json.dumps(out, separators=(",", ":")))
    print(f"{len(cards)} cards, {len(seasons)} seasons -> {path} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
