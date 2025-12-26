"""
Player Summary API (MVP)
=========================
Generates AI-powered player DNA summaries for batters.

This is a simplified MVP version with:
- Batter summaries only
- In-memory caching
- Basic OpenAI integration
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import hashlib
import json
import os
import logging

from database import get_session
from services.player_patterns import detect_batter_patterns, detect_bowler_patterns
from services.player_aliases import resolve_player_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/player-summary", tags=["Player Summary"])

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 500
TEMPERATURE = 0.3

# In-memory cache (use Redis in production)
summary_cache = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class SummaryResponse(BaseModel):
    success: bool
    player_name: str
    player_type: str  # "batter" or "bowler"
    summary: Optional[str] = None
    patterns: Optional[dict] = None  # Include raw patterns for debugging
    error: Optional[str] = None
    cached: bool = False


# =============================================================================
# Prompts
# =============================================================================

BATTER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this batter's playing style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Role: [1 sentence describing their main role based on phase_distribution and style]
⚡ Batting Style: [1 sentence about their approach using style_classification and evidence]
💪 Sweet Spot: [Best matchup from strengths list with key stats]
⚠️ Vulnerability: [Main weakness from weaknesses list, or "No significant weaknesses identified" if empty]
📊 Entry Pattern: [When they typically bat based on entry_pattern and batting_position]

## Rules
1. Be specific - use actual numbers from the data
2. Keep each bullet to ONE sentence
3. Use cricket terminology appropriately
4. If weaknesses list is empty, write "No clear vulnerabilities identified in current dataset"
5. Format numbers nicely (e.g., "SR 145" not "strike_rate: 145.23456")
6. For strengths/weaknesses, mention the context (e.g., "vs left-arm spin in death overs")

## Example Output
🎯 Primary Role: Middle-overs anchor who faces 45% of balls between overs 7-15
⚡ Batting Style: Calculated aggressor (SR 138) who rotates strike exceptionally well (only 28% dots)
💪 Sweet Spot: Devastating against pace in powerplay (SR 152, Avg 48) with strong boundary hitting
⚠️ Vulnerability: Struggles against left-arm orthodox in middle overs (SR 98, Avg 18)
📊 Entry Pattern: Typically bats at #3, entering within the first 3 overs in 72% of innings

Now generate the summary:"""


BOWLER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this bowler's style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Phase: [Which phase they bowl most AND their effectiveness there - include overs%, wickets%, economy]
⚡ Bowling Profile: [Their style classification with key numbers - economy, SR, dot%, wickets per match]
💪 Best Matchup: [Best crease combo from best_crease_combo - these are OVERALL stats, not phase-specific]
⚠️ Weakness: [Worst crease combo from worst_crease_combo OR phase weakness - be specific with numbers]
📊 Usage Pattern: [Which overs they typically bowl with percentages from typical_overs]

## Rules
1. Be SPECIFIC - every bullet must include at least 2 numbers
2. Keep each bullet to ONE sentence
3. Format economy as "Econ 7.2" and strike rate as "SR 18"
4. For crease combos, translate to readable format:
   - "rhb_rhb" = "vs two right-handers"
   - "rhb_lhb" = "vs right-hander with left-hander at non-striker"
   - "lhb_rhb" = "vs left-hander with right-hander at non-striker"
   - "lhb_lhb" = "vs two left-handers"
5. IMPORTANT: crease_combo_stats are OVERALL career stats for the selected filters - do NOT mention any phase when discussing them
6. Use typical_overs data to state actual over numbers (they are 1-indexed in the data)
7. If crease_combo_stats is empty, focus on phase-based strengths/weaknesses for Best Matchup/Weakness
8. Calculate wickets per match from total_wickets / matches

## Example Output
🎯 Primary Phase: Death specialist (50.7% of wickets) with Econ 7.38 and SR 11.5 in overs 16-20.
⚡ Bowling Profile: Restrictive bowler (SR 15.9, Econ 7.1) who builds pressure with 45.5% dots - averages 1.45 wickets per match.
💪 Best Matchup: Excels vs two left-handers (Econ 5.42, SR 10.3, 44% dots).
⚠️ Weakness: Less effective vs two right-handers (Econ 7.41, SR 16.6).
📊 Usage Pattern: Bowls 19th over in 45.5% of matches, typically overs 19, 4, 2 - averages 3.8 overs per match.

Now generate the summary:"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_cache_key(player_name: str, player_type: str, filters: dict) -> str:
    """Generate cache key from player and filters."""
    filter_str = json.dumps(filters, sort_keys=True)
    combined = f"{player_name}:{player_type}:{filter_str}"
    return hashlib.md5(combined.encode()).hexdigest()


def generate_summary_with_llm(patterns: dict, player_type: str) -> str:
    """Call OpenAI to generate summary from patterns."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured - returning pattern-based summary")
        if player_type == "bowler":
            return generate_bowler_fallback_summary(patterns)
        return generate_fallback_summary(patterns)
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        if player_type == "bowler":
            prompt = BOWLER_SUMMARY_PROMPT.format(pattern_json=json.dumps(patterns, indent=2))
        else:
            prompt = BATTER_SUMMARY_PROMPT.format(pattern_json=json.dumps(patterns, indent=2))
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        if player_type == "bowler":
            return generate_bowler_fallback_summary(patterns)
        return generate_fallback_summary(patterns)


def generate_fallback_summary(patterns: dict) -> str:
    """Generate a basic summary without LLM (fallback)."""
    lines = []
    
    # Primary Role
    phase = patterns.get("primary_phase", "balanced")
    style = patterns.get("style_classification", "balanced")
    lines.append(f"🎯 Primary Role: {phase.title()} specialist with {style} approach")
    
    # Batting Style
    sr = patterns.get("overall_strike_rate", 0)
    dot_pct = patterns.get("overall_dot_percentage", 0)
    lines.append(f"⚡ Batting Style: Strike rate of {sr:.0f} with {dot_pct:.1f}% dot balls")
    
    # Sweet Spot
    strengths = patterns.get("strengths", [])
    if strengths:
        s = strengths[0]
        ctx = s.get("context", "")
        sr_val = s.get("strike_rate", 0)
        avg_val = s.get("average", 0)
        lines.append(f"💪 Sweet Spot: Strong {ctx} (SR {sr_val:.0f}, Avg {avg_val:.1f})")
    else:
        lines.append("💪 Sweet Spot: Consistent across all conditions")
    
    # Vulnerability
    weaknesses = patterns.get("weaknesses", [])
    if weaknesses:
        w = weaknesses[0]
        ctx = w.get("context", "")
        sr_val = w.get("strike_rate", 0)
        lines.append(f"⚠️ Vulnerability: Challenges {ctx} (SR {sr_val:.0f})")
    else:
        lines.append("⚠️ Vulnerability: No clear vulnerabilities identified")
    
    # Entry Pattern
    pos = patterns.get("typical_batting_position")
    entry = patterns.get("entry_pattern", "unknown")
    if pos:
        lines.append(f"📊 Entry Pattern: Typically bats at #{pos}, {entry} entry")
    else:
        lines.append(f"📊 Entry Pattern: {entry.title()} entry pattern")
    
    return "\n".join(lines)


def _format_crease_combo(combo: str) -> str:
    """Convert crease combo code to readable format."""
    mapping = {
        # Database format: lhb_lhb, lhb_rhb, rhb_lhb, rhb_rhb
        "rhb_rhb": "vs two right-handers",
        "rhb_lhb": "vs right-hander (left at non-striker)",
        "lhb_rhb": "vs left-hander (right at non-striker)",
        "lhb_lhb": "vs two left-handers",
        # Also support alternate formats just in case
        "Right-Right": "vs two right-handers",
        "Right-Left": "vs right-hander (left at non-striker)",
        "Left-Right": "vs left-hander (right at non-striker)",
        "Left-Left": "vs two left-handers"
    }
    return mapping.get(combo, f"vs {combo}")


def generate_bowler_fallback_summary(patterns: dict) -> str:
    """Generate a basic bowler summary without LLM (fallback)."""
    lines = []
    
    # Primary Phase - Now with wicket stats
    phase_dist = patterns.get("phase_distribution", {})
    
    # Find the dominant phase
    max_phase = None
    max_overs_pct = 0
    max_phase_data = {}
    for phase_name, phase_data in phase_dist.items():
        if isinstance(phase_data, dict):
            overs_pct = phase_data.get("overs_percentage", 0)
            if overs_pct > max_overs_pct:
                max_overs_pct = overs_pct
                max_phase = phase_name
                max_phase_data = phase_data
    
    if max_phase and max_overs_pct > 40:
        wickets_pct = max_phase_data.get("wickets_percentage", 0)
        economy = max_phase_data.get("economy", 0)
        sr = max_phase_data.get("strike_rate", 0)
        lines.append(
            f"🎯 Primary Phase: {max_phase.title()} specialist ({max_overs_pct:.0f}% of overs) "
            f"taking {wickets_pct:.0f}% of wickets with Econ {economy:.2f} and SR {sr:.1f}"
        )
    else:
        lines.append("🎯 Primary Phase: Workhorse who bowls across all phases")
    
    # Bowling Profile - With actual numbers
    economy = patterns.get("overall_economy", 0)
    sr = patterns.get("overall_strike_rate", 0)
    dot_pct = patterns.get("overall_dot_percentage", 0)
    matches = patterns.get("matches", 1)
    wickets = patterns.get("total_wickets", 0)
    wpg = round(wickets / matches, 1) if matches > 0 else 0
    
    profile = patterns.get("profile_classification", "balanced")
    lines.append(
        f"⚡ Bowling Profile: {profile.replace('_', ' ').title()} "
        f"(SR {sr:.1f}, Econ {economy:.2f}, {dot_pct:.1f}% dots) - {wpg} wickets per match"
    )
    
    # Best Matchup - Best crease combo (overall, not phase-specific)
    best_combo = patterns.get("best_crease_combo")
    if best_combo:
        combo_name = _format_crease_combo(best_combo["combo"])
        lines.append(
            f"💪 Best Matchup: Excels {combo_name} "
            f"(Econ {best_combo['economy']:.2f}, SR {best_combo['strike_rate']:.1f}, {best_combo['dot_percentage']:.0f}% dots)"
        )
    else:
        # Fall back to phase strengths
        strengths = patterns.get("strengths", [])
        if strengths:
            s = strengths[0]
            ctx = s.get("context", "")
            econ = s.get("economy", 0)
            sr_val = s.get("strike_rate", 0)
            lines.append(
                f"💪 Best Matchup: Strong {ctx} (Econ {econ:.2f}, SR {sr_val:.1f})"
            )
        else:
            lines.append("💪 Best Matchup: Consistent across all matchups")
    
    # Weakness - Worst crease combo (overall) or phase weakness
    worst_combo = patterns.get("worst_crease_combo")
    if worst_combo and worst_combo.get("economy", 0) >= 8.5:
        combo_name = _format_crease_combo(worst_combo["combo"])
        lines.append(
            f"⚠️ Weakness: Less effective {combo_name} (Econ {worst_combo['economy']:.2f}, SR {worst_combo['strike_rate']:.1f})"
        )
    else:
        weaknesses = patterns.get("weaknesses", [])
        if weaknesses:
            w = weaknesses[0]
            ctx = w.get("context", "")
            econ = w.get("economy", 0)
            lines.append(
                f"⚠️ Weakness: Can be expensive {ctx} (Econ {econ:.2f})"
            )
        else:
            lines.append("⚠️ Weakness: No clear weaknesses identified")
    
    # Usage Pattern - With actual over numbers and percentages
    typical_overs = patterns.get("typical_overs", [])
    overs_per_match = patterns.get("overs_per_match", 0)
    primary_over = patterns.get("primary_over")
    primary_over_pct = patterns.get("primary_over_percentage", 0)
    
    if typical_overs and len(typical_overs) > 0:
        # Get over numbers for display
        over_nums = [str(o["over"]) for o in typical_overs[:3]]
        if primary_over and primary_over_pct > 0:
            lines.append(
                f"📊 Usage Pattern: Bowls over {primary_over} in {primary_over_pct:.0f}% of matches, "
                f"typically overs {', '.join(over_nums)} - {overs_per_match:.1f} overs per match"
            )
        else:
            lines.append(
                f"📊 Usage Pattern: Typically bowls overs {', '.join(over_nums)}, "
                f"averaging {overs_per_match:.1f} overs per match"
            )
    else:
        lines.append(f"📊 Usage Pattern: Flexible usage, averaging {overs_per_match:.1f} overs per match")
    
    return "\n".join(lines)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/batter/{player_name}", response_model=SummaryResponse)
async def get_batter_summary(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    include_patterns: bool = Query(default=False),
    db: Session = Depends(get_session)
):
    """
    Generate AI-powered batting summary for a player.
    
    This endpoint:
    1. Fetches player stats from existing endpoint
    2. Extracts patterns using rule-based detection
    3. Generates natural language summary using LLM
    4. Caches result for subsequent requests
    
    If no competition filters are provided, automatically includes ALL leagues + international (top 20 teams).
    """
    try:
        # Resolve player alias to canonical name
        resolved_name = resolve_player_name(player_name, db)
        logger.info(f"Resolved player name: '{player_name}' -> '{resolved_name}'")
        
        # If no filters provided, use ALL leagues + international
        if not leagues and not include_international:
            logger.info(f"No competition filters provided for {resolved_name}, using all leagues + international")
            leagues_result = db.execute(text(
                "SELECT DISTINCT competition FROM matches WHERE competition IS NOT NULL AND match_type = 'league'"
            )).fetchall()
            leagues = [r[0] for r in leagues_result if r[0]]
            include_international = True
            top_teams = 20
            logger.info(f"Auto-populated {len(leagues)} leagues + international top 20")
        
        # Build filter dict for cache key
        filters = {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "leagues": leagues,
            "include_international": include_international,
            "top_teams": top_teams,
            "venue": venue
        }
        
        # Check cache (use resolved_name for cache key)
        cache_key = get_cache_key(resolved_name, "batter", filters)
        if cache_key in summary_cache:
            logger.info(f"Cache hit for {resolved_name}")
            cached_result = summary_cache[cache_key]
            return SummaryResponse(
                success=True,
                player_name=resolved_name,
                player_type="batter",
                summary=cached_result["summary"],
                patterns=cached_result["patterns"] if include_patterns else None,
                cached=True
            )
        
        # Fetch stats from existing endpoint
        logger.info(f"Fetching stats for {resolved_name}")
        from main import get_player_stats
        
        stats = get_player_stats(
            player_name=resolved_name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            venue=venue,
            db=db
        )
        
        # Handle empty or None stats
        if not stats or not stats.get("overall") or stats.get("overall", {}).get("matches", 0) == 0:
            return SummaryResponse(
                success=False,
                player_name=resolved_name,
                player_type="batter",
                error="No batting statistics found for this player in the selected date range"
            )
        
        # Add player name to stats
        stats["player_name"] = resolved_name
        
        # Detect patterns
        logger.info(f"Detecting patterns for {resolved_name}")
        patterns = detect_batter_patterns(stats)
        
        # Generate summary
        logger.info(f"Generating summary for {resolved_name}")
        summary = generate_summary_with_llm(patterns, "batter")
        
        # Cache result
        summary_cache[cache_key] = {
            "summary": summary,
            "patterns": patterns
        }
        
        logger.info(f"Successfully generated summary for {resolved_name}")
        return SummaryResponse(
            success=True,
            player_name=resolved_name,
            player_type="batter",
            summary=summary,
            patterns=patterns if include_patterns else None,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"Error generating batter summary for {player_name}: {str(e)}", exc_info=True)
        return SummaryResponse(
            success=False,
            player_name=player_name,  # Keep original name in error for debugging
            player_type="batter",
            error=str(e)
        )


@router.get("/bowler/{player_name}", response_model=SummaryResponse)
async def get_bowler_summary(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    include_patterns: bool = Query(default=False),
    db: Session = Depends(get_session)
):
    """
    Generate AI-powered bowling summary for a player.
    
    If no competition filters are provided, automatically includes ALL leagues + international (top 20 teams).
    """
    try:
        # Resolve player alias to canonical name
        resolved_name = resolve_player_name(player_name, db)
        logger.info(f"Resolved bowler name: '{player_name}' -> '{resolved_name}'")
        
        # If no filters provided, use ALL leagues + international
        if not leagues and not include_international:
            logger.info(f"No competition filters provided for bowler {resolved_name}, using all leagues + international")
            leagues_result = db.execute(text(
                "SELECT DISTINCT competition FROM matches WHERE competition IS NOT NULL AND match_type = 'league'"
            )).fetchall()
            leagues = [r[0] for r in leagues_result if r[0]]
            include_international = True
            top_teams = 20
            logger.info(f"Auto-populated {len(leagues)} leagues + international top 20")
        
        filters = {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "leagues": leagues,
            "include_international": include_international,
            "top_teams": top_teams,
            "venue": venue
        }
        
        # Check cache (use resolved_name for cache key)
        cache_key = get_cache_key(resolved_name, "bowler", filters)
        if cache_key in summary_cache:
            logger.info(f"Cache hit for bowler {resolved_name}")
            cached_result = summary_cache[cache_key]
            return SummaryResponse(
                success=True,
                player_name=resolved_name,
                player_type="bowler",
                summary=cached_result["summary"],
                patterns=cached_result["patterns"] if include_patterns else None,
                cached=True
            )
        
        # Fetch bowling stats
        logger.info(f"Fetching bowling stats for {resolved_name}")
        from main import get_player_bowling_stats
        
        stats = get_player_bowling_stats(
            player_name=resolved_name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            venue=venue,
            db=db
        )
        
        # Handle empty or None stats
        if not stats or not stats.get("overall") or stats.get("overall", {}).get("matches", 0) == 0:
            return SummaryResponse(
                success=False,
                player_name=resolved_name,
                player_type="bowler",
                error="No bowling statistics found for this player in the selected date range"
            )
        
        stats["player_name"] = resolved_name
        
        # Detect patterns (pass db and filters for advanced queries)
        logger.info(f"Detecting bowler patterns for {resolved_name}")
        patterns = detect_bowler_patterns(stats, db=db, filters=filters)
        
        # Generate summary
        logger.info(f"Generating bowler summary for {resolved_name}")
        summary = generate_summary_with_llm(patterns, "bowler")
        
        # Cache result
        summary_cache[cache_key] = {
            "summary": summary,
            "patterns": patterns
        }
        
        logger.info(f"Successfully generated bowler summary for {resolved_name}")
        return SummaryResponse(
            success=True,
            player_name=resolved_name,
            player_type="bowler",
            summary=summary,
            patterns=patterns if include_patterns else None,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"Error generating bowler summary for {player_name}: {str(e)}", exc_info=True)
        return SummaryResponse(
            success=False,
            player_name=player_name,  # Keep original name in error for debugging
            player_type="bowler",
            error=str(e)
        )


@router.delete("/cache")
async def clear_summary_cache():
    """Clear the summary cache (admin endpoint)."""
    global summary_cache
    count = len(summary_cache)
    summary_cache = {}
    logger.info(f"Cleared {count} cached summaries")
    return {"cleared": count, "message": f"Successfully cleared {count} cached summaries"}


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    return {
        "total_cached": len(summary_cache),
        "cache_keys": list(summary_cache.keys())[:10]  # Show first 10 keys
    }
