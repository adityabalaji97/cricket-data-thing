# Hindsight 2025 Wrapped - Implementation Plan

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Technical Architecture](#2-technical-architecture)
3. [File Structure](#3-file-structure)
4. [Backend Implementation](#4-backend-implementation)
5. [Frontend Implementation](#5-frontend-implementation)
6. [Card-by-Card Implementation Guide](#6-card-by-card-implementation-guide)
7. [Styling & Mobile-First Design](#7-styling--mobile-first-design)
8. [Deep Linking & URL Structure](#8-deep-linking--url-structure)
9. [Social Sharing & OG Images](#9-social-sharing--og-images)
10. [Testing Checklist](#10-testing-checklist)
11. [Deployment Notes](#11-deployment-notes)

---

## 1. Project Overview

### 1.1 What We're Building
A Spotify/YouTube-style "Wrapped" experience that tells the story of T20 cricket in 2025. This will be:
- **Mobile-first**: Instagram Stories-like swipeable interface
- **Interactive**: Each card links to deeper analysis in existing app modules
- **Shareable**: Every card can be shared with a unique URL and preview image

### 1.2 Key Features
1. **Story Mode**: 10-16 swipeable cards with tap-to-navigate (tap left = back, tap right = forward)
2. **Dashboard View**: Optional full dashboard underneath the stories
3. **Deep Links**: Every card has "Open in App" and "Recreate in Query Builder" buttons
4. **Default Filter**: All data filtered to `2025-01-01 → 2025-12-31`

### 1.3 Target URL
```
/wrapped/2025
/wrapped/2025?card=death_hitters
/wrapped/2025?card=powerplay_bullies
```

### 1.4 Existing Codebase Context
The app already has these modules we'll leverage:
- **Query Builder** (`/query`) - Flexible data querying with grouping
- **Batter Profile** (`/player`) - Individual batter analysis
- **Bowler Profile** (`/bowler`) - Individual bowler analysis  
- **Team Profile** (`/team`) - Team-level analysis with ELO
- **Venue Analysis** (`/venue`) - Venue-specific stats
- **Matchups** (`/matchups`) - Head-to-head analysis
- **Batter Comparison** (`/comparison`) - Compare multiple batters

---

## 2. Technical Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
├─────────────────────────────────────────────────────────────────┤
│  WrappedPage.jsx                                                 │
│  ├── WrappedStoryContainer.jsx (handles navigation/gestures)    │
│  ├── WrappedCard.jsx (individual card template)                 │
│  ├── cards/                                                      │
│  │   ├── PowerplayBulliesCard.jsx                               │
│  │   ├── DeathHittersCard.jsx                                   │
│  │   ├── VenueVibesCard.jsx                                     │
│  │   └── ... (one file per card type)                           │
│  └── WrappedDashboard.jsx (optional full view)                  │
├─────────────────────────────────────────────────────────────────┤
│                        Backend (FastAPI)                         │
├─────────────────────────────────────────────────────────────────┤
│  routers/wrapped.py                                              │
│  ├── GET /wrapped/2025/cards - Returns all card data            │
│  ├── GET /wrapped/2025/card/{card_id} - Single card data        │
│  └── GET /wrapped/2025/og-image/{card_id} - OG image generator  │
│                                                                  │
│  services/wrapped.py                                             │
│  └── All SQL queries and data transformation logic              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. User visits /wrapped/2025
2. Frontend loads WrappedPage component
3. WrappedPage calls GET /wrapped/2025/cards
4. Backend queries database with 2025 date filter
5. Backend returns pre-computed card data
6. Frontend renders story interface
7. User swipes/taps through cards
8. User clicks "Open in App" → navigates to existing module with filters
9. User clicks "Recreate in Query Builder" → navigates to /query with preset
```

### 2.3 State Management
We'll use React's built-in state (useState, useEffect) since:
- The data is read-only (no mutations)
- State is localized to the Wrapped page
- No complex state sharing needed

---

## 3. File Structure

### 3.1 New Files to Create

```
src/
├── components/
│   └── wrapped/
│       ├── WrappedPage.jsx              # Main page container
│       ├── WrappedStoryContainer.jsx    # Story navigation logic
│       ├── WrappedCard.jsx              # Base card component
│       ├── WrappedProgressBar.jsx       # Top progress indicator
│       ├── WrappedCardActions.jsx       # "Open in App" buttons
│       ├── WrappedDashboard.jsx         # Full dashboard view
│       ├── cards/
│       │   ├── index.js                 # Export all cards
│       │   ├── IntroCard.jsx            # "2025 in one breath"
│       │   ├── PowerplayBulliesCard.jsx
│       │   ├── MiddleMerchantsCard.jsx
│       │   ├── DeathHittersCard.jsx
│       │   ├── PaceVsSpinCard.jsx
│       │   ├── PowerplayThievesCard.jsx
│       │   ├── NineteenthOverGodsCard.jsx
│       │   ├── OverCombosCard.jsx
│       │   ├── EloMoversCard.jsx
│       │   ├── BattingOrderChaosCard.jsx
│       │   ├── TwentiethOverBowlersCard.jsx
│       │   ├── VenueVibesCard.jsx
│       │   ├── VenuePhaseCard.jsx
│       │   ├── VenuePerformersCard.jsx
│       │   ├── MatchupsCard.jsx
│       │   └── FantasyCard.jsx
│       └── visualizations/
│           ├── WrappedBarChart.jsx      # Mobile-optimized bar chart
│           ├── WrappedScatterPlot.jsx   # Mobile-optimized scatter
│           ├── WrappedRadar.jsx         # Mobile-optimized radar
│           ├── WrappedTable.jsx         # Mobile-optimized table
│           └── WrappedLineChart.jsx     # For SR progression
│
├── utils/
│   └── wrappedLinks.js                  # Deep link generators
│
└── styles/
    └── wrapped.css                      # Wrapped-specific styles

routers/
└── wrapped.py                           # New API router

services/
└── wrapped.py                           # New service layer
```

### 3.2 Files to Modify

```
src/App.js                    # Add route for /wrapped/2025
main.py                       # Include wrapped router
```

---

## 4. Backend Implementation

### 4.1 Create the Router File

**File: `routers/wrapped.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_session
from services.wrapped import (
    get_all_wrapped_cards,
    get_single_card_data,
    get_intro_card_data,
    get_powerplay_bullies_data,
    get_middle_merchants_data,
    get_death_hitters_data,
    get_pace_vs_spin_data,
    get_powerplay_wicket_thieves_data,
    get_nineteenth_over_gods_data,
    get_over_combos_data,
    get_elo_movers_data,
    get_batting_order_chaos_data,
    get_twentieth_over_bowlers_data,
    get_venue_vibes_data,
    get_venue_phase_data,
    get_venue_performers_data,
    get_matchups_data,
    get_fantasy_data
)

router = APIRouter(prefix="/wrapped", tags=["wrapped"])

# Default date range for 2025 Wrapped
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2025-12-31"

@router.get("/2025/cards")
def get_wrapped_cards(
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=True),
    db: Session = Depends(get_session)
):
    """
    Get all card data for the 2025 Wrapped experience.
    Returns an array of card objects with their data and metadata.
    """
    try:
        return get_all_wrapped_cards(
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            leagues=leagues,
            include_international=include_international,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/card/{card_id}")
def get_wrapped_card(
    card_id: str,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=True),
    db: Session = Depends(get_session)
):
    """
    Get data for a single wrapped card.
    Useful for deep linking to specific cards.
    """
    try:
        return get_single_card_data(
            card_id=card_id,
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            leagues=leagues,
            include_international=include_international,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/metadata")
def get_wrapped_metadata():
    """
    Get metadata about the wrapped experience.
    Includes card order, titles, descriptions for the UI.
    """
    return {
        "year": 2025,
        "title": "Hindsight 2025 Wrapped",
        "subtitle": "The Year in Overs",
        "date_range": {
            "start": DEFAULT_START_DATE,
            "end": DEFAULT_END_DATE
        },
        "cards": [
            {
                "id": "intro",
                "title": "2025 in One Breath",
                "subtitle": "Global run rate by phase",
                "order": 1
            },
            {
                "id": "powerplay_bullies",
                "title": "Powerplay Bullies",
                "subtitle": "Who dominated the first 6 overs",
                "order": 2
            },
            {
                "id": "middle_merchants",
                "title": "Middle-Overs Merchants",
                "subtitle": "Masters of overs 7-15",
                "order": 3
            },
            {
                "id": "death_hitters",
                "title": "Death is a Personality Trait",
                "subtitle": "The finishers who lived dangerously",
                "order": 4
            },
            {
                "id": "pace_vs_spin",
                "title": "Pace vs Spin: 2025's Split Brain",
                "subtitle": "Who crushed what type of bowling",
                "order": 5
            },
            {
                "id": "powerplay_thieves",
                "title": "Powerplay Wicket Thieves",
                "subtitle": "Early breakthroughs specialists",
                "order": 6
            },
            {
                "id": "nineteenth_over_gods",
                "title": "The 19th Over Gods",
                "subtitle": "Death overs bowling excellence",
                "order": 7
            },
            {
                "id": "over_combos",
                "title": "Captains Told You What They Believed",
                "subtitle": "Most iconic over combinations",
                "order": 8
            },
            {
                "id": "elo_movers",
                "title": "Teams That Became Different People",
                "subtitle": "Biggest ELO risers and fallers",
                "order": 9
            },
            {
                "id": "batting_order_chaos",
                "title": "Batting Order Chaos Index",
                "subtitle": "Most stable vs chaotic lineups",
                "order": 10
            },
            {
                "id": "twentieth_over_bowlers",
                "title": "Who Actually Bowls the 20th?",
                "subtitle": "Death over specialists by team",
                "order": 11
            },
            {
                "id": "venue_vibes",
                "title": "Venues Had Vibes",
                "subtitle": "Par scores and chase bias",
                "order": 12
            },
            {
                "id": "venue_phase",
                "title": "Where Games Were Decided",
                "subtitle": "Phase strategy by venue",
                "order": 13
            },
            {
                "id": "venue_performers",
                "title": "Home Ground Merchants",
                "subtitle": "Top performers at each venue",
                "order": 14
            },
            {
                "id": "matchups",
                "title": "Bogey Bowlers & Bunnies",
                "subtitle": "Most one-sided matchups",
                "order": 15
            },
            {
                "id": "fantasy",
                "title": "Fantasy Cheat Codes",
                "subtitle": "Expected fantasy points leaders",
                "order": 16
            }
        ]
    }
```

### 4.2 Register the Router in main.py

**Add to `main.py`** (near other router imports):

```python
from routers.wrapped import router as wrapped_router

# ... existing code ...

app.include_router(wrapped_router)
```

### 4.3 Create the Service Layer

**File: `services/wrapped.py`**

This is the most important backend file. It contains all the SQL queries that power each card.

```python
"""
Wrapped 2025 Service Layer

This module contains all the data fetching logic for the Wrapped 2025 feature.
Each function corresponds to a specific card in the wrapped experience.

IMPORTANT: All queries filter by date range (2025-01-01 to 2025-12-31 by default)
"""

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import List, Optional, Dict, Any
from datetime import date
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_competition_filter(leagues: List[str], include_international: bool) -> str:
    """
    Builds the competition filter clause used across all queries.
    This ensures consistency with the existing codebase's filtering logic.
    """
    conditions = []
    
    if leagues:
        conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
    
    if include_international:
        conditions.append("(m.match_type = 'international')")
    
    if conditions:
        return " AND (" + " OR ".join(conditions) + ")"
    else:
        return " AND FALSE"  # No matches if no filters selected


def get_base_params(start_date: str, end_date: str, leagues: List[str]) -> Dict:
    """Returns base parameters used in most queries."""
    return {
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues if leagues else []
    }


# ============================================================================
# CARD 1: INTRO - "2025 in One Breath"
# ============================================================================

def get_intro_card_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session
) -> Dict[str, Any]:
    """
    Card 1: Global run rate and wicket cost by phase.
    
    Returns aggregate stats for:
    - Powerplay (overs 0-5)
    - Middle (overs 6-14)  
    - Death (overs 15-19)
    
    Visualized as: Stacked bars (runs + wickets) by phase
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = get_base_params(start_date, end_date, leagues)
    
    query = text(f"""
        WITH phase_data AS (
            SELECT 
                CASE 
                    WHEN d.over < 6 THEN 'powerplay'
                    WHEN d.over >= 6 AND d.over < 15 THEN 'middle'
                    ELSE 'death'
                END as phase,
                COUNT(*) as balls,
                SUM(d.runs_off_bat + d.extras) as runs,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out')
                    THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN d.runs_off_bat IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            {competition_filter}
            GROUP BY phase
        )
        SELECT 
            phase,
            balls,
            runs,
            wickets,
            dots,
            boundaries,
            ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as run_rate,
            ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as runs_per_wicket,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
        FROM phase_data
        ORDER BY 
            CASE phase 
                WHEN 'powerplay' THEN 1 
                WHEN 'middle' THEN 2 
                WHEN 'death' THEN 3 
            END
    """)
    
    results = db.execute(query, params).fetchall()
    
    # Also get total matches count for context
    matches_query = text(f"""
        SELECT COUNT(DISTINCT m.id) as total_matches
        FROM matches m
        WHERE m.date >= :start_date
        AND m.date <= :end_date
        {competition_filter}
    """)
    
    matches_result = db.execute(matches_query, params).fetchone()
    
    return {
        "card_id": "intro",
        "card_title": "2025 in One Breath",
        "card_subtitle": "The rhythm of T20 cricket",
        "total_matches": matches_result.total_matches if matches_result else 0,
        "phases": [
            {
                "phase": row.phase,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "run_rate": float(row.run_rate) if row.run_rate else 0,
                "runs_per_wicket": float(row.runs_per_wicket) if row.runs_per_wicket else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=phase"
        }
    }


# ============================================================================
# CARD 2: POWERPLAY BULLIES
# ============================================================================

def get_powerplay_bullies_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100
) -> Dict[str, Any]:
    """
    Card 2: Top batters in powerplay by strike rate (with min balls filter).
    
    Shows: SR vs Dot% scatter plot with player names
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_balls": min_balls
    }
    
    query = text(f"""
        WITH powerplay_stats AS (
            SELECT 
                bs.striker as player,
                SUM(bs.pp_balls) as balls,
                SUM(bs.pp_runs) as runs,
                SUM(bs.pp_wickets) as wickets,
                SUM(bs.pp_dots) as dots,
                SUM(bs.pp_boundaries) as boundaries,
                COUNT(DISTINCT bs.match_id) as innings
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            AND bs.pp_balls > 0
            {competition_filter}
            GROUP BY bs.striker
            HAVING SUM(bs.pp_balls) >= :min_balls
        )
        SELECT 
            player,
            balls,
            runs,
            wickets,
            dots,
            boundaries,
            innings,
            ROUND(CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric), 2) as strike_rate,
            ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as average,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
        FROM powerplay_stats
        ORDER BY strike_rate DESC
        LIMIT 20
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "powerplay_bullies",
        "card_title": "Powerplay Bullies of 2025",
        "card_subtitle": f"Min {min_balls} balls in powerplay",
        "visualization_type": "scatter",
        "x_axis": "dot_percentage",
        "y_axis": "strike_rate",
        "players": [
            {
                "name": row.player,
                "balls": row.balls,
                "runs": row.runs,
                "innings": row.innings,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "average": float(row.average) if row.average else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "comparison": f"/comparison?start_date={start_date}&end_date={end_date}",
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=0&over_max=5&group_by=batter&min_balls={min_balls}"
        }
    }


# ============================================================================
# CARD 3: MIDDLE-OVERS MERCHANTS
# ============================================================================

def get_middle_merchants_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 150
) -> Dict[str, Any]:
    """
    Card 3: Best middle-overs batters by average AND strike rate.
    
    Shows: Avg vs SR scatter, click opens batter profile at middle overs section
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_balls": min_balls
    }
    
    query = text(f"""
        WITH middle_stats AS (
            SELECT 
                bs.striker as player,
                SUM(bs.middle_balls) as balls,
                SUM(bs.middle_runs) as runs,
                SUM(bs.middle_wickets) as wickets,
                SUM(bs.middle_dots) as dots,
                SUM(bs.middle_boundaries) as boundaries,
                COUNT(DISTINCT bs.match_id) as innings
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            AND bs.middle_balls > 0
            {competition_filter}
            GROUP BY bs.striker
            HAVING SUM(bs.middle_balls) >= :min_balls
        )
        SELECT 
            player,
            balls,
            runs,
            wickets,
            dots,
            boundaries,
            innings,
            ROUND(CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric), 2) as strike_rate,
            ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as average,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
        FROM middle_stats
        WHERE wickets > 0  -- Need dismissals to calculate average
        ORDER BY 
            -- Rank by combined metric: (SR * Avg) / 100 rewards both
            (CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric) * 
             CAST(runs AS numeric) / NULLIF(wickets, 0)) / 100 DESC
        LIMIT 20
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "middle_merchants",
        "card_title": "Middle-Overs Merchants",
        "card_subtitle": f"Masters of overs 7-15 (min {min_balls} balls)",
        "visualization_type": "scatter",
        "x_axis": "average",
        "y_axis": "strike_rate",
        "players": [
            {
                "name": row.player,
                "balls": row.balls,
                "runs": row.runs,
                "innings": row.innings,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "average": float(row.average) if row.average else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=6&over_max=14&group_by=batter&min_balls={min_balls}"
        }
    }


# ============================================================================
# CARD 4: DEATH HITTERS
# ============================================================================

def get_death_hitters_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 75
) -> Dict[str, Any]:
    """
    Card 4: Best death-overs hitters + SR progression profiles.
    
    Shows: SR progression line overlay (top 3) + table
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_balls": min_balls
    }
    
    # Get top death hitters
    query = text(f"""
        WITH death_stats AS (
            SELECT 
                bs.striker as player,
                SUM(bs.death_balls) as balls,
                SUM(bs.death_runs) as runs,
                SUM(bs.death_wickets) as wickets,
                SUM(bs.death_dots) as dots,
                SUM(bs.death_boundaries) as boundaries,
                COUNT(DISTINCT bs.match_id) as innings
            FROM batting_stats bs
            JOIN matches m ON bs.match_id = m.id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            AND bs.death_balls > 0
            {competition_filter}
            GROUP BY bs.striker
            HAVING SUM(bs.death_balls) >= :min_balls
        )
        SELECT 
            player,
            balls,
            runs,
            wickets,
            dots,
            boundaries,
            innings,
            ROUND(CAST(runs * 100.0 / NULLIF(balls, 0) AS numeric), 2) as strike_rate,
            ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as average,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
        FROM death_stats
        ORDER BY strike_rate DESC
        LIMIT 15
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "death_hitters",
        "card_title": "Death is a Personality Trait",
        "card_subtitle": f"Finishers in overs 16-20 (min {min_balls} balls)",
        "visualization_type": "table_with_highlight",
        "players": [
            {
                "name": row.player,
                "balls": row.balls,
                "runs": row.runs,
                "innings": row.innings,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "average": float(row.average) if row.average else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "comparison": f"/comparison?start_date={start_date}&end_date={end_date}",
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=16&over_max=19&group_by=batter&min_balls={min_balls}"
        }
    }


# ============================================================================
# CARD 5: PACE VS SPIN
# ============================================================================

def get_pace_vs_spin_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100
) -> Dict[str, Any]:
    """
    Card 5: Batters who were pace-only vs spin-only monsters.
    
    Shows: Bar chart of (SR vs pace - SR vs spin) delta
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_balls": min_balls
    }
    
    query = text(f"""
        WITH pace_types AS (
            SELECT name FROM players 
            WHERE bowler_type IN ('RF', 'RFM', 'RM', 'LF', 'LFM', 'LM')
        ),
        spin_types AS (
            SELECT name FROM players 
            WHERE bowler_type IN ('RO', 'RL', 'LO', 'LC')
        ),
        batter_vs_pace AS (
            SELECT 
                d.batter,
                COUNT(*) as balls,
                SUM(d.runs_off_bat + d.extras) as runs
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler IN (SELECT name FROM pace_types)
            AND m.date >= :start_date
            AND m.date <= :end_date
            {competition_filter}
            GROUP BY d.batter
            HAVING COUNT(*) >= :min_balls
        ),
        batter_vs_spin AS (
            SELECT 
                d.batter,
                COUNT(*) as balls,
                SUM(d.runs_off_bat + d.extras) as runs
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE d.bowler IN (SELECT name FROM spin_types)
            AND m.date >= :start_date
            AND m.date <= :end_date
            {competition_filter}
            GROUP BY d.batter
            HAVING COUNT(*) >= :min_balls
        )
        SELECT 
            COALESCE(p.batter, s.batter) as player,
            p.balls as pace_balls,
            p.runs as pace_runs,
            ROUND(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric), 2) as sr_vs_pace,
            s.balls as spin_balls,
            s.runs as spin_runs,
            ROUND(CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric), 2) as sr_vs_spin,
            ROUND(CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric) - 
                  CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric), 2) as sr_delta
        FROM batter_vs_pace p
        FULL OUTER JOIN batter_vs_spin s ON p.batter = s.batter
        WHERE p.balls IS NOT NULL AND s.balls IS NOT NULL
        ORDER BY ABS(
            CAST(p.runs * 100.0 / NULLIF(p.balls, 0) AS numeric) - 
            CAST(s.runs * 100.0 / NULLIF(s.balls, 0) AS numeric)
        ) DESC
        LIMIT 20
    """)
    
    results = db.execute(query, params).fetchall()
    
    # Separate into pace crushers and spin crushers
    pace_crushers = [r for r in results if r.sr_delta and r.sr_delta > 0][:5]
    spin_crushers = [r for r in results if r.sr_delta and r.sr_delta < 0][:5]
    
    return {
        "card_id": "pace_vs_spin",
        "card_title": "Pace vs Spin: 2025's Split Brain",
        "card_subtitle": f"Who dominated which bowling type (min {min_balls} balls each)",
        "visualization_type": "diverging_bar",
        "pace_crushers": [
            {
                "name": row.player,
                "sr_vs_pace": float(row.sr_vs_pace) if row.sr_vs_pace else 0,
                "sr_vs_spin": float(row.sr_vs_spin) if row.sr_vs_spin else 0,
                "sr_delta": float(row.sr_delta) if row.sr_delta else 0,
                "pace_balls": row.pace_balls,
                "spin_balls": row.spin_balls
            }
            for row in pace_crushers
        ],
        "spin_crushers": [
            {
                "name": row.player,
                "sr_vs_pace": float(row.sr_vs_pace) if row.sr_vs_pace else 0,
                "sr_vs_spin": float(row.sr_vs_spin) if row.sr_vs_spin else 0,
                "sr_delta": float(row.sr_delta) if row.sr_delta else 0,
                "pace_balls": row.pace_balls,
                "spin_balls": row.spin_balls
            }
            for row in spin_crushers
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=batter,bowler_type&min_balls={min_balls}"
        }
    }
```

### 4.4 Continue Service Layer (Part 2)

Add to the same file (`services/wrapped.py`):

```python
# ============================================================================
# CARD 6: POWERPLAY WICKET THIEVES
# ============================================================================

def get_powerplay_wicket_thieves_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_wickets: int = 10
) -> Dict[str, Any]:
    """
    Card 6: Best powerplay wicket-takers by strike rate + dot%.
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_wickets": min_wickets
    }
    
    query = text(f"""
        WITH pp_bowling AS (
            SELECT 
                bw.bowler as player,
                SUM(bw.pp_overs) * 6 as balls,
                SUM(bw.pp_runs) as runs,
                SUM(bw.pp_wickets) as wickets,
                SUM(bw.pp_dots) as dots,
                COUNT(DISTINCT bw.match_id) as innings
            FROM bowling_stats bw
            JOIN matches m ON bw.match_id = m.id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            AND bw.pp_overs > 0
            {competition_filter}
            GROUP BY bw.bowler
            HAVING SUM(bw.pp_wickets) >= :min_wickets
        )
        SELECT 
            player,
            balls,
            runs,
            wickets,
            dots,
            innings,
            ROUND(CAST(balls AS numeric) / NULLIF(wickets, 0), 2) as strike_rate,
            ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as economy,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage
        FROM pp_bowling
        ORDER BY strike_rate ASC
        LIMIT 15
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "powerplay_thieves",
        "card_title": "Powerplay Wicket Thieves",
        "card_subtitle": f"Early breakthrough specialists (min {min_wickets} wickets)",
        "visualization_type": "table",
        "bowlers": [
            {
                "name": row.player,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "innings": row.innings,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                "economy": float(row.economy) if row.economy else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=0&over_max=5&group_by=bowler&min_balls=50"
        }
    }


# ============================================================================
# CARD 7: 19TH OVER GODS
# ============================================================================

def get_nineteenth_over_gods_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_overs: int = 10
) -> Dict[str, Any]:
    """
    Card 7: Bowlers who dominated overs 18-20.
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_overs": min_overs
    }
    
    query = text(f"""
        WITH death_bowling AS (
            SELECT 
                bw.bowler as player,
                SUM(bw.death_overs) * 6 as balls,
                SUM(bw.death_runs) as runs,
                SUM(bw.death_wickets) as wickets,
                SUM(bw.death_dots) as dots,
                COUNT(DISTINCT bw.match_id) as innings
            FROM bowling_stats bw
            JOIN matches m ON bw.match_id = m.id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            AND bw.death_overs > 0
            {competition_filter}
            GROUP BY bw.bowler
            HAVING SUM(bw.death_overs) >= :min_overs
        )
        SELECT 
            player,
            balls,
            runs,
            wickets,
            dots,
            innings,
            ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as economy,
            ROUND(CAST(balls AS numeric) / NULLIF(wickets, 0), 2) as strike_rate,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage
        FROM death_bowling
        ORDER BY economy ASC
        LIMIT 15
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "nineteenth_over_gods",
        "card_title": "The 19th Over Gods",
        "card_subtitle": f"Death overs excellence (min {min_overs} overs)",
        "visualization_type": "table",
        "bowlers": [
            {
                "name": row.player,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "innings": row.innings,
                "economy": float(row.economy) if row.economy else 0,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 999,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=16&over_max=19&group_by=bowler"
        }
    }


# ============================================================================
# CARD 9: ELO MOVERS
# ============================================================================

def get_elo_movers_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session
) -> Dict[str, Any]:
    """
    Card 9: Biggest ELO risers/fallers in 2025.
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = get_base_params(start_date, end_date, leagues)
    
    # Get ELO changes - this uses the existing ELO tracking in matches table
    query = text(f"""
        WITH team_elo_changes AS (
            SELECT 
                team,
                MIN(elo) as min_elo,
                MAX(elo) as max_elo,
                FIRST_VALUE(elo) OVER (PARTITION BY team ORDER BY date) as start_elo,
                LAST_VALUE(elo) OVER (PARTITION BY team ORDER BY date 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_elo
            FROM (
                SELECT m.team1 as team, m.team1_elo as elo, m.date
                FROM matches m
                WHERE m.date >= :start_date AND m.date <= :end_date
                {competition_filter}
                UNION ALL
                SELECT m.team2 as team, m.team2_elo as elo, m.date
                FROM matches m
                WHERE m.date >= :start_date AND m.date <= :end_date
                {competition_filter}
            ) all_elos
            GROUP BY team
        )
        SELECT 
            team,
            start_elo,
            end_elo,
            (end_elo - start_elo) as elo_change,
            max_elo as peak_elo,
            min_elo as trough_elo
        FROM team_elo_changes
        WHERE start_elo IS NOT NULL AND end_elo IS NOT NULL
        ORDER BY ABS(end_elo - start_elo) DESC
        LIMIT 20
    """)
    
    try:
        results = db.execute(query, params).fetchall()
        
        risers = [r for r in results if r.elo_change and r.elo_change > 0][:5]
        fallers = [r for r in results if r.elo_change and r.elo_change < 0][:5]
        
        return {
            "card_id": "elo_movers",
            "card_title": "Teams That Became Different People",
            "card_subtitle": "Biggest ELO movements in 2025",
            "visualization_type": "diverging_bar",
            "risers": [
                {
                    "team": row.team,
                    "start_elo": row.start_elo,
                    "end_elo": row.end_elo,
                    "elo_change": row.elo_change,
                    "peak_elo": row.peak_elo
                }
                for row in risers
            ],
            "fallers": [
                {
                    "team": row.team,
                    "start_elo": row.start_elo,
                    "end_elo": row.end_elo,
                    "elo_change": row.elo_change,
                    "trough_elo": row.trough_elo
                }
                for row in fallers
            ],
            "deep_links": {
                "team_profile": f"/team?start_date={start_date}&end_date={end_date}"
            }
        }
    except Exception as e:
        logger.error(f"Error fetching ELO data: {e}")
        return {
            "card_id": "elo_movers",
            "card_title": "Teams That Became Different People",
            "error": "ELO data not available for selected filters"
        }


# ============================================================================
# CARD 12: VENUE VIBES
# ============================================================================

def get_venue_vibes_data(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_matches: int = 5
) -> Dict[str, Any]:
    """
    Card 12: Venue leaderboard - par score + chase bias.
    """
    
    competition_filter = build_competition_filter(leagues, include_international)
    params = {
        **get_base_params(start_date, end_date, leagues),
        "min_matches": min_matches
    }
    
    query = text(f"""
        WITH venue_stats AS (
            SELECT 
                m.venue,
                COUNT(*) as matches,
                SUM(CASE WHEN m.won_batting_first THEN 1 ELSE 0 END) as bat_first_wins,
                SUM(CASE WHEN m.won_fielding_first THEN 1 ELSE 0 END) as chase_wins,
                AVG(CASE WHEN d.innings = 1 THEN d.total END) as avg_first_innings
            FROM matches m
            LEFT JOIN (
                SELECT match_id, innings, SUM(runs_off_bat + extras) as total
                FROM deliveries
                GROUP BY match_id, innings
            ) d ON m.id = d.match_id
            WHERE m.date >= :start_date
            AND m.date <= :end_date
            {competition_filter}
            GROUP BY m.venue
            HAVING COUNT(*) >= :min_matches
        )
        SELECT 
            venue,
            matches,
            bat_first_wins,
            chase_wins,
            ROUND(CAST(avg_first_innings AS numeric), 0) as par_score,
            ROUND(CAST(chase_wins * 100.0 / NULLIF(bat_first_wins + chase_wins, 0) AS numeric), 1) as chase_win_pct
        FROM venue_stats
        ORDER BY matches DESC
        LIMIT 15
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "venue_vibes",
        "card_title": "Venues Had Vibes",
        "card_subtitle": f"Par scores and chase bias (min {min_matches} matches)",
        "visualization_type": "scatter",
        "x_axis": "par_score",
        "y_axis": "chase_win_pct",
        "venues": [
            {
                "name": row.venue,
                "matches": row.matches,
                "par_score": int(row.par_score) if row.par_score else 0,
                "chase_win_pct": float(row.chase_win_pct) if row.chase_win_pct else 50,
                "bat_first_wins": row.bat_first_wins,
                "chase_wins": row.chase_wins
            }
            for row in results
        ],
        "deep_links": {
            "venue_analysis": f"/venue?start_date={start_date}&end_date={end_date}"
        }
    }


# ============================================================================
# MASTER FUNCTION: GET ALL CARDS
# ============================================================================

def get_all_wrapped_cards(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session
) -> Dict[str, Any]:
    """
    Fetches data for all wrapped cards.
    Returns a complete dataset for the wrapped experience.
    """
    
    cards = []
    
    # Card 1: Intro
    try:
        cards.append(get_intro_card_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching intro card: {e}")
        cards.append({"card_id": "intro", "error": str(e)})
    
    # Card 2: Powerplay Bullies
    try:
        cards.append(get_powerplay_bullies_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching powerplay bullies: {e}")
        cards.append({"card_id": "powerplay_bullies", "error": str(e)})
    
    # Card 3: Middle Merchants
    try:
        cards.append(get_middle_merchants_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching middle merchants: {e}")
        cards.append({"card_id": "middle_merchants", "error": str(e)})
    
    # Card 4: Death Hitters
    try:
        cards.append(get_death_hitters_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching death hitters: {e}")
        cards.append({"card_id": "death_hitters", "error": str(e)})
    
    # Card 5: Pace vs Spin
    try:
        cards.append(get_pace_vs_spin_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching pace vs spin: {e}")
        cards.append({"card_id": "pace_vs_spin", "error": str(e)})
    
    # Card 6: Powerplay Wicket Thieves
    try:
        cards.append(get_powerplay_wicket_thieves_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching powerplay thieves: {e}")
        cards.append({"card_id": "powerplay_thieves", "error": str(e)})
    
    # Card 7: 19th Over Gods
    try:
        cards.append(get_nineteenth_over_gods_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching 19th over gods: {e}")
        cards.append({"card_id": "nineteenth_over_gods", "error": str(e)})
    
    # Card 9: ELO Movers
    try:
        cards.append(get_elo_movers_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching elo movers: {e}")
        cards.append({"card_id": "elo_movers", "error": str(e)})
    
    # Card 12: Venue Vibes
    try:
        cards.append(get_venue_vibes_data(start_date, end_date, leagues, include_international, db))
    except Exception as e:
        logger.error(f"Error fetching venue vibes: {e}")
        cards.append({"card_id": "venue_vibes", "error": str(e)})
    
    return {
        "year": 2025,
        "date_range": {"start": start_date, "end": end_date},
        "total_cards": len(cards),
        "cards": cards
    }


def get_single_card_data(
    card_id: str,
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session
) -> Dict[str, Any]:
    """
    Fetches data for a single card by ID.
    """
    
    card_functions = {
        "intro": get_intro_card_data,
        "powerplay_bullies": get_powerplay_bullies_data,
        "middle_merchants": get_middle_merchants_data,
        "death_hitters": get_death_hitters_data,
        "pace_vs_spin": get_pace_vs_spin_data,
        "powerplay_thieves": get_powerplay_wicket_thieves_data,
        "nineteenth_over_gods": get_nineteenth_over_gods_data,
        "elo_movers": get_elo_movers_data,
        "venue_vibes": get_venue_vibes_data,
    }
    
    if card_id not in card_functions:
        raise ValueError(f"Unknown card ID: {card_id}")
    
    return card_functions[card_id](
        start_date, end_date, leagues, include_international, db
    )
```

---

## 5. Frontend Implementation

### 5.1 Update App.js to Add Route

**Modify: `src/App.js`**

Add the import and route for the Wrapped page:

```jsx
// Add to imports at top of file
import WrappedPage from './components/wrapped/WrappedPage';

// Add to the Routes section (inside <Routes>):
<Route path="/wrapped/2025" element={<WrappedPage />} />
```

### 5.2 Main Page Container

**File: `src/components/wrapped/WrappedPage.jsx`**

```jsx
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Alert } from '@mui/material';
import WrappedStoryContainer from './WrappedStoryContainer';
import config from '../../config';
import './wrapped.css';

const WrappedPage = () => {
  const [searchParams] = useSearchParams();
  const [cardsData, setCardsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Get initial card from URL if present
  const initialCardId = searchParams.get('card');

  useEffect(() => {
    const fetchWrappedData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setCardsData(data);
      } catch (err) {
        console.error('Error fetching wrapped data:', err);
        setError('Failed to load Wrapped 2025 data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchWrappedData();
  }, []);

  if (loading) {
    return (
      <Box className="wrapped-loading">
        <CircularProgress size={60} sx={{ color: '#1DB954' }} />
        <p>Loading your 2025 Wrapped...</p>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="wrapped-error">
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!cardsData || !cardsData.cards || cardsData.cards.length === 0) {
    return (
      <Box className="wrapped-error">
        <Alert severity="warning">No data available for 2025 Wrapped.</Alert>
      </Box>
    );
  }

  return (
    <WrappedStoryContainer 
      cards={cardsData.cards} 
      initialCardId={initialCardId}
      year={cardsData.year}
    />
  );
};

export default WrappedPage;
```

### 5.3 Story Container (Navigation Logic)

**File: `src/components/wrapped/WrappedStoryContainer.jsx`**

```jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import WrappedProgressBar from './WrappedProgressBar';
import WrappedCard from './WrappedCard';
import './wrapped.css';

const WrappedStoryContainer = ({ cards, initialCardId, year }) => {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  
  // Find initial card index
  const getInitialIndex = () => {
    if (initialCardId) {
      const index = cards.findIndex(card => card.card_id === initialCardId);
      return index >= 0 ? index : 0;
    }
    return 0;
  };
  
  const [currentIndex, setCurrentIndex] = useState(getInitialIndex());
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);

  // Minimum swipe distance (in px)
  const minSwipeDistance = 50;

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        goToNext();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goToPrevious();
      } else if (e.key === 'Escape') {
        handleClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentIndex]);

  // Update URL when card changes
  useEffect(() => {
    const currentCard = cards[currentIndex];
    if (currentCard) {
      const newUrl = `/wrapped/2025?card=${currentCard.card_id}`;
      window.history.replaceState(null, '', newUrl);
    }
  }, [currentIndex, cards]);

  const goToNext = useCallback(() => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(prev => prev + 1);
    }
  }, [currentIndex, cards.length]);

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
    }
  }, [currentIndex]);

  const goToCard = useCallback((index) => {
    if (index >= 0 && index < cards.length) {
      setCurrentIndex(index);
    }
  }, [cards.length]);

  const handleClose = () => {
    navigate('/');
  };

  // Touch handlers for swipe
  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;
    
    if (isLeftSwipe) {
      goToNext();
    } else if (isRightSwipe) {
      goToPrevious();
    }
  };

  // Tap navigation (Instagram-style)
  const handleTap = (e) => {
    // Don't trigger tap navigation if clicking on interactive elements
    if (e.target.closest('button') || e.target.closest('a')) {
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const containerWidth = rect.width;

    // Left third = previous, right two-thirds = next
    if (x < containerWidth / 3) {
      goToPrevious();
    } else {
      goToNext();
    }
  };

  const currentCard = cards[currentIndex];

  return (
    <Box 
      ref={containerRef}
      className="wrapped-container"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onClick={handleTap}
    >
      {/* Progress Bar */}
      <WrappedProgressBar 
        totalCards={cards.length} 
        currentIndex={currentIndex}
        onProgressClick={goToCard}
      />

      {/* Close Button */}
      <IconButton 
        className="wrapped-close-btn"
        onClick={handleClose}
        aria-label="Close"
      >
        <CloseIcon />
      </IconButton>

      {/* Current Card */}
      <WrappedCard 
        cardData={currentCard}
        cardIndex={currentIndex}
        totalCards={cards.length}
      />

      {/* Navigation hints (mobile) */}
      <Box className="wrapped-nav-hints">
        <span className="nav-hint nav-hint-left">‹</span>
        <span className="nav-hint nav-hint-right">›</span>
      </Box>
    </Box>
  );
};

export default WrappedStoryContainer;
```

### 5.4 Progress Bar Component

**File: `src/components/wrapped/WrappedProgressBar.jsx`**

```jsx
import React from 'react';
import { Box } from '@mui/material';
import './wrapped.css';

const WrappedProgressBar = ({ totalCards, currentIndex, onProgressClick }) => {
  return (
    <Box className="wrapped-progress-bar">
      {Array.from({ length: totalCards }, (_, index) => (
        <Box
          key={index}
          className={`progress-segment ${index === currentIndex ? 'active' : ''} ${index < currentIndex ? 'completed' : ''}`}
          onClick={(e) => {
            e.stopPropagation();
            onProgressClick(index);
          }}
        />
      ))}
    </Box>
  );
};

export default WrappedProgressBar;
```

### 5.5 Base Card Component

**File: `src/components/wrapped/WrappedCard.jsx`**

```jsx
import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import BuildIcon from '@mui/icons-material/Build';
import WrappedCardActions from './WrappedCardActions';

// Import card-specific visualizations
import IntroCard from './cards/IntroCard';
import PowerplayBulliesCard from './cards/PowerplayBulliesCard';
import MiddleMerchantsCard from './cards/MiddleMerchantsCard';
import DeathHittersCard from './cards/DeathHittersCard';
import PaceVsSpinCard from './cards/PaceVsSpinCard';
import PowerplayThievesCard from './cards/PowerplayThievesCard';
import NineteenthOverGodsCard from './cards/NineteenthOverGodsCard';
import EloMoversCard from './cards/EloMoversCard';
import VenueVibesCard from './cards/VenueVibesCard';
import './wrapped.css';

// Map card IDs to their specific visualization components
const cardComponents = {
  'intro': IntroCard,
  'powerplay_bullies': PowerplayBulliesCard,
  'middle_merchants': MiddleMerchantsCard,
  'death_hitters': DeathHittersCard,
  'pace_vs_spin': PaceVsSpinCard,
  'powerplay_thieves': PowerplayThievesCard,
  'nineteenth_over_gods': NineteenthOverGodsCard,
  'elo_movers': EloMoversCard,
  'venue_vibes': VenueVibesCard,
};

const WrappedCard = ({ cardData, cardIndex, totalCards }) => {
  const navigate = useNavigate();
  
  if (!cardData) {
    return (
      <Box className="wrapped-card wrapped-card-error">
        <Typography>Card data unavailable</Typography>
      </Box>
    );
  }

  // Check for error in card data
  if (cardData.error) {
    return (
      <Box className="wrapped-card wrapped-card-error">
        <Typography variant="h5">{cardData.card_title || 'Error'}</Typography>
        <Typography>{cardData.error}</Typography>
      </Box>
    );
  }

  // Get the specific card component
  const CardComponent = cardComponents[cardData.card_id];

  return (
    <Box className="wrapped-card">
      {/* Card Header */}
      <Box className="wrapped-card-header">
        <Typography variant="overline" className="wrapped-card-index">
          {cardIndex + 1} / {totalCards}
        </Typography>
        <Typography variant="h4" className="wrapped-card-title">
          {cardData.card_title}
        </Typography>
        <Typography variant="subtitle1" className="wrapped-card-subtitle">
          {cardData.card_subtitle}
        </Typography>
      </Box>

      {/* Card Content - Specific visualization */}
      <Box className="wrapped-card-content">
        {CardComponent ? (
          <CardComponent data={cardData} />
        ) : (
          <Typography>Visualization not available for this card type</Typography>
        )}
      </Box>

      {/* Card Actions */}
      <WrappedCardActions deepLinks={cardData.deep_links} />
    </Box>
  );
};

export default WrappedCard;
```

### 5.6 Card Actions Component

**File: `src/components/wrapped/WrappedCardActions.jsx`**

```jsx
import React from 'react';
import { Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import BuildIcon from '@mui/icons-material/Build';
import ShareIcon from '@mui/icons-material/Share';
import './wrapped.css';

const WrappedCardActions = ({ deepLinks }) => {
  const navigate = useNavigate();

  const handleOpenInApp = (url) => {
    // Prevent the tap navigation from triggering
    navigate(url);
  };

  const handleShare = async () => {
    const url = window.location.href;
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Hindsight 2025 Wrapped',
          text: 'Check out this T20 cricket stat!',
          url: url,
        });
      } catch (err) {
        console.log('Share cancelled');
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(url);
      // You could show a toast here
    }
  };

  if (!deepLinks) return null;

  return (
    <Box className="wrapped-card-actions" onClick={(e) => e.stopPropagation()}>
      {/* Open in App Button */}
      {deepLinks.comparison && (
        <Button
          variant="contained"
          size="small"
          startIcon={<OpenInNewIcon />}
          onClick={() => handleOpenInApp(deepLinks.comparison)}
          className="wrapped-action-btn"
        >
          Compare Players
        </Button>
      )}
      
      {deepLinks.team_profile && (
        <Button
          variant="contained"
          size="small"
          startIcon={<OpenInNewIcon />}
          onClick={() => handleOpenInApp(deepLinks.team_profile)}
          className="wrapped-action-btn"
        >
          Team Profile
        </Button>
      )}
      
      {deepLinks.venue_analysis && (
        <Button
          variant="contained"
          size="small"
          startIcon={<OpenInNewIcon />}
          onClick={() => handleOpenInApp(deepLinks.venue_analysis)}
          className="wrapped-action-btn"
        >
          Venue Analysis
        </Button>
      )}

      {/* Query Builder Button */}
      {deepLinks.query_builder && (
        <Button
          variant="outlined"
          size="small"
          startIcon={<BuildIcon />}
          onClick={() => handleOpenInApp(deepLinks.query_builder)}
          className="wrapped-action-btn wrapped-action-btn-secondary"
        >
          Recreate Query
        </Button>
      )}

      {/* Share Button */}
      <Button
        variant="text"
        size="small"
        startIcon={<ShareIcon />}
        onClick={handleShare}
        className="wrapped-action-btn wrapped-action-btn-share"
      >
        Share
      </Button>
    </Box>
  );
};

export default WrappedCardActions;
```

---

## 6. Card-by-Card Implementation Guide

### 6.1 Intro Card - "2025 in One Breath"

**File: `src/components/wrapped/cards/IntroCard.jsx`**

```jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const PHASE_COLORS = {
  powerplay: '#4CAF50',
  middle: '#2196F3', 
  death: '#f44336'
};

const PHASE_LABELS = {
  powerplay: 'Powerplay (1-6)',
  middle: 'Middle (7-15)',
  death: 'Death (16-20)'
};

const IntroCard = ({ data }) => {
  if (!data.phases || data.phases.length === 0) {
    return <Typography>No phase data available</Typography>;
  }

  const chartData = data.phases.map(phase => ({
    phase: PHASE_LABELS[phase.phase] || phase.phase,
    'Run Rate': phase.run_rate,
    'Boundary %': phase.boundary_percentage,
    'Dot %': phase.dot_percentage,
    color: PHASE_COLORS[phase.phase] || '#999'
  }));

  return (
    <Box className="intro-card-content">
      {/* Big Number */}
      <Box className="intro-stat-hero">
        <Typography variant="h2" className="hero-number">
          {data.total_matches}
        </Typography>
        <Typography variant="subtitle1" className="hero-label">
          T20 matches analyzed
        </Typography>
      </Box>

      {/* Phase Stats Chart */}
      <Box className="intro-chart">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" domain={[0, 'auto']} tick={{ fontSize: 12 }} />
            <YAxis 
              type="category" 
              dataKey="phase" 
              width={80} 
              tick={{ fontSize: 11 }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(0,0,0,0.8)', 
                border: 'none',
                borderRadius: 8 
              }}
            />
            <Bar dataKey="Run Rate" fill="#1DB954" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Quick Stats */}
      <Box className="intro-quick-stats">
        {data.phases.map(phase => (
          <Box key={phase.phase} className="quick-stat">
            <Typography variant="h6" style={{ color: PHASE_COLORS[phase.phase] }}>
              {phase.run_rate}
            </Typography>
            <Typography variant="caption">
              {phase.phase} RR
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default IntroCard;
```

### 6.2 Powerplay Bullies Card

**File: `src/components/wrapped/cards/PowerplayBulliesCard.jsx`**

```jsx
import React, { useState } from 'react';
import { Box, Typography, Slider } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { useNavigate } from 'react-router-dom';

const PowerplayBulliesCard = ({ data }) => {
  const navigate = useNavigate();
  const [minBallsFilter, setMinBallsFilter] = useState(100);

  if (!data.players || data.players.length === 0) {
    return <Typography>No powerplay data available</Typography>;
  }

  // Filter players based on min balls
  const filteredPlayers = data.players.filter(p => p.balls >= minBallsFilter);

  // Calculate averages for reference lines
  const avgSR = filteredPlayers.reduce((sum, p) => sum + p.strike_rate, 0) / filteredPlayers.length;
  const avgDot = filteredPlayers.reduce((sum, p) => sum + p.dot_percentage, 0) / filteredPlayers.length;

  const handlePlayerClick = (player) => {
    navigate(`/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">{player.name}</Typography>
          <Typography variant="body2">SR: {player.strike_rate}</Typography>
          <Typography variant="body2">Dot%: {player.dot_percentage}%</Typography>
          <Typography variant="body2">Balls: {player.balls}</Typography>
          <Typography variant="caption" sx={{ color: '#1DB954' }}>
            Tap to view profile →
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="scatter-card-content">
      {/* Top 3 highlight */}
      <Box className="top-players-list">
        {filteredPlayers.slice(0, 3).map((player, index) => (
          <Box 
            key={player.name} 
            className="top-player-item"
            onClick={() => handlePlayerClick(player)}
          >
            <Typography variant="h5" className="rank">#{index + 1}</Typography>
            <Box className="player-info">
              <Typography variant="subtitle1">{player.name}</Typography>
              <Typography variant="body2">
                SR: {player.strike_rate} | {player.balls} balls
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Scatter Plot */}
      <Box className="scatter-chart">
        <ResponsiveContainer width="100%" height={200}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="dot_percentage" 
              name="Dot %" 
              domain={['dataMin - 5', 'dataMax + 5']}
              tick={{ fontSize: 10 }}
              label={{ value: 'Dot %', position: 'bottom', fontSize: 10 }}
            />
            <YAxis 
              type="number" 
              dataKey="strike_rate" 
              name="SR" 
              domain={['dataMin - 10', 'dataMax + 10']}
              tick={{ fontSize: 10 }}
              label={{ value: 'SR', angle: -90, position: 'left', fontSize: 10 }}
            />
            <ReferenceLine y={avgSR} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgDot} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={filteredPlayers} 
              fill="#1DB954"
              onClick={(data) => handlePlayerClick(data)}
              cursor="pointer"
            >
              {filteredPlayers.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={index < 3 ? '#1DB954' : '#666'}
                  opacity={index < 3 ? 1 : 0.6}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </Box>

      {/* Min balls slider */}
      <Box className="filter-slider">
        <Typography variant="caption">Min balls: {minBallsFilter}</Typography>
        <Slider
          value={minBallsFilter}
          onChange={(e, val) => setMinBallsFilter(val)}
          min={50}
          max={200}
          step={25}
          size="small"
          sx={{ color: '#1DB954', width: 150 }}
          onClick={(e) => e.stopPropagation()}
        />
      </Box>
    </Box>
  );
};

export default PowerplayBulliesCard;
```

### 6.3 Death Hitters Card

**File: `src/components/wrapped/cards/DeathHittersCard.jsx`**

```jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const DeathHittersCard = ({ data }) => {
  const navigate = useNavigate();

  if (!data.players || data.players.length === 0) {
    return <Typography>No death overs data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    navigate(`/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  // Top 5 for display
  const topPlayers = data.players.slice(0, 5);

  return (
    <Box className="table-card-content">
      {/* Podium-style top 3 */}
      <Box className="podium">
        {/* Second place */}
        <Box className="podium-item second" onClick={() => handlePlayerClick(topPlayers[1])}>
          <Typography variant="h6" className="podium-rank">2</Typography>
          <Typography variant="body2" className="podium-name">{topPlayers[1]?.name}</Typography>
          <Typography variant="h5" className="podium-stat">{topPlayers[1]?.strike_rate}</Typography>
          <Typography variant="caption">SR</Typography>
        </Box>
        
        {/* First place */}
        <Box className="podium-item first" onClick={() => handlePlayerClick(topPlayers[0])}>
          <Typography variant="h5" className="podium-rank">👑</Typography>
          <Typography variant="subtitle1" className="podium-name">{topPlayers[0]?.name}</Typography>
          <Typography variant="h4" className="podium-stat">{topPlayers[0]?.strike_rate}</Typography>
          <Typography variant="caption">SR</Typography>
        </Box>
        
        {/* Third place */}
        <Box className="podium-item third" onClick={() => handlePlayerClick(topPlayers[2])}>
          <Typography variant="h6" className="podium-rank">3</Typography>
          <Typography variant="body2" className="podium-name">{topPlayers[2]?.name}</Typography>
          <Typography variant="h5" className="podium-stat">{topPlayers[2]?.strike_rate}</Typography>
          <Typography variant="caption">SR</Typography>
        </Box>
      </Box>

      {/* Remaining players in compact list */}
      <Box className="remaining-list">
        {topPlayers.slice(3).map((player, index) => (
          <Box 
            key={player.name} 
            className="list-item"
            onClick={() => handlePlayerClick(player)}
          >
            <Typography variant="body2" className="list-rank">#{index + 4}</Typography>
            <Typography variant="body2" className="list-name">{player.name}</Typography>
            <Typography variant="body2" className="list-stat">SR: {player.strike_rate}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default DeathHittersCard;
```

### 6.4 Pace vs Spin Card

**File: `src/components/wrapped/cards/PaceVsSpinCard.jsx`**

```jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { useNavigate } from 'react-router-dom';

const PaceVsSpinCard = ({ data }) => {
  const navigate = useNavigate();

  if ((!data.pace_crushers || data.pace_crushers.length === 0) && 
      (!data.spin_crushers || data.spin_crushers.length === 0)) {
    return <Typography>No pace vs spin data available</Typography>;
  }

  // Combine and prepare data for diverging bar chart
  const chartData = [
    ...data.pace_crushers.map(p => ({
      name: p.name,
      value: p.sr_delta,
      category: 'Pace Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    })),
    ...data.spin_crushers.map(p => ({
      name: p.name,
      value: p.sr_delta, // Will be negative
      category: 'Spin Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    }))
  ].sort((a, b) => b.value - a.value);

  const handlePlayerClick = (playerName) => {
    navigate(`/player?name=${encodeURIComponent(playerName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">{player.name}</Typography>
          <Typography variant="body2">vs Pace: {player.sr_vs_pace}</Typography>
          <Typography variant="body2">vs Spin: {player.sr_vs_spin}</Typography>
          <Typography variant="body2" sx={{ 
            color: player.value > 0 ? '#4CAF50' : '#f44336' 
          }}>
            Delta: {player.value > 0 ? '+' : ''}{player.value}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="diverging-card-content">
      {/* Section Labels */}
      <Box className="section-labels">
        <Typography variant="caption" className="label-left" sx={{ color: '#4CAF50' }}>
          🔥 Pace Crushers
        </Typography>
        <Typography variant="caption" className="label-right" sx={{ color: '#f44336' }}>
          🌀 Spin Crushers
        </Typography>
      </Box>

      {/* Diverging Bar Chart */}
      <Box className="diverging-chart">
        <ResponsiveContainer width="100%" height={250}>
          <BarChart 
            data={chartData} 
            layout="vertical"
            margin={{ top: 10, right: 30, left: 60, bottom: 10 }}
          >
            <XAxis 
              type="number" 
              domain={[-50, 50]}
              tick={{ fontSize: 10 }}
              tickFormatter={(val) => val > 0 ? `+${val}` : val}
            />
            <YAxis 
              type="category" 
              dataKey="name" 
              width={55}
              tick={{ fontSize: 10 }}
            />
            <ReferenceLine x={0} stroke="#fff" />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="value" 
              onClick={(data) => handlePlayerClick(data.name)}
              cursor="pointer"
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={entry.value > 0 ? '#4CAF50' : '#f44336'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Legend */}
      <Box className="chart-legend">
        <Typography variant="caption">
          Positive = Better vs Pace | Negative = Better vs Spin
        </Typography>
      </Box>
    </Box>
  );
};

export default PaceVsSpinCard;
```

### 6.5 ELO Movers Card

**File: `src/components/wrapped/cards/EloMoversCard.jsx`**

```jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import { useNavigate } from 'react-router-dom';

const EloMoversCard = ({ data }) => {
  const navigate = useNavigate();

  if (data.error) {
    return <Typography>{data.error}</Typography>;
  }

  const handleTeamClick = (teamName) => {
    navigate(`/team?team=${encodeURIComponent(teamName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  return (
    <Box className="elo-movers-content">
      {/* Risers Section */}
      <Box className="movers-section risers">
        <Typography variant="h6" className="section-title" sx={{ color: '#4CAF50' }}>
          <TrendingUpIcon /> Biggest Risers
        </Typography>
        {data.risers?.map((team, index) => (
          <Box 
            key={team.team} 
            className="mover-item"
            onClick={() => handleTeamClick(team.team)}
          >
            <Typography variant="body1" className="team-name">{team.team}</Typography>
            <Box className="elo-change positive">
              <Typography variant="h6">+{team.elo_change}</Typography>
              <Typography variant="caption">
                {team.start_elo} → {team.end_elo}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Fallers Section */}
      <Box className="movers-section fallers">
        <Typography variant="h6" className="section-title" sx={{ color: '#f44336' }}>
          <TrendingDownIcon /> Biggest Fallers
        </Typography>
        {data.fallers?.map((team, index) => (
          <Box 
            key={team.team} 
            className="mover-item"
            onClick={() => handleTeamClick(team.team)}
          >
            <Typography variant="body1" className="team-name">{team.team}</Typography>
            <Box className="elo-change negative">
              <Typography variant="h6">{team.elo_change}</Typography>
              <Typography variant="caption">
                {team.start_elo} → {team.end_elo}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default EloMoversCard;
```

### 6.6 Venue Vibes Card

**File: `src/components/wrapped/cards/VenueVibesCard.jsx`**

```jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { useNavigate } from 'react-router-dom';

const VenueVibesCard = ({ data }) => {
  const navigate = useNavigate();

  if (!data.venues || data.venues.length === 0) {
    return <Typography>No venue data available</Typography>;
  }

  const handleVenueClick = (venue) => {
    navigate(`/venue?venue=${encodeURIComponent(venue.name)}&start_date=2025-01-01&end_date=2025-12-31`);
  };

  // Calculate average for reference lines
  const avgPar = data.venues.reduce((sum, v) => sum + v.par_score, 0) / data.venues.length;
  const avgChase = data.venues.reduce((sum, v) => sum + v.chase_win_pct, 0) / data.venues.length;

  // Categorize venues
  const highScoring = data.venues.filter(v => v.par_score > avgPar);
  const chaseFriendly = data.venues.filter(v => v.chase_win_pct > 55);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const venue = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">{venue.name.split(',')[0]}</Typography>
          <Typography variant="body2">Par Score: {venue.par_score}</Typography>
          <Typography variant="body2">Chase Win%: {venue.chase_win_pct}%</Typography>
          <Typography variant="body2">Matches: {venue.matches}</Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="venue-card-content">
      {/* Quick Stats */}
      <Box className="venue-quick-stats">
        <Box className="venue-stat">
          <Typography variant="h5">{highScoring.length}</Typography>
          <Typography variant="caption">High-Scoring Venues</Typography>
        </Box>
        <Box className="venue-stat">
          <Typography variant="h5">{chaseFriendly.length}</Typography>
          <Typography variant="caption">Chase-Friendly</Typography>
        </Box>
      </Box>

      {/* Scatter Plot */}
      <Box className="venue-scatter">
        <ResponsiveContainer width="100%" height={180}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="par_score" 
              name="Par Score"
              domain={['dataMin - 10', 'dataMax + 10']}
              tick={{ fontSize: 10 }}
              label={{ value: 'Par Score', position: 'bottom', fontSize: 10 }}
            />
            <YAxis 
              type="number" 
              dataKey="chase_win_pct" 
              name="Chase Win %"
              domain={[30, 70]}
              tick={{ fontSize: 10 }}
              label={{ value: 'Chase %', angle: -90, position: 'left', fontSize: 10 }}
            />
            <ReferenceLine y={50} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgPar} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.venues} 
              onClick={(data) => handleVenueClick(data)}
              cursor="pointer"
            >
              {data.venues.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={entry.chase_win_pct > 55 ? '#4CAF50' : entry.chase_win_pct < 45 ? '#f44336' : '#2196F3'}
                  opacity={0.8}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </Box>

      {/* Top Venues List */}
      <Box className="top-venues">
        {data.venues.slice(0, 3).map((venue, index) => (
          <Box 
            key={venue.name} 
            className="venue-item"
            onClick={() => handleVenueClick(venue)}
          >
            <Typography variant="body2" className="venue-name">
              {venue.name.split(',')[0]}
            </Typography>
            <Typography variant="caption">
              Par: {venue.par_score} | Chase: {venue.chase_win_pct}%
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default VenueVibesCard;
```

### 6.7 Create Index File for Cards

**File: `src/components/wrapped/cards/index.js`**

```jsx
export { default as IntroCard } from './IntroCard';
export { default as PowerplayBulliesCard } from './PowerplayBulliesCard';
export { default as MiddleMerchantsCard } from './MiddleMerchantsCard';
export { default as DeathHittersCard } from './DeathHittersCard';
export { default as PaceVsSpinCard } from './PaceVsSpinCard';
export { default as PowerplayThievesCard } from './PowerplayThievesCard';
export { default as NineteenthOverGodsCard } from './NineteenthOverGodsCard';
export { default as EloMoversCard } from './EloMoversCard';
export { default as VenueVibesCard } from './VenueVibesCard';

// Add more card exports as you implement them
```

---

## 7. Styling & Mobile-First Design

### 7.1 Main CSS File

**File: `src/components/wrapped/wrapped.css`**

```css
/* ============================================
   WRAPPED 2025 - Mobile-First Styles
   ============================================ */

/* CSS Variables for Wrapped Theme */
:root {
  --wrapped-bg: #121212;
  --wrapped-card-bg: #1a1a1a;
  --wrapped-primary: #1DB954;
  --wrapped-secondary: #b3b3b3;
  --wrapped-text: #ffffff;
  --wrapped-text-muted: #a0a0a0;
  --wrapped-border: #333333;
  --wrapped-success: #4CAF50;
  --wrapped-warning: #ff9800;
  --wrapped-error: #f44336;
}

/* ============================================
   Container & Layout
   ============================================ */

.wrapped-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: var(--wrapped-bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  touch-action: pan-y;
  user-select: none;
  z-index: 1000;
}

.wrapped-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--wrapped-bg);
  color: var(--wrapped-text);
}

.wrapped-loading p {
  margin-top: 16px;
  color: var(--wrapped-secondary);
}

.wrapped-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--wrapped-bg);
  padding: 24px;
}

/* ============================================
   Progress Bar
   ============================================ */

.wrapped-progress-bar {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
}

.progress-segment {
  flex: 1;
  height: 3px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.progress-segment.completed {
  background: var(--wrapped-primary);
}

.progress-segment.active {
  background: var(--wrapped-text);
}

.progress-segment:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* ============================================
   Close Button
   ============================================ */

.wrapped-close-btn {
  position: absolute;
  top: 24px;
  right: 16px;
  z-index: 10;
  color: var(--wrapped-text) !important;
  background: rgba(0, 0, 0, 0.3) !important;
}

.wrapped-close-btn:hover {
  background: rgba(0, 0, 0, 0.5) !important;
}

/* ============================================
   Card Base Styles
   ============================================ */

.wrapped-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 60px 20px 20px;
  overflow-y: auto;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

.wrapped-card-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--wrapped-text-muted);
}

.wrapped-card-header {
  text-align: center;
  margin-bottom: 24px;
}

.wrapped-card-index {
  color: var(--wrapped-primary);
  font-size: 12px;
  letter-spacing: 2px;
}

.wrapped-card-title {
  color: var(--wrapped-text);
  font-weight: 700;
  font-size: 24px;
  margin: 8px 0;
  line-height: 1.2;
}

.wrapped-card-subtitle {
  color: var(--wrapped-secondary);
  font-size: 14px;
}

.wrapped-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ============================================
   Card Actions
   ============================================ */

.wrapped-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  padding: 16px 0;
  margin-top: auto;
}

.wrapped-action-btn {
  font-size: 12px !important;
  padding: 6px 12px !important;
  border-radius: 20px !important;
  text-transform: none !important;
  background: var(--wrapped-primary) !important;
  color: var(--wrapped-bg) !important;
}

.wrapped-action-btn-secondary {
  background: transparent !important;
  border: 1px solid var(--wrapped-primary) !important;
  color: var(--wrapped-primary) !important;
}

.wrapped-action-btn-share {
  background: transparent !important;
  color: var(--wrapped-secondary) !important;
}

/* ============================================
   Navigation Hints
   ============================================ */

.wrapped-nav-hints {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 8px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
}

.wrapped-container:hover .wrapped-nav-hints {
  opacity: 0.3;
}

.nav-hint {
  font-size: 48px;
  color: var(--wrapped-text);
}

/* ============================================
   Intro Card Specific
   ============================================ */

.intro-card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.intro-stat-hero {
  text-align: center;
}

.hero-number {
  font-size: 64px;
  font-weight: 800;
  color: var(--wrapped-primary);
  line-height: 1;
}

.hero-label {
  color: var(--wrapped-secondary);
  margin-top: 8px;
}

.intro-chart {
  width: 100%;
  max-width: 400px;
}

.intro-quick-stats {
  display: flex;
  gap: 24px;
  justify-content: center;
}

.quick-stat {
  text-align: center;
}

.quick-stat h6 {
  font-size: 24px;
  font-weight: 700;
}

.quick-stat span {
  color: var(--wrapped-secondary);
  font-size: 11px;
  text-transform: uppercase;
}

/* ============================================
   Scatter Card Specific
   ============================================ */

.scatter-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.top-players-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.top-player-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--wrapped-card-bg);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.top-player-item:hover {
  background: #252525;
}

.top-player-item .rank {
  color: var(--wrapped-primary);
  font-weight: 700;
  min-width: 40px;
}

.player-info {
  flex: 1;
}

.player-info h6 {
  color: var(--wrapped-text);
  font-size: 14px;
}

.player-info p {
  color: var(--wrapped-secondary);
  font-size: 12px;
}

.scatter-chart {
  background: var(--wrapped-card-bg);
  border-radius: 8px;
  padding: 12px;
}

.filter-slider {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
}

.filter-slider span {
  color: var(--wrapped-secondary);
  font-size: 12px;
}

/* ============================================
   Table Card Specific (Death Hitters, etc.)
   ============================================ */

.table-card-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.podium {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.podium-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  background: var(--wrapped-card-bg);
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
}

.podium-item:hover {
  transform: translateY(-4px);
}

.podium-item.first {
  order: 2;
  padding: 16px;
  background: linear-gradient(135deg, #1DB954 0%, #169c46 100%);
}

.podium-item.second {
  order: 1;
}

.podium-item.third {
  order: 3;
}

.podium-rank {
  font-weight: 700;
  color: var(--wrapped-primary);
}

.podium-item.first .podium-rank {
  color: var(--wrapped-text);
}

.podium-name {
  color: var(--wrapped-text);
  margin: 8px 0;
  text-align: center;
  font-size: 12px;
}

.podium-stat {
  color: var(--wrapped-text);
  font-weight: 700;
}

.podium-item span {
  color: var(--wrapped-secondary);
  font-size: 10px;
}

.remaining-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.list-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: var(--wrapped-card-bg);
  border-radius: 4px;
  cursor: pointer;
}

.list-item:hover {
  background: #252525;
}

.list-rank {
  color: var(--wrapped-secondary);
  min-width: 30px;
}

.list-name {
  flex: 1;
  color: var(--wrapped-text);
}

.list-stat {
  color: var(--wrapped-primary);
  font-weight: 600;
}

/* ============================================
   Diverging Bar Card (Pace vs Spin, ELO)
   ============================================ */

.diverging-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
}

.diverging-chart {
  background: var(--wrapped-card-bg);
  border-radius: 8px;
  padding: 12px;
}

.chart-legend {
  text-align: center;
}

.chart-legend span {
  color: var(--wrapped-secondary);
  font-size: 11px;
}

/* ============================================
   ELO Movers Card
   ============================================ */

.elo-movers-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.movers-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  margin-bottom: 8px;
}

.mover-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--wrapped-card-bg);
  border-radius: 8px;
  cursor: pointer;
}

.mover-item:hover {
  background: #252525;
}

.team-name {
  color: var(--wrapped-text);
}

.elo-change {
  text-align: right;
}

.elo-change.positive h6 {
  color: var(--wrapped-success);
}

.elo-change.negative h6 {
  color: var(--wrapped-error);
}

.elo-change span {
  color: var(--wrapped-secondary);
  font-size: 11px;
}

/* ============================================
   Venue Card
   ============================================ */

.venue-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.venue-quick-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.venue-stat {
  text-align: center;
}

.venue-stat h5 {
  color: var(--wrapped-primary);
  font-size: 28px;
  font-weight: 700;
}

.venue-stat span {
  color: var(--wrapped-secondary);
  font-size: 11px;
}

.venue-scatter {
  background: var(--wrapped-card-bg);
  border-radius: 8px;
  padding: 12px;
}

.top-venues {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.venue-item {
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  background: var(--wrapped-card-bg);
  border-radius: 4px;
  cursor: pointer;
}

.venue-item:hover {
  background: #252525;
}

.venue-name {
  color: var(--wrapped-text);
  font-weight: 500;
}

.venue-item span {
  color: var(--wrapped-secondary);
  font-size: 11px;
}

/* ============================================
   Tooltip Styles
   ============================================ */

.wrapped-tooltip {
  background: rgba(0, 0, 0, 0.9);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--wrapped-border);
}

.wrapped-tooltip h6 {
  color: var(--wrapped-text);
  margin-bottom: 8px;
}

.wrapped-tooltip p {
  color: var(--wrapped-secondary);
  font-size: 12px;
  margin: 4px 0;
}

/* ============================================
   Responsive Adjustments
   ============================================ */

@media (min-width: 768px) {
  .wrapped-card {
    padding: 80px 40px 40px;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .wrapped-card-title {
    font-size: 32px;
  }
  
  .hero-number {
    font-size: 80px;
  }
}

@media (max-width: 360px) {
  .wrapped-card-title {
    font-size: 20px;
  }
  
  .hero-number {
    font-size: 48px;
  }
  
  .podium {
    gap: 4px;
  }
  
  .podium-item {
    padding: 8px;
  }
}
```

---

## 8. Deep Linking & URL Structure

### 8.1 URL Patterns

```
Base URL: /wrapped/2025

Specific card: /wrapped/2025?card=powerplay_bullies
With filters: /wrapped/2025?card=death_hitters&leagues=IPL,BBL

Card IDs:
- intro
- powerplay_bullies
- middle_merchants
- death_hitters
- pace_vs_spin
- powerplay_thieves
- nineteenth_over_gods
- over_combos
- elo_movers
- batting_order_chaos
- twentieth_over_bowlers
- venue_vibes
- venue_phase
- venue_performers
- matchups
- fantasy
```

### 8.2 Deep Link Utility

**File: `src/utils/wrappedLinks.js`**

```javascript
/**
 * Wrapped Deep Link Utilities
 * 
 * Generates URLs for navigating from Wrapped cards to detailed views
 */

const DEFAULT_DATE_RANGE = {
  start: '2025-01-01',
  end: '2025-12-31'
};

/**
 * Generate a batter profile link with 2025 filters
 */
export const getBatterProfileLink = (playerName, additionalParams = {}) => {
  const params = new URLSearchParams({
    name: playerName,
    start_date: DEFAULT_DATE_RANGE.start,
    end_date: DEFAULT_DATE_RANGE.end,
    autoload: 'true',
    ...additionalParams
  });
  return `/player?${params.toString()}`;
};

/**
 * Generate a bowler profile link with 2025 filters
 */
export const getBowlerProfileLink = (playerName, additionalParams = {}) => {
  const params = new URLSearchParams({
    name: playerName,
    start_date: DEFAULT_DATE_RANGE.start,
    end_date: DEFAULT_DATE_RANGE.end,
    autoload: 'true',
    ...additionalParams
  });
  return `/bowler?${params.toString()}`;
};

/**
 * Generate a team profile link with 2025 filters
 */
export const getTeamProfileLink = (teamName, additionalParams = {}) => {
  const params = new URLSearchParams({
    team: teamName,
    start_date: DEFAULT_DATE_RANGE.start,
    end_date: DEFAULT_DATE_RANGE.end,
    autoload: 'true',
    ...additionalParams
  });
  return `/team?${params.toString()}`;
};

/**
 * Generate a venue analysis link with 2025 filters
 */
export const getVenueLink = (venueName, additionalParams = {}) => {
  const params = new URLSearchParams({
    venue: venueName,
    start_date: DEFAULT_DATE_RANGE.start,
    end_date: DEFAULT_DATE_RANGE.end,
    ...additionalParams
  });
  return `/venue?${params.toString()}`;
};

/**
 * Generate a query builder link with preset filters
 */
export const getQueryBuilderLink = ({
  over_min,
  over_max,
  group_by = [],
  min_balls,
  bowler_type = [],
  ...otherFilters
} = {}) => {
  const params = new URLSearchParams({
    start_date: DEFAULT_DATE_RANGE.start,
    end_date: DEFAULT_DATE_RANGE.end
  });
  
  if (over_min !== undefined) params.append('over_min', over_min);
  if (over_max !== undefined) params.append('over_max', over_max);
  if (min_balls) params.append('min_balls', min_balls);
  
  group_by.forEach(col => params.append('group_by', col));
  bowler_type.forEach(type => params.append('bowler_type', type));
  
  Object.entries(otherFilters).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach(v => params.append(key, v));
    } else {
      params.append(key, value);
    }
  });
  
  return `/query?${params.toString()}`;
};

/**
 * Generate a comparison page link with pre-selected players
 */
export const getComparisonLink = (playerNames = []) => {
  const params = new URLSearchParams({
    start_date: DEFAULT_DATE_RANGE.start,
    end_date: DEFAULT_DATE_RANGE.end
  });
  
  playerNames.forEach(name => params.append('players', name));
  
  return `/comparison?${params.toString()}`;
};
```

---

## 9. Social Sharing & OG Images

### 9.1 Meta Tags Setup

For social sharing to work properly, you need to set up Open Graph meta tags. Since this is a React SPA, you have two options:

**Option A: Server-Side Rendering (Recommended for proper previews)**

Add a simple server endpoint that returns HTML with proper OG tags when social media crawlers visit.

**Option B: Static Meta Tags (Simpler but less dynamic)**

Add to `public/index.html`:

```html
<head>
  <!-- Existing meta tags... -->
  
  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://hindsight2020.vercel.app/wrapped/2025" />
  <meta property="og:title" content="Hindsight 2025 Wrapped - T20 Cricket Year in Review" />
  <meta property="og:description" content="Discover the story of T20 cricket in 2025 - powerplay bullies, death specialists, and more!" />
  <meta property="og:image" content="https://hindsight2020.vercel.app/wrapped-preview.png" />

  <!-- Twitter -->
  <meta property="twitter:card" content="summary_large_image" />
  <meta property="twitter:url" content="https://hindsight2020.vercel.app/wrapped/2025" />
  <meta property="twitter:title" content="Hindsight 2025 Wrapped" />
  <meta property="twitter:description" content="T20 Cricket Year in Review" />
  <meta property="twitter:image" content="https://hindsight2020.vercel.app/wrapped-preview.png" />
</head>
```

### 9.2 Share Card Preview Image

Create a preview image at `public/wrapped-preview.png` (1200x630 pixels recommended).

---

## 10. Testing Checklist

### 10.1 Backend Testing

```bash
# Test the wrapped endpoint
curl http://localhost:8000/wrapped/2025/cards

# Test a specific card
curl http://localhost:8000/wrapped/2025/card/powerplay_bullies

# Test metadata
curl http://localhost:8000/wrapped/2025/metadata
```

### 10.2 Frontend Testing Checklist

- [ ] **Navigation**
  - [ ] Tap left side goes to previous card
  - [ ] Tap right side goes to next card
  - [ ] Swipe left goes to next card
  - [ ] Swipe right goes to previous card
  - [ ] Keyboard arrows work (desktop)
  - [ ] Progress bar segments are clickable
  - [ ] ESC key closes wrapped
  - [ ] X button closes wrapped

- [ ] **URL Updates**
  - [ ] URL updates when changing cards
  - [ ] Direct URL to card works (e.g., `/wrapped/2025?card=death_hitters`)
  - [ ] Refresh maintains current card

- [ ] **Deep Links**
  - [ ] "Open in App" buttons navigate correctly
  - [ ] "Recreate Query" opens Query Builder with correct filters
  - [ ] Share button works (copies URL or triggers native share)

- [ ] **Visualizations**
  - [ ] All charts render correctly
  - [ ] Tooltips appear on hover/tap
  - [ ] Click on data points navigates to profiles
  - [ ] Filters (like min_balls slider) work

- [ ] **Mobile Testing**
  - [ ] Full screen on mobile
  - [ ] Touch gestures work smoothly
  - [ ] Text is readable
  - [ ] Buttons are tappable (44px minimum)
  - [ ] No horizontal scroll
  - [ ] Charts scale properly

- [ ] **Error Handling**
  - [ ] Loading state shows
  - [ ] Error state shows with message
  - [ ] Empty data state handled gracefully

### 10.3 Performance Testing

- [ ] Initial load < 3 seconds
- [ ] Card transitions smooth (60fps)
- [ ] No memory leaks when navigating cards
- [ ] Images/charts lazy loaded where appropriate

---

## 11. Deployment Notes

### 11.1 Environment Variables

No new environment variables needed - uses existing `config.js` setup.

### 11.2 Vercel Configuration

Add the wrapped route to `vercel.json`:

```json
{
  "rewrites": [
    { "source": "/wrapped/:path*", "destination": "/index.html" }
  ]
}
```

### 11.3 Deployment Steps

1. **Backend First:**
   ```bash
   # Deploy backend to Heroku
   git push heroku main
   ```

2. **Test API:**
   ```bash
   curl https://your-api-url.herokuapp.com/wrapped/2025/cards
   ```

3. **Frontend Deploy:**
   ```bash
   # Deploy to Vercel (usually automatic with GitHub push)
   vercel --prod
   ```

4. **Verify Production:**
   - Visit `https://hindsight2020.vercel.app/wrapped/2025`
   - Test all navigation
   - Test deep links
   - Test on mobile device

---

## 12. Future Enhancements

### Phase 2 Ideas

1. **More Cards:** Add remaining cards from the original spec
2. **League Selector:** Allow filtering by specific leagues
3. **Compare Years:** Add 2024 comparison data
4. **Animations:** Add card flip/slide animations
5. **Sound Effects:** Optional audio feedback on navigation
6. **Save Favorites:** Let users bookmark favorite cards
7. **Personalized Wrapped:** User-specific stats if authenticated

### Technical Debt

- [ ] Add unit tests for card components
- [ ] Add E2E tests with Cypress
- [ ] Add error boundary for card crashes
- [ ] Implement virtual scrolling for long lists
- [ ] Add skeleton loading states

---

## Quick Start Commands

```bash
# Backend
cd cricket-data-thing
python -m uvicorn main:app --reload

# Frontend (in separate terminal)
cd cricket-data-thing
npm start

# Visit
open http://localhost:3000/wrapped/2025
```

---

**Document Version:** 1.0
**Last Updated:** December 2024
**Author:** Implementation Guide for Junior Developer

