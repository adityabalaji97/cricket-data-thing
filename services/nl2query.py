"""
Natural Language to Query Builder service.
Translates natural language cricket queries into structured filters
for the query builder API.
"""
import os
import json
import time
import logging
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI
from sqlalchemy.orm import Session
try:
    from venue_standardization import VENUE_STANDARDIZATION
except Exception:  # pragma: no cover - defensive fallback
    VENUE_STANDARDIZATION = {}

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 86400  # 24 hours

SYSTEM_PROMPT = """You are a cricket analytics query parser. Convert natural language queries about cricket into structured JSON filters for a ball-by-ball cricket statistics database.

## Output Format
Return a JSON object with these fields:
{
  "filters": { ... },
  "query_mode": "delivery" | "batting_stats" | "bowling_stats",
  "group_by": [...],
  "explanation": "Human-readable explanation of what the query does",
  "confidence": "high" | "medium" | "low",
  "suggestions": ["optional improvement suggestions"]
}

## Available Filters

### Player filters
- "batters": list of batter names (use full names, e.g. "V Kohli", "MS Dhoni", "JC Buttler")
- "bowlers": list of bowler names (use full names)
- "players": list of player names (when role is ambiguous)

### Team filters
- "batting_teams": list of full team names
- "bowling_teams": list of full team names
- "teams": list of full team names (when batting/bowling context unclear)
- "venue": a single venue/ground string (e.g. "Eden Gardens")

### League/competition filters
- "leagues": list of league abbreviations. Valid values: "IPL", "BBL", "PSL", "CPL", "SA20", "ILT20", "BPL", "LPL", "T20 Blast", "T20I"
- "include_international": true/false (for international T20I matches)

### Batting hand filter
- "bat_hand": "RHB" or "LHB" (right-hand or left-hand batter)

### Bowling style filters
- "bowl_style": list of specific bowling styles. Valid values: "RF" (right fast), "RFM" (right fast-medium), "RM" (right medium), "LF" (left fast), "LFM" (left fast-medium), "LM" (left medium), "RO" (right off-spin), "RL" (right leg-spin), "LO" (left orthodox/slow left arm), "LC" (left chinaman)
- "bowl_kind": list for broad grouping. Valid values: "pace bowler", "spin bowler", "mixture/unknown"

### Over/phase filters
- "over_min": integer 0-19 (minimum over number)
- "over_max": integer 0-19 (maximum over number)
- Phase mappings:
  - Powerplay: over_min=0, over_max=5
  - Middle overs: over_min=6, over_max=14
  - Death overs: over_min=15, over_max=19

### Innings filter
- "innings": 1 or 2
- "is_chase": true/false (true means innings=2 chases)
- "match_outcome": list. Valid values: "win", "loss", "tie", "no_result" (always batting-side perspective)
- "chase_outcome": list. Valid values: "win", "loss", "tie", "no_result" (applies to innings=2)
- "toss_decision": list. Valid values: "bat", "field"
- "toss_match_outcome": group_by only. Values: "win", "loss", "tie", "no_result".
  Shows match outcome from the TOSS-WINNING team's perspective.

### Query mode
- "query_mode": "delivery" (default), "batting_stats", or "bowling_stats"
- Use "batting_stats" for innings-level batter performance asks (e.g. "Kohli batting stats in chases")
- Use "bowling_stats" for innings-level bowler performance asks (e.g. "Bumrah economy in wins")
- If not explicitly stats-oriented, default to "delivery"

### Delivery detail filters
- "line": list. Valid values: "ON_THE_STUMPS", "OUTSIDE_OFFSTUMP", "DOWN_LEG", "WIDE_OUTSIDE_OFFSTUMP", "WIDE_DOWN_LEG"
- "length": list. Valid values: "GOOD_LENGTH", "YORKER", "FULL", "SHORT", "BACK_OF_A_LENGTH", "FULL_TOSS", "BOUNCER"
- "shot": list. Valid values: "COVER_DRIVE", "STRAIGHT_DRIVE", "ON_DRIVE", "OFF_DRIVE", "FLICK", "PULL", "HOOK", "CUT", "LATE_CUT", "SQUARE_CUT", "SWEEP", "REVERSE_SWEEP", "SLOG", "SLOG_SWEEP", "DEFENDED", "LEFT_ALONE", "GLANCE", "UPPER_CUT", "SCOOP", "PADDLE", "INSIDE_OUT", "LOFTED_DRIVE"
- "control": 0 (uncontrolled) or 1 (controlled)
- "wagon_zone": list of integers 0-8 (wagon wheel zones)
- "dismissal": list. Valid values: "caught", "bowled", "lbw", "run out", "stumped", "caught and bowled", "hit wicket"

### Result filters
- "min_balls": minimum number of balls (for meaningful samples, suggest 20-50)
- "min_runs": minimum runs threshold for grouped/stat queries
- "max_runs": maximum runs threshold for grouped/stat queries
- "min_wickets": minimum wickets threshold (bowling_stats mode)
- "max_wickets": maximum wickets threshold (bowling_stats mode)
- "start_date": "YYYY-MM-DD" format
- "end_date": "YYYY-MM-DD" format

## Available group_by columns
venue, country, match_id, competition, year, batting_team, bowling_team, batter, bowler, innings, phase, match_outcome, chase_outcome, toss_decision, toss_match_outcome, bat_hand, bowl_style, bowl_kind, crease_combo, line, length, shot, control, wagon_zone, dismissal

## Team Name Mappings (use full names in filters)
- CSK → Chennai Super Kings
- MI → Mumbai Indians
- KKR → Kolkata Knight Riders
- GT → Gujarat Titans
- LSG → Lucknow Super Giants
- PBKS / KXIP → Punjab Kings
- RCB → Royal Challengers Bangalore
- DC / DD → Delhi Capitals
- SRH → Sunrisers Hyderabad
- RR → Rajasthan Royals

## League Aliases
- IPL → Indian Premier League
- BBL → Big Bash League
- PSL → Pakistan Super League
- CPL → Caribbean Premier League
- T20I → International Twenty20

## Rules
1. Always include a sensible "group_by" for the query. If the user asks about a specific batter, group by "batter" at minimum.
2. Set "min_balls" to a reasonable value (20-50) for statistical significance unless the user specifies otherwise.
3. For "vs spin" queries, use "bowl_kind": ["spin bowler"]. For specific types like "vs leg spin", use "bowl_style": ["RL", "LC"].
4. For "vs pace" queries, use "bowl_kind": ["pace bowler"].
5. Use correct phase over ranges: powerplay=0-5, middle=6-14, death=15-19.
6. If the query mentions a league (IPL, BBL, etc.), add it to "leagues".
7. If the query is not about cricket or is too vague, set confidence to "low" and add helpful suggestions.
8. Return ONLY valid JSON, no extra text.
9. If the user wants to compare LHB vs RHB (e.g. "vs lhb/rhb"), do NOT set bat_hand as a filter. Instead, add "bat_hand" to group_by.
10. Use the player's full first and last name when possible (e.g. "Jasprit Bumrah" not "J Bumrah", "Virat Kohli" not "V Kohli", "Varun Chakravarthy" not "V Chakravarthy"). The system will resolve names to the database format automatically.
11. When the user asks about toss impact on winning (e.g. "toss decision vs match outcome"), use group_by: ["toss_decision", "toss_match_outcome"] with query_mode: "batting_stats". Do NOT use "match_outcome" for toss analysis — use "toss_match_outcome" instead.
"""

EXAMPLE_QUERIES = [
    {
        "text": "kohli vs spin since 2023",
        "category": "Delivery analysis"
    },
    {
        "text": "csk powerplay batting over the years",
        "category": "Batting stats"
    },
    {
        "text": "MS Dhoni in winning vs losing chases in IPL",
        "category": "Match context"
    },
    {
        "text": "csk in chasing wins since 2018",
        "category": "Team context"
    },
    {
        "text": "varun chakravarthy vs lhb/rhb",
        "category": "Group by bat_hand"
    },
    {
        "text": "bumrah in 2026 grouped by competition",
        "category": "Group by competition"
    },
    {
        "text": "top batters by toss decision in IPL",
        "category": "Toss context"
    },
    {
        "text": "bowling stats for rashid khan by year",
        "category": "Bowling stats"
    }
]


def _get_cache_key(query: str) -> str:
    return query.strip().lower()


def _get_cached(query: str) -> Optional[Dict[str, Any]]:
    key = _get_cache_key(query)
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["result"]
        else:
            del _cache[key]
    return None


def _set_cache(query: str, result: Dict[str, Any]):
    key = _get_cache_key(query)
    _cache[key] = {"result": result, "timestamp": time.time()}


def get_cache_size() -> int:
    # Clean expired entries
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v["timestamp"] >= CACHE_TTL]
    for k in expired:
        del _cache[k]
    return len(_cache)


def call_openai(query: str) -> Dict[str, Any]:
    """Call OpenAI GPT-4o-mini to parse a natural language cricket query."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1000
    )

    content = response.choices[0].message.content
    return json.loads(content)


# Valid values for validation
VALID_BAT_HAND = {"RHB", "LHB"}
VALID_BOWL_STYLE = {"RF", "RFM", "RM", "LF", "LFM", "LM", "RO", "RL", "LO", "LC"}
VALID_BOWL_KIND = {"pace bowler", "spin bowler", "mixture/unknown"}
VALID_LEAGUES = {"IPL", "BBL", "PSL", "CPL", "SA20", "ILT20", "BPL", "LPL", "T20 Blast", "T20I"}
VALID_QUERY_MODE = {"delivery", "batting_stats", "bowling_stats"}
VALID_MATCH_OUTCOME = {"win", "loss", "tie", "no_result"}
VALID_TOSS_DECISION = {"bat", "field"}
VALID_GROUP_BY = {
    "venue", "country", "match_id", "competition", "year",
    "batting_team", "bowling_team", "batter", "bowler",
    "innings", "phase", "bat_hand", "bowl_style", "bowl_kind",
    "crease_combo", "line", "length", "shot", "control",
    "wagon_zone", "dismissal", "match_outcome", "chase_outcome", "toss_decision",
    "toss_match_outcome"
}


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _build_venue_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    candidates: Dict[str, str] = {}
    for alias, canonical in (VENUE_STANDARDIZATION or {}).items():
        if alias and canonical:
            candidates[alias] = canonical
            candidates[canonical] = canonical
    # Ensure key venues are always available even if mapping import fails.
    candidates.setdefault("Eden Gardens", "Eden Gardens")
    candidates.setdefault("Eden Gardens, Kolkata", "Eden Gardens")
    for raw_name, canonical in candidates.items():
        normalized = _normalize_text(raw_name)
        # Avoid very short fragments that cause false matches.
        if len(normalized) < 8 and len(normalized.split()) < 2:
            continue
        if normalized not in lookup:
            lookup[normalized] = canonical
    return lookup


VENUE_LOOKUP = _build_venue_lookup()


def _infer_venue_from_query(query: str) -> Optional[str]:
    normalized_query = f" {_normalize_text(query)} "
    best_match = None
    best_len = -1
    for venue_text, canonical in VENUE_LOOKUP.items():
        token = f" {venue_text} "
        if token in normalized_query and len(venue_text) > best_len:
            best_match = canonical
            best_len = len(venue_text)
    return best_match


def _contains_explicit_end_bound(query: str) -> bool:
    q = (query or "").lower()
    return bool(
        re.search(r"\bbetween\b.+\band\b", q)
        or re.search(r"\bfrom\b.+\bto\b", q)
        or re.search(r"\b(until|till|through|thru|upto|up to|before|ending)\b", q)
    )


def _append_group_by(group_by: List[str], column: str) -> List[str]:
    if column in group_by:
        return group_by
    return [*group_by, column]


def _build_explanation(filters: Dict[str, Any], group_by: List[str]) -> str:
    mode = filters.get("query_mode", "delivery")
    mode_text = {
        "delivery": "delivery-level data",
        "batting_stats": "innings-level batting stats",
        "bowling_stats": "innings-level bowling stats",
    }.get(mode, "delivery-level data")

    scope_bits = []
    if filters.get("batters"):
        scope_bits.append(f"batters {', '.join(filters['batters'])}")
    if filters.get("bowlers"):
        scope_bits.append(f"bowlers {', '.join(filters['bowlers'])}")
    if filters.get("teams"):
        scope_bits.append(f"teams {', '.join(filters['teams'])}")
    if filters.get("venue"):
        scope_bits.append(f"venue {filters['venue']}")

    constraints = []
    if filters.get("min_runs") is not None:
        constraints.append(f"min runs {filters['min_runs']}")
    if filters.get("max_runs") is not None:
        constraints.append(f"max runs {filters['max_runs']}")
    if filters.get("min_wickets") is not None:
        constraints.append(f"min wickets {filters['min_wickets']}")
    if filters.get("max_wickets") is not None:
        constraints.append(f"max wickets {filters['max_wickets']}")
    if filters.get("start_date"):
        constraints.append(f"from {filters['start_date']}")
    if filters.get("end_date"):
        constraints.append(f"to {filters['end_date']}")

    parts = [f"This query retrieves {mode_text}"]
    if scope_bits:
        parts.append(f"for {', '.join(scope_bits)}")
    if constraints:
        parts.append(f"with {', '.join(constraints)}")
    if group_by:
        parts.append(f"grouped by {', '.join(group_by)}")
    return " ".join(parts).strip() + "."


def validate_filters(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize LLM output, stripping invalid values."""
    filters = parsed.get("filters", {})
    validated = {}

    query_mode = parsed.get("query_mode") or filters.get("query_mode")
    if isinstance(query_mode, str) and query_mode in VALID_QUERY_MODE:
        validated["query_mode"] = query_mode

    # String list filters (pass through - player/team names can't be validated without DB)
    for key in ["batters", "bowlers", "players", "batting_teams", "bowling_teams", "teams"]:
        if key in filters and isinstance(filters[key], list) and len(filters[key]) > 0:
            validated[key] = filters[key]
    if "venue" in filters and isinstance(filters["venue"], str) and filters["venue"].strip():
        validated["venue"] = VENUE_STANDARDIZATION.get(filters["venue"].strip(), filters["venue"].strip())

    # Validated enum filters
    # Track if bat_hand should become a group_by (when LLM returns a list like ["RHB", "LHB"])
    _bat_hand_to_group_by = False
    if "bat_hand" in filters:
        val = filters["bat_hand"]
        if isinstance(val, str) and val in VALID_BAT_HAND:
            validated["bat_hand"] = val
        elif isinstance(val, list):
            # Multiple values means "compare by bat_hand" — use group_by, not filter
            _bat_hand_to_group_by = True

    if "bowl_style" in filters and isinstance(filters["bowl_style"], list):
        valid = [v for v in filters["bowl_style"] if v in VALID_BOWL_STYLE]
        if valid:
            validated["bowl_style"] = valid

    if "bowl_kind" in filters and isinstance(filters["bowl_kind"], list):
        valid = [v for v in filters["bowl_kind"] if v in VALID_BOWL_KIND]
        if valid:
            validated["bowl_kind"] = valid

    if "leagues" in filters and isinstance(filters["leagues"], list):
        valid = [v for v in filters["leagues"] if v in VALID_LEAGUES]
        if valid:
            validated["leagues"] = valid

    # Boolean filters
    if "include_international" in filters:
        validated["include_international"] = bool(filters["include_international"])

    # Integer range filters
    if "over_min" in filters and filters["over_min"] is not None:
        validated["over_min"] = max(0, min(19, int(filters["over_min"])))
    if "over_max" in filters and filters["over_max"] is not None:
        validated["over_max"] = max(0, min(19, int(filters["over_max"])))

    if "innings" in filters:
        val = filters["innings"]
        if isinstance(val, int) and val in (1, 2):
            validated["innings"] = val
        elif isinstance(val, list) and len(val) == 1 and val[0] in (1, 2):
            validated["innings"] = val[0]

    if "is_chase" in filters:
        validated["is_chase"] = bool(filters["is_chase"])

    if "match_outcome" in filters and isinstance(filters["match_outcome"], list):
        valid = [str(v).lower() for v in filters["match_outcome"] if str(v).lower() in VALID_MATCH_OUTCOME]
        if valid:
            validated["match_outcome"] = valid

    if "chase_outcome" in filters and isinstance(filters["chase_outcome"], list):
        valid = [str(v).lower() for v in filters["chase_outcome"] if str(v).lower() in VALID_MATCH_OUTCOME]
        if valid:
            validated["chase_outcome"] = valid

    if "toss_decision" in filters and isinstance(filters["toss_decision"], list):
        valid = [str(v).lower() for v in filters["toss_decision"] if str(v).lower() in VALID_TOSS_DECISION]
        if valid:
            validated["toss_decision"] = valid

    if "control" in filters:
        val = filters["control"]
        if isinstance(val, int) and val in (0, 1):
            validated["control"] = val
        elif isinstance(val, list) and len(val) == 1 and val[0] in (0, 1):
            validated["control"] = val[0]

    # List filters for delivery details
    for key in ["line", "length", "shot", "dismissal"]:
        if key in filters and isinstance(filters[key], list) and len(filters[key]) > 0:
            validated[key] = filters[key]

    if "wagon_zone" in filters and isinstance(filters["wagon_zone"], list):
        valid = [v for v in filters["wagon_zone"] if isinstance(v, int) and 0 <= v <= 8]
        if valid:
            validated["wagon_zone"] = valid

    # Result filters
    if "min_balls" in filters and filters["min_balls"] is not None:
        validated["min_balls"] = max(1, int(filters["min_balls"]))
    if "min_runs" in filters and filters["min_runs"] is not None:
        validated["min_runs"] = max(0, int(filters["min_runs"]))
    if "max_runs" in filters and filters["max_runs"] is not None:
        validated["max_runs"] = max(0, int(filters["max_runs"]))
    if "min_wickets" in filters and filters["min_wickets"] is not None:
        validated["min_wickets"] = max(0, int(filters["min_wickets"]))
    if "max_wickets" in filters and filters["max_wickets"] is not None:
        validated["max_wickets"] = max(0, int(filters["max_wickets"]))

    # Date filters
    for key in ["start_date", "end_date"]:
        if key in filters and filters[key]:
            validated[key] = str(filters[key])

    # Validate group_by
    group_by = parsed.get("group_by", [])
    if isinstance(group_by, list):
        group_by = [col for col in group_by if col in VALID_GROUP_BY]
    else:
        group_by = []

    # If bat_hand was a list (e.g. "vs lhb/rhb"), add it to group_by
    if _bat_hand_to_group_by and "bat_hand" not in group_by:
        group_by.append("bat_hand")

    return {
        "filters": validated,
        "group_by": group_by,
        "explanation": parsed.get("explanation", ""),
        "confidence": parsed.get("confidence", "medium"),
        "suggestions": parsed.get("suggestions", [])
    }


def _post_process_result(query: str, result: Dict[str, Any]) -> Dict[str, Any]:
    filters = result.get("filters", {}) or {}
    group_by = result.get("group_by", []) or []
    q_lower = (query or "").lower()

    # Milestone batting rules, e.g. "virat kohli 100+ scores".
    runs_plus_match = re.search(r"\b(\d+)\s*\+\s*(?:score|scores|run|runs)\b", q_lower)
    if runs_plus_match:
        filters["query_mode"] = "batting_stats"
        filters["min_runs"] = max(0, int(runs_plus_match.group(1)))
        group_by = _append_group_by(group_by, "match_id")

    # Bowling milestone rules, including wicketless asks.
    wickets_plus_match = re.search(r"\b(\d+)\s*\+\s*wickets?\b", q_lower)
    if wickets_plus_match:
        filters["query_mode"] = "bowling_stats"
        filters["min_wickets"] = max(0, int(wickets_plus_match.group(1)))
        group_by = _append_group_by(group_by, "match_id")

    if re.search(r"\b(wicketless|0\s*wickets?|without\s+a\s+wicket)\b", q_lower):
        filters["query_mode"] = "bowling_stats"
        filters["max_wickets"] = 0
        group_by = _append_group_by(group_by, "match_id")

    # Venue inference and canonicalization.
    inferred_venue = _infer_venue_from_query(query)
    if inferred_venue:
        filters["venue"] = VENUE_STANDARDIZATION.get(inferred_venue, inferred_venue)
        explicit_venue_grouping = bool(
            ("grouped by" in q_lower and "venue" in q_lower)
            or ("group by" in q_lower and "venue" in q_lower)
            or
            re.search(r"\b(group(?:ed)?\s+by|by)\s+venue\b", q_lower)
            or re.search(r"\bvenue[-\s]?wise\b", q_lower)
        )
        if not explicit_venue_grouping:
            group_by = [col for col in group_by if col != "venue"]

    # Toss analysis: replace match_outcome with toss_match_outcome when toss context detected.
    if "toss" in q_lower and "match_outcome" in group_by:
        group_by = [("toss_match_outcome" if c == "match_outcome" else c) for c in group_by]
        if filters.get("query_mode") == "delivery":
            filters["query_mode"] = "batting_stats"

    # Since-date normalization: keep start_date, drop end_date unless explicitly bounded.
    if "since" in q_lower and not _contains_explicit_end_bound(query):
        since_date_match = re.search(r"\bsince\s+(\d{4}-\d{2}-\d{2})\b", q_lower)
        since_year_match = re.search(r"\bsince\s+(20\d{2})\b", q_lower)
        if since_date_match:
            filters["start_date"] = since_date_match.group(1)
        elif since_year_match:
            filters["start_date"] = f"{since_year_match.group(1)}-01-01"
        filters.pop("end_date", None)

    # Keep query_mode default if absent.
    filters["query_mode"] = filters.get("query_mode", "delivery")

    # Guardrail for wicket filters.
    if filters.get("query_mode") != "bowling_stats":
        filters.pop("min_wickets", None)
        filters.pop("max_wickets", None)

    result["filters"] = filters
    result["group_by"] = group_by
    result["explanation"] = _build_explanation(filters, group_by)
    return result


def resolve_player_names(names: List[str], db: Session) -> List[str]:
    """Resolve LLM-generated player names against the database.

    Uses search_players_with_aliases for fuzzy matching, returning the
    display_name (delivery_details format) for each matched player.
    Falls back to the original name if no match is found.
    """
    from services.player_aliases import search_players_with_aliases

    resolved = []
    for name in names:
        try:
            results = search_players_with_aliases(name, db, limit=1)
            if results:
                resolved.append(results[0]["display_name"])
            else:
                resolved.append(name)
        except Exception as e:
            logger.warning(f"Failed to resolve player name '{name}': {e}")
            resolved.append(name)
    return resolved


def parse_nl_query(query: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """Parse a natural language query into structured filters.

    Returns validated filters, group_by, explanation, confidence, and suggestions.
    """
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Empty query",
            "filters": {},
            "group_by": [],
            "explanation": "",
            "confidence": "low",
            "suggestions": ["Try a query like 'Kohli vs spin in death overs'"]
        }

    # Check cache
    cached = _get_cached(query)
    if cached:
        return cached

    try:
        raw = call_openai(query)
        result = validate_filters(raw)

        # Resolve player names against DB if session available
        if db is not None:
            filters = result["filters"]
            for key in ["batters", "bowlers", "players"]:
                if key in filters and isinstance(filters[key], list):
                    filters[key] = resolve_player_names(filters[key], db)

        result = _post_process_result(query, result)
        result["success"] = True

        _set_cache(query, result)
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return {
            "success": False,
            "error": "Failed to parse LLM response",
            "filters": {},
            "group_by": [],
            "explanation": "",
            "confidence": "low",
            "suggestions": ["Try rephrasing your query"]
        }
    except Exception as e:
        logger.error(f"NL query parsing error: {e}")
        return {
            "success": False,
            "error": str(e),
            "filters": {},
            "group_by": [],
            "explanation": "",
            "confidence": "low",
            "suggestions": ["Try rephrasing your query"]
        }


def get_example_queries() -> List[Dict[str, str]]:
    """Return example queries for the UI."""
    return EXAMPLE_QUERIES
