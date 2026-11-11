"""
Pick your XI for the top 10 T20I sides (XI_BUILDER_PLAN.md stage 3a, signed off 13 Nov 2026 on the India opener mockup).

    build(db, team)  ->  the side's last T20I XI as eleven slots, each with who has had it lately, the contenders
                         (ranked, with the four measures), a case for and against each, and what moved last match.

Slots: the last T20I XI in batting order; 1-2 openers, 3-4 top order, 5-7 middle and finishers, 8-11 by the bowling
each did most in the side's recent T20Is (powerplay pace, middle-overs spin, death pace; else "lower order").
Contenders: anyone who played T20Is for the side since Jan 2025, plus locals in its home leagues with 400+ balls in the
band (batting) or 240+ in the phase (bowling) there. Local = not overseas by services/nationality for that country.
Measures, all T20s since Jan 2025 in the role (T20Is and every league): batting strike rate, boundary %, control %,
balls per dismissal; bowling economy, dot %, false shot %, balls per wicket. 150-ball floor, a small-sample flag under
300. Ranked by strike rate (batting) or economy (bowling). No verdicts: one "for" and one "against", both numbers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

SINCE = date(2025, 1, 1)
FLOOR, SMALL = 150, 300
# Home-league balls a local needs in the band / phase to be a contender: India's as signed off (a 14-game IPL); a
# 10-game league (BBL, Super Smash) can't reach 400 in one role, so the others need less.
LOCAL_MIN = {"India": {"bat": 400, "bowl": 240}}
LOCAL_MIN_DEFAULT = {"bat": 250, "bowl": 180}
SHOW = 9
RECENT = 8

# The top 10 T20I sides and their home leagues (competition names as delivery_details stores them).
TEAMS: Dict[str, List[str]] = {
    "India": ["IPL", "SMAT"],
    "Australia": ["BBL"],
    "England": ["T20 Blast", "Men's Hundred"],
    "South Africa": ["SA20", "CSA Pro20 Cup", "CSA T20 Challenge"],
    "New Zealand": ["Super Smash"],
    "Pakistan": ["PSL", "National T20 Cup"],
    "West Indies": ["CPL"],
    "Sri Lanka": ["LPL", "SLC T20 League"],
    "Afghanistan": ["Shpageeza CL"],
    "Bangladesh": ["BPL", "National Cricket League T20"],
}
BANDS = {"openers": (1, 2), "top": (3, 4), "middle": (5, 7)}
BAND_LABEL = {"openers": "Opener", "top": "No. 3-4", "middle": "No. 5-7"}
BOWL_ROLES = {"powerplay|pace": "Powerplay pace", "middle|spin": "Middle-overs spin", "death|pace": "Death pace"}
BAND_WORDS = {"openers": "as an opener", "top": "at 3-4", "middle": "at 5-7"}
PHASE_WORDS = {"powerplay|pace": "in the powerplay", "middle|spin": "in the middle overs", "death|pace": "at the death"}


def _band(pos: int) -> Optional[str]:
    for k, (a, b) in BANDS.items():
        if a <= pos <= b:
            return k
    return None


def _kind(bowl_kind: Optional[str]) -> str:
    return "spin" if bowl_kind == "spin bowler" else "pace"


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 < n % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _bat_measures(t: Dict[str, float]) -> Dict[str, Optional[float]]:
    b = t["balls"]
    return {"sr": 100 * t["runs"] / b, "bnd": 100 * t["boundaries"] / b,
            "ctl": 100 * t["ctl"] / t["tagged"] if t["tagged"] else None, "bpd": b / t["outs"] if t["outs"] else None}


def _bowl_measures(t: Dict[str, float]) -> Dict[str, Optional[float]]:
    b = t["balls"]
    return {"econ": 6 * t["runs"] / b, "dot": 100 * t["dots"] / b,
            "false": 100 - 100 * t["ctl"] / t["tagged"] if t["tagged"] else None, "bpw": b / t["wkts"] if t["wkts"] else None}


# How each measure reads in a case line, and which way is better.
BAT_SAY = {"sr": ("strike rate {v:.0f} {w}", True), "bnd": ("a boundary off {v:.1f}% of balls {w}", True),
           "ctl": ("in control on {v:.0f}% of balls {w}", True), "bpd": ("out every {v:.1f} balls {w}", True)}
BOWL_SAY = {"econ": ("economy {v:.2f} {w}", False), "dot": ("dots on {v:.0f}% of balls {w}", True),
            "false": ("false shots on {v:.0f}% of balls {w}", True), "bpw": ("a wicket every {v:.1f} balls {w}", False)}


def _cases(rows: List[Dict[str, Any]], say: Dict[str, Any], words: str) -> None:
    """One "for" (his best-ranked measure among the contenders shown) and one "against" (his worst, or a small sample)."""
    n = len(rows)
    for r in rows:
        ranks = {}
        for k, (_t, higher) in say.items():
            vals = sorted([x["m"][k] for x in rows if x["m"][k] is not None], reverse=higher)
            if r["m"][k] is not None:
                ranks[k] = vals.index(r["m"][k]) + 1
        if not ranks:
            continue
        best = min(ranks, key=lambda k: ranks[k])
        worst = max(ranks, key=lambda k: ranks[k])
        line = lambda k: say[k][0].format(v=r["m"][k], w=words)  # noqa: E731
        r["for"] = f"{line(best)}, {'the best' if ranks[best] == 1 else _ordinal(ranks[best])} of {n}"
        r["against"] = (f"{r['balls']} balls in the role since 2025: a small sample" if r["balls"] < SMALL
                        else f"{line(worst)}, {_ordinal(ranks[worst])} of {n}" if ranks[worst] > ranks[best] else "little: he's level on all four")


def build(db, team: str) -> Dict[str, Any]:
    from sqlalchemy import text

    from services.nationality import is_overseas, overseas_years
    from services.query_builder_v2 import run_deliveries_query as q

    home = TEAMS[team]
    t20i = dict(fmt="T20", include_international=True, leagues=[], start_date=SINCE, limit=10000)
    # 1. The side's T20Is since 2025: batting positions and bowling by phase and kind, per match.
    bat = q(db, batting_teams=[team], group_by=["match_id", "batter", "batting_position"], metrics_perspective="batting", **t20i)["data"]
    bowl = q(db, bowling_teams=[team], group_by=["match_id", "bowler", "phase", "bowl_kind"], metrics_perspective="bowling", **t20i)["data"]
    ids = sorted({r["match_id"] for r in bat} | {r["match_id"] for r in bowl}, key=str)
    dates = dict(db.execute(text("SELECT id::text, date FROM matches WHERE id::text = ANY(:i)"), {"i": [str(i) for i in ids]}).fetchall())
    opp = dict(db.execute(text("""SELECT id::text, CASE WHEN team1 = :t THEN team2 ELSE team1 END FROM matches
                                  WHERE id::text = ANY(:i)"""), {"i": [str(i) for i in ids], "t": team}).fetchall())
    order = sorted(ids, key=lambda i: (dates.get(str(i)) or date.min), reverse=True)
    if not order:
        return {"team": team, "slots": [], "note": "No T20Is since 2025"}
    # A match the feed caught mid-game has a partial scorecard (data-fix notes: "feed partial matches"): skip any where
    # the side has under ten overs of batting and bowling in the data, so the XI and "what moved" come from a full one.
    balls_in = Counter()
    for r in bat + bowl:
        balls_in[r["match_id"]] += r.get("balls") or 0
    order = [m for m in order if balls_in[m] >= 60] or order
    last, recent = order[0], order[:RECENT]
    capped = {r["batter"] for r in bat} | {r["bowler"] for r in bowl}
    # Each player's main bowling role across the side's T20Is (most balls).
    role_balls: Dict[str, Counter] = defaultdict(Counter)
    for r in bowl:
        role_balls[r["bowler"]][f"{r['phase']}|{_kind(r.get('bowl_kind'))}"] += r.get("balls") or 0

    def main_role(name):
        c = Counter({k: v for k, v in role_balls[name].items() if k in BOWL_ROLES})
        return c.most_common(1)[0][0] if c else None

    # 2. The last XI in batting order (non-batters after, by their bowling).
    pos_last = {r["batter"]: int(r["batting_position"]) for r in bat if r["match_id"] == last and r.get("batting_position")}
    bowled_last = [r["bowler"] for r in sorted((r for r in bowl if r["match_id"] == last), key=lambda r: -(r.get("balls") or 0))]
    # Those who didn't bat go in by where they usually bat in the side's T20Is (Hardie before Zampa), then the rest.
    usual: Dict[str, List[int]] = defaultdict(list)
    for r in bat:
        if r.get("batting_position"):
            usual[r["batter"]].append(int(r["batting_position"]))
    med = lambda n: sorted(usual[n])[len(usual[n]) // 2] if usual[n] else 12  # noqa: E731
    xi = sorted(pos_last, key=lambda n: pos_last[n]) + sorted([n for n in dict.fromkeys(bowled_last) if n not in pos_last], key=med)
    # Who neither batted nor bowled last time isn't in the ball-by-ball data (a short chase: West Indies batted five).
    # Fill to eleven from the side's most-used players in its last 8 T20Is, each placed by his usual batting position.
    if len(xi) < 11:
        used = Counter()
        for r in bat:
            if r["match_id"] in recent:
                used[r["batter"]] += 1
        for r in bowl:
            if r["match_id"] in recent:
                used[r["bowler"]] += 0.5  # once per phase row: counts less than an innings
        extra = [n for n, _ in used.most_common() if n not in xi][: 11 - len(xi)]
        xi = sorted(xi + extra, key=lambda n: pos_last.get(n, med(n) + 0.5))
    xi = xi[:11]
    # Who's had each batting band lately; each bowling role lately.
    band_recent: Dict[str, Counter] = defaultdict(Counter)
    for r in bat:
        if r["match_id"] in recent and r.get("batting_position") and _band(int(r["batting_position"])):
            band_recent[_band(int(r["batting_position"]))][r["batter"]] += 1
    role_recent: Dict[str, Counter] = defaultdict(Counter)
    seen = set()
    for r in bowl:
        k = f"{r['phase']}|{_kind(r.get('bowl_kind'))}"
        if r["match_id"] in recent and k in BOWL_ROLES and (r["match_id"], r["bowler"], k) not in seen:
            seen.add((r["match_id"], r["bowler"], k))
            role_recent[k][r["bowler"]] += 1

    # 3. Home-league locals with enough balls in a band or role there.
    league = dict(fmt="T20", include_international=False, leagues=home, start_date=SINCE, limit=10000)
    lbat = q(db, group_by=["batter", "batting_position"], metrics_perspective="batting", min_balls=1, **league)["data"]
    lbowl = q(db, group_by=["bowler", "phase", "bowl_kind"], metrics_perspective="bowling", min_balls=1, **league)["data"]
    years = overseas_years(db, team, team == "India")
    local_band: Dict[str, Counter] = defaultdict(Counter)
    for r in lbat:
        b = _band(int(r["batting_position"])) if r.get("batting_position") else None
        if b:
            local_band[b][r["batter"]] += r.get("balls") or 0
    local_role: Dict[str, Counter] = defaultdict(Counter)
    for r in lbowl:
        k = f"{r['phase']}|{_kind(r.get('bowl_kind'))}"
        if k in BOWL_ROLES:
            local_role[k][r["bowler"]] += r.get("balls") or 0
    local = lambda n: not is_overseas(years, n, date.today().year)  # noqa: E731

    # 4. Everyone's numbers in every T20 since 2025, by band and by role.
    pool = set(capped)
    for b in BANDS:
        pool |= {n for n, v in local_band[b].items() if v >= LOCAL_MIN.get(team, LOCAL_MIN_DEFAULT)["bat"] and local(n)}
    for k in BOWL_ROLES:
        pool |= {n for n, v in local_role[k].items() if v >= LOCAL_MIN.get(team, LOCAL_MIN_DEFAULT)["bowl"] and local(n)}
    pool = sorted(pool)
    every = dict(fmt="T20", include_international=False, leagues=[], start_date=SINCE, limit=10000)
    abat = q(db, batters=pool, group_by=["batter", "batting_position"], metrics_perspective="batting", **every)["data"]
    abowl = q(db, bowlers=pool, group_by=["bowler", "phase", "bowl_kind"], metrics_perspective="bowling", **every)["data"]
    tb: Dict[tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in abat:
        b = _band(int(r["batting_position"])) if r.get("batting_position") else None
        if not b:
            continue
        t = tb[(r["batter"], b)]
        for k, src in (("balls", "balls"), ("runs", "runs"), ("outs", "wickets"), ("boundaries", "boundaries"), ("tagged", "control_tagged"), ("inns", "innings_count")):
            t[k] += r.get(src) or 0
        t["ctl"] += (r.get("control_percentage") or 0) * (r.get("control_tagged") or 0) / 100
    tw: Dict[tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in abowl:
        k = f"{r['phase']}|{_kind(r.get('bowl_kind'))}"
        if k not in BOWL_ROLES:
            continue
        t = tw[(r["bowler"], k)]
        for kk, src in (("balls", "balls"), ("runs", "runs"), ("wkts", "wickets"), ("dots", "dots"), ("tagged", "control_tagged")):
            t[kk] += r.get(src) or 0
        t["ctl"] += (r.get("control_percentage") or 0) * (r.get("control_tagged") or 0) / 100

    def contenders(kind: str, key: str, holder: Optional[str]) -> List[Dict[str, Any]]:
        table, meas, say, words = (tb, _bat_measures, BAT_SAY, BAND_WORDS[key]) if kind == "bat" else (tw, _bowl_measures, BOWL_SAY, PHASE_WORDS[key])
        rows = []
        others = set(xi) - {holder}  # in the XI already, in another slot: not a contender for this one
        for (n, k), t in table.items():
            if k != key or t["balls"] < FLOOR or n in others:
                continue
            rows.append({"name": n, "balls": int(t["balls"]), "capped": n in capped, "m": {kk: (round(v, 2) if v is not None else None) for kk, v in meas(t).items()}})
        rows.sort(key=lambda r: -r["m"]["sr"] if kind == "bat" else r["m"]["econ"])
        shown = rows[:SHOW]
        if holder and holder not in {r["name"] for r in shown}:
            shown += [r for r in rows if r["name"] == holder]
        _cases(shown, say, words)
        for r in shown:
            r["small"] = r["balls"] < SMALL
            r["holder"] = r["name"] == holder
        return shown

    # 5. What moved: each XI player's last match.
    last_bat = {r["batter"]: r for r in bat if r["match_id"] == last}
    last_bowl: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in bowl:
        if r["match_id"] == last:
            for k in ("balls", "runs", "wickets"):
                last_bowl[r["bowler"]][k] += r.get(k) or 0

    def moved(name):
        bits = []
        if name in last_bat:
            r = last_bat[name]
            bits.append(f"{int(r['runs'])} off {int(r['balls'])} at No. {int(r['batting_position'])}")
        if name in last_bowl:
            b = last_bowl[name]
            ov = f"{int(b['balls']) // 6}{'.' + str(int(b['balls']) % 6) if int(b['balls']) % 6 else ''}"
            bits.append(f"{int(b['wickets'])} for {int(b['runs'])} in {ov} over{'' if ov == '1' else 's'}")
        return "; ".join(bits) or "didn't bat or bowl"

    slots = []
    for i, name in enumerate(xi):
        pos = i + 1
        band = _band(pos)
        if band:
            slot = {"n": pos, "kind": "bat", "role": band, "label": BAND_LABEL[band],
                    "had": [{"name": n, "times": c} for n, c in band_recent[band].most_common(5)]}
            slot["contenders"] = contenders("bat", band, name)
        else:
            role = main_role(name)
            slot = {"n": pos, "kind": "bowl" if role else "lower", "role": role, "label": BOWL_ROLES.get(role, "Lower order")}
            if role:
                slot["had"] = [{"name": n, "times": c} for n, c in role_recent[role].most_common(5)]
                slot["contenders"] = contenders("bowl", role, name)
        slot.update({"holder": name, "moved": moved(name)})
        slots.append(slot)
    return {"team": team, "as_of": str(dates.get(str(last))), "last_opponent": opp.get(str(last)), "recent": len(recent),
            "home_leagues": home, "slots": slots, "window": "All T20s since Jan 2025, T20Is and every league"}


def page_key(team: str) -> Dict[str, Any]:
    return {"kind": "intl_xi", "v": 1, "team": team, "day": date.today()}


def get_page(db, team: str, wait: bool = False) -> Dict[str, Any]:
    """Cached per side and day; a cold build (30-50 s) runs in the background (services/page_builds: the API answers
    503 and the page asks again), and the nightly warm builds all ten (scripts/warm_intl_xi.py)."""
    from services.page_builds import get_or_build

    return get_or_build(db, page_key(team), lambda d: build(d, team), wait=wait)
