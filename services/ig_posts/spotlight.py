"""
A player spotlight: one post on one player when the news is about them (a recall, a comeback, a debut), from a spec.

    build(db, spec)  ->  {slides, title, verdict, players, fact} or None

Slides: hook; their arc (a measure by phase and year); then the same measure against their team's peers, year by year
(Impact and runs saved, powerplay and death); their record in the series' country by ground; what the series grounds do
for their kind of bowler with the new ball; end. "The deeper cut" goes in as slide 3 when the post is queued
(services/ig_backlog.add_deep_cut).

Everyone is compared on all their T20s (leagues=[] with include_international=False; with True it would be
internationals only): a recalled player has no internationals in the window. Every number comes from the query builder;
code writes every title.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from services.ig_posts.cards import card, fmt

MIN_CELL_BALLS = 30   # a bowler's phase in a year needs this many balls to get a number
PEER_MIN_BALLS = 120  # international balls in the window to count as one of the team's pacers
PEER_MIN_PER_INNINGS = 15  # balls an innings: a frontline bowler, not a batter who bowls two overs
MAX_ROWS = 9          # what the heat table fits
PHASES = [("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death")]
ARC_PHASES = [("powerplay", "Powerplay"), ("death", "Death")]  # a pacer's middle overs are too few to read by year
#: Surnames shared by too many players to name someone by (two Kumars in one table): their first name instead.
COMMON_SURNAMES = {"Kumar", "Singh", "Yadav", "Sharma", "Khan", "Patel", "Ahmed", "Reddy", "Pandya", "Chahar", "Malik",
                   "Iyer", "Ali", "Hasan", "Rahman"}

SPECS: Dict[str, Dict[str, Any]] = {
    "bhuvi": {
        "player": "Bhuvneshwar Kumar", "role": "bowler", "bowl_kind": "pace bowler", "team": "India",
        "years": [2023, 2024, 2025, 2026], "arc_from": 2022, "country": "New Zealand", "fmt": "T20",
        "venues": [("Hagley Oval", ["Hagley Oval, Christchurch"]),
                   ("Wellington", ["Westpac Stadium, Wellington", "Sky Stadium, Wellington", "WestpacTrust Stadium, Wellington"]),
                   ("Eden Park", ["Eden Park, Auckland"]),
                   ("Seddon Park", ["Seddon Park, Hamilton"])],
        "venues_since": 2018,
        "hook": "Bhuvneshwar Kumar is back for India after four years. Is he better than the pacers who replaced him?",
        "kicker": "India v New Zealand T20Is",
        "sub": "Impact and runs saved, phase by phase, year by year",
        "tags": ["#INDvNZ", "#TeamIndia", "#Bhuvi"],
        "key": "spotlight-bhuvneshwar-kumar-2026-10",
    },
    "bhuvi-blr": {
        "type": "venue_matchups", "player": "Bhuvneshwar Kumar", "role": "bowler", "bowl_kind": "pace bowler",
        "team": "India", "opponent": "West Indies", "series_start": date(2026, 10, 1), "since": date(2025, 1, 1),
        "venue": "M Chinnaswamy Stadium", "venue_short": "Chinnaswamy",
        "short_names": {"Gujarat Titans": "GT", "Delhi Capitals": "DC", "Punjab Kings": "PBKS", "Rajasthan Royals": "RR",
                        "Chennai Super Kings": "CSK", "Sunrisers Hyderabad": "SRH", "Lucknow Super Giants": "LSG",
                        "Mumbai Indians": "MI", "Kolkata Knight Riders": "KKR"},
        "hook": "Bhuvneshwar Kumar is back for India at the Chinnaswamy, his IPL home. Pacers get hit there. Does he?",
        "kicker": "India v West Indies · 5th T20I, Bengaluru",
        "sub": "Every spell there, the new ball, and West Indies' top order",
        "tags": ["#INDvWI", "#TeamIndia", "#Bhuvi", "#Chinnaswamy"],
        "method": ("Impact is computed ball by ball (T20 Primer method) on every men's T20, IPL included; matchups "
                   "cover every T20 each batter played."),
        "key": "spotlight-bhuvneshwar-kumar-chinnaswamy-2026-10",
    },
    "shami-odi": {
        "type": "case_odi", "player": "Mohammad Shami", "role": "bowler", "bowl_kind": "pace bowler", "team": "India",
        "since": date(2019, 1, 1), "peers_since": date(2023, 1, 1), "last_game": date(2025, 3, 9), "own_from": date(2025, 1, 1),
        "own_label": "his 7 ODIs in 2025", "series_start": date(2026, 11, 4),
        "venues": [("Eden Park", ["Eden Park, Auckland"]),
                   ("Wellington", ["Westpac Stadium, Wellington", "Sky Stadium, Wellington", "WestpacTrust Stadium, Wellington"]),
                   ("Seddon Park", ["Seddon Park, Hamilton"]),
                   ("Bay Oval", ["Bay Oval, Mount Maunganui"])],
        "hook": "Mohammad Shami last bowled for India in the Champions Trophy final. Should he be in the ODI squad for New Zealand?",
        "kicker": "India in New Zealand ODIs", "sub": "The case, phase by phase, and the doubts",
        "tags": ["#Shami", "#TeamIndia", "#INDvNZ", "#ODI"],
        "method": ("wickets, averages and economy from every ODI ball by ball (overs 1-10, 11-40, 41-50); his Vijay "
                   "Hazare Trophy figures are ESPNcricinfo's."),
        "key": "spotlight-mohammad-shami-odi-2026-10",
        # Not in Cricsheet: Vijay Hazare 2025-26 totals read from ESPNcricinfo's most-wickets page (the user's
        # screenshot, 9 Oct 2026: 7 mat, 362 balls, 8 mdns, 368 runs, 15 wkts).
        "external": {"heading": "From elsewhere · Vijay Hazare Trophy 2025-26",
                     "lines": ["15 wickets in 7 matches for Bengal", "Economy 6.10 · average 24.5 · 8 maidens",
                               "A wicket every 24 balls"],
                     "source": "ESPNcricinfo", "confirmed": True},
    },
    "sooryavanshi-nz": {
        "type": "batter_v_attack", "player": "Vaibhav Sooryavanshi", "role": "batter", "since": date(2025, 1, 1),
        "team": "India", "opponent": "New Zealand", "partner": "Abhishek Sharma",
        "openers": ["Vaibhav Sooryavanshi", "Abhishek Sharma", "Sanju Samson", "Ishan Kishan", "Finn Allen", "Tim Seifert",
                    "Devon Conway"],
        "options": ["Vaibhav Sooryavanshi", "Sanju Samson", "Ishan Kishan"],
        "sides": "India's and New Zealand's", "names": {"Vaibhav Sooryavanshi": "Sooryavanshi", "Ishan Kishan": "Kishan",
                                                         "Abhishek Sharma": "Abhishek", "Sanju Samson": "Samson"},
        "kicker": "India in New Zealand T20Is", "sub": "His runs, the other openers, and the one ball that slows him",
        "tags": ["#NZvIND", "#TeamIndia", "#VaibhavSooryavanshi"],
        "method": "Impact and strike rate in every men's T20 since January 2025 (IPL, T20Is and more).",
        "prompt": "Does he open in Christchurch?",
        "key": "spotlight-sooryavanshi-nz-2026-10",
    },
    "kohli-warner-ipl": {
        "type": "player_compare", "scope": "IPL",
        "players": [{"name": "Virat Kohli", "label": "Kohli", "start": date(2023, 1, 1), "end": date(2026, 12, 31),
                     "leagues": ["IPL"]},
                    {"name": "David Warner", "label": "Warner", "start": date(2015, 1, 1), "end": date(2019, 12, 31),
                     "leagues": ["IPL"]}],
        "kicker": "Kohli 2023-26 or Warner 2015-19?", "sub": "Same numbers, different eras",
        "tags": ["#IPL", "#ViratKohli", "#DavidWarner", "#RCB", "#SRH"],
        "method": ("every IPL ball for each in his window; Impact (runs added to the team's projected total) and WPA "
                   "(win probability added) are judged against the conditions of the day."),
        "prompt": "Who would you pick?",
        "key": "spotlight-kohli-warner-ipl-2026-10",
    },
    "india-openers-nz": {
        "type": "openers_case", "side": "India", "side_word": "India's", "side_poss": "India's", "since": date(2025, 1, 1),
        "candidates": ["Abhishek Sharma", "Vaibhav Sooryavanshi", "Sanju Samson", "Ishan Kishan"],
        "keepers": ["Sanju Samson", "Ishan Kishan"],
        "names": {"Vaibhav Sooryavanshi": "Sooryavanshi", "Ishan Kishan": "Kishan", "Abhishek Sharma": "Abhishek",
                  "Sanju Samson": "Samson"},
        # New Zealand's attack: the new-ball quicks, Santner's left-arm spin, Bracewell's and Phillips's off-spin
        "attack": [{"label": "New-ball pace", "kinds": ["pace bowler"], "powerplay": True,
                    "help": "New-ball pace: overs 1-6"},
                   {"label": "Left-arm spin", "styles": ["SLA"], "who": "Santner", "help": "Left-arm spin (Santner)"},
                   {"label": "Off-spin", "styles": ["OB"], "help": "Off-spin (Bracewell, Phillips)"}],
        "kicker": "India in New Zealand T20Is", "sub": "Four openers, three top-order slots: go big or go home",
        "tags": ["#NZvIND", "#TeamIndia", "#AbhishekSharma", "#VaibhavSooryavanshi", "#SanjuSamson", "#IshanKishan"],
        "method": ("every powerplay innings (overs 1-6) in men's T20s since January 2025, sorted by Impact (runs added to "
                   "the team's projected total): big at +15 or more, costly below 0."),
        "prompt": "Which three would you pick?",
        "key": "spotlight-india-openers-nz-2026-10",
    },
    "nz-india-t20i": {
        "type": "series_preview", "since": date(2018, 1, 1), "form_since": date(2025, 1, 1),
        # One ground under every name it has had: Wellington's stadium went WestpacTrust -> Westpac -> Sky -> Henry
        # (2026). Eden Park's Outer Oval (most Super Smash games in Auckland) and the Basin Reserve are other grounds.
        "grounds": [
            {"label": "Hagley Oval", "names": ["Hagley Oval, Christchurch"]},
            {"label": "Wellington", "names": ["Sky Stadium, Wellington", "Westpac Stadium, Wellington", "Westpac Stadium",
                                              "WestpacTrust Stadium, Wellington", "Henry Stadium, Wellington"]},
            {"label": "Eden Park", "names": ["Eden Park, Auckland"]},
            {"label": "Seddon Park", "names": ["Seddon Park, Hamilton"]},
        ],
        "sides": [
            {"team": "India", "batters": ["Abhishek Sharma", "Sanju Samson", "Ishan Kishan", "Shreyas Iyer", "Tilak Varma",
                                          "Shivam Dube", "Vaibhav Sooryavanshi"],
             "against": ["pace", "left-arm spin", "off-spin"],
             "attack": "pace (Henry, Ferguson, Jamieson, Duffy, Milne), Santner's left-arm spin, Bracewell's off-spin"},
            {"team": "New Zealand", "batters": ["Finn Allen", "Devon Conway", "Tim Seifert", "Mark Chapman", "Daryl Mitchell",
                                                "Glenn Phillips", "Michael Bracewell"],
             "against": ["wrist spin", "left-arm pace", "right-arm pace"],
             "attack": "wrist spin (Kuldeep, Varun), left-arm pace (Arshdeep), right-arm pace (Bhuvneshwar, Mayank)"},
        ],
        "names": {"Shreyas Iyer": "Iyer", "Tilak Varma": "Tilak", "Ishan Kishan": "Kishan", "Vaibhav Sooryavanshi": "Sooryavanshi",
                  "Daryl Mitchell": "Mitchell", "Glenn Phillips": "Phillips"},
        "hook": "Five T20Is, four grounds. What wins in New Zealand?",
        "kicker": "India in New Zealand T20Is", "sub": "The grounds, pace v spin, and how each side's batters meet the other's attack",
        "tags": ["#NZvIND", "#TeamIndia", "#BlackCaps", "#T20I"],
        "method": ("Ground numbers are every men's T20 at each ground since 2018 (Super Smash and T20Is); match-ups are "
                   "Impact per 100 balls in every T20 since 2025."),
        "link": "/venue?venue=Hagley+Oval%2C+Christchurch&team1=New+Zealand&team2=India",
        "prompt": "Who wins the series?",
        "key": "spotlight-nz-india-t20i-preview-2026-10",
    },
    "sky": {
        "type": "case_t20", "player": "Suryakumar Yadav", "display": "SKY", "role": "batter", "team": "India",
        "years": [2022, 2023, 2024, 2025, 2026], "with_from": date(2025, 1, 1), "last_game": date(2026, 3, 8),
        "career_from": 2021, "slump_year": 2025, "rival": "Shreyas Iyer",
        "event": {"label": "2026 T20 World Cup", "start": date(2026, 2, 7), "end": date(2026, 3, 8)},
        "hook": "Lots of fans want SKY back in India's T20I side. Is there a case?",
        "kicker": "#BringBackSKY", "sub": "His career, the slump, Shreyas Iyer's rise and the case, in Impact and win probability",
        "tags": ["#SKY", "#BringBackSKY", "#TeamIndia", "#SuryakumarYadav"],
        "method": ("Impact (runs added to the team's projected total) and win probability added are computed ball by ball "
                   "(T20 Primer method) on every T20I and IPL game."),
        "names": {"Tilak Varma": "Tilak", "Ishan Kishan": "Kishan", "Shreyas Iyer": "Iyer"},
        "teams": {"United States of America": "USA"},
        "prompt": "Should he be back?",
        "key": "spotlight-suryakumar-yadav-case-2026-10",
    },
}


#: Surname particles that belong with the surname: "de Kock", "van der Dussen", "du Plessis", "ul Haq".
PARTICLES = ("de", "du", "van", "von", "der", "den", "ul", "al", "da", "di", "le", "la", "ten")


def short_name(name: str) -> str:
    parts = str(name).split()
    if len(parts) < 2:
        return name
    if parts[-1] in COMMON_SURNAMES:
        return parts[0]
    first = next((i for i, p in enumerate(parts[1:], 1) if p.lower() in PARTICLES), len(parts) - 1)
    return " ".join(parts[first:])


def per_over(row: Dict[str, Any], measure: str) -> Optional[float]:
    """Impact or runs above average per over (bowling view: + is good for the bowler)."""
    if (row.get("balls") or 0) < MIN_CELL_BALLS:
        return None
    v = row.get("impact_per_100" if measure == "impact" else "raa_per_100")
    return None if v is None else 6 * v / 100


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 2000, "metrics_perspective": "bowling"}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def all_t20s(**args) -> Dict[str, Any]:
    """Every men's T20 (leagues, internationals, domestic)."""
    return {"leagues": [], "include_international": False, **args}


def peers(db, spec: Dict[str, Any]) -> List[str]:
    """The team's bowlers of this kind in internationals across the years, most used first (part-timers out)."""
    years = spec["years"]
    rows = _q(db, group_by=["bowler"], bowling_teams=[spec["team"]], bowl_kind=[spec["bowl_kind"]],
              include_international=True, leagues=[], start_date=date(years[0], 1, 1), min_balls=PEER_MIN_BALLS)
    rows = [r for r in rows if (r.get("balls") or 0) >= PEER_MIN_PER_INNINGS * (r.get("innings_count") or 1)]
    rows.sort(key=lambda r: -(r.get("balls") or 0))
    return [r["bowler"] for r in rows if r["bowler"] != spec["player"]][: MAX_ROWS - 1]


def phase_years(db, bowlers: List[str], start: int) -> Dict[Tuple[str, int, str], Dict[str, Any]]:
    """(bowler, year, phase) -> row, every T20 since `start`."""
    rows = _q(db, **all_t20s(), bowlers=bowlers, group_by=["bowler", "year", "phase"], start_date=date(start, 1, 1))
    return {(r["bowler"], int(r["year"]), r["phase"]): r for r in rows}


def _pct(values: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    """Percentile of each value within its column (0..100, higher is better); None stays None."""
    have = sorted(v for v in values.values() if v is not None)
    if len(have) < 2:
        return {k: (None if v is None else 50.0) for k, v in values.items()}
    return {k: (None if v is None else 100 * sum(1 for x in have if x < v) / (len(have) - 1)) for k, v in values.items()}


def heat(table: Dict[str, Dict[str, Optional[float]]], cols: List[str], subject: str, order: List[str]) -> Dict[str, Any]:
    """The scorecard visual's payload: rows x columns, each cell shaded by its percentile in its column."""
    pcts = {c: _pct({name: table[name].get(c) for name in order}) for c in cols}
    leaders = {c: max((n for n in order if table[n].get(c) is not None), key=lambda n: table[n][c], default=None) for c in cols}
    return {
        "metrics": [{"key": c, "label": c, "format": "signed1"} for c in cols],
        "rows": [{"name": n, "short": short_name(n), "values": {c: table[n].get(c) for c in cols},
                  "pct": {c: pcts[c][n] for c in cols}, "leader": [c for c in cols if leaders[c] == n],
                  "highlight": n == subject} for n in order],
    }


def arc_card(spec, data, measure: str = "impact") -> Optional[Dict[str, Any]]:
    """Their measure by phase (rows) and year (columns), from the last year before the recall."""
    p = spec["player"]
    years = [str(y) for y in range(spec["arc_from"], spec["years"][-1] + 1)]
    table = {label: {y: per_over(data[(p, int(y), key)], measure) if (p, int(y), key) in data else None for y in years}
             for key, label in ARC_PHASES}
    order = [label for _, label in ARC_PHASES]
    payload = heat(table, years, "", order)
    # One player across years: shade every cell against the whole table, and no "best that year" rings.
    flat = _pct({f"{r}|{y}": table[r][y] for r in order for y in years})
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["leader"] = []
        r["pct"] = {y: flat[f"{r['name']}|{y}"] for y in years}
    pp = table["Powerplay"]
    first, last = years[0], years[-1]
    who = short_name(p)
    earlier = [v for y, v in pp.items() if y != last and v is not None]
    if pp.get(last) is not None and earlier and pp[last] > max(earlier):
        title = f"{who}'s best new-ball year since {first}: {fmt(pp[last], 'signed1')} Impact an over in the {last} powerplay"
    elif pp.get(last) is not None and pp.get(first) is not None and pp[last] >= pp[first] * 0.6 and pp[last] > 0:
        title = f"{who} is back near his best with the new ball: {fmt(pp[last], 'signed1')} an over in {last}"
    elif pp.get(last) is not None:
        title = f"{who} in the powerplay: {fmt(pp[last], 'signed1')} an over in {last}"
    else:
        return None
    payload["method"] = ("Impact per over: runs taken off the batting side's projected total, wickets included "
                         "(+ is good for the bowler). Every T20 he played; – under 30 balls. Brighter is better.")
    return card("arc", "scorecard", title, payload, f"{p} · all T20s {first}-{last}",
                "His Impact per over, by phase and year")


def peer_card(spec, data, bowlers: List[str], phase: str, measure: str) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    cols = [str(y) for y in spec["years"]]
    table = {b: {y: per_over(data[(b, int(y), phase)], measure) if (b, int(y), phase) in data else None for y in cols}
             for b in bowlers}
    order = [b for b in bowlers if any(v is not None for v in table[b].values())]
    if p not in order or len(order) < 4:
        return None
    payload = heat(table, cols, p, order)
    last = cols[-1]
    ranked = sorted((b for b in order if table[b].get(last) is not None), key=lambda b: -table[b][last])
    phase_word = dict(PHASES)[phase].lower()
    what = "Impact" if measure == "impact" else "runs saved"
    unit = "per over"
    if p in ranked:
        rank = ranked.index(p) + 1
        ahead = [short_name(b) for b in ranked[: rank - 1]]
        if rank == 1:
            title = f"In {last}, no India pacer beat {short_name(p)}'s {phase_word} {what}: {fmt(table[p][last], 'signed1')} {unit}"
        elif rank <= 3:
            title = (f"In {last}, only {' and '.join(ahead)} beat {short_name(p)}'s {phase_word} {what} "
                     f"({fmt(table[p][last], 'signed1')} {unit})")
        else:
            title = f"In {last}, {short_name(p)} ranked {rank} of {len(ranked)} India pacers for {phase_word} {what}"
    else:
        title = f"{dict(PHASES)[phase]} {what} by year: {short_name(p)} against India's pacers"
    help_ = ("Impact per over (wickets included)" if measure == "impact" else "Runs saved per over against an average bowler") \
        + f", {phase_word}; brighter is better"
    payload["method"] = (f"Every T20 each bowler played (IPL, internationals, domestic); – under {MIN_CELL_BALLS} balls "
                         f"in the {phase_word} that year. Shade: rank within the year. Ring: best that year.")
    return card(f"peers-{phase}-{measure}", "scorecard", title, payload,
                f"India's pacers in T20Is since {cols[0]}, with {short_name(p)} · all T20s", help_)


def nz_record_card(db, spec) -> Optional[Dict[str, Any]]:
    p, country = spec["player"], spec["country"]
    rows = _q(db, group_by=["country", "venue", "year"], bowlers=[p], include_international=False, leagues=[])
    mine = [r for r in rows if r.get("country") == country and (r.get("balls") or 0)]
    if not mine:
        return None
    series = {v for _, names in spec["venues"] for v in names}
    label = {v: lab for lab, names in spec["venues"] for v in names}

    def figures(r):
        overs = f"{r['balls'] // 6}.{r['balls'] % 6}" if r["balls"] % 6 else str(r["balls"] // 6)
        return f"{r['wickets']}/{r['runs']} in {overs} overs ({r['year']})"
    out = [{"name": label.get(r["venue"], r["venue"].split(",")[0]), "value": 6 * r["runs"] / r["balls"],
            "detail": figures(r), "highlight": r["venue"] in series} for r in sorted(mine, key=lambda r: (r["venue"] not in series, r["year"]))]
    balls = sum(r["balls"] for r in mine)
    econ = 6 * sum(r["runs"] for r in mine) / balls
    wkts = sum(r["wickets"] for r in mine)
    played = {label[r["venue"]] for r in mine if r["venue"] in series}
    never = [lab for lab, _ in spec["venues"] if lab not in played]
    title = (f"{short_name(p)} has bowled {balls} balls of T20 cricket in {country}: {wkts} wickets at {econ:.1f} an over")
    payload = {"metric": {"label": "runs an over", "format": "dec1", "signed": False}, "rows": out[:7]}
    out_card = card("nz-record", "metric_bars", title, payload,
                    f"{p} · T20s in {country}" + (f" · never bowled at {', '.join(never)}" if never else ""),
                    "Economy by ground; lime: grounds in this series")
    out_card["small_sample"] = True
    return out_card


def grounds_card(db, spec) -> Optional[Dict[str, Any]]:
    """New-ball pace (powerplay) at each series ground against every men's T20 since `venues_since`."""
    since = date(spec["venues_since"], 1, 1)
    common = all_t20s(bowl_kind=[spec["bowl_kind"]], over_max=5, start_date=since, group_by=["innings"])

    def agg(rows):
        balls = sum(r.get("balls") or 0 for r in rows)
        runs = sum(r.get("runs") or 0 for r in rows)
        wkts = sum(r.get("wickets") or 0 for r in rows)
        return balls, runs, wkts
    fb, fr, fw = agg(_q(db, **common))
    if not fb:
        return None
    field_econ = 6 * fr / fb
    rows, notes = [], []
    for lab, names in spec["venues"]:
        b = r = w = 0
        for v in names:
            vb, vr, vw = agg(_q(db, **common, venue=v))
            b, r, w = b + vb, r + vr, w + vw
        if b < 120:
            continue
        rows.append({"label": lab, "subject": 6 * r / b, "field": field_econ, "highlight": False})
        notes.append((lab, 6 * r / b, b / w if w else None, b))
    if len(rows) < 2:
        return None
    best = min(notes, key=lambda n: n[1])
    for row in rows:
        row["highlight"] = row["label"] == best[0]
    title = (f"New-ball pace goes for {best[1]:.1f} an over at {best[0]}, {field_econ:.1f} across all T20s")
    bpw = ", ".join(f"{lab} {x:.0f}" for lab, _e, x, _b in notes if x)
    payload = {"metric": {"label": f"powerplay runs an over by pace bowlers · balls per wicket: {bpw}", "format": "dec1",
                          "signed": False},
               "series": ["This ground", "All men's T20s"], "rows": rows}
    return card("grounds", "deep_compare", title, payload,
                f"Pace bowlers, overs 1-6, every men's T20 since {spec['venues_since']} · {sum(n[3] for n in notes):,} balls at these grounds",
                f"The series grounds for {spec['bowl_kind'].replace(' bowler', '')} with the new ball")


ACCURACY_MIN_BALLS = 200  # tracked powerplay balls for a row (and 8 rows leave room for the definition line)


def accuracy_card(db, spec, bowlers: List[str]) -> Optional[Dict[str, Any]]:
    """The new ball, ball by ball: how often each pacer lands it on a good length, drops it short, and draws a false shot
    (a ball the batter didn't control), powerplays since the first year. Accuracy is a skill that holds from year to
    year; how many false shots become wickets mostly doesn't, so it isn't here."""
    from datetime import date as _date

    p = spec["player"]
    common = all_t20s(bowlers=bowlers, over_max=5, start_date=_date(spec["years"][0], 1, 1))
    lengths = _q(db, **common, group_by=["bowler", "length"])
    control = _q(db, **common, group_by=["bowler", "control"])
    table: Dict[str, Dict[str, Optional[float]]] = {}
    tracked: Dict[str, int] = {}
    for b in bowlers:
        lr = [r for r in lengths if r["bowler"] == b and r.get("length")]
        cr = [r for r in control if r["bowler"] == b and r.get("control") is not None]
        lt, ct = sum(r["balls"] for r in lr), sum(r["balls"] for r in cr)
        if lt < ACCURACY_MIN_BALLS or ct < ACCURACY_MIN_BALLS:
            continue
        tracked[b] = lt
        table[b] = {
            "Good length": 100 * sum(r["balls"] for r in lr if r["length"] == "GOOD_LENGTH") / lt,
            "Short": 100 * sum(r["balls"] for r in lr if r["length"] == "SHORT") / lt,
            "False shots": 100 * sum(r["balls"] for r in cr if r["control"] == 0) / ct,
        }
    if p not in table or len(table) < 4:
        return None
    order = sorted(table, key=lambda b: -table[b]["Good length"])
    cols = ["Good length", "Short", "False shots"]
    payload = heat(table, cols, p, order)
    # Short: fewer is better, so its shading and ring run the other way.
    flipped = _pct({b: -table[b]["Short"] for b in order})
    best_short = min(order, key=lambda b: table[b]["Short"])
    for r in payload["rows"]:
        r["pct"]["Short"] = flipped[r["name"]]
        r["leader"] = [c for c in r["leader"] if c != "Short"] + (["Short"] if r["name"] == best_short else [])
    for m in payload["metrics"]:
        m["format"] = "pct0"
    me = table[p]
    more_false = [short_name(b) for b in order if table[b]["False shots"] > me["False shots"] + 2]
    first = order[0] == p
    title = (f"{short_name(p)} lands {me['Good length']:.0f}% of his new balls on a good length"
             + (", more than any India pacer" if first else ""))
    named = more_false[:3]
    who = ", ".join(named[:-1]) + f" and {named[-1]}" if len(named) > 1 else "".join(named)
    help_ = (f"Accuracy, not menace: {who} draw{'s' if len(named) == 1 else ''} more false shots" if named
             else "Accuracy and menace: no India pacer draws more false shots")
    payload["method"] = "False shot: a ball the batter didn't control (a miss, an edge, a mis-hit). Ring: best."
    out = card("accuracy", "scorecard", title, payload,
               f"India's pacers, powerplays in every T20 since {spec['years'][0]} · {tracked[p]:,} of {short_name(p)}'s balls tracked",
               help_)
    out["kicker"] = "The deeper cut"
    return out


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if spec.get("type") == "venue_matchups":  # a ground and an opposition (services/ig_posts/venue_spotlight.py)
        from services.ig_posts import venue_spotlight

        return venue_spotlight.build(db, spec)
    if spec.get("type") == "case_odi":  # an ODI case (services/ig_posts/case_odi.py)
        from services.ig_posts import case_odi

        return case_odi.build(db, spec)
    if spec.get("type") == "batter_v_attack":  # a batter against the bowling he's about to face (batter_v_attack.py)
        from services.ig_posts import batter_v_attack

        return batter_v_attack.build(db, spec)
    if spec.get("type") == "squad_review":  # one team's squad, phase by phase (services/ig_posts/squad_post.py)
        from services.ig_posts import squad_post

        return squad_post.build(db, spec)
    if spec.get("type") == "series_preview":  # a series' grounds and match-ups (services/ig_posts/series_preview.py)
        from services.ig_posts import series_preview

        return series_preview.build(db, spec)
    if spec.get("type") == "player_compare":  # two batters, each in his own window (services/ig_posts/player_compare.py)
        from services.ig_posts import player_compare

        return player_compare.build(db, spec)
    if spec.get("type") == "openers_case":  # who opens: boom, bust and the possible top threes (openers_case.py)
        from services.ig_posts import openers_case

        return openers_case.build(db, spec)
    if spec.get("type") == "case_t20":  # a T20I batter's case, in Impact and WPA (services/ig_posts/case_t20.py)
        from services.ig_posts import case_t20

        return case_t20.build(db, spec)
    p = spec["player"]
    bowlers = [p] + peers(db, spec)
    data = phase_years(db, bowlers, min(spec["arc_from"], spec["years"][0]))
    deep = accuracy_card(db, spec, bowlers) if spec["role"] == "bowler" else None
    cards = [c for c in (
        arc_card(spec, data),
        deep,  # slide 3: the post's own deeper cut, so the generic one isn't added
        peer_card(spec, data, bowlers, "powerplay", "impact"),
        peer_card(spec, data, bowlers, "death", "impact"),
        peer_card(spec, data, bowlers, "powerplay", "raa"),
        peer_card(spec, data, bowlers, "death", "raa"),
        nz_record_card(db, spec),
        grounds_card(db, spec),
    ) if c]
    if len(cards) < 4:
        return None
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [{"type": "end", "heading": "Every number, free",
                  "body": "Impact, runs saved and every phase of every bowler: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]  # the deeper cut has its own caption line
    verdict = told[0]["title"] + ". " + (told[1]["title"] + "." if len(told) > 1 else "")
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": verdict, "players": bowlers,
            "deep_cut": {"probe": "accuracy", "subject": p, "sentence": deep["title"], "by": "spotlight"} if deep else None}


def make_post(db, spec: Dict[str, Any], built: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """The queueable post for a spec: carousel saved, fact, caption (with the spec's own deeper cut when it has one; the
    generic one is added by the caller, ig_backlog.add_deep_cut, otherwise). None when the data can't make the post."""
    from services import ig_captions, ig_carousel

    built = built or build(db, spec)
    if not built:
        return None
    carousel = ig_carousel.save(db, built["slides"], built["title"], {"spotlight": spec["key"]}, "ig-spotlight")
    subject = spec.get("player") or spec.get("kicker")  # a series preview is about a series, not one player
    fact = {"kind": "spotlight", "subject": subject, "subject_role": spec.get("role", "series"), "title": built["title"],
            "verdict": built["verdict"], "kicker": spec["kicker"], "carousel_id": carousel["id"],
            "slides": len(built["slides"]), "render": True, "spec": next(k for k, v in SPECS.items() if v is spec)}
    for k in ("deep_cut_scope", "deep_cut_exclude", "link"):  # link: the post's page on the site (a series: its first ground)
        if spec.get(k):
            fact[k] = spec[k]
    caption = ig_captions.build(built["title"], built["verdict"], "spotlight",
                                spec.get("method") or "Impact and runs saved are computed ball by ball (T20 Primer method), "
                                                      "on every T20 each bowler played.",
                                [spec["player"]] if spec.get("player") else built.get("players", [])[:2],
                                spec["kicker"], spec.get("tags", []), prompt=spec.get("prompt") or built.get("prompt"))
    post = {"key": spec["key"], "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "caption": caption, "players": [spec["player"]] if spec.get("player") else built.get("players", [])}
    if built.get("deep_cut"):  # the spotlight's own (slide 3)
        fact["deep_cut"] = built["deep_cut"]
        post["caption"] = ig_captions.with_deep_cut(caption, built["deep_cut"]["sentence"])
    return post


# Squad reviews: one spec a team, built from the league's squads file (services/ig_posts/squad_post.spec_for).
def _squad_specs() -> Dict[str, Dict[str, Any]]:
    from services.ig_posts.squad_post import spec_for

    teams = {"pr": "Paarl Royals", "dsg": "Durban's Super Giants", "jsk": "Joburg Super Kings", "mict": "MI Cape Town",
             "pc": "Pretoria Capitals", "sec": "Sunrisers Eastern Cape"}
    out = {}
    for short, team in teams.items():
        try:
            out[f"sa20-2027-{short}"] = spec_for("data/squads/sa20_2027.json", team, f"spotlight-sa20-2027-squad-{short}")
        except (OSError, StopIteration, KeyError):  # pragma: no cover - no squads file in this checkout
            pass
    return out


SPECS.update(_squad_specs())
