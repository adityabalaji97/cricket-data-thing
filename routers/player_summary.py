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
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import hashlib
import json
import os
import logging

from database import get_session
from services.player_patterns import detect_batter_patterns

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
        return generate_fallback_summary(patterns)
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
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
    """
    try:
        # Build filter dict for cache key
        filters = {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "leagues": leagues,
            "include_international": include_international,
            "top_teams": top_teams,
            "venue": venue
        }
        
        # Check cache
        cache_key = get_cache_key(player_name, "batter", filters)
        if cache_key in summary_cache:
            logger.info(f"Cache hit for {player_name}")
            cached_result = summary_cache[cache_key]
            return SummaryResponse(
                success=True,
                player_name=player_name,
                player_type="batter",
                summary=cached_result["summary"],
                patterns=cached_result["patterns"] if include_patterns else None,
                cached=True
            )
        
        # Fetch stats from existing endpoint
        logger.info(f"Fetching stats for {player_name}")
        from main import get_player_stats
        
        stats = get_player_stats(
            player_name=player_name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            venue=venue,
            db=db
        )
        
        # Add player name to stats
        stats["player_name"] = player_name
        
        # Detect patterns
        logger.info(f"Detecting patterns for {player_name}")
        patterns = detect_batter_patterns(stats)
        
        # Generate summary
        logger.info(f"Generating summary for {player_name}")
        summary = generate_summary_with_llm(patterns, "batter")
        
        # Cache result
        summary_cache[cache_key] = {
            "summary": summary,
            "patterns": patterns
        }
        
        logger.info(f"Successfully generated summary for {player_name}")
        return SummaryResponse(
            success=True,
            player_name=player_name,
            player_type="batter",
            summary=summary,
            patterns=patterns if include_patterns else None,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"Error generating batter summary for {player_name}: {str(e)}", exc_info=True)
        return SummaryResponse(
            success=False,
            player_name=player_name,
            player_type="batter",
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
