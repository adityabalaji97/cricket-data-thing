"""
Where a post's X thread sends people: the exact page behind the post, not the bio page.

    post_link(fact)  ->  "/scorecard/1529233?utm_source=x&utm_medium=thread"

  recap, otd the match's scorecard
  debate     the query builder with the question's own query (facts.link, written when the post is built)
  note/record  the note the post comes from
  preview    the match preview (venue page with both teams)
  play       the Guess the Innings game
  spotlight  the player's page, else /links
Every link carries utm_source=x (the usage report counts it) and utm_medium=thread.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

SITE = "hindsightcricket.com"
UTM = {"utm_source": "x", "utm_medium": "thread"}


def _format_slug(fmt: str, gender: str) -> str:
    return "all" if fmt == "ALL" else f"{'mens' if gender == 'male' else 'womens'}-{fmt.lower()}"


def query_path(params: Dict[str, Any], group_by: List[str], fmt: str = "T20", gender: str = "male") -> str:
    """The /query page for these query-builder params (it auto-runs); the twin of mcp_server._hindsight_url."""
    pairs: List[tuple] = []
    for key, value in params.items():
        if value is None or value == [] or value == "" or value is False or (key == "query_mode" and value == "delivery"):
            continue
        if isinstance(value, (list, tuple)):
            pairs.extend((key, str(v)) for v in value)
        elif isinstance(value, bool):
            pairs.append((key, "true"))
        else:
            pairs.append((key, str(value)))
    pairs.extend(("group_by", g) for g in group_by)
    pairs.append(("fmt", _format_slug(fmt, gender)))
    return f"/query?{urlencode(pairs)}"


def _is_team(name: str) -> bool:
    """A team, not a player (a record post's subject can be either)."""
    from models import INTERNATIONAL_TEAMS_RANKED, teams_mapping

    return name in INTERNATIONAL_TEAMS_RANKED or name in teams_mapping or name in teams_mapping.values()


def _path(fact: Dict[str, Any]) -> str:
    if fact.get("link"):
        return fact["link"]
    if fact.get("kind") in ("recap", "otd") and fact.get("match_id"):
        return f"/scorecard/{fact['match_id']}"
    if fact.get("note_slug"):
        return f"/notes/{fact['note_slug']}"
    fx = fact.get("fixture") or {}
    if fact.get("kind") == "preview" and fx.get("venue"):
        return "/venue?" + urlencode({"venue": fx["venue"], "team1": fx.get("team1", ""), "team2": fx.get("team2", "")})
    if fact.get("kind") == "play":
        return "/games/guess-innings"
    if fact.get("subject") and fact.get("subject_role") != "series" and not _is_team(fact["subject"]):  # a series isn't a player
        return "/player?" + urlencode({"name": fact["subject"]})
    return "/links"


def post_link(fact: Optional[Dict[str, Any]]) -> str:
    """The post's page on the site, with the X campaign tags, without the scheme (X links it and counts it as 23)."""
    path = _path(fact or {})
    return f"{SITE}{path}{'&' if '?' in path else '?'}{urlencode(UTM)}"
