#!/usr/bin/env python3
"""
Pin the 19-0 game's data (XI_BUILDER_PLAN.md X10) to services/pinned/season_draft_<LEAGUE>.json: every player-season
as a card, every team-season's role profile, each season era-adjusted.

Era adjustment: each role's number is a ratio to that season's league rate for the role (openers' average, the 3-4s'
and 5-7s' strike rate, powerplay pace and middle-overs spin wickets per four overs, death pace economy), so Kohli 2016
and a 2009 opener compare. A team-season's role ratio is its busiest holders' pooled number over the league rate
(services/squad_grade.role_value, the template's rule); a card's is his own.

    python scripts/build_season_draft.py [--league=BBL] [--refresh-overseas]
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


# The leagues the game runs for (13 Nov 2026): home country (overseas = internationals for anyone else), the XI's
# overseas cap, and whether "a league abroad before 2019" counts as overseas evidence (true of Indians, who didn't play
# abroad; not of Australians, who did). "Made the playoffs" is top four in the simulated table for every league.
LEAGUES = {
    "IPL": {"home": "India", "overseas_max": 4, "abroad_signal": True},
    "BBL": {"home": "Australia", "overseas_max": 3, "abroad_signal": False},
    "CPL": {"home": "West Indies", "overseas_max": 4, "abroad_signal": False},
    "PSL": {"home": "Pakistan", "overseas_max": 4, "abroad_signal": False},
}

from services.nationality import (  # noqa: E402  (shared with Pick your XI)
    CARD_WINDOW, FULL_MEMBERS, INDIAN_COMPS, aliases, is_overseas, overseas_years)


def keeper_years(db):
    """({name: [stumping years, one entry per stumping]}, {name: auction WK-Batter years}) (13 Nov 2026). Only the keeper
    stumps, so stumpings in any men's match on the scorecards (under scorecard and display names) find keepers,
    part-time ones included. One stumping can be a stand-in (David Miller, Gurkeerat Singh) and the auction's label
    alone can be wrong (Shahbaz Ahmed, 2020), so is_keeper wants two stumpings, or the label and one."""
    from collections import defaultdict

    from sqlalchemy import text

    stumps, label = defaultdict(list), defaultdict(set)
    alias = aliases(db)
    for name, y, n in db.execute(text("""
        SELECT d.fielder, EXTRACT(YEAR FROM m.date)::int, COUNT(*) FROM deliveries d JOIN matches m ON m.id = d.match_id
        WHERE d.wicket_type = 'stumped' AND d.fielder IS NOT NULL GROUP BY 1, 2""")).fetchall():
        for nm in {name, alias.get(name)} - {None}:
            stumps[nm] += [int(y)] * int(n)
    for name, y in db.execute(text("""
        SELECT p.display_name, a.year FROM auction_lots a JOIN player_identity p ON p.pid = a.pid WHERE a.role = 'WK-Batter'
        UNION SELECT player_name, year FROM auction_lots WHERE role = 'WK-Batter'""")).fetchall():
        label[name].add(int(y))
    return stumps, label


KEEPER_WINDOW = 2


def is_keeper(keepers, name, season):
    """Two stumpings within KEEPER_WINDOW years; or the auction's WK-Batter label and one stumping; or the label in two
    auctions (young keepers with few stumpings: Porel, Rawat); or, for a newcomer, the label in the latest auction for
    that same season (Kartik Sharma 2026). Not the label once on its own (Shahbaz Ahmed, 2020)."""
    stumps, label = keepers
    s = int(str(season)[:4])
    near = sum(1 for y in stumps.get(name, ()) if abs(s - y) <= KEEPER_WINDOW)
    labels = {y for y in label.get(name, ()) if abs(s - y) <= KEEPER_WINDOW + 1}
    latest = max((y for ys in label.values() for y in ys), default=None)
    return bool(near >= 2 or (near >= 1 and labels) or len(labels) >= 2
            or (labels == {s} and s == latest and len(label.get(name, ())) == 1))


def write_version(path=None):
    """src/utils/draftDataVersion.js: a hash of each league's pinned data. The app and the link previews put it in the
    data URL, so a rebuild reaches phones at once (the response is cached for up to a week). 13 Nov 2026."""
    import hashlib

    vs = {}
    for f in sorted((ROOT / "services/pinned").glob("season_draft_*.json")):
        vs[f.stem.replace("season_draft_", "")] = hashlib.sha1(f.read_bytes()).hexdigest()[:10]
    body = ", ".join(f"{k}: '{v}'" for k, v in vs.items())
    (ROOT / "src/utils/draftDataVersion.js").write_text(
        "// Written by scripts/build_season_draft.py: each league's pinned 19-0 data version (a hash). Don't edit.\n"
        f"export default {{ {body} }};\n")
    print(f"data versions {vs}")


def main() -> int:
    league = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--league=")), "IPL").upper()
    cfg = LEAGUES[league]
    path = ROOT / f"services/pinned/season_draft_{league}.json"
    if "--refresh-overseas" in sys.argv:  # just the overseas and keeper flags on the pinned file
        from database import get_session

        data = json.loads(path.read_text())
        db = next(get_session())
        ov, wk = overseas_years(db, cfg["home"], cfg["abroad_signal"]), keeper_years(db)
        before = sum(c["overseas"] for c in data["cards"])
        for c in data["cards"]:
            c["overseas"] = is_overseas(ov, c["name"], c["season"])
            c["wk"] = is_keeper(wk, c["name"], c["season"])
        print(f"keepers: {sum(c['wk'] for c in data['cards'])} cards")
        path.write_text(json.dumps(data, separators=(",", ":")))
        print(f"overseas cards {before} -> {sum(c['overseas'] for c in data['cards'])}")
        write_version(path)
        return 0

    from sqlalchemy import text

    from database import get_session
    from services.squad_grade import ROLES, _slot_rows, main_bat_slot, role_value
    from services.team_roles import bat_slot, league_roles

    db = next(get_session())
    data = league_roles(db, league)
    overseas = overseas_years(db, cfg["home"], cfg["abroad_signal"])
    keepers = keeper_years(db)
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
                    for k in ("balls", "runs", "wickets", "innings_count"):
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
                    ratios[key] = {"r": round(v / rate[key], 4), "balls": int(t["balls"])}  # the ratio scores; cards show bat/bowl
            if ratios:
                bowled = sum(t["balls"] for t in m["bowl"].values())
                # The card's headline numbers (what the player sees; the ratios are what's scored): batting in each band
                # he did enough of (runs, balls, outs, innings), bowling over the whole season (runs, balls, wickets).
                bat = {key: {"runs": int(m["bat"][slot]["runs"]), "balls": int(m["bat"][slot]["balls"]),
                             "outs": int(m["bat"][slot]["wickets"]), "inns": int(m["bat"][slot]["innings_count"])}
                       for key, _l, side, slot, *_r in roles if side == "bat" and key in ratios}
                bowl = None
                if bowled >= 24:
                    bowl = {"runs": int(sum(t["runs"] for t in m["bowl"].values())), "balls": int(bowled),
                            "wkts": int(sum(t["wickets"] for t in m["bowl"].values()))}
                cards.append({"name": name, "season": str(s["season"]), "team": m["teams"][0], "overseas": is_overseas(overseas, name, s["season"]), "wk": is_keeper(keepers, name, s["season"]),
                              "roles": ratios, "bat": bat, "bowl": bowl})
        print(s["season"], len(teams), "teams,", sum(1 for c in cards if c["season"] == str(s["season"])), "cards")
    out = {"league": league, "rules": {"overseas_max": cfg["overseas_max"], "home": cfg["home"]}, "roles": [{"key": r[0], "label": r[1], "measure": r[4], "lower": r[6]} for r in roles],
           "seasons": seasons, "cards": cards}
    path.write_text(json.dumps(out, separators=(",", ":")))
    print(f"{len(cards)} cards, {len(seasons)} seasons -> {path} ({path.stat().st_size // 1024} KB)")
    write_version(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
