# Google-Style Search Landing Page Implementation Plan

## Overview

This document outlines a comprehensive plan to create a new Google-style search landing page for Hindsight Cricket Analytics. The page will feature a simple, clean design with a central search bar and two buttons: "Search" and "I'm Feeling Lucky".

**Key Objectives:**
- Simple, minimalist Google-style design
- Unified search across players, teams, and venues
- Display both batting AND bowling stats for players (unified player view)
- Implement recent/frequent search history
- "I'm Feeling Lucky" random navigation feature

---

## 1. Default Parameters

All searches will use these default parameters unless explicitly overridden:

```javascript
const DEFAULT_PARAMS = {
  start_date: `${new Date().getFullYear() - 1}-01-01`, // First day of previous year
  end_date: new Date().toISOString().split('T')[0],    // Current date
  leagues: [],                                          // All leagues
  include_international: true,                          // Include international matches
  top_teams: 20,                                        // Top 20 international teams
  venue: null                                           // All venues
};
```

---

## 2. Directory Structure

```
cricket-data-thing/
├── src/
│   ├── components/
│   │   └── search/                    # NEW DIRECTORY
│   │       ├── GoogleSearchLanding.jsx
│   │       ├── SearchBar.jsx
│   │       ├── SearchResults.jsx
│   │       ├── PlayerSearchResult.jsx
│   │       ├── TeamSearchResult.jsx
│   │       ├── VenueSearchResult.jsx
│   │       ├── RecentSearches.jsx
│   │       └── searchConfig.js
│   └── utils/
│       └── searchStorage.js           # NEW
├── routers/
│   └── search.py                      # NEW
├── services/
│   ├── search.py                      # NEW
│   ├── team_summary.py                # NEW
│   └── venue_summary.py               # NEW
```

---

## Phase 1: Backend - Search Infrastructure

### Step 1.1: Create Search Service
**File:** `services/search.py`

Key functions:
- `search_entities(query, db)` - Unified search across players/teams/venues
- `get_random_entity(db)` - Random selection for "I'm Feeling Lucky"

### Step 1.2: Create Search Router
**File:** `routers/search.py`

Endpoints:
- `GET /search/suggestions?q={query}` - Autocomplete suggestions
- `GET /search/random` - Random entity for "I'm Feeling Lucky"

### Step 1.3: Register Router in main.py

---

## Phase 2: Backend - Team & Venue DNA Summaries

### Step 2.1: Team DNA Summary Service
**File:** `services/team_summary.py`

### Step 2.2: Venue DNA Summary Service  
**File:** `services/venue_summary.py`

### Step 2.3: Add Endpoints to player_summary.py
- `GET /player-summary/team/{team_name}`
- `GET /player-summary/venue/{venue_name}`

---

## Phase 3: Frontend - Core Components

### Step 3.1: searchConfig.js
Default parameters and constants.

### Step 3.2: GoogleSearchLanding.jsx
Main landing page with centered search bar.

### Step 3.3: SearchBar.jsx
Autocomplete search with debounced API calls.

### Step 3.4: SearchResults.jsx
Routes to appropriate result component based on entity type.

---

## Phase 4: Frontend - Result Components

### Step 4.1: PlayerSearchResult.jsx
- Displays BOTH batting and bowling stats
- Player DNA summaries for both
- Collapsible visualizations

### Step 4.2: TeamSearchResult.jsx
- Team stats cards
- Team DNA summary
- Phase performance charts

### Step 4.3: VenueSearchResult.jsx
- Venue overview stats
- Venue DNA summary
- Win percentage charts

---

## Phase 5: Frontend - Recent Searches

### Step 5.1: searchStorage.js
LocalStorage utilities for recent searches.

### Step 5.2: RecentSearches.jsx
Display recent searches as clickable chips.

---

## Phase 6: Integration & Testing

### Step 6.1: Update App.js
Add `/search` route.

### Step 6.2: Testing Checklist

**Backend:**
- [ ] `/search/suggestions?q=kohli` returns players
- [ ] `/search/suggestions?q=RCB` returns teams
- [ ] `/search/suggestions?q=chinnaswamy` returns venues
- [ ] `/search/random` returns valid entity

**Frontend:**
- [ ] Autocomplete populates as user types
- [ ] Player selection shows batting + bowling stats
- [ ] Team selection shows visualizations
- [ ] Venue selection shows analysis
- [ ] "I'm Feeling Lucky" navigates correctly
- [ ] Recent searches stored and displayed

---

## API Endpoints Summary

### New Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/search/suggestions` | GET | Autocomplete |
| `/search/random` | GET | I'm Feeling Lucky |
| `/player-summary/team/{team}` | GET | Team DNA |
| `/player-summary/venue/{venue}` | GET | Venue DNA |

### Existing Endpoints to Reuse
- `/player/{name}/stats` - Batting
- `/player/{name}/bowling_stats` - Bowling
- `/player-summary/batter/{name}` - Batter DNA
- `/player-summary/bowler/{name}` - Bowler DNA
- `/teams/{team}/matches` - Team data
- `/venue_notes/{venue}` - Venue analysis

---

## Implementation Order

1. **Backend Phase 1**: Search service + router (2-3 hours)
2. **Frontend Phase 3**: Core landing page + search bar (3-4 hours)
3. **Frontend Phase 4.1**: PlayerSearchResult (3-4 hours)
4. **Frontend Phase 5**: Recent searches (1-2 hours)
5. **Backend Phase 2**: Team/Venue DNA (3-4 hours)
6. **Frontend Phase 4.2-4.3**: Team/Venue results (3-4 hours)
7. **Testing & Polish** (2-3 hours)

**Total: 18-24 hours**

---

*Last Updated: December 2024*
