"""
"Idea → pack": a hunch typed into the admin queue becomes a content pack.

    "Gill–Kohli control % in the first ODI v WI compared to other ODI partnerships"

The existing natural-language parser (services/nl2query.py, under its monthly cost cap) turns
the idea into query-builder parameters; the query runs through the query cache and becomes a
chart snapshot with the idea's subject highlighted; the title is built in code from the
highlighted row ("Shubman Gill and Virat Kohli rank 2nd of 48 ODI partnerships (1,000+ balls) for
control % since 2019, at 87.3%") and checked by services/content_rules.py.

When the subject is not in the result yet (usually: the match is not loaded), the idea is parked
with the date of the latest loaded match, and every nightly run retries parked ideas until they
resolve or turn 14 days old.
"""
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services import content_rules, idea_stats
from services.records import ordinal
from services.snapshots import QUERY_PARAMS, SnapshotError, metric_label, title_parts

logger = logging.getLogger(__name__)

PARK_DAYS = 14
COMPARE = re.compile(r"\b(compar\w*|vs\.? others?|other|rank\w*|among|against (all|every|other)|best|highest|lowest|record)\b", re.I)
ENTITY_GROUPS = {"batter": "batters", "bowler": "bowlers", "partnership": "batters", "batting_team": "batting_teams",
                 "bowling_team": "bowling_teams"}
# "the first ODI v WI", "last night's game against India": the idea is about one match.
SPECIFIC_MATCH = re.compile(r"\b(first|second|third|fourth|fifth|last|latest|this|1st|2nd|3rd|4th|5th)\b.{0,20}"
                            r"\b(odi|t20i?|match|game)\b", re.I)
# Count-within and race ideas are parsed in code (services/idea_stats.py), not by the model.
WITHIN = idea_stats.WITHIN
NUMBER_WORDS = idea_stats.NUMBER_WORDS
WATCH_DAYS = 30  # resolved list/race ideas are re-run nightly this long, so new entries update the pack

METRIC_WORDS = [
    (r"control", "control_percentage"), (r"strike[- ]?rate|\bsr\b", "strike_rate"), (r"econ", "economy"),
    (r"dot", "dot_percentage"), (r"boundar", "boundary_percentage"), (r"average|\bavg\b", "average"),
    (r"impact", "impact"), (r"\bwpa\b", "wpa"), (r"wicket", "wickets"), (r"\bruns?\b", "runs"),
]


def _format_for(idea: str, choice: Optional[str]) -> str:
    if choice and choice.upper() in ("T20", "ODI", "ALL"):
        return choice.upper()
    if re.search(r"\bODIs?\b|one[- ]day", idea, re.I):
        return "ODI"
    if re.search(r"\bT20I?s?\b|\bIPL\b|\bBBL\b|\bPSL\b|\bCPL\b|\bSA20\b", idea, re.I):
        return "T20"
    return "ALL"


def _metric_for(idea: str, parsed: Dict[str, Any]) -> Optional[str]:
    for pattern, metric in METRIC_WORDS:
        if re.search(pattern, idea, re.I):
            return metric
    chart = parsed.get("recommended_chart") or {}
    return chart.get("y_axis") or (parsed.get("recommended_columns") or [None])[0]


def plan(idea: str, fmt_choice: Optional[str], db: Session, client: str = "admin") -> Dict[str, Any]:
    """Parse the idea: {spec, scope} for count-within / race ideas, else query-builder params.

    Every idea is logged to nl_query_log under `client` (public graphics as "[graphic] ..."), which
    is also what the public daily limit counts (routers/snapshots.ideas_today).
    """
    from services.nl2query import log_nl_query_event_background

    tag = "[idea]" if client == "admin" else "[graphic]"
    spec = idea_stats.parse_race(idea) or idea_stats.parse_debut(idea) or idea_stats.parse_count_within(idea)
    if spec:
        log_nl_query_event_background(query_text=f"{tag} {idea}", parse_result={"success": True}, ip_address=client,
                                      execution_time_ms=None)
        return {"spec": spec, "scope": idea_stats.parse_scope(idea, db, fmt_choice)}
    if WITHIN.search(idea) and re.search(r"\b(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")\b", idea, re.I):
        raise SnapshotError("Counting players within one innings or match only works for centuries, fifties and "
                            "wicket hauls so far; the query builder can't express this one yet.")
    from services.nl2query import parse_nl_query

    parsed = parse_nl_query(idea, db=db)
    log_nl_query_event_background(query_text=f"{tag} {idea}", parse_result=parsed, ip_address=client,
                                  execution_time_ms=None)
    if not parsed.get("success", True) or not parsed.get("group_by"):
        raise SnapshotError(parsed.get("error") or "Could not turn the idea into a query (no grouping).")
    if parsed.get("warnings"):
        # A condition the query can't apply (e.g. a control % threshold) would make the pack rank
        # the wrong group, as "50+ average, 100+ SR" once did; refuse and say which.
        raise SnapshotError("Can't build this pack exactly: " + " ".join(parsed["warnings"]))
    filters = {k: v for k, v in (parsed.get("filters") or {}).items() if k in QUERY_PARAMS and v not in (None, [], "")}
    group_by = [g for g in parsed["group_by"] if g != "format"]
    fmt = _format_for(idea, fmt_choice)

    # "X compared to other partnerships": X is the highlight, not a filter; filtering to X would
    # leave nothing to compare against.
    highlight = None
    entity_key = next((ENTITY_GROUPS[g] for g in group_by if g in ENTITY_GROUPS), None)
    if entity_key and filters.get(entity_key) and COMPARE.search(idea):
        names = filters.pop(entity_key)
        highlight = names if isinstance(names, list) else [names]
    # One match against a named opponent, compared with others: rank per match (group by
    # match_id) against every partnership/innings, not just those against that opponent -- the
    # team filters only identified the match. attempt() then takes the subject from that match.
    if SPECIFIC_MATCH.search(idea) and _opponent_in(idea, db):
        if "match_id" not in group_by:
            group_by.append("match_id")
        if COMPARE.search(idea):
            for key in ("teams", "batting_teams", "bowling_teams"):
                filters.pop(key, None)
    metric = _metric_for(idea, parsed)
    params = {**filters, "group_by": group_by, "fmt": fmt, "gender": "male", "query_mode": filters.get("query_mode") or "delivery"}
    return {"params": params, "metric": metric, "highlight": highlight, "explanation": parsed.get("explanation"),
            # Kept for the chart chooser: a scatter is offered only when the question named two metrics.
            "chart": parsed.get("recommended_chart")}


def _row_name(row: Dict[str, Any], label_key: str) -> str:
    return str(row.get(label_key) or "")


# Capitalised words in an idea that are not names: formats, competitions, months, sentence words.
NOT_NAMES = {"odi", "odis", "t20", "t20i", "t20is", "ipl", "bbl", "psl", "cpl", "sa20", "test", "tests", "the", "first",
             "second", "third", "fourth", "fifth", "final", "world", "cup", "trophy", "series", "compared", "compare",
             "highest", "lowest", "best", "most", "which", "who", "what", "how", "control", "since", "in", "v", "vs",
             "top", "fastest", "slowest", "biggest", "partnerships", "partnership", "batters", "bowlers", "death",
             "powerplay", "middle", "overs", "strike", "rate", "economy", "runs", "wickets", "and", "with", "for",
             "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
             "november", "december", "dot", "dots", "ball", "balls", "boundary", "boundaries", "average", "impact",
             "openers", "pace", "spin", "season", "seasons", "year", "phase", "innings", "economy", "teams", "players",
             "left-arm", "right-arm", "spinners", "seamers", "batter", "bowler", "wi", "sa", "nz", "aus", "eng", "ind", "pak", "sl", "ban", "afg", "ire", "zim"}


def _mentions(idea: str) -> List[str]:
    """Probable player/team name words in the idea: capitalised and not a stop word."""
    words = re.findall(r"\b([A-Z][a-zA-Z'-]{2,})\b", idea.strip())
    return [w for w in words if w.lower() not in NOT_NAMES]


def _find_mentioned(rows: List[Dict[str, Any]], label_key: str, mentions: List[str]) -> Optional[int]:
    """The best-ranked row whose label contains the most mentioned names (both halves of a pair)."""
    wanted = {m.lower() for m in mentions}
    best, best_hits = None, 0
    for i, r in enumerate(rows):
        tokens = set(re.findall(r"[a-z'-]+", _row_name(r, label_key).lower()))
        hits = len(tokens & wanted)
        if hits > best_hits:
            best, best_hits = i, hits
    need = 2 if " & " in _row_name(rows[0], label_key) and len(wanted) >= 2 else 1
    return best if best_hits >= need else None


TEAM_SHORT = {"wi": "West Indies", "sa": "South Africa", "nz": "New Zealand", "aus": "Australia", "eng": "England",
              "ind": "India", "pak": "Pakistan", "sl": "Sri Lanka", "ban": "Bangladesh", "afg": "Afghanistan",
              "ire": "Ireland", "zim": "Zimbabwe"}
MATCH_WINDOW_DAYS = 30


def _opponent_in(idea: str, db: Session) -> Optional[str]:
    """A team the idea is played against ("v WI", "against West Indies"), if it names one."""
    m = re.search(r"\b(?:v|vs\.?|versus|against)\s+([A-Za-z][A-Za-z .'-]{1,40})", idea, re.I)
    if not m:
        return None
    phrase = m.group(1).strip().lower()
    first = phrase.split()[0]
    if first in TEAM_SHORT:
        return TEAM_SHORT[first]
    teams = [r[0] for r in db.execute(text(
        "SELECT DISTINCT team1 FROM matches WHERE date >= now() - interval '3 years' "
        "UNION SELECT DISTINCT team2 FROM matches WHERE date >= now() - interval '3 years'"))]
    hits = [t for t in teams if t and phrase.startswith(t.lower())]
    return max(hits, key=len) if hits else None


def _recent_matches_against(db: Session, team: str, fmt: str) -> List[str]:
    where = "" if fmt == "ALL" else "AND format = :fmt"
    return [r[0] for r in db.execute(text(f"""
        SELECT id FROM matches WHERE :team IN (team1, team2) AND date >= CURRENT_DATE - :days {where}
    """), {"team": team, "days": MATCH_WINDOW_DAYS, "fmt": fmt})]


def _find(rows: List[Dict[str, Any]], label_key: str, names: List[str]) -> Optional[int]:
    """Index of the row the highlight names: an exact label first, else the first row whose label
    contains every named player's surname. A partnership highlight ("Shubman Gill & Virat Kohli") is
    two players; read as one name it matched only "Kohli", i.e. the first stand with Kohli in it."""
    wanted = {str(n).strip().lower() for n in names if n}
    for i, r in enumerate(rows):
        if _row_name(r, label_key).strip().lower() in wanted:
            return i
    people = [p for n in names if n for p in re.split(r"\s+(?:&|and)\s+", str(n).strip()) if p]
    surnames = [p.split()[-1].lower() for p in people]
    for i, r in enumerate(rows):
        label = _row_name(r, label_key).lower()
        if surnames and all(s in label for s in surnames):
            return i
    return None


# Counts read "with 147 sixes"; rates read "at 87.3%" / "at 207.3".
COUNT_METRICS = {"runs", "balls", "wickets", "sixes", "fours", "dots", "boundaries", "innings_count", "matches",
                 "fifties", "hundreds", "catches", "dismissals"}


def _value_text(metric: str, value: float) -> str:
    if metric.endswith("percentage"):
        return f"{value:.1f}%"
    if metric in COUNT_METRICS or float(value).is_integer():
        return f"{int(round(value)):,}"
    return f"{value:.1f}" if metric == "strike_rate" or abs(value) >= 100 else f"{value:.2f}"


def _value_phrase(metric: str, value: float) -> str:
    if metric in COUNT_METRICS:
        return f"with {_value_text(metric, value)} {metric_label(metric)}"
    return f"at {_value_text(metric, value)}"


def _latest_loaded(db: Session, fmt: str) -> Optional[date]:
    where = "" if fmt == "ALL" else "WHERE format = :fmt"
    return db.execute(text(f"SELECT max(date) FROM matches {where}"), {"fmt": fmt}).scalar()


LOWER_IS_BETTER = {"economy"}


def _ascending(metric: str, group_by: List[str]) -> bool:
    bowling = any(g in ("bowler", "bowling_team") for g in group_by)
    return metric in LOWER_IS_BETTER or (bowling and metric in ("average", "strike_rate"))


def _attempt_rollup(db: Session, idea_text: str, planned: Dict[str, Any]) -> Dict[str, Any]:
    """"3 centuries (vs India) in an ODI innings": every such innings, latest first, as a list."""
    from services.snapshots import create_static_snapshot

    spec, scope = planned["spec"], planned["scope"]
    n, noun = int(spec["n"]), spec["noun"]
    groups = idea_stats.count_within(db, spec, scope)
    first_year, window = idea_stats.window_text(db, scope)
    fmt = idea_stats.scope_label(scope)
    unit = "innings" if spec["unit"] == "innings" else "matches"
    units_noun = " ".join(filter(None, [scope.get("team"), fmt, unit])) + (f" against {scope['opponent']}" if scope.get("opponent") else "")
    if not groups:
        return {"status": "failed", "note": f"No {units_noun} with {n}+ {noun} in Hindsight's data{window}."}
    latest, count = groups[0], len(groups)
    only = "the only" if count == 1 else f"one of {count}"
    if spec["unit"] == "innings":
        title = (f"{_poss_team(latest['team'])} {len(latest['members'])} {noun} v {latest['opp']} ({latest['date']:%b %Y}) "
                 f"make it {only} {units_noun} with {n}+ {noun}{window}")
    else:  # a match's milestones come from both sides
        title = (f"{latest['team']} v {latest['opp']} ({latest['date']:%b %Y}) had {len(latest['members'])} {noun}, "
                 f"{only} {units_noun} with {n}+{window}")
    rows = [{"label": f"{g['team']} v {g['opp']}", "date": g["date"].isoformat(), "sub": f"{g['date']:%d %b %Y}",
             "count": len(g["members"]), "display": f"{len(g['members'])} {noun}", "details": g["details"]} for g in groups]
    data = {
        "layout": "list", "title": title, "kicker": f"{fmt} · {unit}",
        "subtitle": f"Every {units_noun.replace(' matches', ' match')} with {n}+ {noun}, latest first",
        "filter_chips": [fmt, window.strip()], "group_by": [unit], "query_mode": "ranking", "rows": rows,
        "columns": ["label", "sub", "display", "details"], "metric_columns": ["count"],
        "chart": {"type": "list", "label_key": "label", "metric": "count"},
        "hindsight_url": f"{content_rules.SITE_URL}/query", "total_rows": count, "source": "scorecards",
    }
    snap = create_static_snapshot(db, "ranking", data, title, {"idea": idea_text, "spec": spec, "scope": scope, "title": title,
                                                               "entries": [r["date"] for r in rows]}, created_by="idea")
    fact = {
        "kind": "idea", "subject": latest["team"], "title": title,
        "numbers": {"count": len(latest["members"]), "n": n, "total": count, "rank": 1,
                    "years": [first_year, latest["date"].year], "details": [r["details"] for r in rows]},
        "method": f"All {count} {units_noun} in Hindsight's data{window} with {n}+ {noun}, latest first: "
                  + "; ".join(f"{r['label']} {r['sub']} ({', '.join(r['details'])})" for r in rows[:8]) + ".",
    }
    return {"status": "resolved", "fact": fact, "snapshot": snap}


def _attempt_race(db: Session, idea_text: str, planned: Dict[str, Any]) -> Dict[str, Any]:
    """"Fastest to 100 in ODIs": every innings/player that got there, ranked, subject highlighted."""
    from services.snapshots import create_static_snapshot

    spec, scope = planned["spec"], planned["scope"]
    rows, caveat = idea_stats.race(db, spec, scope)
    words = idea_stats.race_words(spec, scope)
    first_year, window = idea_stats.window_text(db, scope)
    career = idea_stats.span_of(spec) == "career"
    if career:
        window = idea_stats.debut_floor(db, scope, ball_by_ball=spec["unit"] == "balls")[1]
    opp_part = f" against {scope['opponent']}" if scope.get("opponent") else ""
    if not rows:
        return {"status": "failed", "note": f"Nobody reached {words['what']}{opp_part} in Hindsight's data{window}."}
    for r in rows:
        r["label"] = r["name"] if career else f"{r['name']} v {r['opp']}, {r['date'].year}"
    mentions = _scoped_mentions(idea_text, scope)
    idx = _find_mentioned(rows, "name", mentions) if mentions else 0
    if idx is None:
        return {"status": "parked", "note": f"{' '.join(mentions)} not among those who reached {words['what']} yet."}
    hit, n = rows[idx], len(rows)
    rank = 1 + sum(1 for r in rows if (r["value"] < hit["value"] if spec["direction"] == "fastest" else r["value"] > hit["value"]))
    tied = sum(1 for r in rows if r["value"] == hit["value"]) > 1
    sup = idea_stats.sup_word(rank, spec["direction"], tied)
    unit = "balls" if spec["unit"] == "balls" else "innings"
    verb = f"took {spec['target']} wickets" if spec["measure"] == "wickets" and not career else f"reached {words['what']}"
    against = "" if career else f" v {hit['opp']} ({hit['date']:%b %Y})"
    title = f"{hit['name']} {verb} in {hit['value']:,} {unit}{against}, {sup} of {n:,} {words['noun']}{opp_part}{window}"
    shown = list(range(min(8, n))) if idx < 8 else list(range(7)) + [idx]
    ranks = [1 + sum(1 for r in rows if (r["value"] < rows[i]["value"] if spec["direction"] == "fastest" else r["value"] > rows[i]["value"]))
             for i in shown]
    fmt = idea_stats.scope_label(scope)
    data = {
        "title": title, "kicker": f"{fmt} · {spec['direction']} to {spec['target']:,}",
        "metric_label": f"{unit} to {words['what']}", "filter_chips": [fmt, window.strip(" ()")],
        "group_by": ["players" if career else "innings"], "query_mode": "ranking",
        "columns": ["rank", "label", "value", "display"], "metric_columns": ["value"],
        "rows": [{"rank": rk, "label": rows[i]["label"], "value": rows[i]["value"], "display": f"{rows[i]['value']:,} {unit}",
                  "highlight": i == idx and bool(mentions)} for i, rk in zip(shown, ranks)],
        "chart": {"type": "bar", "label_key": "label", "metric": "value"}, "lower_is_better": spec["direction"] == "fastest",
        "hindsight_url": f"{content_rules.SITE_URL}/query", "total_rows": n, "source": "ball-by-ball" if unit == "balls" else "scorecards",
        "note": caveat if career else None,
    }
    snap = create_static_snapshot(db, "ranking", data, title, {"idea": idea_text, "spec": spec, "scope": scope, "title": title,
                                                               "top": [r["label"] for r in rows[:8]]}, created_by="idea")
    fact = {
        "kind": "idea", "subject": hit["name"], "title": title,
        "numbers": {"value": hit["value"], "target": spec["target"], "rank": rank, "total": n,
                    "years": [first_year, first_year + 1, hit["date"].year,
                              idea_stats.debut_floor(db, scope, ball_by_ball=spec["unit"] == "balls")[0].year]},
        "method": (f"{spec['direction'].capitalize()} to {words['what']}: {unit} "
                   f"when the running total first reached it, across {n:,} {words['noun']}{opp_part}{window}. "
                   + (caveat if career else "")).strip(),
    }
    return {"status": "resolved", "fact": fact, "snapshot": snap}


DEBUT_WORDS = {  # (metric, best is high) -> superlative, noun
    ("runs", True): ("highest", "debut scores"), ("runs", False): ("lowest", "debut scores"),
    ("runs_conceded", True): ("most expensive", "debut spells"), ("runs_conceded", False): ("cheapest", "debut spells"),
    ("figures", True): ("best", "debut figures"), ("figures", False): ("worst", "debut figures"),
    ("economy", False): ("most economical", "debut spells"), ("economy", True): ("least economical", "debut spells"),
}


def _attempt_debut(db: Session, idea_text: str, planned: Dict[str, Any]) -> Dict[str, Any]:
    """"Most runs conceded on ODI debut": every player's first innings or spell, ranked."""
    from services.snapshots import create_static_snapshot

    spec, scope = planned["spec"], planned["scope"]
    rows, window = idea_stats.debut(db, spec, scope)
    fmt = idea_stats.scope_label(scope)
    word, noun = DEBUT_WORDS[(spec["metric"], spec["desc"])]
    who = f"{scope['team']} " if scope.get("team") else ""
    opp_part = f" against {scope['opponent']}" if scope.get("opponent") else ""
    if not rows:
        return {"status": "failed", "note": f"No {who}{fmt} {noun}{opp_part} in Hindsight's data{window}."}
    batting = spec["table"] == "batting"
    for r in rows:
        r["label"] = f"{r['name']} v {r['opp']}, {r['date'].year}"
        overs = idea_stats.overs_text(r.get("overs")) if not batting else None
        r["display"] = (f"{r['runs']} ({r['balls']})" if batting else
                        f"{r['wickets']}/{r['runs']} ({overs})" if spec["metric"] == "figures" else
                        f"{r['economy']:.2f} ({overs} ov)" if spec["metric"] == "economy" else f"{r['runs']} ({overs} ov)")
        r["value"] = (r["runs"] if spec["metric"] in ("runs", "runs_conceded") else
                      r["wickets"] if spec["metric"] == "figures" else round(r["economy"] or 0, 2))
    mentions = _scoped_mentions(idea_text, scope)
    idx = _find_mentioned(rows, "name", mentions) if mentions else 0
    if idx is None:
        return {"status": "parked", "note": f"{' '.join(mentions)} has no {fmt} debut in Hindsight's data yet."}
    hit, n = rows[idx], len(rows)
    same = [i for i, r in enumerate(rows) if r["value"] == hit["value"] and (spec["metric"] != "figures" or r["runs"] == hit["runs"])]
    rank, tied = same[0] + 1, len(same) > 1
    sup = idea_stats.sup_word(rank, word, tied)
    when = f"on {fmt} debut v {hit['opp']} ({hit['date']:%b %Y})"
    if batting:
        lead = f"{hit['name']} made {hit['runs']} off {hit['balls']} {when}"
    elif spec["metric"] == "figures":
        lead = f"{hit['name']} took {hit['wickets']}/{hit['runs']} {when}"
    elif spec["metric"] == "economy":
        lead = f"{hit['name']} conceded {hit['runs']} in {idea_stats.overs_text(hit['overs'])} overs (economy {hit['economy']:.2f}) {when}"
    else:
        lead = f"{hit['name']} conceded {hit['runs']} in {idea_stats.overs_text(hit['overs'])} overs {when}"
    title = f"{lead}, {sup} of {n:,} {who}{fmt} {noun}{opp_part}{window}"
    shown = list(range(min(8, n))) if idx < 8 else list(range(7)) + [idx]
    data = {
        "title": title, "kicker": f"{fmt} · debuts", "metric_label": noun.replace("debut ", "").capitalize(),
        "filter_chips": [fmt, window.strip(" ()")], "group_by": ["debuts"], "query_mode": "ranking",
        "columns": ["rank", "label", "value", "display"], "metric_columns": ["value"],
        "rows": [{"rank": i + 1, "label": rows[i]["label"], "value": float(rows[i]["value"]), "display": rows[i]["display"],
                  "highlight": i == idx and bool(mentions)} for i in shown],
        "chart": {"type": "bar", "label_key": "label", "metric": "value"},
        "lower_is_better": spec["metric"] == "economy" and not spec["desc"],
        "hindsight_url": f"{content_rules.SITE_URL}/query", "total_rows": n, "source": "scorecards",
    }
    snap = create_static_snapshot(db, "ranking", data, title, {"idea": idea_text, "spec": spec, "scope": scope, "title": title},
                                  created_by="idea")
    fact = {
        "kind": "idea", "subject": hit["name"], "title": title,
        "numbers": {"runs": hit["runs"], "balls": hit.get("balls"), "wickets": hit.get("wickets"),
                    "overs": idea_stats.overs_text(hit.get("overs")) if not batting else None,
                    "economy": round(hit["economy"], 2) if hit.get("economy") else None, "rank": rank, "total": n,
                    "years": [hit["date"].year, idea_stats.debut_floor(db, scope)[0].year]},
        "method": f"Each player's first {'innings' if batting else 'spell'} in {fmt} cricket in Hindsight's data{window}, "
                  f"ranked across {n:,} {noun}.",
    }
    return {"status": "resolved", "fact": fact, "snapshot": snap}


def _scoped_mentions(idea: str, scope: Dict[str, Any]) -> List[str]:
    """Name-like words in the idea, minus the team/opponent it is scoped to ("for India")."""
    scoped = {w.lower() for t in (scope.get("team"), scope.get("opponent")) if t for w in t.split()}
    return [m for m in _mentions(idea) if m.lower() not in scoped]


def _poss_team(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _form_base(data: Dict[str, Any], **extra) -> Dict[str, Any]:
    keep = ("kicker", "subtitle", "filter_chips", "group_by", "hindsight_url", "total_rows", "source", "metric_label")
    return {**{k: data[k] for k in keep if k in data}, **extra}


def _line_form(rows, label_key, metric, idx, data, parts):
    """A season trend: rows in time order, the subject's (or latest) season highlighted."""
    ordered = sorted(rows, key=lambda r: str(r.get(label_key)))
    hi_label = rows[idx].get(label_key) if idx is not None else ordered[-1].get(label_key)
    points = [{"x": str(r.get(label_key)), "y": float(r[metric]), "display": _value_text(metric, float(r[metric])),
               "highlight": r.get(label_key) == hi_label} for r in ordered if r.get(metric) is not None]
    first, last = points[0], points[-1]
    who = parts["who"]
    title = (f"{who + chr(39) + 's ' if who else ''}{metric_label(metric)} by season: "
             f"{first['display']} in {first['x']}, {last['display']} in {last['x']}")
    return _form_base(data, layout="line", title=title, metric=metric, points=points), title


def _scatter_form(rows, label_key, axes, idx, data, name, total, parts):
    """Two metrics across the field (top 40 by the ranking metric, plus the subject)."""
    x, y = axes
    take = list(range(min(40, len(rows))))
    if idx is not None and idx not in take:
        take.append(idx)
    points = [{"label": _row_name(rows[i], label_key), "x": float(rows[i][x]), "y": float(rows[i][y]),
               "highlight": i == idx} for i in take if rows[i].get(x) is not None and rows[i].get(y) is not None]
    subj = rows[idx] if idx is not None else None
    if subj is not None:
        title = (f"{name}: {metric_label(y).lower()} {_value_text(y, float(subj[y]))} at "
                 f"{metric_label(x).lower()} {_value_text(x, float(subj[x]))} among {total:,} {parts['scope']}{parts['window']}")
    else:
        title = f"{metric_label(y)} v {metric_label(x)}: {parts['scope']}{parts['window']}"
    unit = (data.get("group_by") or ["players"])[0].replace("_", " ") + "s"
    return _form_base(data, layout="scatter", title=title, x_metric=x, y_metric=y, points=points, unit=unit), title


def _stat_form(rows, label_key, metric, idx, total, data, name, parts, title):
    """The single headline number, its rank, and the next three for context."""
    i = idx or 0
    value = float(rows[i][metric])
    context = [{"rank": j + 1, "label": _row_name(rows[j], label_key), "display": _value_text(metric, float(rows[j][metric]))}
               for j in range(len(rows)) if j != i][:3]
    rank_text = f"{ordinal(i + 1)} of {total:,} {parts['scope']}{parts['minimum']}{parts['window']}"
    return _form_base(data, layout="stat", title=title, metric=metric, value_display=_value_text(metric, value),
                      subject=name, rank_text=rank_text, context=context), title


PHASE_ORDER = ["powerplay", "middle", "death"]


def _split_label(key: str, value: Any) -> str:
    v = str(value)
    if key == "bowl_kind":
        return {"pace bowler": "v pace", "spin bowler": "v spin"}.get(v, v)
    if key == "innings":
        return {"1": "1st innings", "2": "2nd innings"}.get(v, f"innings {v}")
    return v.replace("_", " ").capitalize()


def _pivot(rows, label_key, split_key, metric):
    """{entity: {split: value}} in first-seen (i.e. ranked) entity order."""
    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        if r.get(metric) is None:
            continue
        out.setdefault(_row_name(r, label_key), {})[str(r.get(split_key))] = float(r[metric])
    return out


def _dumbbell_form(rows, label_key, split_key, metric, subject_label, data):
    """Two splits per entity (v pace / v spin...): entities with both values, the subject included."""
    splits = sorted({str(r.get(split_key)) for r in rows if r.get(split_key) is not None})[:2]
    pivot = {e: v for e, v in _pivot(rows, label_key, split_key, metric).items() if all(s in v for s in splits)}
    names = list(pivot)[:8]
    subject = _row_name({label_key: subject_label}, label_key) if subject_label is not None else None
    if subject and subject in pivot and subject not in names:
        names = names[:7] + [subject]
    out_rows = [{"label": e, "a": pivot[e][splits[0]], "b": pivot[e][splits[1]], "highlight": e == subject} for e in names]
    la, lb = _split_label(split_key, splits[0]), _split_label(split_key, splits[1])
    if subject and subject in pivot:
        va, vb = pivot[subject][splits[0]], pivot[subject][splits[1]]
        title = f"{subject}: {metric_label(metric).lower()} {_value_text(metric, va)} {la}, {_value_text(metric, vb)} {lb}"
    else:
        title = f"{metric_label(metric)} {la} and {lb}"
    return _form_base(data, layout="dumbbell", title=title, metric=metric, series=[la, lb], rows=out_rows), title


ENTITY_FILTERS = {"batter": "batters", "bowler": "bowlers", "batting_team": "batting_teams", "bowling_team": "bowling_teams"}


def _complete_split_rows(db: Session, rows, label_key, query_params):
    """Rows for a stacked split with every part present.

    The idea's minimums (min_balls...) apply to each (player, part) row, so a player's small parts
    (Kohli's death overs) dropped out and his bar showed a share of a smaller total. Re-query the
    players on show without the per-row minimums. Falls back to the rows given when the entity
    cannot be filtered on.
    """
    from services.snapshots import _clean_query_params, _query_data

    key = ENTITY_FILTERS.get(label_key)
    if not key:
        return rows
    names = list(dict.fromkeys(r.get(label_key) for r in rows if r.get(label_key)))[:12]
    params = {k: v for k, v in query_params.items()
              if k not in ("min_balls", "max_balls", "min_runs", "max_runs", "min_wickets", "max_wickets", "having",
                           "sort_by", "sort_descending")}
    params[key] = names
    try:
        full = _query_data(db, _clean_query_params(params))
    except Exception:
        return rows
    return full.get("rows") or rows


def _stacked_form(rows, label_key, split_key, metric, subject_label, data):
    """How each entity's total splits into parts (runs by phase...), biggest totals first."""
    pivot = _pivot(rows, label_key, split_key, metric)
    parts = sorted({p for v in pivot.values() for p in v},
                   key=lambda p: (PHASE_ORDER.index(p) if p in PHASE_ORDER else 99, -sum(v.get(p, 0) for v in pivot.values())))
    by_total = sorted(pivot, key=lambda e: -sum(pivot[e].values()))
    names = by_total[:8]
    subject = _row_name({label_key: subject_label}, label_key) if subject_label is not None else None
    if subject and subject in pivot and subject not in names:
        names = names[:7] + [subject]
    pretty = {p: _split_label(split_key, p) for p in parts}
    out_rows = [{"label": e, "values": {pretty[p]: pivot[e].get(p, 0) for p in parts},
                 "display": f"{_value_text(metric, sum(pivot[e].values()))} {metric_label(metric).lower()}",
                 "highlight": e == subject} for e in names]
    focus = subject if subject in pivot else names[0]
    tot = sum(pivot[focus].values()) or 1
    big = max(parts, key=lambda p: pivot[focus].get(p, 0))
    title = f"{focus}: {round(pivot[focus].get(big, 0) * 100 / tot)}% of {metric_label(metric).lower()} come {pretty[big].lower()}"
    if split_key == "phase":
        title = f"{focus} scores {round(pivot[focus].get(big, 0) * 100 / tot)}% of his {metric_label(metric).lower()} in the {pretty[big].lower()}"
    return _form_base(data, layout="stacked", title=title, metric=metric, parts=[pretty[p] for p in parts], rows=out_rows), title


def _field_form(rows, metric, data, parts):
    """Share of the metric by wagon-wheel zone (zone 0 = no recorded direction, left out)."""
    from services.match_scorecard import ZONE_LABELS

    zones = [{"zone": int(r["wagon_zone"]), "label": ZONE_LABELS.get(int(r["wagon_zone"]), str(r["wagon_zone"])),
              "value": float(r[metric] or 0)} for r in rows if r.get("wagon_zone") not in (None, 0, "0") and r.get(metric) is not None]
    total = sum(z["value"] for z in zones) or 1
    top = max(zones, key=lambda z: z["value"]) if zones else {"label": "", "value": 0}
    who = parts["who"]
    title = f"{who + ' takes ' if who else ''}{round(top['value'] * 100 / total)}% of {'his ' if who else ''}{metric_label(metric).lower()} through {top['label'].lower()}"
    title = title[:1].upper() + title[1:]
    return _form_base(data, layout="field", title=title, metric=metric, zones=zones), title


def _diverging_form(rows, label_key, metric, data, parts, title, split_rows):
    """Bars either side of zero. For one player's splits (phases, bowler types) the title names him
    and the best and worst split instead of 'powerplay rank 1st of 3 phases'."""
    if split_rows and parts["who"]:
        ranked = sorted(rows, key=lambda r: -float(r[metric]))
        best, worst = ranked[0], ranked[-1]
        title = (f"{parts['who']}: {metric_label(metric).lower()} {_value_text(metric, float(best[metric]))} "
                 f"{_split_label(label_key, best.get(label_key)).lower()}, {_value_text(metric, float(worst[metric]))} "
                 f"{_split_label(label_key, worst.get(label_key)).lower()}")
    return _form_base(data, layout="diverging", title=title, metric=metric, rows=data["rows"]), title


def attempt(db: Session, idea_text: str, planned: Dict[str, Any], created_by: str = "idea") -> Dict[str, Any]:
    """Run a planned idea. Returns {status: 'resolved', fact, snapshot} or {status: 'parked', note}."""
    from services.snapshots import create_static_snapshot

    if planned.get("spec"):
        kind = planned["spec"]["type"]
        return {"race": _attempt_race, "debut": _attempt_debut}.get(kind, _attempt_rollup)(db, idea_text, planned)

    params = dict(planned["params"])
    for key in ("start_date", "end_date"):
        if isinstance(params.get(key), str):
            params[key] = date.fromisoformat(params[key])
    metric, highlight = planned.get("metric"), planned.get("highlight")
    from services.coverage import DEFAULT_MIN_COVERAGE, describe_floor
    min_coverage = planned.get("min_coverage", DEFAULT_MIN_COVERAGE)
    query_params = {**planned["params"], "limit": 20000, "min_coverage": min_coverage}
    if metric:
        query_params.update(sort_by=metric, sort_descending=not _ascending(metric, params["group_by"]))
    # The full ordering (through the query cache), to find the subject's true rank; only the
    # ranking image built below is stored as a snapshot.
    from services.snapshots import _clean_query_params, _query_data

    full = _query_data(db, _clean_query_params(query_params))
    rows = full.get("rows") or []
    readable = [g for g in params["group_by"] if g not in ("match_id", "innings")]
    label_key = readable[0] if readable else (full.get("chart") or {}).get("label_key") or params["group_by"][0]
    if "match_id" in params["group_by"] and rows:
        dates = {str(r["id"]): r["date"] for r in db.execute(text("SELECT id, date FROM matches WHERE id = ANY(:ids)"),
                                                               {"ids": list({str(r["match_id"]) for r in rows})}).mappings()}
        for r in rows:
            d = dates.get(str(r.get("match_id")))
            if d and label_key in r:
                r[label_key] = f"{r[label_key]}, {d:%b %Y}"
    if not metric or not rows or metric not in rows[0]:
        metric = (full.get("chart") or {}).get("metric")
    if not rows or not metric:
        return {"status": "parked", "note": "The query returned nothing to chart yet."}
    # A row without the metric (e.g. no control data for that batter) cannot be ranked; it used to sort
    # first and crash the build. The total counts only rankable rows.
    unrankable = sum(1 for r in rows if r.get(metric) is None)
    rows = [r for r in rows if r.get(metric) is not None]
    if not rows:
        return {"status": "parked", "note": "No rows have a value for this metric yet."}
    # Ranked by a tagged metric (control %): rows under the coverage floor are ranked after the rest
    # (services/coverage.py) and are not part of "Nth of M" -- M counts only the rows that qualify.
    coverage = full.get("coverage") if (full.get("coverage") or {}).get("tag") else None
    if coverage:
        excluded_rows = [r for r in rows if r.get("coverage_excluded")]
        rows = [r for r in rows if not r.get("coverage_excluded")] + excluded_rows

    # "…in the first ODI v WI": a per-match question about a named opponent. The subject must come
    # from a recent match against that team, not from any match in history.
    candidates = rows
    if "match_id" in params["group_by"]:
        opponent = _opponent_in(idea_text, db)
        if opponent:
            recent = set(_recent_matches_against(db, opponent, params.get("fmt") or "ALL"))
            candidates = [r for r in rows if str(r.get("match_id")) in recent]
            if not candidates:
                latest = _latest_loaded(db, params.get("fmt") or "ALL")
                when = f" Latest match loaded: {latest:%d %b %Y}." if latest else ""
                return {"status": "parked",
                        "note": f"No match v {opponent} in the last {MATCH_WINDOW_DAYS} days is loaded yet.{when}"}

    idx = 0
    # Grouped by season, zone, phase, bowler type...: the rows are not people, so the player named in
    # the idea is a filter, not a row to find (finding "Kohli" among years used to park the idea).
    time_rows = label_key in ("year", "wagon_zone", "phase", "bowl_kind", "bowl_style", "line", "length", "shot",
                              "over", "innings", "dismissal", "bat_hand", "match_outcome", "toss_decision")
    mentions = [] if (highlight or time_rows) else _mentions(idea_text)
    if time_rows:
        highlight = None
    if highlight or mentions:
        found = _find(candidates, label_key, highlight) if highlight else _find_mentioned(candidates, label_key, mentions)
        idx = rows.index(candidates[found]) if found is not None else None  # rank in the full ordering
        highlight = highlight or mentions
        if idx is None:
            latest = _latest_loaded(db, params.get("fmt") or "ALL")
            when = f" Latest match loaded: {latest:%d %b %Y}." if latest else ""
            return {"status": "parked", "note": f"{' & '.join(highlight)} not in this query's results yet.{when}"}
    row, total = rows[idx], (int(full.get("total_rows") or len(rows)) - unrankable if unrankable else int(full.get("total_rows") or len(rows)))
    if coverage:
        total = coverage["included"]
        if row.get("coverage_excluded"):
            # Never publish a rank the data can't support: this row's tagged balls are too few.
            pct = row.get(coverage["column"])
            return {"status": "parked",
                    "note": (f"{_row_name(row, label_key)} has {coverage['label']} data for only "
                             f"{(pct if pct is not None else 0):g}% of balls, under the {coverage['min']:g}% minimum, "
                             "so it can't be ranked by this metric. Lower the minimum coverage to include it.")}
    warnings = _coverage_warnings(rows, idx, full.get("coverage_tags") or [], min_coverage, label_key)
    value = float(row[metric])
    parts = title_parts(params, coverage)
    name = _row_name(row, label_key).replace(" & ", " and ")
    title = (f"{name} rank {ordinal(idx + 1)} of {total:,} {parts['scope']}{parts['filters']}{parts['minimum']}{parts['venue']}"
             f"{parts['overs']} for {metric_label(metric)}{parts['window'].replace(',', '')}, {_value_phrase(metric, value)}")
    if time_rows and parts["who"]:
        # Rows are seasons / phases / zones of one player: "2026 rank 1st of 7 T20 years" read badly.
        title = (f"{parts['who']}'s best {readable[0].replace('_', ' ')} for {metric_label(metric).lower()}"
                 f"{parts['window']}: {_split_label(label_key, row.get(label_key))}, {_value_phrase(metric, value)}")

    # The image: the top rows, with the subject swapped in at its true rank when it is lower.
    shown = list(range(min(8, len(rows)))) if idx < 8 else list(range(7)) + [idx]
    fmt_label = {"ODI": "ODI", "T20": "T20"}.get(params.get("fmt"), "")
    data = {
        "title": title, "kicker": " · ".join(filter(None, [fmt_label, *(g.replace("_", " ") + "s" for g in params["group_by"])])),
        "subtitle": full.get("subtitle"), "filter_chips": full.get("filter_chips") or [],
        "group_by": params["group_by"], "query_mode": "ranking",
        "columns": ["rank", "label", metric, "display"], "metric_columns": [metric], "metric_label": metric_label(metric),
        "rows": [{"rank": i + 1, "label": _row_name(rows[i], label_key), metric: float(rows[i][metric]),
                  "display": _value_text(metric, float(rows[i][metric])), "highlight": i == idx} for i in shown],
        "chart": {"type": "bar", "label_key": "label", "metric": metric},
        "hindsight_url": full.get("hindsight_url"), "total_rows": total, "source": "ball-by-ball",
        # Next to "Data as of" on the image: what was filtered, how complete the tagged data is for
        # the subject, and what a shot family contains.
        "footnote": _footnote(params, row, name, coverage, full.get("coverage_tags") or [], full.get("filter_chips") or []),
    }
    # Chart forms (services/pack_charts): every form the data supports gets its own snapshot so the
    # admin page can switch; Jev (or the rule order) picks which one the pack leads with.
    from services import pack_charts

    axes = pack_charts.scatter_axes(planned.get("chart"), metric, rows)
    split_key = params["group_by"][1] if len(params["group_by"]) == 2 else None
    shape = {"group_by": params["group_by"], "rows": len(rows), "metric": metric, "subject": name,
             "has_subject": bool(highlight or mentions), "scatter": axes,
             "entities": len({r.get(label_key) for r in rows}),
             "split_values": len({r.get(split_key) for r in rows}) if split_key else 0,
             "mixed_signs": any(float(r[metric]) < 0 for r in rows[:8]) and any(float(r[metric]) > 0 for r in rows[:8])}
    forms = pack_charts.valid_forms(shape) or ["bars"]
    ranking = pack_charts.rank_forms(idea_text, shape, forms)
    form_data = {"bars": (data, title)}
    if "line" in forms:
        form_data["line"] = _line_form(rows, label_key, metric, idx, data, parts)
    if "scatter" in forms:
        form_data["scatter"] = _scatter_form(rows, label_key, axes, idx, data, name, total, parts)
    if "stat" in forms:
        form_data["stat"] = _stat_form(rows, label_key, metric, idx, total, data, name, parts, title)
    if "diverging" in forms:
        form_data["diverging"] = _diverging_form(rows, label_key, metric, data, parts, title, time_rows)
    if "dumbbell" in forms or "stacked" in forms:
        subject_label = rows[idx].get(label_key) if (highlight or mentions) else None
        if "dumbbell" in forms:
            form_data["dumbbell"] = _dumbbell_form(rows, label_key, split_key, metric, subject_label, data)
        if "stacked" in forms:
            form_data["stacked"] = _stacked_form(_complete_split_rows(db, rows, label_key, query_params),
                                                 label_key, split_key, metric, subject_label, data)
    if "field" in forms:
        form_data["field"] = _field_form(rows, metric, data, parts)
    snaps = {}
    for form in ranking["order"]:
        form_payload, form_title = form_data.get(form, (None, None))
        if form_payload is None:
            continue
        snaps[form] = create_static_snapshot(
            db, "ranking", form_payload, form_title,
            {"idea": idea_text, "params": query_params, "metric": metric, "title": form_title, "form": form},
            created_by=created_by)
    lead = next(f for f in ranking["order"] if f in snaps)
    snap = snaps[lead]
    title = form_data[lead][1]
    chart_options = [{"form": f, "snapshot_id": snaps[f]["id"], "title": form_data[f][1],
                      "p": ranking["probabilities"].get(f)} for f in ranking["order"] if f in snaps]
    fact = {
        "kind": "idea", "subject": name, "title": title,
        "numbers": {"value": round(value, 2), "rank": idx + 1, "total": total, "min_balls": params.get("min_balls"),
                    "years": [d.year for d in (params.get("start_date"), params.get("end_date")) if d]},
        "method": f"Ranked by {metric_label(metric)} among {total:,} {parts['scope']}{parts['overs']}{parts['minimum']}{parts['window']}, "
                  "from ball-by-ball data on Hindsight's query builder.",
        "chart_options": chart_options, "chart_picked_by": ranking["by"],
    }
    fact["warnings"] = warnings
    return {"status": "resolved", "fact": fact, "snapshot": snap}


def _tag_columns(row: Dict[str, Any], coverage: Optional[Dict[str, Any]], tags: List[str]) -> List[str]:
    cols = [coverage["tag"]] if coverage else []
    return cols + [t for t in tags if t not in cols]


def _footnote(params, row, name, coverage, tags, chips) -> str:
    """"ODI · 2001–2026 · control data: 99.9% of Gill and Kohli's balls (90% min) · Pull / hook = ..."."""
    from services.coverage import TAG_LABELS
    from services.shot_families import FAMILIES

    parts = [c for c in chips if c and not str(c).startswith("All formats")][:3]
    for tag in _tag_columns(row, coverage, tags):
        pct = row.get(f"{tag}_coverage_pct")
        if pct is not None:
            floor = f" ({coverage['min']:g}% min)" if coverage and coverage["tag"] == tag else ""
            parts.append(f"{TAG_LABELS.get(tag, tag)} data: {pct:g}% of {name}'s balls{floor}")
    for fam in params.get("shot_family") or []:
        label, shots = FAMILIES.get(str(fam).upper(), (None, ()))
        if label:
            parts.append(f"{label} = {', '.join(shots)}")
    return " · ".join(parts)


def _coverage_warnings(rows, idx, tags, min_coverage, label_key) -> List[str]:
    """A tag filter (shot, line...) counts only tagged balls: say so when the subject, or anyone ranked
    above it, has less tagged data than the floor."""
    if not tags or not min_coverage:
        return []
    out = []
    for i in range(idx + 1):
        for tag in tags:
            pct = rows[i].get(f"{tag}_coverage_pct")
            if pct is not None and pct < min_coverage:
                out.append(f"{_row_name(rows[i], label_key)} (rank {i + 1}) has {tag} data for only {pct:g}% of "
                           f"balls, so their count may be short.")
    return out


def _pack_from_fact(db: Session, idea_id: int, result: Dict[str, Any]) -> Optional[int]:
    fact, snap = result["fact"], result["snapshot"]
    known = [fact["numbers"]]
    errors, warnings = content_rules.check_title(fact["title"], known, fact["subject"])
    if errors:
        warnings = errors + warnings  # an idea's pack is reviewed by hand anyway: show, don't drop
    rank, total = fact["numbers"]["rank"], fact["numbers"]["total"]
    if rank > max(10, total * 0.1):
        warnings.append(f"Ranks {ordinal(rank)} of {total:,}: not a standout, probably not worth posting.")
    previous = db.execute(text("SELECT snapshot_id FROM content_packs WHERE angle_key = :k"),
                          {"k": f"idea:{idea_id}"}).scalar()
    if previous and previous != snap["id"]:
        warnings.insert(0, "Updated with new data since the first version.")
    live = snap["data"].get("hindsight_url") or f"{content_rules.SITE_URL}/query"
    sep = "&" if "?" in live else "?"
    link = f"{live}{sep}utm_source=reddit&utm_campaign=pack-{snap['id']}"
    from database import engine

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO content_packs (match_id, snapshot_id, angle_key, title, first_comment, subreddit, flair,
                                       facts, rule_warnings, status, post_by, source)
            VALUES (NULL, :s, :k, :t, :c, 'r/Cricket', 'Stats', CAST(:f AS jsonb), CAST(:w AS jsonb), 'ready', :pb, 'idea')
            ON CONFLICT (angle_key) WHERE angle_key IS NOT NULL DO UPDATE SET
                title = EXCLUDED.title, first_comment = EXCLUDED.first_comment, facts = EXCLUDED.facts,
                rule_warnings = EXCLUDED.rule_warnings,
                status = CASE WHEN content_packs.snapshot_id IS DISTINCT FROM EXCLUDED.snapshot_id THEN 'ready'
                              ELSE content_packs.status END,
                post_by = CASE WHEN content_packs.snapshot_id IS DISTINCT FROM EXCLUDED.snapshot_id THEN EXCLUDED.post_by
                               ELSE content_packs.post_by END,
                snapshot_id = EXCLUDED.snapshot_id
            RETURNING id
        """), {"s": snap["id"], "k": f"idea:{idea_id}", "t": fact["title"],
               "c": f"{fact['method']}\n\nRun it yourself: {link}\n\nData: Hindsight (hindsightcricket.com), a free cricket stats site.",
               "f": json.dumps({**fact, "alternates": []}, default=str), "w": json.dumps(warnings),
               "pb": content_rules.post_by(date.today())}).first()
    return row[0] if row else None


def _finish(db: Session, idea_id: int, result: Dict[str, Any], planned: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from database import engine

    pack_id = _pack_from_fact(db, idea_id, result) if result["status"] == "resolved" else None
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE content_ideas SET status = :st, note = :note, pack_id = :pack,
                   params = COALESCE(CAST(:params AS jsonb), params),
                   resolved_at = CASE WHEN :st = 'resolved' THEN now() ELSE resolved_at END
            WHERE id = :id
        """), {"id": idea_id, "st": result["status"], "note": result.get("note") or (result.get("fact") or {}).get("title"),
               "pack": pack_id, "params": json.dumps(planned, default=str) if planned else None})
    return {**{k: v for k, v in result.items() if k in ("status", "note")}, "pack_id": pack_id}


def create_idea(text_: str) -> int:
    from database import engine

    with engine.begin() as conn:
        return conn.execute(text("INSERT INTO content_ideas (text, status) VALUES (:t, 'pending') RETURNING id"),
                            {"t": text_.strip()}).scalar()


def process_idea(db: Session, idea_id: int, fmt_choice: Optional[str] = None) -> Dict[str, Any]:
    idea = db.execute(text("SELECT id, text FROM content_ideas WHERE id = :id"), {"id": idea_id}).mappings().first()
    try:
        planned = plan(idea["text"], fmt_choice, db)
        return _finish(db, idea_id, attempt(db, idea["text"], planned), planned)
    except Exception as exc:  # the parser, the query, or a bad plan: record why, keep the queue going
        logger.exception("idea %s failed", idea_id)
        db.rollback()
        return _finish(db, idea_id, {"status": "failed", "note": str(exc)[:300]})


def retry_parked(db: Session) -> Dict[str, int]:
    """Nightly: re-run parked ideas (give up after PARK_DAYS) and watched list/race ideas (a new
    entry -- e.g. today's third century -- refreshes the pack and puts it back in the queue)."""
    counts = {"resolved": 0, "parked": 0, "failed": 0}
    parked = db.execute(text("""
        SELECT id, text, params, created_at, status FROM content_ideas
        WHERE status = 'parked'
           OR (status = 'resolved' AND params ? 'spec' AND created_at >= now() - make_interval(days => :watch))
    """), {"watch": WATCH_DAYS}).mappings().all()
    for idea in parked:
        try:
            if idea["status"] == "parked" and idea["created_at"] < datetime.now(timezone.utc) - timedelta(days=PARK_DAYS):
                result = {"status": "failed", "note": f"Still no data after {PARK_DAYS} days."}
            elif idea["params"]:
                result = attempt(db, idea["text"], idea["params"])
            else:
                result = {"status": "failed", "note": "No stored plan to retry."}
        except Exception as exc:
            db.rollback()
            result = {"status": "failed", "note": str(exc)[:300]}
        _finish(db, idea["id"], result)
        counts[result["status"]] += 1
    return counts
