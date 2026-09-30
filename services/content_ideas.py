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
from services.snapshots import QUERY_PARAMS, SnapshotError, create_snapshot, metric_label, title_parts

logger = logging.getLogger(__name__)

PARK_DAYS = 14
COMPARE = re.compile(r"\b(compar\w*|vs\.? others?|other|rank\w*|among|against (all|every|other)|best|highest|lowest|record)\b", re.I)
ENTITY_GROUPS = {"batter": "batters", "bowler": "bowlers", "partnership": "batters", "batting_team": "batting_teams",
                 "bowling_team": "bowling_teams"}
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
    metric = _metric_for(idea, parsed)
    params = {**filters, "group_by": group_by, "fmt": fmt, "gender": "male", "query_mode": filters.get("query_mode") or "delivery"}
    return {"params": params, "metric": metric, "highlight": highlight, "explanation": parsed.get("explanation")}


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


def attempt(db: Session, idea_text: str, planned: Dict[str, Any]) -> Dict[str, Any]:
    """Run a planned idea. Returns {status: 'resolved', fact, snapshot} or {status: 'parked', note}."""
    from services.snapshots import create_static_snapshot

    params = dict(planned["params"])
    for key in ("start_date", "end_date"):
        if isinstance(params.get(key), str):
            params[key] = date.fromisoformat(params[key])
    metric, highlight = planned.get("metric"), planned.get("highlight")
    query_params = {**planned["params"], "limit": 500}
    if metric:
        query_params.update(sort_by=metric, sort_descending=not _ascending(metric, params["group_by"]))
    full = create_snapshot(db, "query", query_params, created_by="idea")["data"]
    rows = full.get("rows") or []
    label_key = (full.get("chart") or {}).get("label_key") or params["group_by"][0]
    if not metric or not rows or metric not in rows[0]:
        metric = (full.get("chart") or {}).get("metric")
    if not rows or not metric:
        return {"status": "parked", "note": "The query returned nothing to chart yet."}

    idx = 0
    mentions = [] if highlight else _mentions(idea_text)
    if highlight or mentions:
        idx = _find(rows, label_key, highlight) if highlight else _find_mentioned(rows, label_key, mentions)
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
