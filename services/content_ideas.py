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

from services import content_rules
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
# "3 batter centuries in an ODI innings": count qualifying players within one innings or match.
# The query builder has no such second step, so ideas run it here (see _attempt_rollup).
WITHIN = re.compile(r"\bin\s+(?:a|an|one|the same|a single|single)\s+(?:[\w-]+\s+){0,2}?(innings|match|game)\b", re.I)
NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
MILESTONES = [  # (pattern, member dimension, threshold filter, plural noun)
    (r"centur|hundreds|\b100s\b|tons\b", "batter", {"min_runs": 100}, "centuries"),
    (r"half[- ]centur|fift|\b50s\b", "batter", {"min_runs": 50}, "50+ scores"),
    (r"five[- ]?(?:wicket|fers?)|5[- ]?(?:wicket|fers?|wkt)", "bowler", {"min_wickets": 5}, "five-wicket hauls"),
    (r"four[- ]?(?:wicket|fers?)|4[- ]?(?:wicket|fers?|wkt)", "bowler", {"min_wickets": 4}, "four-wicket hauls"),
    (r"three[- ]?(?:wicket|fers?)|3[- ]?(?:wicket|fers?|wkt)", "bowler", {"min_wickets": 3}, "three-wicket hauls"),
]


def count_within(idea: str) -> Optional[Dict[str, Any]]:
    """{n, unit, member, threshold, noun} for "N <milestones> in an innings/match" ideas, else None."""
    m = WITHIN.search(idea)
    if not m:
        return None
    before = idea[:m.start()]
    counts = [int(t) if t.isdigit() else NUMBER_WORDS[t.lower()]
              for t in re.findall(r"\b(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")\b(?![- ]?(?:wicket|fer|wkt))", before, re.I)]
    counts = [c for c in counts if 2 <= c <= 11]
    milestone = next(((dim, thr, noun) for pat, dim, thr, noun in MILESTONES if re.search(pat, idea, re.I)), None)
    if not counts or not milestone:
        return None
    return {"n": counts[0], "unit": "innings" if m.group(1).lower() == "innings" else "match",
            "member": milestone[0], "threshold": milestone[1], "noun": milestone[2]}


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


def plan(idea: str, fmt_choice: Optional[str], db: Session) -> Dict[str, Any]:
    """Parse the idea into snapshot params: {params, metric, highlight, explanation}."""
    from services.nl2query import log_nl_query_event_background, parse_nl_query

    parsed = parse_nl_query(idea, db=db)
    log_nl_query_event_background(query_text=f"[idea] {idea}", parse_result=parsed, ip_address="admin",
                                  execution_time_ms=None)
    if not parsed.get("success", True) or not parsed.get("group_by"):
        raise SnapshotError(parsed.get("error") or "Could not turn the idea into a query (no grouping).")
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
    rollup = count_within(idea)
    if rollup:
        # Step one is every qualifying player-innings (e.g. every ODI hundred); the count per
        # innings happens in _attempt_rollup. The milestone comes from the words, not the parser.
        for key in ("min_runs", "max_runs", "min_wickets", "max_wickets", "min_balls"):
            filters.pop(key, None)
        filters.update(rollup["threshold"])
        group_by = ["match_id", "innings", rollup["member"]]
        metric = "runs" if rollup["member"] == "batter" else "wickets"
        highlight = None
    elif WITHIN.search(idea) and re.search(r"\b(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")\b", idea, re.I):
        raise SnapshotError("Counting players within one innings or match only works for centuries, fifties and "
                            "wicket hauls so far; the query builder can't express this one yet.")
    params = {**filters, "group_by": group_by, "fmt": fmt, "gender": "male", "query_mode": filters.get("query_mode") or "delivery"}
    return {"params": params, "metric": metric, "highlight": highlight, "rollup": rollup,
            "explanation": parsed.get("explanation")}


def _row_name(row: Dict[str, Any], label_key: str) -> str:
    return str(row.get(label_key) or "")


# Capitalised words in an idea that are not names: formats, competitions, months, sentence words.
NOT_NAMES = {"odi", "odis", "t20", "t20i", "t20is", "ipl", "bbl", "psl", "cpl", "sa20", "test", "tests", "the", "first",
             "second", "third", "fourth", "fifth", "final", "world", "cup", "trophy", "series", "compared", "compare",
             "highest", "lowest", "best", "most", "which", "who", "what", "how", "control", "since", "in", "v", "vs",
             "top", "fastest", "slowest", "biggest", "partnerships", "partnership", "batters", "bowlers", "death",
             "powerplay", "middle", "overs", "strike", "rate", "economy", "runs", "wickets", "and", "with", "for",
             "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
             "november", "december", "wi", "sa", "nz", "aus", "eng", "ind", "pak", "sl", "ban", "afg", "ire", "zim"}


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
    """Index of the first row whose label contains every highlight name's surname."""
    surnames = [n.split()[-1].lower() for n in names if n]
    for i, r in enumerate(rows):
        label = _row_name(r, label_key).lower()
        if surnames and all(s in label for s in surnames):
            return i
    return None


def _value_text(metric: str, value: float) -> str:
    if metric.endswith("percentage"):
        return f"{value:.1f}%"
    return f"{value:,.0f}" if metric in ("runs", "balls", "wickets") else f"{value:.2f}"


def _latest_loaded(db: Session, fmt: str) -> Optional[date]:
    where = "" if fmt == "ALL" else "WHERE format = :fmt"
    return db.execute(text(f"SELECT max(date) FROM matches {where}"), {"fmt": fmt}).scalar()


LOWER_IS_BETTER = {"economy"}


def _ascending(metric: str, group_by: List[str]) -> bool:
    bowling = any(g in ("bowler", "bowling_team") for g in group_by)
    return metric in LOWER_IS_BETTER or (bowling and metric in ("average", "strike_rate"))


def _innings_info(db: Session, match_ids: List[str]) -> Dict[tuple, Dict[str, Any]]:
    """(match_id, innings) -> {team, opp, date}, from the deliveries themselves."""
    rows = db.execute(text("""
        SELECT dd.p_match, dd.inns, MAX(dd.team_bat) AS team, MAX(dd.team_bowl) AS opp, MAX(m.date) AS date
        FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
        WHERE dd.p_match = ANY(:ids) GROUP BY 1, 2
    """), {"ids": match_ids}).mappings()
    return {(str(r["p_match"]), int(r["inns"])): dict(r) for r in rows}


def _first_year(db: Session, fmt: str) -> Optional[int]:
    where = "" if fmt == "ALL" else "WHERE format = :fmt"
    first = db.execute(text(f"SELECT MIN(match_date) FROM delivery_details {where}"), {"fmt": fmt}).scalar()
    return int(str(first)[:4]) if first else None


def _attempt_rollup(db: Session, idea_text: str, planned: Dict[str, Any]) -> Dict[str, Any]:
    """"3 centuries in an ODI innings": every qualifying player-innings, counted per innings/match.

    Result: every innings (or match) with N+ of them, latest first, each with its individual
    performances -- shown as a list image, not bars (the counts are all ~N).
    """
    from services.snapshots import _clean_query_params, _query_data, create_static_snapshot

    rollup, params = planned["rollup"], dict(planned["params"])
    member, n, noun = rollup["member"], int(rollup["n"]), rollup["noun"]
    full = _query_data(db, _clean_query_params({**params, "limit": 20000, "sort_by": planned["metric"]}))
    rows = full.get("rows") or []
    info = _innings_info(db, sorted({str(r["match_id"]) for r in rows}))
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in rows:
        inn = info.get((str(r["match_id"]), int(r["innings"])))
        if not inn:
            continue
        key = (str(r["match_id"]), int(r["innings"])) if rollup["unit"] == "innings" else (str(r["match_id"]),)
        if member == "bowler":  # a bowler's side is the one fielding
            inn = {**inn, "team": inn["opp"], "opp": inn["team"]}
        groups.setdefault(key, []).append({**r, **inn})
    hits = sorted((g for g in groups.values() if len(g) >= n), key=lambda g: g[0]["date"], reverse=True)
    fmt = params.get("fmt") or "ALL"
    fmt_label = {"ODI": "ODI", "T20": "T20", "ALL": ""}.get(fmt, fmt)
    first_year = _first_year(db, fmt)
    unit_noun = f"{fmt_label} {rollup['unit']}".strip()
    units_noun = f"{fmt_label} {'innings' if rollup['unit'] == 'innings' else 'matches'}".strip()
    if not hits:
        return {"status": "failed", "note": f"No {units_noun} with {n}+ {noun} in Hindsight's data since {first_year}."}

    def perf(r: Dict[str, Any]) -> str:
        if member == "batter":
            return f"{r['batter']} {int(r['runs'])} ({int(r['balls'])})"
        return f"{r['bowler']} {int(r['wickets'])}/{int(r['runs'])}"

    list_rows = []
    for g in hits:
        lead = g[0]
        label = f"{lead['team']} v {lead['opp']}"
        members = sorted(g, key=lambda r: r["runs" if member == "batter" else "wickets"], reverse=True)
        list_rows.append({"label": label, "date": lead["date"].isoformat(), "sub": f"{lead['date']:%d %b %Y}",
                          "count": len(g), "display": f"{len(g)} {noun}", "details": [perf(r) for r in members]})

    latest = hits[0][0]
    count = len(hits)
    only = "the only" if count == 1 else f"one of {count}"
    if rollup["unit"] == "innings":
        title = (f"{_poss_team(latest['team'])} {len(hits[0])} {noun} v {latest['opp']} ({latest['date']:%b %Y}) make it "
                 f"{only} {units_noun} with {n}+ {noun} since {first_year}")
    else:  # a match's milestones come from both sides
        title = (f"{latest['team']} v {latest['opp']} ({latest['date']:%b %Y}) had {len(hits[0])} {noun}, "
                 f"{only} {units_noun} with {n}+ since {first_year}")
    data = {
        "layout": "list", "title": title, "kicker": f"{fmt_label} · {'innings' if rollup['unit'] == 'innings' else 'matches'}".strip(" ·"),
        "subtitle": f"Every {unit_noun} with {n}+ {noun}, latest first", "filter_chips": [fmt_label, f"since {first_year}"],
        "group_by": [rollup["unit"]], "query_mode": "ranking", "rows": list_rows, "columns": ["label", "sub", "display", "details"],
        "metric_columns": ["count"], "chart": {"type": "list", "label_key": "label", "metric": "count"},
        "hindsight_url": full.get("hindsight_url"), "total_rows": count, "source": "ball-by-ball",
    }
    snap = create_static_snapshot(db, "ranking", data, title, {"idea": idea_text, "rollup": rollup, "params": params,
                                                               "title": title}, created_by="idea")
    fact = {
        "kind": "idea", "subject": latest["team"], "title": title,
        "numbers": {"count": len(hits[0]), "n": n, "total": count, "rank": 1, "years": [first_year, latest["date"].year],
                    "details": [r["details"] for r in list_rows]},
        "method": f"All {count} {units_noun} in Hindsight's ball-by-ball data since {first_year} with {n}+ {noun}, latest first: "
                  + "; ".join(f"{r['label']} {r['sub']} ({', '.join(r['details'])})" for r in list_rows[:6]) + ".",
    }
    return {"status": "resolved", "fact": fact, "snapshot": snap}


def _poss_team(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def attempt(db: Session, idea_text: str, planned: Dict[str, Any]) -> Dict[str, Any]:
    """Run a planned idea. Returns {status: 'resolved', fact, snapshot} or {status: 'parked', note}."""
    from services.snapshots import create_static_snapshot

    if planned.get("rollup"):
        return _attempt_rollup(db, idea_text, planned)

    params = dict(planned["params"])
    for key in ("start_date", "end_date"):
        if isinstance(params.get(key), str):
            params[key] = date.fromisoformat(params[key])
    metric, highlight = planned.get("metric"), planned.get("highlight")
    query_params = {**planned["params"], "limit": 20000}
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
    mentions = [] if highlight else _mentions(idea_text)
    if highlight or mentions:
        found = _find(candidates, label_key, highlight) if highlight else _find_mentioned(candidates, label_key, mentions)
        idx = rows.index(candidates[found]) if found is not None else None  # rank in the full ordering
        highlight = highlight or mentions
        if idx is None:
            latest = _latest_loaded(db, params.get("fmt") or "ALL")
            when = f" Latest match loaded: {latest:%d %b %Y}." if latest else ""
            return {"status": "parked", "note": f"{' & '.join(highlight)} not in this query's results yet.{when}"}
    row, total = rows[idx], int(full.get("total_rows") or len(rows))
    value = float(row[metric])
    parts = title_parts(params)
    name = _row_name(row, label_key).replace(" & ", " and ")
    title = (f"{name} rank {ordinal(idx + 1)} of {total:,} {parts['scope']}{parts['minimum']}{parts['venue']}{parts['overs']} "
             f"for {metric_label(metric)}{parts['window'].replace(',', '')}, at {_value_text(metric, value)}")

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
    }
    snap = create_static_snapshot(db, "ranking", data, title, {"idea": idea_text, "params": query_params, "metric": metric, "title": title},
                                  created_by="idea")
    fact = {
        "kind": "idea", "subject": name, "title": title,
        "numbers": {"value": round(value, 2), "rank": idx + 1, "total": total, "min_balls": params.get("min_balls"),
                    "years": [d.year for d in (params.get("start_date"), params.get("end_date")) if d]},
        "method": f"Ranked by {metric_label(metric)} among {total:,} {parts['scope']}{parts['overs']}{parts['minimum']}{parts['window']}, "
                  "from ball-by-ball data on Hindsight's query builder.",
    }
    return {"status": "resolved", "fact": fact, "snapshot": snap}


def _pack_from_fact(db: Session, idea_id: int, result: Dict[str, Any]) -> Optional[int]:
    fact, snap = result["fact"], result["snapshot"]
    known = [fact["numbers"]]
    errors, warnings = content_rules.check_title(fact["title"], known, fact["subject"])
    if errors:
        warnings = errors + warnings  # an idea's pack is reviewed by hand anyway: show, don't drop
    rank, total = fact["numbers"]["rank"], fact["numbers"]["total"]
    if rank > max(10, total * 0.1):
        warnings.append(f"Ranks {ordinal(rank)} of {total:,}: not a standout, probably not worth posting.")
    live = snap["data"].get("hindsight_url") or f"{content_rules.SITE_URL}/query"
    sep = "&" if "?" in live else "?"
    link = f"{live}{sep}utm_source=reddit&utm_campaign=pack-{snap['id']}"
    from database import engine

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO content_packs (match_id, snapshot_id, angle_key, title, first_comment, subreddit, flair,
                                       facts, rule_warnings, status, post_by, source)
            VALUES (NULL, :s, :k, :t, :c, 'r/Cricket', 'Stats', CAST(:f AS jsonb), CAST(:w AS jsonb), 'ready', :pb, 'idea')
            ON CONFLICT (angle_key) WHERE angle_key IS NOT NULL DO UPDATE SET title = EXCLUDED.title
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
    """Nightly: re-run parked ideas against the new data; give up after PARK_DAYS."""
    counts = {"resolved": 0, "parked": 0, "failed": 0}
    parked = db.execute(text("SELECT id, text, params, created_at FROM content_ideas WHERE status = 'parked'")).mappings().all()
    for idea in parked:
        try:
            if idea["created_at"] < datetime.now(timezone.utc) - timedelta(days=PARK_DAYS):
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
