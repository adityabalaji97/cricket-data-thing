# Contextual Query Builder Links - Implementation Spec

> **Goal**: Drive users from Player/Bowler/Venue pages to the Query Builder by showing relevant, pre-filled query suggestions based on the current context.
> 
> **Estimated Effort**: 4-6 hours  
> **Impact**: High (converts casual browsers → power users)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Query Templates by Page](#3-query-templates-by-page)
4. [UI Component Design](#4-ui-component-design)
5. [Implementation Guide](#5-implementation-guide)
6. [File Changes Summary](#6-file-changes-summary)
7. [Testing Checklist](#7-testing-checklist)

---

## 1. Overview

### 1.1 The Problem

The Query Builder is powerful but underutilized because:
- Users don't know what questions they can ask
- There's no natural path from profile pages to Query Builder
- The learning curve is steep for first-time users

### 1.2 The Solution

Add contextual "Explore in Query Builder" prompts on existing pages that:
- Ask interesting questions relevant to what the user is viewing
- Link directly to Query Builder with pre-filled filters
- Auto-execute the query so users see results immediately

### 1.3 Example User Flow

```
1. User views Virat Kohli's Batter Profile
2. User sees: "🔍 How does Kohli perform against leg-spinners in death overs?"
3. User clicks the link
4. Query Builder opens with filters pre-set and results already loaded
5. User thinks: "Wow, I can ask anything like this!"
```

---

## 2. Architecture

### 2.1 New Utility File

Create a new utility file that generates Query Builder URLs based on context.

**File**: `src/utils/queryBuilderLinks.js`

```javascript
/**
 * Query Builder Link Generator
 * 
 * This utility creates pre-filled Query Builder URLs for contextual prompts.
 * Each function returns an object with:
 *   - question: Human-readable question to display
 *   - url: The Query Builder URL with pre-filled parameters
 *   - tags: Category tags for filtering/styling
 */

// Base URL for Query Builder
const QUERY_BUILDER_PATH = '/query';

/**
 * Builds a Query Builder URL from filters and groupBy arrays
 * Reuses the existing filtersToUrlParams logic
 */
export const buildQueryUrl = (filters, groupBy = []) => {
  const params = new URLSearchParams();
  
  // Add filters
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(item => params.append(key, item));
      } else {
        params.append(key, value);
      }
    }
  });
  
  // Add grouping
  groupBy.forEach(col => params.append('group_by', col));
  
  return `${QUERY_BUILDER_PATH}?${params.toString()}`;
};

/**
 * Generate contextual queries for a BATTER profile
 * 
 * @param {string} playerName - The batter's name (e.g., "V Kohli")
 * @param {object} context - Additional context from the page
 * @param {string} context.startDate - Start date filter
 * @param {string} context.endDate - End date filter  
 * @param {string[]} context.leagues - Selected leagues
 * @param {string} context.venue - Selected venue (optional)
 * @returns {Array} Array of query objects
 */
export const getBatterContextualQueries = (playerName, context = {}) => {
  const { startDate, endDate, leagues = [], venue } = context;
  
  // Base filters that apply to all queries for this batter
  const baseFilters = {
    batters: [playerName],
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
    ...(leagues.length > 0 && { leagues }),
    ...(venue && venue !== 'All Venues' && { venue }),
  };
  
  const queries = [
    // Query 1: Performance vs Spin by Phase
    {
      question: `How does ${playerName.split(' ').pop()} perform against spin in each phase?`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          bowler_type: ['LC', 'LO', 'RL', 'RO'], // All spin types
          min_balls: 10,
        },
        ['phase', 'bowler_type']
      ),
      tags: ['spin', 'phase', 'matchup'],
      priority: 1,
    },
    
    // Query 2: Performance vs Pace by Phase
    {
      question: `How does ${playerName.split(' ').pop()} handle pace bowling by phase?`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          bowler_type: ['RF', 'RFM', 'RM', 'LF', 'LFM', 'LM'], // All pace types
          min_balls: 10,
        },
        ['phase', 'bowler_type']
      ),
      tags: ['pace', 'phase', 'matchup'],
      priority: 2,
    },
    
    // Query 3: Performance by Ball Direction
    {
      question: `Where does ${playerName.split(' ').pop()} score most runs? (ball direction)`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 20,
        },
        ['ball_direction']
      ),
      tags: ['technique', 'ball_direction'],
      priority: 3,
    },
    
    // Query 4: Death Overs Deep Dive
    {
      question: `${playerName.split(' ').pop()}'s death overs performance breakdown`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 16,
          over_max: 19,
          min_balls: 10,
        },
        ['bowler_type']
      ),
      tags: ['death', 'phase', 'finishing'],
      priority: 4,
    },
    
    // Query 5: Powerplay Performance
    {
      question: `${playerName.split(' ').pop()} in powerplay: spin vs pace`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 0,
          over_max: 5,
          min_balls: 10,
        },
        ['bowler_type']
      ),
      tags: ['powerplay', 'phase'],
      priority: 5,
    },
    
    // Query 6: Year-over-Year Trend
    {
      question: `${playerName.split(' ').pop()}'s performance trend by year`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 50,
        },
        ['year']
      ),
      tags: ['trend', 'career'],
      priority: 6,
    },
  ];
  
  return queries;
};

/**
 * Generate contextual queries for a BOWLER profile
 * 
 * @param {string} playerName - The bowler's name
 * @param {object} context - Additional context
 * @param {string} context.bowlerType - The bowler's type (e.g., "RF", "LO")
 * @returns {Array} Array of query objects
 */
export const getBowlerContextualQueries = (playerName, context = {}) => {
  const { startDate, endDate, leagues = [], venue, bowlerType } = context;
  
  const baseFilters = {
    bowlers: [playerName],
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
    ...(leagues.length > 0 && { leagues }),
    ...(venue && venue !== 'All Venues' && { venue }),
  };
  
  const shortName = playerName.split(' ').pop();
  
  const queries = [
    // Query 1: Performance vs LHB vs RHB
    {
      question: `${shortName} vs left-handers vs right-handers`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 20,
        },
        ['striker_batter_type']
      ),
      tags: ['matchup', 'handedness'],
      priority: 1,
    },
    
    // Query 2: Performance by Phase
    {
      question: `${shortName}'s effectiveness across match phases`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 15,
        },
        ['phase']
      ),
      tags: ['phase', 'economy'],
      priority: 2,
    },
    
    // Query 3: Death Overs Breakdown
    {
      question: `${shortName} in death overs: by batter handedness`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 16,
          over_max: 19,
          min_balls: 10,
        },
        ['striker_batter_type']
      ),
      tags: ['death', 'matchup'],
      priority: 3,
    },
    
    // Query 4: Crease Combo Analysis
    {
      question: `How do batting combinations affect ${shortName}?`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 15,
        },
        ['crease_combo']
      ),
      tags: ['crease_combo', 'advanced'],
      priority: 4,
    },
    
    // Query 5: Ball Direction Analysis
    {
      question: `Where does ${shortName} get hit most? (by ball direction)`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 20,
        },
        ['ball_direction']
      ),
      tags: ['technique', 'ball_direction'],
      priority: 5,
    },
    
    // Query 6: Yearly Trend
    {
      question: `${shortName}'s bowling evolution by year`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 50,
        },
        ['year']
      ),
      tags: ['trend', 'career'],
      priority: 6,
    },
  ];
  
  return queries;
};

/**
 * Generate contextual queries for a VENUE analysis page
 * 
 * @param {string} venueName - The venue name
 * @param {object} context - Additional context
 * @returns {Array} Array of query objects
 */
export const getVenueContextualQueries = (venueName, context = {}) => {
  const { startDate, endDate, leagues = [], team1, team2 } = context;
  
  const baseFilters = {
    venue: venueName,
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
    ...(leagues.length > 0 && { leagues }),
  };
  
  // Shorten venue name for display
  const shortVenue = venueName.split(',')[0];
  
  const queries = [
    // Query 1: Batting by Phase
    {
      question: `Scoring patterns at ${shortVenue} by phase`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 50,
        },
        ['phase']
      ),
      tags: ['phase', 'scoring'],
      priority: 1,
    },
    
    // Query 2: Spin vs Pace at Venue
    {
      question: `Spin vs pace bowling at ${shortVenue}`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 100,
        },
        ['bowler_type']
      ),
      tags: ['bowling', 'matchup'],
      priority: 2,
    },
    
    // Query 3: Crease Combos at Venue
    {
      question: `Left-right batting combinations at ${shortVenue}`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          min_balls: 50,
        },
        ['crease_combo']
      ),
      tags: ['crease_combo', 'tactics'],
      priority: 3,
    },
    
    // Query 4: Death Overs at Venue
    {
      question: `Death overs scoring at ${shortVenue}`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 16,
          over_max: 19,
          min_balls: 50,
        },
        ['bowler_type']
      ),
      tags: ['death', 'scoring'],
      priority: 4,
    },
  ];
  
  // Add team-specific queries if teams are selected
  if (team1) {
    queries.push({
      question: `${team1.abbreviated_name || team1} batters at ${shortVenue}`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          batting_teams: [team1.full_name || team1],
          min_balls: 20,
        },
        ['batter', 'phase']
      ),
      tags: ['team', team1.abbreviated_name || team1],
      priority: 5,
    });
  }
  
  if (team2) {
    queries.push({
      question: `${team2.abbreviated_name || team2} batters at ${shortVenue}`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          batting_teams: [team2.full_name || team2],
          min_balls: 20,
        },
        ['batter', 'phase']
      ),
      tags: ['team', team2.abbreviated_name || team2],
      priority: 6,
    });
  }
  
  return queries;
};

/**
 * Generate contextual queries for TEAM MATCHUP pages
 */
export const getMatchupContextualQueries = (team1, team2, context = {}) => {
  const { startDate, endDate, leagues = [] } = context;
  
  const baseFilters = {
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
    ...(leagues.length > 0 && { leagues }),
  };
  
  const team1Name = team1?.full_name || team1;
  const team2Name = team2?.full_name || team2;
  const team1Short = team1?.abbreviated_name || team1;
  const team2Short = team2?.abbreviated_name || team2;
  
  return [
    // Query 1: Team 1 batting vs Team 2 bowling
    {
      question: `${team1Short} batters vs ${team2Short} bowlers`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          batting_teams: [team1Name],
          bowling_teams: [team2Name],
          min_balls: 20,
        },
        ['batter', 'bowler_type']
      ),
      tags: ['matchup', team1Short],
      priority: 1,
    },
    
    // Query 2: Team 2 batting vs Team 1 bowling
    {
      question: `${team2Short} batters vs ${team1Short} bowlers`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          batting_teams: [team2Name],
          bowling_teams: [team1Name],
          min_balls: 20,
        },
        ['batter', 'bowler_type']
      ),
      tags: ['matchup', team2Short],
      priority: 2,
    },
    
    // Query 3: Phase comparison
    {
      question: `${team1Short} vs ${team2Short}: phase-by-phase breakdown`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          teams: [team1Name, team2Name],
          min_balls: 50,
        },
        ['batting_team', 'phase']
      ),
      tags: ['phase', 'comparison'],
      priority: 3,
    },
  ];
};
```

---

## 3. Query Templates by Page

### 3.1 Batter Profile Queries

| Query | Filters | Group By | Why It's Interesting |
|-------|---------|----------|---------------------|
| "vs spin by phase" | `bowler_type: [LC,LO,RL,RO]` | `phase, bowler_type` | Shows spin vulnerability/strength |
| "vs pace by phase" | `bowler_type: [RF,RFM,RM,LF,LFM,LM]` | `phase, bowler_type` | Shows pace handling |
| "by ball direction" | `min_balls: 20` | `ball_direction` | Shows scoring zones |
| "death overs" | `over_min: 16, over_max: 19` | `bowler_type` | Shows finishing ability |
| "powerplay" | `over_min: 0, over_max: 5` | `bowler_type` | Shows opening ability |
| "trend by year" | `min_balls: 50` | `year` | Shows career trajectory |

### 3.2 Bowler Profile Queries

| Query | Filters | Group By | Why It's Interesting |
|-------|---------|----------|---------------------|
| "vs LHB vs RHB" | `min_balls: 20` | `striker_batter_type` | Shows handedness preference |
| "by phase" | `min_balls: 15` | `phase` | Shows phase specialization |
| "death overs by hand" | `over_min: 16, over_max: 19` | `striker_batter_type` | Shows death bowling effectiveness |
| "by crease combo" | `min_balls: 15` | `crease_combo` | Shows LH-RH combination impact |
| "by ball direction" | `min_balls: 20` | `ball_direction` | Shows where they get hit |
| "trend by year" | `min_balls: 50` | `year` | Shows career evolution |

### 3.3 Venue Queries

| Query | Filters | Group By | Why It's Interesting |
|-------|---------|----------|---------------------|
| "scoring by phase" | `min_balls: 50` | `phase` | Shows venue character |
| "spin vs pace" | `min_balls: 100` | `bowler_type` | Shows pitch behavior |
| "crease combos" | `min_balls: 50` | `crease_combo` | Shows tactical patterns |
| "death scoring" | `over_min: 16, over_max: 19` | `bowler_type` | Shows death over behavior |

---

## 4. UI Component Design

### 4.1 New Component: `ContextualQueryPrompts.jsx`

Create a reusable component that displays query suggestions.

**File**: `src/components/ContextualQueryPrompts.jsx`

```jsx
import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Chip, 
  Card, 
  CardContent,
  Collapse,
  IconButton
} from '@mui/material';
import { Link } from 'react-router-dom';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

/**
 * ContextualQueryPrompts Component
 * 
 * Displays contextual Query Builder links based on the current page context.
 * 
 * @param {Array} queries - Array of query objects from queryBuilderLinks.js
 * @param {string} title - Section title (optional)
 * @param {number} initialCount - Number of queries to show initially (default: 3)
 * @param {boolean} compact - Use compact styling for inline placement
 */
const ContextualQueryPrompts = ({ 
  queries = [], 
  title = "🔍 Explore in Query Builder",
  initialCount = 3,
  compact = false 
}) => {
  const [expanded, setExpanded] = useState(false);
  
  if (!queries || queries.length === 0) {
    return null;
  }
  
  // Sort by priority and slice
  const sortedQueries = [...queries].sort((a, b) => a.priority - b.priority);
  const visibleQueries = expanded ? sortedQueries : sortedQueries.slice(0, initialCount);
  const hasMore = sortedQueries.length > initialCount;
  
  if (compact) {
    // Compact inline version for embedding in stat cards
    return (
      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
          <SearchIcon sx={{ fontSize: 14 }} />
          Dig Deeper
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {visibleQueries.map((query, index) => (
            <Chip
              key={index}
              label={query.question}
              component={Link}
              to={query.url}
              clickable
              size="small"
              variant="outlined"
              color="primary"
              sx={{ 
                fontSize: '0.7rem',
                '&:hover': { 
                  backgroundColor: 'primary.light',
                  color: 'white'
                }
              }}
            />
          ))}
        </Box>
      </Box>
    );
  }
  
  // Full card version
  return (
    <Card sx={{ mt: 3, mb: 3, backgroundColor: 'grey.50' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrendingUpIcon color="primary" />
            {title}
          </Typography>
          {hasMore && (
            <IconButton size="small" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          )}
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Click any question below to see the data in Query Builder:
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {visibleQueries.map((query, index) => (
            <Box
              key={index}
              component={Link}
              to={query.url}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1.5,
                borderRadius: 1,
                backgroundColor: 'white',
                textDecoration: 'none',
                color: 'inherit',
                border: '1px solid',
                borderColor: 'grey.200',
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: 'primary.main',
                  backgroundColor: 'primary.50',
                  transform: 'translateX(4px)',
                }
              }}
            >
              <SearchIcon color="primary" sx={{ fontSize: 20 }} />
              <Typography variant="body2" sx={{ flex: 1, fontWeight: 500 }}>
                {query.question}
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                {query.tags.slice(0, 2).map((tag, tagIndex) => (
                  <Chip
                    key={tagIndex}
                    label={tag}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.65rem', height: 20 }}
                  />
                ))}
              </Box>
            </Box>
          ))}
        </Box>
        
        {hasMore && (
          <Collapse in={!expanded}>
            <Button
              fullWidth
              variant="text"
              onClick={() => setExpanded(true)}
              sx={{ mt: 1 }}
            >
              Show {sortedQueries.length - initialCount} more queries
            </Button>
          </Collapse>
        )}
      </CardContent>
    </Card>
  );
};

export default ContextualQueryPrompts;
```

---

## 5. Implementation Guide

### 5.1 Step 1: Create the Utility File

1. Create `src/utils/queryBuilderLinks.js` with the code from Section 2.1
2. Test the URL generation manually in browser console

### 5.2 Step 2: Create the UI Component

1. Create `src/components/ContextualQueryPrompts.jsx` with the code from Section 4.1
2. Import and test with hardcoded data first

### 5.3 Step 3: Integrate into PlayerProfile.jsx

**Location in file**: After the `CareerStatsCards` component (around line 180)

```jsx
// Add import at top of file
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getBatterContextualQueries } from '../utils/queryBuilderLinks';

// Inside the component, after stats are loaded, generate queries:
const contextualQueries = stats ? getBatterContextualQueries(selectedPlayer, {
  startDate: dateRange.start,
  endDate: dateRange.end,
  leagues: competitionFilters.leagues,
  venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
}) : [];

// In the render, after CareerStatsCards:
{stats && !loading && (
  <Box sx={{ mt: 4 }}>
    <CareerStatsCards stats={stats} />
    
    {/* ADD THIS */}
    <ContextualQueryPrompts 
      queries={contextualQueries}
      title={`🔍 Explore ${selectedPlayer}'s Data`}
    />
    
    <Box sx={{ mt: 3 }}>
      <ContributionGraph ... />
    </Box>
    ...
  </Box>
)}
```

### 5.4 Step 4: Integrate into BowlerProfile.jsx

**Location**: After `BowlingCareerStatsCards` component

```jsx
// Add import at top
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getBowlerContextualQueries } from '../utils/queryBuilderLinks';

// Generate queries when stats load
const contextualQueries = stats ? getBowlerContextualQueries(selectedPlayer, {
  startDate: dateRange.start,
  endDate: dateRange.end,
  leagues: competitionFilters.leagues,
  venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
}) : [];

// In render, after BowlingCareerStatsCards:
{stats && !loading && (
  <Box sx={{ mt: 4 }}>
    <BowlingCareerStatsCards stats={stats} />
    
    {/* ADD THIS */}
    <ContextualQueryPrompts 
      queries={contextualQueries}
      title={`🔍 Explore ${selectedPlayer}'s Bowling Data`}
    />
    
    <Box sx={{ mt: 4, display: 'grid', ... }}>
      ...
    </Box>
  </Box>
)}
```

### 5.5 Step 5: Integrate into VenueNotes.jsx (Venue Analysis)

This requires passing venue context. Add after the venue stats summary section.

```jsx
// Add import
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getVenueContextualQueries } from '../utils/queryBuilderLinks';

// Generate queries (venue and team info come from props)
const contextualQueries = getVenueContextualQueries(venue, {
  startDate,
  endDate,
  leagues: [], // Pass from competition filter if available
  team1: selectedTeam1,
  team2: selectedTeam2,
});

// Add to render (after venue overview, before detailed sections)
<ContextualQueryPrompts 
  queries={contextualQueries}
  title={`🔍 Explore ${venue.split(',')[0]} Data`}
/>
```

### 5.6 Step 6: Integrate into MatchupsTab.jsx

```jsx
// Add import
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getMatchupContextualQueries } from '../utils/queryBuilderLinks';

// Generate when both teams are selected
const contextualQueries = (selectedTeam1 && selectedTeam2) 
  ? getMatchupContextualQueries(selectedTeam1, selectedTeam2, {
      startDate: dateRange.start,
      endDate: dateRange.end,
      leagues: competitionFilters.leagues,
    })
  : [];

// Add to render after matchup summary
{contextualQueries.length > 0 && (
  <ContextualQueryPrompts 
    queries={contextualQueries}
    title="🔍 Deep Dive into This Matchup"
  />
)}
```

---

## 6. File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/utils/queryBuilderLinks.js` | **CREATE** | URL generator utility |
| `src/components/ContextualQueryPrompts.jsx` | **CREATE** | UI component |
| `src/components/PlayerProfile.jsx` | **MODIFY** | Add imports + component |
| `src/components/BowlerProfile.jsx` | **MODIFY** | Add imports + component |
| `src/components/VenueNotes.jsx` | **MODIFY** | Add imports + component |
| `src/components/MatchupsTab.jsx` | **MODIFY** | Add imports + component |

---

## 7. Testing Checklist

### 7.1 Unit Tests for URL Generation

```javascript
// Test in browser console or Jest
import { getBatterContextualQueries, buildQueryUrl } from './utils/queryBuilderLinks';

// Test 1: Basic URL generation
const url = buildQueryUrl({ batters: ['V Kohli'], min_balls: 10 }, ['phase']);
console.assert(url.includes('batters=V+Kohli') || url.includes('batters=V%20Kohli'));
console.assert(url.includes('group_by=phase'));

// Test 2: Batter queries generation
const queries = getBatterContextualQueries('V Kohli', { 
  startDate: '2023-01-01', 
  leagues: ['IPL'] 
});
console.assert(queries.length >= 5);
console.assert(queries[0].url.startsWith('/query?'));
console.assert(queries[0].question.includes('Kohli'));
```

### 7.2 Integration Testing

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| Batter link works | 1. Go to V Kohli profile<br>2. Click first query link | Query Builder opens with Kohli filtered, results shown |
| Bowler link works | 1. Go to JJ Bumrah profile<br>2. Click first query link | Query Builder opens with Bumrah filtered |
| Venue link works | 1. Go to Venue Analysis for Wankhede<br>2. Click a query link | Query Builder opens with venue filtered |
| Context preserved | 1. Set date range to 2024<br>2. Click query link | Query Builder shows 2024 filter |
| Tags display | View any query prompt | Tags show correctly, max 2 visible |
| Expand/collapse | Click "Show more" | Hidden queries appear |

### 7.3 Visual QA

- [ ] Component blends with existing page design
- [ ] Hover states work on query links
- [ ] Mobile responsive (links wrap properly)
- [ ] Links are clearly clickable (cursor, hover effect)
- [ ] Tags are readable (proper font size)

---

## 8. Future Enhancements

Once the basic system is working, consider:

1. **Analytics tracking**: Track which queries get clicked most
2. **Personalized queries**: Show different queries based on user history
3. **Dynamic queries**: Generate queries based on interesting patterns in the current data (e.g., "Kohli averages 60+ vs left-arm spin - explore more")
4. **Query of the day**: Rotate featured queries on landing page

---

## Appendix A: Bowler Type Codes Reference

| Code | Meaning |
|------|---------|
| RF | Right-arm Fast |
| RFM | Right-arm Fast-Medium |
| RM | Right-arm Medium |
| RO | Right-arm Off-spin |
| RL | Right-arm Leg-spin |
| LF | Left-arm Fast |
| LFM | Left-arm Fast-Medium |
| LM | Left-arm Medium |
| LO | Left-arm Orthodox (spin) |
| LC | Left-arm Chinaman |

## Appendix B: Ball Direction Codes

| Code | Meaning |
|------|---------|
| down the ground | Straight down the wicket |
| cover | Through cover region |
| point | Through point region |
| third man | Behind square on off side |
| fine leg | Behind square on leg side |
| midwicket | Through midwicket |
| square leg | Square on leg side |
| long on | Straight on leg side |
| long off | Straight on off side |

---

**Document Version**: 1.0  
**Created**: December 2024  
**Author**: Implementation Spec for Hindsight Cricket Analytics
