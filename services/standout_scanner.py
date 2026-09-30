"""
Standout scanner: ball-by-ball angles in a newly loaded match that stand out against history.

The kind of stat a fan spots on X ("Gill and Kohli were in control of 91% of their stand") found
by code for every match. Each template groups one match's deliveries (partnerships, innings,
spells, team phases), computes a metric, and ranks it against every comparable group in the same
scope (format; competition for leagues) since 2015. Only near-top values become facts, each with
its rank, sample size, window and the chart rows that prove it.

Complements services/records.py (scorecard records from the stats tables): these templates need
delivery_details, i.e. control %, partnerships and phase scoring. Control % uses the query
builder's own formula, so a number in a post matches what the site shows.

Populations are computed once per (template, scope) per process and data version, so scanning
ten matches in one nightly run costs ten cheap per-match lookups, not ten full scans.
"""
import bisect
import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.analytics_common import phase_bounds
from services.match_recap import _poss
from services.player_aliases import ALIAS_MAP_CTE
from services.query_cache import data_version
from services.records import CHART_ROWS, SINCE, _scope, _superlative, ordinal

RANK_MAX = 10           # ordinal claims ("the 7th-highest") up to here
TOP_SHARE = 0.01        # beyond that, "in the top 1%" still counts
MIN_POPULATION = 300
CONTROL_COVERAGE = 0.8  # a group needs control data on 80% of its balls to be ranked on control

_POPULATIONS: Dict[Tuple, List[Dict[str, Any]]] = {}

BAT = "COALESCE(am_bat.canonical_name, dd.bat)"
NS = "COALESCE(am_ns.canonical_name, dd.non_striker)"
BOWL = "COALESCE(am_bowl.canonical_name, dd.bowl)"
PAIR = f"(LEAST({BAT}, {NS}) || ' & ' || GREATEST({BAT}, {NS}))"
LEGAL = "CASE WHEN COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END"
AGGS = f"""
    SUM({LEGAL}) AS balls,
    SUM(COALESCE(dd.score, 0)) AS runs,
    SUM(COALESCE(dd.batruns, 0)) AS bat_runs,
    SUM(CASE WHEN LOWER(dd.out::text) = 'true' THEN 1 ELSE 0 END) AS wickets,
    SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) AS controlled,
    COUNT(dd.control) AS control_known
"""


def _min_balls(fmt: str, t20: int, odi: int) -> int:
    return odi if fmt == "ODI" else t20


def _templates(fmt: str) -> List[Dict[str, Any]]:
    phases = phase_bounds(fmt, "male")
    pp_end, death_start = phases[0].end_over, phases[-1].start_over  # 0-indexed overs
    pp_label = f"overs 1-{pp_end + 1}"
    stand = _min_balls(fmt, 30, 60)
    inn = _min_balls(fmt, 20, 50)
    spell = _min_balls(fmt, 18, 42)
    control = "controlled * 100.0 / NULLIF(control_known, 0)"
    covered = f"control_known >= {CONTROL_COVERAGE} * balls"
    return [
        {"kind": "stand_control", "group": "partnerships", "name": PAIR, "team": "dd.team_bat",
         "opp": "dd.team_bowl", "metric": control, "desc": True, "having": f"balls >= {stand} AND {covered}",
         "label": "control %", "word": "highest",
         "lead": "{name} were in control of {value}% of their {balls}-ball stand v {opp}",
         "noun": f"{{comp}} partnerships of {stand}+ balls",
         "display": lambda r: f"{r['value']:.1f}%",
         "method": f"Control %: share of deliveries the batters were in control of (ball-by-ball data). Ranked "
                   f"against {{n:,}} {{comp}} partnerships of {stand}+ balls since {{since}} with control data."},
        {"kind": "stand_runs", "group": "partnerships", "name": PAIR, "team": "dd.team_bat", "opp": "dd.team_bowl",
         "metric": "runs", "desc": True, "having": "balls >= 1", "label": "runs", "word": "biggest",
         "lead": "{name} added {runs} off {balls} balls v {opp}", "noun": "{comp} partnerships",
         "display": lambda r: f"{int(r['runs'])} ({int(r['balls'])})",
         "method": "Partnership runs (including extras) ranked against {n:,} {comp} partnerships since {since}."},
        {"kind": "innings_control", "group": "innings", "name": BAT, "team": "dd.team_bat", "opp": "dd.team_bowl",
         "metric": control, "desc": True, "having": f"balls >= {inn} AND {covered}", "label": "control %",
         "word": "highest",
         "lead": "{name} ({bat_runs} off {balls}) was in control of {value}% of deliveries v {opp}",
         "noun": f"{{comp}} innings of {inn}+ balls",
         "display": lambda r: f"{r['value']:.1f}%",
         "method": f"Control %: share of deliveries the batter was in control of. Ranked against {{n:,}} {{comp}} "
                   f"innings of {inn}+ balls since {{since}} with control data."},
        {"kind": "spell_control", "group": "spells", "name": BOWL, "team": "dd.team_bowl", "opp": "dd.team_bat",
         "metric": control, "desc": False, "having": f"balls >= {spell} AND {covered}", "label": "batters' control %",
         "word": "lowest",
         "lead": "{poss} {balls}-ball spell v {opp} held batters to {value}% control",
         "noun": f"{{comp}} spells of {spell}+ balls",
         "display": lambda r: f"{r['value']:.1f}%",
         "method": f"Batters' control % against the bowler (lower = harder to play). Ranked against {{n:,}} {{comp}} "
                   f"spells of {spell}+ balls since {{since}} with control data."},
        {"kind": "powerplay_runs", "group": "innings", "name": "dd.team_bat", "team": "dd.team_bat",
         "opp": "dd.team_bowl", "metric": "runs", "desc": True, "having": "balls >= 1",
         "where": f"AND dd.over <= {pp_end}", "label": f"runs in {pp_label}", "word": "highest",
         "lead": f"{{poss}} {{runs}}/{{wickets}} in {pp_label} v {{opp}}", "noun": "{comp} powerplays",
         "display": lambda r: f"{int(r['runs'])}/{int(r['wickets'])}",
         "method": f"Runs in {pp_label}, ranked against {{n:,}} {{comp}} innings since {{since}}."},
        {"kind": "death_runs", "group": "innings", "name": "dd.team_bat", "team": "dd.team_bat",
         "opp": "dd.team_bowl", "metric": "runs", "desc": True, "having": "balls >= 12",
         "where": f"AND dd.over >= {death_start}", "label": f"runs in overs {death_start + 1}+", "word": "highest",
         "lead": f"{{poss}} {{runs}}/{{wickets}} in overs {death_start + 1}-{phases[-1].end_over + 1} v {{opp}}",
         "noun": "{comp} death-overs innings",
         "display": lambda r: f"{int(r['runs'])}/{int(r['wickets'])}",
         "method": f"Runs in overs {death_start + 1}-{phases[-1].end_over + 1}, ranked against {{n:,}} {{comp}} "
                   f"innings since {{since}}."},
    ]


def _group_sql(template: Dict[str, Any], scope: Dict[str, Any], match_filter: str) -> str:
    return f"""
        WITH {ALIAS_MAP_CTE},
        g AS (
            SELECT dd.p_match AS match_id, dd.inns, {template['name']} AS name, {template['team']} AS team,
                   {template['opp']} AS opp, m.date, {AGGS}
            FROM delivery_details dd
            JOIN matches m ON m.id = dd.p_match
            LEFT JOIN alias_map am_bat ON LOWER(dd.bat) = am_bat.name_key
            LEFT JOIN alias_map am_ns ON LOWER(dd.non_striker) = am_ns.name_key
            LEFT JOIN alias_map am_bowl ON LOWER(dd.bowl) = am_bowl.name_key
            WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since {match_filter}
                  {template.get('where', '')}
            GROUP BY 1, 2, 3, 4, 5, 6
        )
        SELECT *, {template['metric']} AS value FROM g WHERE {template['having']}
    """


def _population(db: Session, template: Dict[str, Any], scope: Dict[str, Any], gender: str) -> List[Dict[str, Any]]:
    key = (template["kind"], scope["label"], scope["fmt"], gender, data_version(db))
    if key not in _POPULATIONS:
        rows = db.execute(text(_group_sql(template, scope, "")),
                          {**scope["params"], "fmt": scope["fmt"], "gender": gender, "since": SINCE}).mappings()
        pop = [dict(r) for r in rows if r["value"] is not None]
        pop.sort(key=lambda r: float(r["value"]), reverse=template["desc"])
        _POPULATIONS[key] = pop
    return _POPULATIONS[key]


def _rank(pop: List[Dict[str, Any]], value: float, desc: bool) -> Tuple[int, bool]:
    """1-based competition rank of value in pop, and whether it is tied."""
    keys = [-float(r["value"]) if desc else float(r["value"]) for r in pop]  # ascending
    k = -value if desc else value
    lo, hi = bisect.bisect_left(keys, k - 1e-9), bisect.bisect_right(keys, k + 1e-9)
    return lo + 1, hi - lo > 1


def _pretty(r: Dict[str, Any]) -> Dict[str, Any]:
    value = float(r["value"])
    return {"value": round(value, 1), "runs": int(r["runs"]), "balls": int(r["balls"]), "bat_runs": int(r["bat_runs"]),
            "wickets": int(r["wickets"])}


def scan_match(db: Session, match: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Standout facts for one match (a `matches` row as a dict), strongest first."""
    scope = _scope(match)
    gender = match.get("gender") or "male"
    facts: List[Dict[str, Any]] = []
    for template in _templates(scope["fmt"]):
        mine = [dict(r) for r in db.execute(
            text(_group_sql(template, scope, "AND dd.p_match = :mid")),
            {**scope["params"], "fmt": scope["fmt"], "gender": gender, "since": SINCE, "mid": str(match["id"])},
        ).mappings() if r["value"] is not None]
        if not mine:
            continue
        pop = _population(db, template, scope, gender)
        n = len(pop)
        if n < MIN_POPULATION:
            continue
        since_year = max(SINCE.year, min(r["date"] for r in pop).year)
        for hit in mine:
            rank, tied = _rank(pop, float(hit["value"]), template["desc"])
            if rank > RANK_MAX and rank > n * TOP_SHARE:
                continue
            sup = (("joint " if tied else "") + _superlative(rank, template["word"])) if rank <= RANK_MAX \
                else f"in the top {max(1, math.ceil(rank * 100 / n))}%"
            numbers = _pretty(hit)
            # One ending for every template: ", the 3rd-highest of 2,672 ODI powerplays since 2015".
            name = hit["name"].replace(" & ", " and ")  # titles read "Gill and Kohli"; chart labels keep "&"
            fields = dict(name=name, poss=_poss(name), opp=hit["opp"], comp=scope["label"], **numbers)
            title = (f"{template['lead'].format(**fields)}, {sup} of {n:,} "
                     f"{template['noun'].format(**fields)} since {since_year}")
            top = pop[:CHART_ROWS]
            chart_rows = top if any(_same(r, hit) for r in top) else top[:CHART_ROWS - 1] + [hit]
            facts.append({
                "kind": template["kind"], "team": hit["team"], "subject": hit["name"], "title": title,
                "rank": rank, "n": n, "since_year": since_year, "numbers": numbers, "scope": scope["label"],
                # Ordinal claims weigh by rank and sample size; "top 1%" claims are weaker (1% of 33,000
                # partnerships is rank 330) and rely on Jev to be picked. Control angles get a nudge:
                # they are the stats only Hindsight has.
                "weight": ((RANK_MAX + 1 - rank) * math.log10(n) if rank <= RANK_MAX else 3.0)
                          + (1 if "control" in template["kind"] else 0),
                "method": template["method"].format(comp=scope["label"], since=since_year, n=n),
                "chart": {
                    "metric": "value", "metric_label": template["label"], "group": template["group"],
                    "rows": [{"rank": _rank(pop, float(r["value"]), template["desc"])[0] if not _same(r, hit) else rank,
                              "label": f"{r['name']}, {r['date'].year}", "value": round(float(r["value"]), 1),
                              "display": template["display"](r), "highlight": _same(r, hit)} for r in chart_rows],
                },
            })
    return sorted(facts, key=lambda f: f["weight"], reverse=True)


def _same(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return a["match_id"] == b["match_id"] and a["inns"] == b["inns"] and a["name"] == b["name"]


def clear_cache() -> None:
    _POPULATIONS.clear()
