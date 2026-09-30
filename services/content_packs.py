"""
Content packs: a Reddit/X-ready post (image, title, first comment, where and when to post) for
each newly loaded match worth covering, queued for a human in the admin "Social" tab.

Facts come from code (services/records.py, services/match_recap.py); Jev ranks how share-worthy
they are; services/content_rules.py checks every title and routes it. Nothing here writes a
number: titles are the facts' own sentences, and a title whose numbers are not in the facts is
refused. Rules and their reasons: docs/content_guidelines.md.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services import content_rules
from services.competition_aliases import canonical_competition
from services.fact_curation import score_facts
from services.records import match_records

logger = logging.getLogger(__name__)

SHARE_CRITERIA = [
    "Dull: no cricket fan would stop scrolling for this",
    "Minor: mildly interesting, to this team's fans only",
    "Interesting: fans of this competition would upvote it",
    "Striking: a record or first that neutral cricket fans would share",
    "Remarkable: an all-time great performance people will be talking about",
]
PER_MATCH = 2
# The "win probability & Impact of X v Y" post is a proven r/Cricket series (550-670 upvotes a
# post), so for high-audience competitions it gets its own slot instead of competing with
# records on Jev's share-worthiness score.
SERIES_COMPETITIONS = {"IPL", "BBL", "PSL", "SA20", "Men's Hundred", "T20I"}
JEV_MIN_SCORE = 2.0      # "Interesting" or better
FALLBACK_MIN_WEIGHT = 4.0


def _recap_fact(db: Session, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The proven "win probability & Impact" series post, for T20s with Primer metrics."""
    if match.get("format") != "T20":
        return None
    from services.match_recap import build_recap
    from services.match_scorecard import get_match_scorecard_service

    try:
        scorecard = get_match_scorecard_service(match_id=str(match["id"]), min_balls=6, db=db)
    except Exception:
        return None
    if not (scorecard.get("summary") or {}).get("primer"):
        return None
    recap = build_recap(scorecard, db)
    if not recap.get("available"):
        return None
    headline = recap["headline"].rstrip(".")
    series = canonical_competition(match.get("competition")) in SERIES_COMPETITIONS
    return {
        "kind": "win_prob", "subject": match["team1"], "team": match.get("winner"), "weight": 5.0, "series": series,
        "title": f"{match['team1']} v {match['team2']} win probability and Impact. {headline}.",
        "numbers": {"headline": recap["headline"], "bullets": recap["bullets"]},
        "method": "Win probability and Impact (runs added to the batting side's projected total) from "
                  "ball-by-ball data, after Ganjoo's T20 Primer. " + " ".join(recap["bullets"]),
    }


def candidate_facts(db: Session, match: Dict[str, Any]) -> List[Dict[str, Any]]:
    facts = match_records(db, match)
    recap = _recap_fact(db, match)
    if recap:
        facts.append(recap)
    for i, f in enumerate(facts):
        f["id"] = f"f{i}"
        f["text"] = f["title"]
    return facts


def choose(facts: List[Dict[str, Any]], match: Dict[str, Any], per_match: int = PER_MATCH) -> List[Dict[str, Any]]:
    if not facts:
        return []
    state = {
        "match": f"{match['team1']} v {match['team2']}, {match.get('competition')} {match['date']}",
        "task": "Each candidate is a verified stat from this match, to be posted as an image on r/Cricket. "
                "Judge how much cricket fans would want to see and share it.",
    }
    series = [f for f in facts if f.get("series")]
    rest = [f for f in facts if not f.get("series")]
    if score_facts(rest, state, "How share-worthy is this stat?", SHARE_CRITERIA):
        ranked = sorted((f for f in rest if (f.get("score") or 0) >= JEV_MIN_SCORE),
                        key=lambda f: (f["score"], f["weight"]), reverse=True)
    else:
        ranked = sorted((f for f in rest if f["weight"] >= FALLBACK_MIN_WEIGHT), key=lambda f: f["weight"], reverse=True)
    return series + ranked[:per_match]


def _ranking_data(fact: Dict[str, Any], match: Dict[str, Any]) -> Dict[str, Any]:
    chart = fact["chart"]
    metric, scope = chart["metric"], fact["scope"]
    return {
        "title": fact["title"],
        "kicker": f"{scope} · {chart['group']}",
        "subtitle": fact["method"],
        "filter_chips": [scope, f"since {fact['since_year']}"],
        "group_by": [chart["group"]],
        "query_mode": "ranking",
        "columns": ["rank", "label", metric, "display"],
        "metric_columns": [metric],
        "rows": chart["rows"],
        "chart": {"type": "bar", "label_key": "label", "metric": metric},
        "hindsight_url": f"{content_rules.SITE_URL}/scorecard/{match['id']}",
        "note": fact["method"],
        "source": f"{scope} since {fact['since_year']} · Hindsight data",
    }


def build_pack(db: Session, match: Dict[str, Any], fact: Dict[str, Any], source: str = "records",
               dry_run: bool = False) -> Optional[Dict[str, Any]]:
    from services.snapshots import create_snapshot, create_static_snapshot

    angle_key = f"{match['id']}:{fact['kind']}:{fact.get('subject') or ''}"
    known = [fact.get("numbers") or {}, {"n": fact.get("n"), "since": fact.get("since_year"), "rank": fact.get("rank")}]
    errors, warnings = content_rules.check_title(fact["title"], known, fact.get("subject"))
    if errors:
        logger.info("pack refused (%s): %s -- %s", angle_key, fact["title"], errors)
        return {"angle_key": angle_key, "title": fact["title"], "refused": errors}
    routing = content_rules.route(match, fact)
    pack = {
        "angle_key": angle_key, "title": fact["title"], "subreddit": routing["subreddit"], "flair": routing["flair"],
        "rule_warnings": warnings, "post_by": content_rules.post_by(match["date"]),
    }
    if dry_run:
        return pack

    if fact["kind"] == "win_prob":
        snap = create_snapshot(db, "win_prob", {"match_id": str(match["id"])}, created_by="packs")
    else:
        snap = create_static_snapshot(db, "ranking", _ranking_data(fact, match), fact["title"],
                                      {"pack": angle_key}, created_by="packs")
    link = content_rules.tracked_url(f"/scorecard/{match['id']}", f"pack-{snap['id']}")
    stored_facts = {k: v for k, v in fact.items() if k not in ("chart", "id", "text")}
    stored_facts["alternates"] = routing["alternates"]
    from database import engine

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO content_packs (match_id, snapshot_id, angle_key, title, first_comment, subreddit, flair,
                                       facts, rule_warnings, status, post_by, source)
            VALUES (:m, :s, :k, :t, :c, :sub, :fl, CAST(:facts AS jsonb), CAST(:w AS jsonb), 'ready', :pb, :src)
            ON CONFLICT (angle_key) WHERE angle_key IS NOT NULL DO NOTHING
            RETURNING id
        """), {"m": str(match["id"]), "s": snap["id"], "k": angle_key, "t": fact["title"],
               "c": content_rules.first_comment(fact, link), "sub": routing["subreddit"], "fl": routing["flair"],
               "facts": json.dumps(stored_facts, default=str), "w": json.dumps(warnings), "pb": pack["post_by"],
               "src": source}).first()
    pack.update(id=row[0] if row else None, snapshot_id=snap["id"], duplicate=row is None)
    return pack


def recent_matches(db: Session, days: int = 10, match_ids: Optional[List[str]] = None,
                   include_done: bool = False) -> List[Dict[str, Any]]:
    """In-scope matches from the last `days` days that have no packs yet (or the given ids)."""
    if match_ids:
        rows = db.execute(text("SELECT * FROM matches WHERE id = ANY(:ids)"), {"ids": [str(m) for m in match_ids]})
    else:
        rows = db.execute(text("""
            SELECT m.* FROM matches m
            WHERE m.date >= :since
              AND (:all OR NOT EXISTS (SELECT 1 FROM content_packs p WHERE p.match_id = m.id))
            ORDER BY m.date DESC
        """), {"since": date.today() - timedelta(days=days), "all": include_done})
    return [dict(r) for r in rows.mappings() if content_rules.in_scope(dict(r))]


def expire(db: Session) -> int:
    from database import engine

    with engine.begin() as conn:
        return conn.execute(text(
            "UPDATE content_packs SET status = 'expired' WHERE status = 'ready' AND post_by < now()"
        )).rowcount


def generate(db: Session, days: int = 10, match_ids: Optional[List[str]] = None, per_match: int = PER_MATCH,
             dry_run: bool = False) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"matches": 0, "packs": [], "refused": [], "expired": 0}
    for match in recent_matches(db, days, match_ids):
        summary["matches"] += 1
        try:
            facts = candidate_facts(db, match)
            for fact in choose(facts, match, per_match):
                pack = build_pack(db, match, fact, "recap" if fact["kind"] == "win_prob" else "records", dry_run)
                (summary["refused"] if pack.get("refused") else summary["packs"]).append(pack)
        except Exception:
            logger.exception("content packs failed for match %s", match.get("id"))
            db.rollback()
    if not dry_run:
        summary["expired"] = expire(db)
    return summary
