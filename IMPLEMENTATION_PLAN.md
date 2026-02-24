# Implementation Plan: Upcoming Fixtures, AI Match Previews & Venue Delivery Stats

## IMPORTANT: Project Directory

**All work should be done in: `/Users/adityabalaji/cdt/cricket-data-thing/`**

- Backend (FastAPI): `/Users/adityabalaji/cdt/cricket-data-thing/`
- Frontend (React): `/Users/adityabalaji/cdt/cricket-data-thing/src/`
- Services: `/Users/adityabalaji/cdt/cricket-data-thing/services/`
- Routers: `/Users/adityabalaji/cdt/cricket-data-thing/routers/`

**NOT** `/Users/adityabalaji/blah/cricket-data-thing/` (that's an older copy).

---

## Key Existing Files to Reuse

| File | What it provides |
|------|-----------------|
| `services/delivery_data_service.py` | `get_venue_match_stats()`, `get_venue_phase_stats()`, filter builders for delivery_details |
| `services/wrapped/card_length_masters.py` | `LENGTH_LABELS` map, normalization pattern |
| `routers/player_summary.py` | OpenAI integration pattern (cache, prompt, fallback) |
| `models.py` | `teams_mapping` (full team name -> abbreviation) |
| `src/data/iplSchedule.js` | Current hardcoded schedule to replace |
| `src/components/LandingPage.jsx` | Landing page consuming fixtures |
| `src/components/VenueNotes.jsx` | Venue analysis page to add delivery stats + preview card |
| `src/components/BowlingAnalysis.jsx` | Self-fetching component pattern to follow |
| `src/config.js` | `config.API_URL` for API calls |

---

## Implementation Order

### Step 1: Venue Delivery Stats (fully independent, lowest risk)

#### Backend: New endpoint in `main.py`

Add near the existing `/venue_notes/{venue}` endpoint:

```python
@app.get("/venues/{venue}/delivery-stats")
def get_venue_delivery_stats(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    db: Session = Depends(get_session)
):
```

Queries the `delivery_details` table (which has `line`, `length`, `shot`, `control` columns). Use filter patterns from `services/delivery_data_service.py`:
- Reuse `build_venue_filter_delivery_details()` for venue filtering
- Reuse `build_competition_filter_delivery_details()` for league filtering
- Normalize values with `UPPER(REPLACE(dd.length, ' ', '_'))` (same as `card_length_masters.py`)
- Use `LENGTH_LABELS` map from `card_length_masters.py` for display names

**Returns 5 datasets:**

1. **`length_distribution`**: Per-length-type: balls, runs, SR, wickets, control%, percentage
2. **`line_distribution`**: Per-line-type: same metrics
3. **`shot_distribution`**: Top 15 shot types by frequency: balls, runs, SR, control%
4. **`control_by_phase`**: 4 phases (PP/Mid1/Mid2/Death): total balls, control%, SR
5. **`data_coverage`**: `{ total_balls, balls_with_length, balls_with_control, balls_with_shot, balls_with_line, matches_covered }`

Data coverage lets the frontend decide whether to show each tab.

#### Frontend: New file `src/components/VenueDeliveryStats.jsx`

Self-fetching tabbed card component (follow `BowlingAnalysis.jsx` pattern):
- Props: `venue, startDate, endDate, team1, team2, isMobile, leagues, includeInternational`
- Fetches from `/venues/{venue}/delivery-stats?start_date=...&end_date=...`
- Returns `null` if `data.data_coverage.matches_covered < 3`

**4 tabs:**
1. **Length Distribution**: Horizontal BarChart, Y-axis = length labels, X-axis = % deliveries, bars colored by SR
2. **Line Distribution**: Same structure for line types
3. **Shot Types**: Horizontal BarChart sorted by SR descending, top 12-15 shots
4. **Control% by Phase**: Grouped BarChart with 4 groups (PP/Mid1/Mid2/Death), two bars per group: Control% + Strike Rate

Uses recharts (already imported in the project): `BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip`

#### Frontend: Modify `src/components/VenueNotes.jsx`

Insert after the PhaseWiseStrategy card (after the `</Card>` closing the PhaseWiseStrategy grid item around line 855-856):

```jsx
<Grid item xs={12}>
    <VenueDeliveryStats
        venue={venue}
        startDate={startDate}
        endDate={endDate}
        team1={selectedTeam1?.full_name}
        team2={selectedTeam2?.full_name}
        isMobile={isMobile}
    />
</Grid>
```

Import at top: `import VenueDeliveryStats from './VenueDeliveryStats';`

No conditional wrapper needed - VenueDeliveryStats returns null when data is insufficient.

---

### Step 2: ESPN Fixture Scraper + Frontend Wiring

#### Backend: New file `services/fixture_scraper.py`

Scrape ESPN hidden API (no key needed):
```
GET https://site.api.espn.com/apis/personalized/v2/scoreboard/header?sport=cricket&region=in&lang=en
```

Function: `fetch_upcoming_fixtures(count=5) -> List[dict]`
- Fetch from ESPN endpoint
- Filter to upcoming/scheduled matches
- Map each match to: `{ date, time, venue, team1, team2, team1Abbr, team2Abbr, series, matchId }`
- Use `teams_mapping` from `models.py` to generate abbreviations
- Add `VENUE_NAME_MAP` dict to translate ESPN venue names to DB venue names (e.g., `"M.Chinnaswamy Stadium, Bengaluru"` -> `"M Chinnaswamy Stadium, Bangalore"`)
- Cache results for 1 hour (simple timestamp check)
- Fallback: return empty list on error

#### Backend: New file `routers/fixtures.py`

```python
from fastapi import APIRouter, Query
from services.fixture_scraper import fetch_upcoming_fixtures

router = APIRouter(prefix="/fixtures", tags=["Fixtures"])

@router.get("/upcoming")
def get_upcoming_fixtures(count: int = Query(default=5, ge=1, le=20)):
    return fetch_upcoming_fixtures(count)
```

#### Register in `main.py`

Add with other router imports:
```python
from routers.fixtures import router as fixtures_router
```
And register:
```python
app.include_router(fixtures_router)
```

#### Frontend: Modify `src/data/iplSchedule.js`

Replace hardcoded schedule with async API call:
- Remove `iplSchedule` array
- Replace `getUpcomingMatches()` with `fetchUpcomingMatches(count)` that calls `GET /fixtures/upcoming?count={count}`
- Keep `formatDate()` and `formatVenue()` utility exports
- The function should return data shaped like the old format: `{ matchNumber, date, time, venue, team1, team2, team1Abbr, team2Abbr }`

```javascript
import config from '../config';

export const fetchUpcomingMatches = async (count = 3) => {
  try {
    const response = await fetch(`${config.API_URL}/fixtures/upcoming?count=${count}`);
    if (!response.ok) throw new Error('Failed to fetch fixtures');
    const data = await response.json();
    return data.map((match, index) => ({
      matchNumber: index + 1,
      date: match.date,
      time: match.time,
      venue: match.venue,
      team1: match.team1,
      team2: match.team2,
      team1Abbr: match.team1_abbr,
      team2Abbr: match.team2_abbr,
    }));
  } catch (error) {
    console.error('Error fetching upcoming matches:', error);
    return [];
  }
};

export const formatDate = (dateString) => {
  const date = new Date(dateString);
  const options = { weekday: 'short', month: 'short', day: 'numeric' };
  return date.toLocaleDateString('en-US', options);
};

export const formatVenue = (venue) => venue;
```

#### Frontend: Modify `src/components/LandingPage.jsx`

- Change import: `import { fetchUpcomingMatches, formatDate, formatVenue } from '../data/iplSchedule';`
- In useEffect (line ~44), change to: `const nextMatches = await fetchUpcomingMatches(3);`
- Remove the `todayString` logic since the backend handles date filtering now
- Everything else stays the same since the data shape is preserved

---

### Step 3: AI Match Preview Generation

#### Backend: New file `services/match_preview.py`

Function: `gather_preview_context(venue, team1, team2, db) -> dict`

Collects data from existing services/queries:
- Venue stats via `get_venue_match_stats()` from `services/delivery_data_service.py`
- Phase stats via `get_venue_phase_stats()` from same service
- H2H last 10 matches: `SELECT date, winner, team1_elo, team2_elo FROM matches WHERE ...`
- Recent form (last 5 for each team): W/L record
- Latest ELO for both teams from `matches` table

#### Backend: New file `routers/match_preview.py`

Follow the exact pattern from `routers/player_summary.py`:
- Same OpenAI config: `gpt-4o-mini`, `max_tokens=800`, `temperature=0.4`
- Same cache pattern: in-memory dict with MD5 hash key
- Same fallback pattern: rule-based summary if OpenAI fails

```python
router = APIRouter(prefix="/match-preview", tags=["Match Preview"])

@router.get("/{venue}/{team1_abbr}/{team2_abbr}")
```

**Prompt** - structured output with 5 sections:
- Venue Profile (avg scores, bat/chase bias)
- Form Guide (recent W/L for both teams)
- Head-to-Head (record + trends)
- Key Matchup Factor (tactical insight from data)
- Preview Take (prediction with reasoning)

#### Register in `main.py` alongside fixtures router.

#### Frontend: New file `src/components/MatchPreviewCard.jsx`

Small self-fetching component:
- Props: `venue`, `team1Abbr`, `team2Abbr`
- Auto-fetches preview on mount from `/match-preview/{venue}/{team1Abbr}/{team2Abbr}`
- Renders the 5-section text in a Card with subtle background
- Loading spinner, error handling

#### Frontend: Modify `src/components/LandingPage.jsx`

Add to each fixture card (after the Venue Analysis + Team Matchups buttons):
- "AI Preview" button that fetches on click
- Shows preview text in a collapsible Paper below the buttons
- State: `previewData` dict and `previewLoading` dict keyed by `team1Abbr-team2Abbr`

#### Frontend: Modify `src/components/VenueNotes.jsx`

Add preview card at top of "Team Performance Analysis" section when both teams selected:

```jsx
{selectedTeam1 && selectedTeam2 && (
    <Grid item xs={12}>
        <MatchPreviewCard
            venue={venue}
            team1Abbr={selectedTeam1.abbreviated_name}
            team2Abbr={selectedTeam2.abbreviated_name}
        />
    </Grid>
)}
```

Import: `import MatchPreviewCard from './MatchPreviewCard';`

---

## Files Summary

| File | Action | Step |
|------|--------|------|
| `main.py` | MODIFY - add delivery-stats endpoint + register 2 routers | 1, 2, 3 |
| `services/fixture_scraper.py` | CREATE | 2 |
| `routers/fixtures.py` | CREATE | 2 |
| `services/match_preview.py` | CREATE | 3 |
| `routers/match_preview.py` | CREATE | 3 |
| `src/components/VenueDeliveryStats.jsx` | CREATE | 1 |
| `src/components/MatchPreviewCard.jsx` | CREATE | 3 |
| `src/data/iplSchedule.js` | MODIFY - replace hardcoded with async API | 2 |
| `src/components/LandingPage.jsx` | MODIFY - async fixtures + AI preview button | 2, 3 |
| `src/components/VenueNotes.jsx` | MODIFY - insert VenueDeliveryStats + MatchPreviewCard | 1, 3 |

## Verification

1. `curl /fixtures/upcoming?count=3` - returns current upcoming matches
2. `curl "/venues/M Chinnaswamy Stadium, Bangalore/delivery-stats?start_date=2024-01-01"` - returns distributions
3. `curl "/match-preview/M Chinnaswamy Stadium, Bangalore/RCB/CSK"` - returns 5-section preview
4. Frontend: landing page loads fixtures dynamically, venue page shows delivery stats card
5. Graceful degradation: VenueDeliveryStats returns null when data insufficient

---

## Deferred UX Improvements (Parked)

Venue Tactical Explorer follow-ups (deferred for later):

- Wagon wheel should default to **zone aggregation** with a clear metric toggle (runs / wickets / balls / SR), plus **LHB/RHB** filtering.
- Users should be able to **drill down from zones into individual rays** on demand (click zone -> ray view).
- Venue pitch map cell metrics should stay **consistent with batter pitch maps**:
  - Primary: `Avg @ SR`
  - Secondary: `Boundary % | Dot % | Control %`
- Potential future optimization: server-side aggregation/pagination for large wagon-wheel payloads and richer zone hover tooltips.
