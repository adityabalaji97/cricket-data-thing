# Natural Language to Query Builder (NL2SQL) - Implementation Spec

> **Goal**: Allow users to query cricket data using natural language instead of manually setting filters.
> 
> **Example**: *"Show me Virat Kohli's performance against leg spinners in death overs"* → Auto-filled Query Builder with results
>
> **Estimated Effort**: 2-3 days  
> **Monetization Potential**: High (this is the premium feature gate)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Why NL2Filters, Not NL2SQL](#2-why-nl2filters-not-nl2sql)
3. [Filter Schema Reference](#3-filter-schema-reference)
4. [LLM Prompt Engineering](#4-llm-prompt-engineering)
5. [Backend Implementation](#5-backend-implementation)
6. [Frontend Implementation](#6-frontend-implementation)
7. [Cost Optimization](#7-cost-optimization)
8. [Error Handling](#8-error-handling)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment & Monitoring](#10-deployment--monitoring)

---

## 1. Architecture Overview

### 1.1 System Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Input    │     │   LLM Service   │     │  Query Builder  │
│                 │     │                 │     │                 │
│ "Kohli vs spin  │────▶│ Parse & Map to  │────▶│ Execute with    │
│  in death overs"│     │ Filter JSON     │     │ pre-filled      │
│                 │     │                 │     │ filters         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │ Structured JSON │
                        │ {               │
                        │   batters: [...],│
                        │   bowler_type:..,│
                        │   over_min: 16   │
                        │ }               │
                        └─────────────────┘
```

### 1.2 Key Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| NL Input Box | React Component | User types natural language query |
| Backend API | FastAPI Endpoint | Sends query to LLM, returns structured filters |
| LLM Service | OpenAI/Anthropic API | Parses NL → structured JSON |
| Query Builder | Existing Component | Receives filters, executes query |

### 1.3 Tech Stack Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | **OpenAI GPT-4o-mini** | Best cost/performance ratio for structured output |
| Fine-tuning | **No** | Few-shot prompting is sufficient and more flexible |
| Output Format | **JSON** | Direct mapping to existing filter structure |
| Caching | **Yes** | Cache common queries to reduce API costs |

---

## 2. Why NL2Filters, Not NL2SQL

### 2.1 The Key Insight

We're **NOT** generating raw SQL. We're mapping natural language to your **existing filter structure**. This is:

- **Safer**: No SQL injection risk, no malformed queries
- **Cheaper**: Smaller output = fewer tokens
- **Easier**: Constrained output space, easier to validate
- **Maintainable**: Filter structure already handles edge cases

### 2.2 Comparison

| Approach | Risk | Complexity | Cost |
|----------|------|------------|------|
| True NL2SQL | High (SQL injection, syntax errors) | Very High | High |
| NL2Filters (ours) | Low (validated JSON) | Medium | Low |

### 2.3 What the LLM Actually Does

```
INPUT:  "Kohli vs left arm spin in powerplay in IPL 2024"

OUTPUT: {
  "filters": {
    "batters": ["V Kohli"],
    "bowler_type": ["LO", "LC"],
    "over_min": 0,
    "over_max": 5,
    "leagues": ["IPL"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  },
  "group_by": ["bowler_type"],
  "explanation": "Filtering for V Kohli batting against left-arm orthodox (LO) and left-arm chinaman (LC) spinners during powerplay overs (0-5) in IPL 2024"
}
```

---

## 3. Filter Schema Reference

### 3.1 Complete Filter Schema

This is the JSON schema the LLM must output. It maps directly to your `QueryFilters` component.

```typescript
interface NL2FiltersOutput {
  filters: {
    // Date filters
    start_date?: string;        // "YYYY-MM-DD" format
    end_date?: string;          // "YYYY-MM-DD" format
    
    // Competition filters
    venue?: string;             // Exact venue name
    leagues?: string[];         // ["IPL", "BBL", "PSL", etc.]
    include_international?: boolean;
    top_teams?: number;         // 5-20, only if include_international=true
    
    // Team filters
    teams?: string[];           // Teams in any role
    batting_teams?: string[];   // Teams when batting
    bowling_teams?: string[];   // Teams when bowling
    
    // Player filters
    batters?: string[];         // Batter names
    bowlers?: string[];         // Bowler names
    
    // Match context
    innings?: 1 | 2;            // 1st or 2nd innings
    over_min?: number;          // 0-19
    over_max?: number;          // 0-19
    
    // Cricket-specific filters
    bowler_type?: string[];     // ["RF", "LO", "RL", etc.]
    striker_batter_type?: "RHB" | "LHB";
    non_striker_batter_type?: "RHB" | "LHB";
    crease_combo?: string;      // "RHB_RHB", "LHB_RHB", etc.
    ball_direction?: string;    // "cover", "midwicket", etc.
    
    // Result filters
    min_balls?: number;         // Minimum sample size
    max_balls?: number;
    min_runs?: number;
    max_runs?: number;
  };
  
  group_by: string[];           // ["phase", "bowler_type", "batter", etc.]
  
  explanation: string;          // Human-readable explanation of the query
  
  confidence: "high" | "medium" | "low";  // How confident the LLM is
  
  suggestions?: string[];       // Alternative interpretations if ambiguous
}
```

### 3.2 Valid Values Reference

#### Bowler Types
```javascript
const BOWLER_TYPES = {
  // Pace
  "RF": "Right-arm Fast",
  "RFM": "Right-arm Fast-Medium", 
  "RM": "Right-arm Medium",
  "LF": "Left-arm Fast",
  "LFM": "Left-arm Fast-Medium",
  "LM": "Left-arm Medium",
  
  // Spin
  "RO": "Right-arm Off-spin",
  "RL": "Right-arm Leg-spin (Leg Break)",
  "LO": "Left-arm Orthodox",
  "LC": "Left-arm Chinaman (Unorthodox)"
};

// Groupings for common terms
const BOWLER_TYPE_ALIASES = {
  "pace": ["RF", "RFM", "RM", "LF", "LFM", "LM"],
  "fast": ["RF", "RFM", "LF", "LFM"],
  "medium": ["RM", "LM"],
  "spin": ["RO", "RL", "LO", "LC"],
  "off spin": ["RO"],
  "leg spin": ["RL"],
  "left arm spin": ["LO", "LC"],
  "right arm spin": ["RO", "RL"],
  "orthodox": ["LO"],
  "chinaman": ["LC"],
  "wrist spin": ["RL", "LC"],
  "finger spin": ["RO", "LO"]
};
```

#### Phase Mappings (Over Ranges)
```javascript
const PHASE_MAPPINGS = {
  "powerplay": { over_min: 0, over_max: 5 },
  "pp": { over_min: 0, over_max: 5 },
  "middle overs": { over_min: 6, over_max: 14 },
  "middle": { over_min: 6, over_max: 14 },
  "death": { over_min: 16, over_max: 19 },
  "death overs": { over_min: 16, over_max: 19 },
  "slog overs": { over_min: 16, over_max: 19 }
};
```

#### League Names
```javascript
const LEAGUE_ALIASES = {
  "ipl": "IPL",
  "indian premier league": "IPL",
  "bbl": "BBL",
  "big bash": "BBL",
  "psl": "PSL",
  "pakistan super league": "PSL",
  "cpl": "CPL",
  "caribbean premier league": "CPL",
  "the hundred": "The Hundred",
  "hundred": "The Hundred",
  "sa20": "SA20",
  "msl": "MSL",
  "bpl": "BPL",
  "lpl": "LPL",
  "ilt20": "ILT20"
};
```

#### Group By Columns
```javascript
const VALID_GROUP_BY = [
  "venue",
  "match_id", 
  "crease_combo",
  "ball_direction",
  "bowler_type",
  "striker_batter_type",
  "non_striker_batter_type",
  "innings",
  "batting_team",
  "bowling_team",
  "batter",
  "bowler",
  "competition",
  "year",
  "phase"
];
```

### 3.3 Player Name Handling

**Critical**: Player names in the database use a specific format. The LLM needs to handle variations:

```javascript
const PLAYER_NAME_EXAMPLES = {
  // Database format: "FirstInitial LastName" or "Full FirstName LastName"
  "Virat Kohli": "V Kohli",
  "Rohit Sharma": "RG Sharma", 
  "MS Dhoni": "MS Dhoni",
  "Jasprit Bumrah": "JJ Bumrah",
  "Rashid Khan": "Rashid Khan",
  
  // The LLM should try common variations
  // Backend will do fuzzy matching as fallback
};
```

---

## 4. LLM Prompt Engineering

### 4.1 System Prompt

This is the core prompt that instructs the LLM how to parse cricket queries.

```python
SYSTEM_PROMPT = """You are a cricket analytics query parser. Your job is to convert natural language questions about cricket into structured filter parameters.

## Your Task
Convert the user's natural language query into a JSON object with filters and groupings that can be used to query a cricket ball-by-ball database.

## Output Format
Always respond with a valid JSON object in this exact format:
{
  "filters": { ... },
  "group_by": [...],
  "explanation": "...",
  "confidence": "high|medium|low",
  "suggestions": [...] // optional, only if query is ambiguous
}

## Cricket Domain Knowledge

### Bowler Types (use these exact codes)
PACE:
- RF = Right-arm Fast
- RFM = Right-arm Fast-Medium
- RM = Right-arm Medium
- LF = Left-arm Fast
- LFM = Left-arm Fast-Medium
- LM = Left-arm Medium

SPIN:
- RO = Right-arm Off-spin
- RL = Right-arm Leg-spin/Leg-break
- LO = Left-arm Orthodox (slow left-arm)
- LC = Left-arm Chinaman/Unorthodox

Common groupings:
- "pace/pacers/fast bowlers" = ["RF", "RFM", "RM", "LF", "LFM", "LM"]
- "spin/spinners" = ["RO", "RL", "LO", "LC"]
- "left-arm spin" = ["LO", "LC"]
- "right-arm spin" = ["RO", "RL"]
- "wrist spin" = ["RL", "LC"]
- "finger spin" = ["RO", "LO"]
- "leg spin" = ["RL"]
- "off spin" = ["RO"]

### Match Phases (T20 overs 0-19)
- Powerplay/PP: over_min=0, over_max=5 (overs 1-6)
- Middle overs: over_min=6, over_max=14 (overs 7-15)
- Death overs: over_min=16, over_max=19 (overs 17-20)

### Leagues
Use these exact names: IPL, BBL, PSL, CPL, MSL, LPL, BPL, SA20, ILT20, The Hundred, MLC

### Player Names
Players are stored as "FirstInitial LastName" (e.g., "V Kohli", "JJ Bumrah", "MS Dhoni").
If unsure of exact format, use the most likely variation.

### Batter Types
- RHB = Right-hand batter
- LHB = Left-hand batter

### Crease Combinations (striker_nonstriker)
- RHB_RHB, RHB_LHB, LHB_RHB, LHB_LHB

### Valid group_by columns
venue, match_id, crease_combo, ball_direction, bowler_type, striker_batter_type, 
non_striker_batter_type, innings, batting_team, bowling_team, batter, bowler, 
competition, year, phase

## Rules
1. ALWAYS set min_balls (usually 10-50) for grouped queries to filter out small samples
2. When user mentions a year like "2024", set start_date="2024-01-01" and end_date="2024-12-31"
3. When user mentions "this year" or "recent", use start_date from current year
4. If query is about a specific player's batting, use "batters" field
5. If query is about a specific player's bowling, use "bowlers" field
6. Choose appropriate group_by based on what the user wants to compare
7. For team vs team queries, use batting_teams and bowling_teams appropriately
8. Set confidence="low" if the query is ambiguous and provide suggestions

## Examples

User: "Kohli vs spin in death overs in IPL"
{
  "filters": {
    "batters": ["V Kohli"],
    "bowler_type": ["RO", "RL", "LO", "LC"],
    "over_min": 16,
    "over_max": 19,
    "leagues": ["IPL"],
    "min_balls": 10
  },
  "group_by": ["bowler_type"],
  "explanation": "V Kohli's batting performance against all spin types during death overs (16-19) in IPL matches, grouped by specific spin type",
  "confidence": "high"
}

User: "Compare CSK and MI batting in powerplay"
{
  "filters": {
    "over_min": 0,
    "over_max": 5,
    "min_balls": 50
  },
  "group_by": ["batting_team", "phase"],
  "explanation": "Comparing Chennai Super Kings and Mumbai Indians batting performance during powerplay overs, showing team-wise breakdown",
  "confidence": "high"
}

User: "How does Bumrah perform against left-handers?"
{
  "filters": {
    "bowlers": ["JJ Bumrah"],
    "striker_batter_type": "LHB",
    "min_balls": 20
  },
  "group_by": ["phase"],
  "explanation": "JJ Bumrah's bowling performance against left-hand batters, broken down by match phase",
  "confidence": "high"
}

User: "Best batters at Wankhede in 2024"
{
  "filters": {
    "venue": "Wankhede Stadium, Mumbai",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "min_balls": 30
  },
  "group_by": ["batter"],
  "explanation": "Top batting performers at Wankhede Stadium in 2024, filtered to batters with at least 30 balls faced",
  "confidence": "high"
}

User: "Rashid Khan's economy rate by phase"
{
  "filters": {
    "bowlers": ["Rashid Khan"],
    "min_balls": 30
  },
  "group_by": ["phase"],
  "explanation": "Rashid Khan's bowling statistics broken down by match phase (powerplay, middle, death)",
  "confidence": "high"
}
"""
```

### 4.2 Few-Shot Examples (Additional)

Add these to the prompt for better coverage:

```python
ADDITIONAL_EXAMPLES = """
User: "Left-right batting combinations vs spin"
{
  "filters": {
    "bowler_type": ["RO", "RL", "LO", "LC"],
    "min_balls": 100
  },
  "group_by": ["crease_combo"],
  "explanation": "Analysis of how different batting hand combinations (LHB-RHB, RHB-RHB, etc.) perform against spin bowling",
  "confidence": "high"
}

User: "Death bowling specialists"
{
  "filters": {
    "over_min": 16,
    "over_max": 19,
    "min_balls": 100
  },
  "group_by": ["bowler"],
  "explanation": "Bowlers with significant death overs experience, showing their performance statistics",
  "confidence": "high"
}

User: "RCB vs MI head to head"
{
  "filters": {
    "teams": ["Royal Challengers Bangalore", "Mumbai Indians"],
    "min_balls": 50
  },
  "group_by": ["batting_team", "phase"],
  "explanation": "Head-to-head comparison between RCB and MI across different match phases",
  "confidence": "high"
}

User: "Which direction does Dhoni score most?"
{
  "filters": {
    "batters": ["MS Dhoni"],
    "min_balls": 20
  },
  "group_by": ["ball_direction"],
  "explanation": "MS Dhoni's scoring distribution by ball direction (cover, midwicket, etc.)",
  "confidence": "high"
}
"""
```

---

## 5. Backend Implementation

### 5.1 New API Endpoint

Create a new file: `routers/nl2query.py`

```python
"""
Natural Language to Query Builder API
=====================================
Converts natural language cricket queries to structured filter parameters.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import openai
import json
import hashlib
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nl2query", tags=["Natural Language Query"])

# ============================================================================
# Configuration
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Cost-effective, good at structured output
MAX_TOKENS = 1000
TEMPERATURE = 0.1  # Low temperature for consistent structured output

# Simple in-memory cache (replace with Redis in production)
query_cache: Dict[str, Dict] = {}
CACHE_TTL_HOURS = 24

# ============================================================================
# Request/Response Models
# ============================================================================

class NLQueryRequest(BaseModel):
    """Request model for natural language query."""
    query: str = Field(..., min_length=3, max_length=500, description="Natural language query")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context (current filters, etc.)")

class FilterOutput(BaseModel):
    """Structured filter output."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    venue: Optional[str] = None
    leagues: Optional[List[str]] = None
    include_international: Optional[bool] = None
    top_teams: Optional[int] = None
    teams: Optional[List[str]] = None
    batting_teams: Optional[List[str]] = None
    bowling_teams: Optional[List[str]] = None
    batters: Optional[List[str]] = None
    bowlers: Optional[List[str]] = None
    innings: Optional[int] = None
    over_min: Optional[int] = None
    over_max: Optional[int] = None
    bowler_type: Optional[List[str]] = None
    striker_batter_type: Optional[str] = None
    non_striker_batter_type: Optional[str] = None
    crease_combo: Optional[str] = None
    ball_direction: Optional[str] = None
    min_balls: Optional[int] = None
    max_balls: Optional[int] = None
    min_runs: Optional[int] = None
    max_runs: Optional[int] = None

class NLQueryResponse(BaseModel):
    """Response model for natural language query."""
    success: bool
    filters: Optional[FilterOutput] = None
    group_by: List[str] = []
    explanation: str
    confidence: str = "medium"
    suggestions: Optional[List[str]] = None
    query_url: Optional[str] = None  # Pre-built URL for Query Builder
    error: Optional[str] = None
    cached: bool = False

# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """You are a cricket analytics query parser. Your job is to convert natural language questions about cricket into structured filter parameters.

## Your Task
Convert the user's natural language query into a JSON object with filters and groupings that can be used to query a cricket ball-by-ball database.

## Output Format
Always respond with a valid JSON object in this exact format:
{
  "filters": { ... },
  "group_by": [...],
  "explanation": "...",
  "confidence": "high|medium|low",
  "suggestions": [...] // optional, only if query is ambiguous
}

## Cricket Domain Knowledge

### Bowler Types (use these exact codes)
PACE: RF (Right Fast), RFM (Right Fast-Medium), RM (Right Medium), LF (Left Fast), LFM (Left Fast-Medium), LM (Left Medium)
SPIN: RO (Right Off-spin), RL (Right Leg-spin), LO (Left Orthodox), LC (Left Chinaman)

Common groupings:
- "pace/pacers/fast bowlers" = ["RF", "RFM", "RM", "LF", "LFM", "LM"]
- "spin/spinners" = ["RO", "RL", "LO", "LC"]
- "left-arm spin" = ["LO", "LC"]
- "leg spin/leggies" = ["RL"]
- "off spin/offies" = ["RO"]
- "wrist spin" = ["RL", "LC"]

### Match Phases (T20 overs 0-19, 0-indexed)
- Powerplay/PP: over_min=0, over_max=5
- Middle overs: over_min=6, over_max=14
- Death overs: over_min=16, over_max=19

### Leagues
Use exact names: IPL, BBL, PSL, CPL, MSL, LPL, BPL, SA20, ILT20, The Hundred, MLC

### Player Names
Format: "FirstInitial LastName" (e.g., "V Kohli", "JJ Bumrah", "MS Dhoni", "RG Sharma")

### Batter Types
- RHB = Right-hand batter
- LHB = Left-hand batter

### Valid group_by columns
venue, match_id, crease_combo, ball_direction, bowler_type, striker_batter_type, non_striker_batter_type, innings, batting_team, bowling_team, batter, bowler, competition, year, phase

## Rules
1. ALWAYS set min_balls (10-100) for grouped queries
2. Year "2024" means start_date="2024-01-01", end_date="2024-12-31"
3. "this year" or "recent" means current year
4. Player batting stats → use "batters" field
5. Player bowling stats → use "bowlers" field
6. Set confidence="low" if ambiguous, provide suggestions
7. For vs queries (X vs Y bowling type), the player is batting

## Examples

User: "Kohli vs spin in death overs in IPL"
{"filters":{"batters":["V Kohli"],"bowler_type":["RO","RL","LO","LC"],"over_min":16,"over_max":19,"leagues":["IPL"],"min_balls":10},"group_by":["bowler_type"],"explanation":"V Kohli batting against spin in death overs in IPL","confidence":"high"}

User: "Bumrah against left-handers"
{"filters":{"bowlers":["JJ Bumrah"],"striker_batter_type":"LHB","min_balls":20},"group_by":["phase"],"explanation":"JJ Bumrah bowling to left-hand batters by phase","confidence":"high"}

User: "Best death bowlers in IPL 2024"
{"filters":{"leagues":["IPL"],"start_date":"2024-01-01","end_date":"2024-12-31","over_min":16,"over_max":19,"min_balls":50},"group_by":["bowler"],"explanation":"Top death overs bowlers in IPL 2024","confidence":"high"}

User: "CSK vs MI batting comparison"
{"filters":{"teams":["Chennai Super Kings","Mumbai Indians"],"min_balls":100},"group_by":["batting_team","phase"],"explanation":"CSK and MI batting comparison by phase","confidence":"high"}
"""

# ============================================================================
# Helper Functions
# ============================================================================

def get_cache_key(query: str) -> str:
    """Generate cache key from query."""
    normalized = query.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()

def is_cache_valid(cache_entry: Dict) -> bool:
    """Check if cache entry is still valid."""
    if "timestamp" not in cache_entry:
        return False
    cached_time = datetime.fromisoformat(cache_entry["timestamp"])
    return datetime.now() - cached_time < timedelta(hours=CACHE_TTL_HOURS)

def build_query_url(filters: Dict, group_by: List[str]) -> str:
    """Build Query Builder URL from filters."""
    from urllib.parse import urlencode
    
    params = []
    
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                params.append((key, item))
        elif isinstance(value, bool):
            params.append((key, str(value).lower()))
        else:
            params.append((key, value))
    
    for col in group_by:
        params.append(("group_by", col))
    
    return f"/query?{urlencode(params)}"

def call_openai(query: str) -> Dict:
    """Call OpenAI API to parse query."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        response_format={"type": "json_object"}  # Ensure JSON output
    )
    
    content = response.choices[0].message.content
    return json.loads(content)

def validate_and_clean_filters(raw_filters: Dict) -> Dict:
    """Validate and clean filter values."""
    cleaned = {}
    
    # Valid bowler types
    valid_bowler_types = {"RF", "RFM", "RM", "LF", "LFM", "LM", "RO", "RL", "LO", "LC"}
    
    # Valid group_by columns
    valid_group_by = {
        "venue", "match_id", "crease_combo", "ball_direction", "bowler_type",
        "striker_batter_type", "non_striker_batter_type", "innings",
        "batting_team", "bowling_team", "batter", "bowler", "competition", "year", "phase"
    }
    
    for key, value in raw_filters.items():
        if value is None:
            continue
            
        # Validate bowler_type
        if key == "bowler_type" and isinstance(value, list):
            cleaned[key] = [v for v in value if v in valid_bowler_types]
            if not cleaned[key]:
                del cleaned[key]
            continue
        
        # Validate over ranges
        if key in ["over_min", "over_max"]:
            if isinstance(value, int) and 0 <= value <= 19:
                cleaned[key] = value
            continue
        
        # Validate innings
        if key == "innings":
            if value in [1, 2]:
                cleaned[key] = value
            continue
        
        # Pass through other values
        cleaned[key] = value
    
    return cleaned

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/parse", response_model=NLQueryResponse)
async def parse_natural_language_query(request: NLQueryRequest):
    """
    Parse a natural language cricket query into structured filters.
    
    Example queries:
    - "Kohli vs spin in death overs"
    - "Best powerplay bowlers in IPL 2024"
    - "CSK batting at Chepauk"
    """
    try:
        query = request.query.strip()
        
        # Check cache first
        cache_key = get_cache_key(query)
        if cache_key in query_cache and is_cache_valid(query_cache[cache_key]):
            cached = query_cache[cache_key]
            return NLQueryResponse(
                success=True,
                filters=FilterOutput(**cached["filters"]),
                group_by=cached["group_by"],
                explanation=cached["explanation"],
                confidence=cached["confidence"],
                suggestions=cached.get("suggestions"),
                query_url=cached["query_url"],
                cached=True
            )
        
        # Call LLM
        logger.info(f"Parsing NL query: {query}")
        llm_response = call_openai(query)
        
        # Validate and clean filters
        raw_filters = llm_response.get("filters", {})
        cleaned_filters = validate_and_clean_filters(raw_filters)
        
        group_by = llm_response.get("group_by", [])
        # Validate group_by
        valid_group_by = {
            "venue", "match_id", "crease_combo", "ball_direction", "bowler_type",
            "striker_batter_type", "non_striker_batter_type", "innings",
            "batting_team", "bowling_team", "batter", "bowler", "competition", "year", "phase"
        }
        group_by = [g for g in group_by if g in valid_group_by]
        
        explanation = llm_response.get("explanation", "Query parsed successfully")
        confidence = llm_response.get("confidence", "medium")
        suggestions = llm_response.get("suggestions")
        
        # Build Query Builder URL
        query_url = build_query_url(cleaned_filters, group_by)
        
        # Cache the result
        cache_entry = {
            "filters": cleaned_filters,
            "group_by": group_by,
            "explanation": explanation,
            "confidence": confidence,
            "suggestions": suggestions,
            "query_url": query_url,
            "timestamp": datetime.now().isoformat()
        }
        query_cache[cache_key] = cache_entry
        
        return NLQueryResponse(
            success=True,
            filters=FilterOutput(**cleaned_filters),
            group_by=group_by,
            explanation=explanation,
            confidence=confidence,
            suggestions=suggestions,
            query_url=query_url,
            cached=False
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return NLQueryResponse(
            success=False,
            explanation="Failed to parse LLM response",
            error="Invalid response format from AI"
        )
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return NLQueryResponse(
            success=False,
            explanation="AI service temporarily unavailable",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error parsing query: {e}")
        return NLQueryResponse(
            success=False,
            explanation="An error occurred while parsing your query",
            error=str(e)
        )

@router.get("/examples")
async def get_example_queries():
    """Get example natural language queries for the UI."""
    return {
        "examples": [
            {
                "query": "Kohli vs spin in death overs",
                "category": "Player Analysis"
            },
            {
                "query": "Best powerplay bowlers in IPL 2024",
                "category": "Leaderboards"
            },
            {
                "query": "Left-right batting combinations vs leg spin",
                "category": "Advanced Analysis"
            },
            {
                "query": "CSK vs MI head to head batting",
                "category": "Team Comparison"
            },
            {
                "query": "Bumrah's economy by phase",
                "category": "Player Analysis"
            },
            {
                "query": "Scoring at Chinnaswamy in death overs",
                "category": "Venue Analysis"
            }
        ]
    }

@router.get("/health")
async def health_check():
    """Check if NL2Query service is configured and ready."""
    return {
        "status": "ok" if OPENAI_API_KEY else "not_configured",
        "model": OPENAI_MODEL,
        "cache_size": len(query_cache)
    }
```

### 5.2 Register Router in main.py

Add to your `main.py`:

```python
# Add import at top
from routers.nl2query import router as nl2query_router

# Register router (after other routers)
app.include_router(nl2query_router)
```

### 5.3 Environment Variables

Add to your `.env` or environment:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

---

## 6. Frontend Implementation

### 6.1 New Component: `NLQueryInput.jsx`

Create file: `src/components/NLQueryInput.jsx`

```jsx
import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Collapse,
  IconButton,
  Tooltip,
  Fade
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import CloseIcon from '@mui/icons-material/Close';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import config from '../config';

// Example queries to show users
const EXAMPLE_QUERIES = [
  "Kohli vs spin in death overs",
  "Best powerplay bowlers in IPL 2024",
  "CSK batting at Chepauk",
  "Bumrah against left-handers",
  "Left-right combinations vs leg spin"
];

/**
 * NLQueryInput Component
 * 
 * Provides a natural language input for querying cricket data.
 * Converts user input to Query Builder filters using AI.
 * 
 * @param {function} onFiltersGenerated - Callback with generated filters (optional, for embedding)
 * @param {boolean} autoNavigate - Whether to auto-navigate to Query Builder (default: true)
 * @param {boolean} showExamples - Whether to show example queries (default: true)
 * @param {string} placeholder - Custom placeholder text
 */
const NLQueryInput = ({ 
  onFiltersGenerated,
  autoNavigate = true,
  showExamples = true,
  placeholder = "Ask anything about cricket... e.g., 'Kohli vs spin in death overs'"
}) => {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  
  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);
  
  const handleSubmit = async (e) => {
    e?.preventDefault();
    
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await axios.post(`${config.API_URL}/nl2query/parse`, {
        query: query.trim()
      });
      
      if (response.data.success) {
        setResult(response.data);
        
        // Call callback if provided
        if (onFiltersGenerated) {
          onFiltersGenerated({
            filters: response.data.filters,
            groupBy: response.data.group_by
          });
        }
        
        // Auto-navigate to Query Builder if enabled
        if (autoNavigate && response.data.query_url) {
          // Small delay to show the explanation
          setTimeout(() => {
            navigate(response.data.query_url);
          }, 1500);
        }
      } else {
        setError(response.data.error || 'Failed to parse query');
      }
    } catch (err) {
      console.error('NL Query error:', err);
      setError(err.response?.data?.detail || 'Failed to process query. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleExampleClick = (example) => {
    setQuery(example);
    // Auto-submit after setting
    setTimeout(() => {
      handleSubmit();
    }, 100);
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };
  
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 3, 
        mb: 3, 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        borderRadius: 2
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <AutoAwesomeIcon />
        <Typography variant="h6" fontWeight="bold">
          Ask in Plain English
        </Typography>
        <Tooltip title="How to use">
          <IconButton 
            size="small" 
            onClick={() => setShowHelp(!showHelp)}
            sx={{ color: 'white', ml: 'auto' }}
          >
            <HelpOutlineIcon />
          </IconButton>
        </Tooltip>
      </Box>
      
      {/* Help section */}
      <Collapse in={showHelp}>
        <Alert 
          severity="info" 
          sx={{ mb: 2 }}
          action={
            <IconButton size="small" onClick={() => setShowHelp(false)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          }
        >
          <Typography variant="body2" gutterBottom>
            <strong>Tips for better queries:</strong>
          </Typography>
          <Typography variant="body2" component="ul" sx={{ m: 0, pl: 2 }}>
            <li>Mention specific players: "Kohli", "Bumrah", "Dhoni"</li>
            <li>Specify bowling types: "spin", "pace", "leg spin", "left-arm"</li>
            <li>Use phases: "powerplay", "death overs", "middle overs"</li>
            <li>Add context: "in IPL", "at Wankhede", "in 2024"</li>
          </Typography>
        </Alert>
      </Collapse>
      
      {/* Input form */}
      <form onSubmit={handleSubmit}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            inputRef={inputRef}
            fullWidth
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={loading}
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'rgba(255,255,255,0.95)',
                borderRadius: 2,
                '& fieldset': {
                  borderColor: 'transparent',
                },
                '&:hover fieldset': {
                  borderColor: 'rgba(255,255,255,0.5)',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'white',
                },
              },
            }}
            InputProps={{
              endAdornment: loading && <CircularProgress size={20} />
            }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={loading || !query.trim()}
            sx={{
              backgroundColor: 'rgba(255,255,255,0.2)',
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.3)',
              },
              minWidth: 100
            }}
            startIcon={<SearchIcon />}
          >
            {loading ? 'Parsing...' : 'Search'}
          </Button>
        </Box>
      </form>
      
      {/* Error display */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
      
      {/* Result display */}
      <Collapse in={!!result}>
        <Fade in={!!result}>
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 1 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              <strong>Understood:</strong> {result?.explanation}
            </Typography>
            
            {result?.confidence === 'low' && result?.suggestions && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                <Typography variant="body2">
                  <strong>Did you mean:</strong>
                </Typography>
                {result.suggestions.map((suggestion, i) => (
                  <Typography key={i} variant="body2">• {suggestion}</Typography>
                ))}
              </Alert>
            )}
            
            {autoNavigate && (
              <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                Redirecting to Query Builder...
              </Typography>
            )}
          </Box>
        </Fade>
      </Collapse>
      
      {/* Example queries */}
      {showExamples && !result && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" sx={{ opacity: 0.8 }}>
            Try these:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {EXAMPLE_QUERIES.map((example, index) => (
              <Chip
                key={index}
                label={example}
                onClick={() => handleExampleClick(example)}
                size="small"
                sx={{
                  backgroundColor: 'rgba(255,255,255,0.2)',
                  color: 'white',
                  cursor: 'pointer',
                  '&:hover': {
                    backgroundColor: 'rgba(255,255,255,0.3)',
                  }
                }}
              />
            ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default NLQueryInput;
```

### 6.2 Integration Options

#### Option A: Add to Query Builder Page (Recommended)

In `QueryBuilder.jsx`, add at the top:

```jsx
// Add import
import NLQueryInput from './NLQueryInput';

// In the component, before the existing content:
return (
  <Box sx={{ my: 3 }}>
    {/* Natural Language Input - NEW */}
    <NLQueryInput 
      autoNavigate={false}  // Don't navigate, just fill filters
      onFiltersGenerated={({ filters, groupBy }) => {
        // Apply the generated filters
        setFilters(prev => ({
          ...prev,
          ...filters
        }));
        setGroupBy(groupBy);
        setShowPrefilledQueries(false);
        
        // Auto-execute the query
        setTimeout(() => {
          executeQuery();
        }, 100);
      }}
    />
    
    {/* Rest of existing Query Builder UI */}
    <Typography variant="h4" gutterBottom>
      🏏 Query Builder
    </Typography>
    ...
  </Box>
);
```

#### Option B: Add to Landing Page

In `LandingPage.jsx`, add after the hero section:

```jsx
import NLQueryInput from './NLQueryInput';

// In render, after the hero Paper:
<NLQueryInput 
  autoNavigate={true}
  showExamples={true}
/>
```

#### Option C: Global Search Bar (Advanced)

Add to the navigation/header for site-wide access.

### 6.3 Mobile Considerations

The component is responsive by default, but add this to `App.js` or a global style:

```css
/* For mobile keyboard handling */
@media (max-width: 600px) {
  .nl-query-input {
    position: sticky;
    top: 0;
    z-index: 100;
  }
}
```

---

## 7. Cost Optimization

### 7.1 Cost Breakdown

| Model | Input Cost | Output Cost | Avg Query Cost |
|-------|------------|-------------|----------------|
| GPT-4o | $5/1M tokens | $15/1M tokens | ~$0.01/query |
| **GPT-4o-mini** | **$0.15/1M tokens** | **$0.60/1M tokens** | **~$0.0003/query** |
| GPT-3.5-turbo | $0.50/1M tokens | $1.50/1M tokens | ~$0.0005/query |

**Recommendation**: Use GPT-4o-mini. It's ~30x cheaper than GPT-4o and handles structured output well.

### 7.2 Cost Reduction Strategies

#### Strategy 1: Aggressive Caching
```python
# Cache for 24 hours - most cricket queries repeat
CACHE_TTL_HOURS = 24

# Normalize queries before caching
def normalize_query(query: str) -> str:
    """Normalize query for cache key."""
    # Lowercase, remove extra spaces
    normalized = " ".join(query.lower().split())
    # Expand common abbreviations to canonical form
    replacements = {
        "vs": "against",
        "pp": "powerplay",
        "ipl": "indian premier league",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized
```

#### Strategy 2: Query Classification (Skip LLM for simple queries)
```python
# Pre-built pattern matching for common queries
SIMPLE_PATTERNS = [
    {
        "pattern": r"^(\w+)\s+vs\s+spin$",
        "handler": lambda m: {
            "filters": {"batters": [m.group(1)], "bowler_type": ["RO","RL","LO","LC"]},
            "group_by": ["bowler_type"]
        }
    },
    # Add more patterns...
]

def try_simple_parse(query: str) -> Optional[Dict]:
    """Try to parse query without LLM."""
    for pattern_config in SIMPLE_PATTERNS:
        match = re.match(pattern_config["pattern"], query, re.IGNORECASE)
        if match:
            return pattern_config["handler"](match)
    return None
```

#### Strategy 3: Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/parse")
@limiter.limit("10/minute")  # 10 queries per minute per IP
async def parse_query(request: NLQueryRequest):
    ...
```

#### Strategy 4: Token Optimization
- Keep system prompt concise (~800 tokens vs 2000+)
- Use JSON mode to avoid verbose outputs
- Set max_tokens=500 (responses are small)

### 7.3 Projected Costs

| Scenario | Queries/Month | Monthly Cost |
|----------|---------------|--------------|
| Light usage | 1,000 | $0.30 |
| Medium usage | 10,000 | $3.00 |
| Heavy usage | 100,000 | $30.00 |
| Viral (with cache) | 1,000,000 | ~$100* |

*With 80% cache hit rate

---

## 8. Error Handling

### 8.1 Error Types and Responses

```python
class NLQueryError(Exception):
    """Base exception for NL Query errors."""
    pass

class QueryTooVagueError(NLQueryError):
    """Query is too vague to parse."""
    pass

class UnsupportedQueryError(NLQueryError):
    """Query type is not supported."""
    pass

# Error response examples
ERROR_RESPONSES = {
    "too_vague": {
        "success": False,
        "error": "Query is too vague. Please be more specific.",
        "suggestions": [
            "Try specifying a player name",
            "Add a time period like 'in IPL 2024'",
            "Mention what you want to compare (vs spin, by phase, etc.)"
        ]
    },
    "no_cricket_context": {
        "success": False,
        "error": "I couldn't identify a cricket-related query.",
        "suggestions": [
            "Try asking about a specific player",
            "Ask about team performance",
            "Query venue statistics"
        ]
    },
    "rate_limited": {
        "success": False,
        "error": "Too many requests. Please wait a moment.",
        "retry_after": 60
    }
}
```

### 8.2 Frontend Error Display

```jsx
// In NLQueryInput.jsx
const getErrorMessage = (error) => {
  if (error.includes('rate limit')) {
    return {
      message: "You're asking too fast! Please wait a moment.",
      severity: "warning"
    };
  }
  if (error.includes('vague')) {
    return {
      message: "Could you be more specific? Try adding player names, phases, or leagues.",
      severity: "info"
    };
  }
  return {
    message: error,
    severity: "error"
  };
};
```

### 8.3 Graceful Degradation

If the LLM service is unavailable:

```jsx
// Show manual Query Builder as fallback
{error && error.includes('unavailable') && (
  <Alert severity="warning">
    AI search is temporarily unavailable. 
    <Button component={Link} to="/query">
      Use Manual Query Builder →
    </Button>
  </Alert>
)}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests for Parser

Create `tests/test_nl2query.py`:

```python
import pytest
from routers.nl2query import call_openai, validate_and_clean_filters

class TestNL2Query:
    """Test suite for NL2Query functionality."""
    
    @pytest.mark.parametrize("query,expected_filters", [
        (
            "Kohli vs spin in death overs",
            {
                "batters": ["V Kohli"],
                "bowler_type": ["RO", "RL", "LO", "LC"],
                "over_min": 16,
                "over_max": 19
            }
        ),
        (
            "Bumrah against left-handers",
            {
                "bowlers": ["JJ Bumrah"],
                "striker_batter_type": "LHB"
            }
        ),
        (
            "CSK batting in IPL 2024",
            {
                "batting_teams": ["Chennai Super Kings"],
                "leagues": ["IPL"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        ),
    ])
    def test_query_parsing(self, query, expected_filters):
        """Test that queries are parsed correctly."""
        result = call_openai(query)
        
        for key, expected_value in expected_filters.items():
            assert key in result["filters"], f"Missing key: {key}"
            if isinstance(expected_value, list):
                assert set(result["filters"][key]) == set(expected_value)
            else:
                assert result["filters"][key] == expected_value
    
    def test_bowler_type_validation(self):
        """Test that invalid bowler types are filtered out."""
        raw = {"bowler_type": ["RF", "INVALID", "LO"]}
        cleaned = validate_and_clean_filters(raw)
        assert cleaned["bowler_type"] == ["RF", "LO"]
    
    def test_over_range_validation(self):
        """Test that over ranges are validated."""
        raw = {"over_min": -1, "over_max": 25}
        cleaned = validate_and_clean_filters(raw)
        assert "over_min" not in cleaned
        assert "over_max" not in cleaned
```

### 9.2 Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestNL2QueryAPI:
    """Integration tests for NL2Query API."""
    
    def test_parse_endpoint(self):
        """Test the parse endpoint."""
        response = client.post("/nl2query/parse", json={
            "query": "Kohli vs spin"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "filters" in data
        assert "V Kohli" in data["filters"].get("batters", [])
    
    def test_examples_endpoint(self):
        """Test the examples endpoint."""
        response = client.get("/nl2query/examples")
        assert response.status_code == 200
        assert "examples" in response.json()
    
    def test_health_endpoint(self):
        """Test the health check."""
        response = client.get("/nl2query/health")
        assert response.status_code == 200
    
    def test_empty_query(self):
        """Test handling of empty query."""
        response = client.post("/nl2query/parse", json={
            "query": ""
        })
        assert response.status_code == 422  # Validation error
    
    def test_rate_limiting(self):
        """Test rate limiting."""
        # Make 15 requests rapidly
        for i in range(15):
            response = client.post("/nl2query/parse", json={
                "query": f"test query {i}"
            })
        
        # Last few should be rate limited
        assert response.status_code == 429
```

### 9.3 Manual Test Cases

| Test Case | Query | Expected Behavior |
|-----------|-------|-------------------|
| Basic batter query | "Kohli stats" | Returns Kohli batting stats |
| Bowler query | "Bumrah bowling" | Returns Bumrah bowling stats |
| Phase filter | "death over batting" | Sets over_min=16, over_max=19 |
| Team query | "CSK vs MI" | Sets both teams |
| Year filter | "IPL 2024" | Sets date range for 2024 |
| Bowling type | "vs spin" | Sets spin bowler types |
| Venue query | "at Wankhede" | Sets venue filter |
| Complex query | "Kohli vs left arm spin in death at Wankhede in IPL" | All filters set correctly |
| Ambiguous query | "best players" | Returns low confidence + suggestions |
| Invalid query | "weather tomorrow" | Returns error + suggestions |

---

## 10. Deployment & Monitoring

### 10.1 Environment Setup

```bash
# Production environment variables
OPENAI_API_KEY=sk-xxx
NL2QUERY_CACHE_TTL=24
NL2QUERY_RATE_LIMIT=10/minute
NL2QUERY_MODEL=gpt-4o-mini
```

### 10.2 Monitoring Metrics

Track these metrics:

```python
# Add to nl2query.py
from prometheus_client import Counter, Histogram

# Metrics
nl2query_requests = Counter(
    'nl2query_requests_total',
    'Total NL2Query requests',
    ['status', 'cached']
)

nl2query_latency = Histogram(
    'nl2query_latency_seconds',
    'NL2Query request latency'
)

nl2query_confidence = Counter(
    'nl2query_confidence_total',
    'NL2Query confidence levels',
    ['level']
)
```

### 10.3 Logging

```python
# Structured logging for debugging
logger.info("NL2Query", extra={
    "query": query,
    "filters": result.get("filters"),
    "group_by": result.get("group_by"),
    "confidence": result.get("confidence"),
    "cached": cached,
    "latency_ms": latency
})
```

### 10.4 Alerting

Set up alerts for:
- Error rate > 5%
- P95 latency > 3s
- OpenAI API errors
- Cache hit rate < 50%

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `routers/nl2query.py` | CREATE | Backend API endpoint |
| `src/components/NLQueryInput.jsx` | CREATE | Frontend input component |
| `src/components/QueryBuilder.jsx` | MODIFY | Integrate NL input |
| `main.py` | MODIFY | Register router |
| `.env` | MODIFY | Add OPENAI_API_KEY |
| `tests/test_nl2query.py` | CREATE | Test suite |

---

## Monetization Integration

This feature is ideal for gating behind a paywall:

```jsx
// In NLQueryInput.jsx
const NLQueryInput = ({ isPremiumUser = false }) => {
  if (!isPremiumUser) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <AutoAwesomeIcon sx={{ fontSize: 48, color: 'gold' }} />
        <Typography variant="h6">AI-Powered Search</Typography>
        <Typography color="text.secondary">
          Ask questions in plain English and get instant insights
        </Typography>
        <Button variant="contained" color="primary" sx={{ mt: 2 }}>
          Upgrade to Pro - $7/month
        </Button>
      </Paper>
    );
  }
  
  // ... rest of component for premium users
};
```

---

**Document Version**: 1.0  
**Created**: December 2024  
**Author**: Implementation Spec for Hindsight Cricket Analytics
