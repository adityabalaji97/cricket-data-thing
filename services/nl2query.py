"""
Natural Language to Query Builder service.
Translates natural language cricket queries into structured filters
for the query builder API.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from openai import OpenAI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 86400  # 24 hours

SYSTEM_PROMPT = """You are a cricket analytics query parser. Convert natural language queries about cricket into structured JSON filters for a ball-by-ball cricket statistics database.

## Output Format
Return a JSON object with these fields:
{
  "filters": { ... },
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

### Delivery detail filters
- "line": list. Valid values: "ON_THE_STUMPS", "OUTSIDE_OFFSTUMP", "DOWN_LEG", "WIDE_OUTSIDE_OFFSTUMP", "WIDE_DOWN_LEG"
- "length": list. Valid values: "GOOD_LENGTH", "YORKER", "FULL", "SHORT", "BACK_OF_A_LENGTH", "FULL_TOSS", "BOUNCER"
- "shot": list. Valid values: "COVER_DRIVE", "STRAIGHT_DRIVE", "ON_DRIVE", "OFF_DRIVE", "FLICK", "PULL", "HOOK", "CUT", "LATE_CUT", "SQUARE_CUT", "SWEEP", "REVERSE_SWEEP", "SLOG", "SLOG_SWEEP", "DEFENDED", "LEFT_ALONE", "GLANCE", "UPPER_CUT", "SCOOP", "PADDLE", "INSIDE_OUT", "LOFTED_DRIVE"
- "control": 0 (uncontrolled) or 1 (controlled)
- "wagon_zone": list of integers 0-8 (wagon wheel zones)
- "dismissal": list. Valid values: "caught", "bowled", "lbw", "run out", "stumped", "caught and bowled", "hit wicket"

### Result filters
- "min_balls": minimum number of balls (for meaningful samples, suggest 20-50)
- "start_date": "YYYY-MM-DD" format
- "end_date": "YYYY-MM-DD" format

## Available group_by columns
venue, country, match_id, competition, year, batting_team, bowling_team, batter, bowler, innings, phase, bat_hand, bowl_style, bowl_kind, crease_combo, line, length, shot, control, wagon_zone, dismissal

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
"""

EXAMPLE_QUERIES = [
    {
        "text": "Kohli vs spin in death overs in IPL",
        "category": "Player matchup"
    },
    {
        "text": "CSK powerplay batting this season",
        "category": "Team analysis"
    },
    {
        "text": "Left arm spinners in the middle overs",
        "category": "Bowling analysis"
    },
    {
        "text": "Top batters against short balls",
        "category": "Shot analysis"
    },
    {
        "text": "Bowled dismissals by length",
        "category": "Dismissal patterns"
    },
    {
        "text": "RCB vs MI head to head batting",
        "category": "Team matchup"
    },
    {
        "text": "Yorker effectiveness in death overs",
        "category": "Delivery analysis"
    },
    {
        "text": "Uncontrolled shots by wagon zone",
        "category": "Shot quality"
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
VALID_GROUP_BY = {
    "venue", "country", "match_id", "competition", "year",
    "batting_team", "bowling_team", "batter", "bowler",
    "innings", "phase", "bat_hand", "bowl_style", "bowl_kind",
    "crease_combo", "line", "length", "shot", "control",
    "wagon_zone", "dismissal"
}


def validate_filters(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize LLM output, stripping invalid values."""
    filters = parsed.get("filters", {})
    validated = {}

    # String list filters (pass through - player/team names can't be validated without DB)
    for key in ["batters", "bowlers", "players", "batting_teams", "bowling_teams", "teams"]:
        if key in filters and isinstance(filters[key], list) and len(filters[key]) > 0:
            validated[key] = filters[key]

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
