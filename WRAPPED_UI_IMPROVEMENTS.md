# Wrapped 2025 UI Improvements - Implementation Plan

> **CRITICAL**: All file changes MUST be made in `/Users/adityabalaji/cdt/cricket-data-thing/` directory. Do NOT modify files in any other directory.

## Overview

This document outlines the UI improvements needed for the Wrapped 2025 feature. Each section contains detailed, step-by-step instructions for implementation.

---

## Table of Contents

1. [Header Layout Redesign](#1-header-layout-redesign)
2. [Mobile Safari Fullscreen Fix](#2-mobile-safari-fullscreen-fix)
3. [Title Overflow Prevention](#3-title-overflow-prevention)
4. [Share Button PNG Export](#4-share-button-png-export)
5. [External Links Handling](#5-external-links-handling)
6. [Intro Card Enhancements](#6-intro-card-enhancements)
7. [Player Team Affiliations](#7-player-team-affiliations)
8. [Pace vs Spin Card Fixes](#8-pace-vs-spin-card-fixes)

---

## 1. Header Layout Redesign

### Current State
- Too much padding at top
- "1/9" counter displayed (unnecessary)
- Close button not positioned correctly

### Target State (Instagram Stories style)
```
┌─────────────────────────────────────────┐
│ [progress bars across full width]       │
│ 🔷 hindsight wrapped 2025    ⋮   ✕     │
│                                         │
│         [Card Content]                  │
└─────────────────────────────────────────┘
```

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/WrappedViewer.jsx`

### Step-by-Step Instructions

#### Step 1.1: Update the header structure
Find the header section in `WrappedViewer.jsx`. Look for elements containing:
- The close button (`×` or `X`)
- The card counter (e.g., "1 / 9")
- Progress bars

Replace the header layout with this structure:
```jsx
{/* Progress bars - full width at very top */}
<div className="w-full px-2 pt-2">
  <div className="flex gap-1">
    {cards.map((_, index) => (
      <div
        key={index}
        className={`h-0.5 flex-1 rounded-full ${
          index < currentCardIndex ? 'bg-green-500' :
          index === currentCardIndex ? 'bg-green-500' : 'bg-gray-600'
        }`}
      />
    ))}
  </div>
</div>

{/* Header row with logo, menu, and close button */}
<div className="flex items-center justify-between px-4 py-2">
  {/* Left side: Logo + Title */}
  <div className="flex items-center gap-2">
    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
      <span className="text-white text-xs font-bold">H</span>
    </div>
    <span className="text-white text-sm font-medium">hindsight wrapped 2025</span>
  </div>
  
  {/* Right side: Menu + Close */}
  <div className="flex items-center gap-3">
    {/* Three-dot menu for filters */}
    <button 
      onClick={() => setShowFilterMenu(true)}
      className="text-white p-1"
    >
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <circle cx="12" cy="5" r="2"/>
        <circle cx="12" cy="12" r="2"/>
        <circle cx="12" cy="19" r="2"/>
      </svg>
    </button>
    
    {/* Close button */}
    <button 
      onClick={onClose}
      className="text-white p-1"
    >
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</div>
```

#### Step 1.2: Remove the card counter
Search for any element displaying `{currentCardIndex + 1} / {cards.length}` or similar. DELETE this element entirely.

#### Step 1.3: Add filter menu state
Add these state variables at the top of the component:
```jsx
const [showFilterMenu, setShowFilterMenu] = useState(false);
```

#### Step 1.4: Create FilterMenu component
Create a new file: `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/FilterMenu.jsx`

```jsx
import React from 'react';

const FilterMenu = ({ 
  isOpen, 
  onClose, 
  leagues, 
  selectedLeagues, 
  onLeagueChange,
  includeInternational,
  onInternationalChange 
}) => {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-end justify-center">
      <div className="bg-gray-900 w-full max-w-md rounded-t-2xl p-4 max-h-[70vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-white font-semibold">Filters</h3>
          <button onClick={onClose} className="text-gray-400">Done</button>
        </div>
        
        {/* International toggle */}
        <div className="flex justify-between items-center py-3 border-b border-gray-700">
          <span className="text-white">Include International</span>
          <input 
            type="checkbox" 
            checked={includeInternational}
            onChange={(e) => onInternationalChange(e.target.checked)}
            className="w-5 h-5"
          />
        </div>
        
        {/* League selection */}
        <div className="mt-4">
          <h4 className="text-gray-400 text-sm mb-2">Leagues</h4>
          {leagues.map(league => (
            <div key={league} className="flex justify-between items-center py-2">
              <span className="text-white text-sm">{league}</span>
              <input 
                type="checkbox"
                checked={selectedLeagues.includes(league)}
                onChange={() => onLeagueChange(league)}
                className="w-4 h-4"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FilterMenu;
```

#### Step 1.5: Reduce top padding
Find the main container div and reduce/remove top padding. Look for classes like `pt-8`, `pt-12`, `py-8` etc. Change to `pt-0` or remove entirely.

---

## 2. Mobile Safari Fullscreen Fix

### Current State
Safari's tab bar persists at bottom, taking up screen space.

### Target State
Attempt to hide Safari UI for more immersive experience.

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/WrappedViewer.jsx`
- `/Users/adityabalaji/cdt/cricket-data-thing/public/index.html` (if exists, or App.jsx)

### Step-by-Step Instructions

#### Step 2.1: Add viewport meta tag
In the HTML head (or via React Helmet), ensure this meta tag exists:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
```

#### Step 2.2: Use safe-area-inset CSS
Update the main container in `WrappedViewer.jsx`:
```jsx
<div className="fixed inset-0 bg-black z-50" 
     style={{ 
       paddingBottom: 'env(safe-area-inset-bottom)',
       paddingTop: 'env(safe-area-inset-top)'
     }}>
```

#### Step 2.3: Add full height styles
Add to the main container:
```jsx
className="fixed inset-0 bg-black z-50 min-h-screen min-h-[100dvh]"
```

The `100dvh` (dynamic viewport height) accounts for Safari's collapsing UI.

---

## 3. Title Overflow Prevention

### Current State
Long titles like "Middle-Overs Merchants" wrap to two lines on mobile.

### Target State
All titles fit on single line by using shorter, more concise titles.

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/services/wrapped.py` (backend - update titles)
- `/Users/adityabalaji/cdt/cricket-data-thing/routers/wrapped.py` (metadata endpoint)

### Step-by-Step Instructions

#### Step 3.1: Update card titles in backend service
In `/Users/adityabalaji/cdt/cricket-data-thing/services/wrapped.py`, update the `card_title` values in each card method's return statement:

| Current Title | New Concise Title |
|---------------|-------------------|
| `2025 in One Breath` | `2025 in One Breath` (keep) |
| `Powerplay Bullies of 2025` | `Powerplay Bullies` |
| `Middle-Overs Merchants` | `Middle Merchants` |
| `Death is a Personality Trait` | `Death Hitters` |
| `Pace vs Spin: 2025's Split Brain` | `Pace vs Spin` |
| `Powerplay Wicket Thieves` | `PP Wicket Thieves` |
| `The 19th Over Gods` | `Death Over Gods` |
| `Teams That Became Different People` | `ELO Movers` |
| `Venues Had Vibes` | `Venue Vibes` |

#### Step 3.2: Update metadata endpoint
In `/Users/adityabalaji/cdt/cricket-data-thing/routers/wrapped.py`, find the `get_wrapped_metadata()` function and update the `cards` array with matching concise titles.

#### Step 3.3: Move creative titles to subtitles
The longer, creative titles can become subtitles instead:

```python
# Example for Death Hitters card:
return {
    "card_id": "death_hitters",
    "card_title": "Death Hitters",  # Short, fits on one line
    "card_subtitle": "Death is a Personality Trait",  # Creative tagline as subtitle
    ...
}
```

#### Step 3.4: Full title mapping
Update each card method in `services/wrapped.py`:

```python
# Card 2: Powerplay Bullies
"card_title": "Powerplay Bullies",
"card_subtitle": "Who dominated the first 6 overs",

# Card 3: Middle Merchants  
"card_title": "Middle Merchants",
"card_subtitle": "Masters of overs 7-15",

# Card 4: Death Hitters
"card_title": "Death Hitters", 
"card_subtitle": "The finishers who lived dangerously",

# Card 5: Pace vs Spin
"card_title": "Pace vs Spin",
"card_subtitle": "2025's split brain bowling matchups",

# Card 6: PP Wicket Thieves
"card_title": "PP Wicket Thieves",
"card_subtitle": "Early breakthrough specialists",

# Card 7: Death Over Gods
"card_title": "Death Over Gods",
"card_subtitle": "Overs 16-20 bowling excellence",

# Card 8: ELO Movers
"card_title": "ELO Movers",
"card_subtitle": "Teams that became different people",

# Card 9: Venue Vibes
"card_title": "Venue Vibes",
"card_subtitle": "Par scores and chase bias",
```

---

## 4. Share Button PNG Export

### Current State
Share button copies/shares a link.

### Target State
Share button exports the card as a PNG/JPG image.

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/WrappedViewer.jsx`
- Create: `/Users/adityabalaji/cdt/cricket-data-thing/src/utils/shareUtils.js`

### Step-by-Step Instructions

#### Step 4.1: Install html2canvas
Run in terminal:
```bash
cd /Users/adityabalaji/cdt/cricket-data-thing
npm install html2canvas
```

#### Step 4.2: Create share utility
Create `/Users/adityabalaji/cdt/cricket-data-thing/src/utils/shareUtils.js`:
```jsx
import html2canvas from 'html2canvas';

export const captureCardAsImage = async (elementRef) => {
  if (!elementRef.current) return null;
  
  try {
    const canvas = await html2canvas(elementRef.current, {
      backgroundColor: '#000000',
      scale: 2, // Higher quality
      useCORS: true,
      logging: false
    });
    
    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Error capturing card:', error);
    return null;
  }
};

export const downloadImage = (dataUrl, filename) => {
  const link = document.createElement('a');
  link.download = filename;
  link.href = dataUrl;
  link.click();
};

export const shareImage = async (dataUrl, title) => {
  // Convert data URL to blob
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  const file = new File([blob], 'wrapped-card.png', { type: 'image/png' });
  
  if (navigator.share && navigator.canShare({ files: [file] })) {
    // Native share (mobile)
    await navigator.share({
      files: [file],
      title: title,
      text: 'Check out my Hindsight Wrapped 2025!'
    });
  } else {
    // Fallback: download
    downloadImage(dataUrl, `hindsight-wrapped-${Date.now()}.png`);
  }
};
```

#### Step 4.3: Add ref to card container
In `WrappedViewer.jsx`, add a ref:
```jsx
const cardRef = useRef(null);

// Wrap the card content
<div ref={cardRef}>
  {/* Current card component */}
</div>
```

#### Step 4.4: Update share button handler
```jsx
import { captureCardAsImage, shareImage } from '../../utils/shareUtils';

const handleShare = async () => {
  const imageData = await captureCardAsImage(cardRef);
  if (imageData) {
    await shareImage(imageData, `Hindsight Wrapped 2025 - ${currentCard.card_title}`);
  }
};
```

---

## 5. External Links Handling

### Current State
Links open in the same tab, navigating away from Wrapped.

### Target State
Links open in new tab OR show confirmation dialog.

### Files to Modify
- All card components with deep links in `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/`

### Step-by-Step Instructions

#### Step 5.1: Find all link elements
Search for `<a href` or `<Link to` in all card components.

#### Step 5.2: Add target="_blank" and visual indicator
Update links to:
```jsx
<a 
  href={deepLink}
  target="_blank"
  rel="noopener noreferrer"
  className="inline-flex items-center gap-1 text-green-400 hover:text-green-300"
>
  View in Query Builder
  {/* External link icon */}
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
</a>
```

#### Step 5.3: Update the "Recreate Query" button
Find the Recreate Query button and update:
```jsx
<a
  href={cardData.deep_links?.query_builder}
  target="_blank"
  rel="noopener noreferrer"
  className="inline-flex items-center gap-2 px-4 py-2 bg-transparent border border-green-500 text-green-500 rounded-full hover:bg-green-500/10"
>
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
  Recreate Query
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
</a>
```

---

## 6. Intro Card Enhancements

### Current State
- Full-width bar chart for run rates (excessive)
- Missing toss win % data

### Target State
- Compact visualization
- Add batting first vs batting second win %

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/IntroCard.jsx`
- `/Users/adityabalaji/cdt/cricket-data-thing/services/wrapped.py` (backend)

### Step-by-Step Instructions

#### Step 6.1: Update backend to include toss data
In `/Users/adityabalaji/cdt/cricket-data-thing/services/wrapped.py`, find `get_intro_card_data` method.

Add this query AFTER the existing queries:
```python
# Get toss/win statistics
toss_query = text(f"""
    SELECT 
        SUM(CASE WHEN m.won_batting_first = true THEN 1 ELSE 0 END) as bat_first_wins,
        SUM(CASE WHEN m.won_fielding_first = true THEN 1 ELSE 0 END) as chase_wins,
        COUNT(*) as total_decided
    FROM matches m
    WHERE m.date >= :start_date
    AND m.date <= :end_date
    AND (m.won_batting_first = true OR m.won_fielding_first = true)
    {competition_filter}
""")

toss_result = db.execute(toss_query, params).fetchone()
```

Update the return dict to include:
```python
return {
    "card_id": "intro",
    "card_title": "2025 in One Breath",
    "card_subtitle": "The rhythm of T20 cricket",
    "total_matches": matches_result.total_matches if matches_result else 0,
    "toss_stats": {
        "bat_first_wins": toss_result.bat_first_wins if toss_result else 0,
        "chase_wins": toss_result.chase_wins if toss_result else 0,
        "bat_first_pct": round(
            (toss_result.bat_first_wins * 100.0 / toss_result.total_decided), 1
        ) if toss_result and toss_result.total_decided > 0 else 50
    },
    "phases": [...],
    ...
}
```

#### Step 6.2: Redesign IntroCard component
In `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/IntroCard.jsx`:

```jsx
const IntroCard = ({ data }) => {
  const { total_matches, phases, toss_stats } = data;
  
  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      {/* Title */}
      <h1 className="text-2xl font-bold text-white mb-1">{data.card_title}</h1>
      <p className="text-gray-400 text-sm mb-6">{data.card_subtitle}</p>
      
      {/* Match count - hero number */}
      <div className="text-center mb-8">
        <span className="text-6xl font-bold text-green-500">{total_matches}</span>
        <p className="text-gray-400 mt-1">T20 matches analyzed</p>
      </div>
      
      {/* Toss/Win Stats - NEW */}
      <div className="w-full max-w-xs mb-8">
        <div className="flex justify-between items-center mb-2">
          <span className="text-gray-400 text-sm">Bat First Wins</span>
          <span className="text-gray-400 text-sm">Chase Wins</span>
        </div>
        <div className="h-3 bg-gray-700 rounded-full overflow-hidden flex">
          <div 
            className="bg-green-500 h-full"
            style={{ width: `${toss_stats?.bat_first_pct || 50}%` }}
          />
          <div 
            className="bg-blue-500 h-full"
            style={{ width: `${100 - (toss_stats?.bat_first_pct || 50)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-green-500 text-sm font-medium">
            {toss_stats?.bat_first_pct || 50}%
          </span>
          <span className="text-blue-500 text-sm font-medium">
            {(100 - (toss_stats?.bat_first_pct || 50)).toFixed(1)}%
          </span>
        </div>
      </div>
      
      {/* Phase Run Rates - Compact horizontal display */}
      <div className="flex justify-center gap-6 w-full">
        {phases?.map((phase) => (
          <div key={phase.phase} className="text-center">
            <span className={`text-2xl font-bold ${
              phase.phase === 'powerplay' ? 'text-green-500' :
              phase.phase === 'middle' ? 'text-blue-500' : 'text-red-500'
            }`}>
              {phase.run_rate}
            </span>
            <p className="text-gray-400 text-xs uppercase mt-1">
              {phase.phase === 'powerplay' ? 'PP RR' :
               phase.phase === 'middle' ? 'MID RR' : 'DEATH RR'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 7. Player Team Affiliations

### Current State
Players displayed without team context.

### Target State
Show abbreviated team name for each player.

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/services/wrapped.py` (backend)
- Card components in `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/`

### Step-by-Step Instructions

#### Step 7.1: Update backend queries
For EACH card method that returns player data, modify the SQL query to include the player's most recent team.

Example for `get_powerplay_bullies_data`:
```python
query = text(f"""
    WITH powerplay_stats AS (
        SELECT 
            bs.striker as player,
            bs.batting_team as team,  -- Add team
            SUM(bs.pp_balls) as balls,
            ...
        FROM batting_stats bs
        JOIN matches m ON bs.match_id = m.id
        WHERE ...
        GROUP BY bs.striker, bs.batting_team  -- Group by team too
        ...
    ),
    -- Get most recent team per player
    player_teams AS (
        SELECT DISTINCT ON (player) 
            player, 
            team
        FROM powerplay_stats
        ORDER BY player, balls DESC  -- Use the team where they played most
    )
    SELECT 
        ps.player,
        pt.team,
        SUM(ps.balls) as balls,
        ...
    FROM powerplay_stats ps
    JOIN player_teams pt ON ps.player = pt.player
    GROUP BY ps.player, pt.team
    ORDER BY strike_rate DESC
    LIMIT 20
""")
```

#### Step 7.2: Add team abbreviation mapping
Create `/Users/adityabalaji/cdt/cricket-data-thing/src/utils/teamAbbreviations.js`:
```javascript
export const TEAM_ABBREVIATIONS = {
  'Mumbai Indians': 'MI',
  'Chennai Super Kings': 'CSK',
  'Royal Challengers Bangalore': 'RCB',
  'Royal Challengers Bengaluru': 'RCB',
  'Kolkata Knight Riders': 'KKR',
  'Delhi Capitals': 'DC',
  'Punjab Kings': 'PBKS',
  'Rajasthan Royals': 'RR',
  'Sunrisers Hyderabad': 'SRH',
  'Gujarat Titans': 'GT',
  'Lucknow Super Giants': 'LSG',
  'India': 'IND',
  'Australia': 'AUS',
  'England': 'ENG',
  'Pakistan': 'PAK',
  'South Africa': 'SA',
  'New Zealand': 'NZ',
  'West Indies': 'WI',
  'Sri Lanka': 'SL',
  'Bangladesh': 'BAN',
  'Afghanistan': 'AFG',
  // Add more as needed
};

export const getTeamAbbr = (teamName) => {
  return TEAM_ABBREVIATIONS[teamName] || teamName?.substring(0, 3).toUpperCase() || '???';
};
```

#### Step 7.3: Update card components to display team
Example for player list items:
```jsx
import { getTeamAbbr } from '../../../utils/teamAbbreviations';

// In the player row:
<div className="flex items-center gap-2">
  <span className="text-white font-medium">{player.name}</span>
  <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
    {getTeamAbbr(player.team)}
  </span>
</div>
```

---

## 8. Pace vs Spin Card Fixes

### Current State
- Pace Crushers / Spin Crushers labels may be swapped
- Wasted space on left of chart
- Player names overflow to two lines

### Target State
- Correct label positioning
- Full-width chart
- Single-line player names

### Files to Modify
- `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/PaceVsSpinCard.jsx`

### Step-by-Step Instructions

#### Step 8.1: Fix label positions
The labels should be:
- **Left side (negative values)**: "Spin Crushers" (players who are BETTER vs spin, hence negative SR delta)
- **Right side (positive values)**: "Pace Crushers" (players who are BETTER vs pace, hence positive SR delta)

Update the header:
```jsx
<div className="flex justify-between items-center mb-4 px-4">
  {/* Left = Spin Crushers (negative delta = better vs spin) */}
  <div className="flex items-center gap-1">
    <span className="text-xl">🌀</span>
    <span className="text-cyan-400 text-sm font-medium">Spin Crushers</span>
  </div>
  
  {/* Right = Pace Crushers (positive delta = better vs pace) */}
  <div className="flex items-center gap-1">
    <span className="text-orange-400 text-sm font-medium">Pace Crushers</span>
    <span className="text-xl">🔥</span>
  </div>
</div>
```

#### Step 8.2: Maximize chart width
Update the chart container:
```jsx
<div className="w-full px-2">  {/* Minimal horizontal padding */}
  {/* Chart content */}
</div>
```

#### Step 8.3: Fix player name overflow
For the bar labels (player names), use:
```jsx
<text
  className="text-xs fill-gray-300 truncate"
  style={{ 
    textOverflow: 'ellipsis',
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    maxWidth: '80px'  // Limit width
  }}
>
  {/* Use abbreviated name if too long */}
  {player.name.length > 12 
    ? player.name.split(' ').map(n => n[0]).join('. ') + '.'
    : player.name
  }
</text>
```

#### Step 8.4: Compact the Y-axis labels
Create a name shortener function:
```jsx
const shortenName = (name) => {
  if (name.length <= 10) return name;
  const parts = name.split(' ');
  if (parts.length >= 2) {
    // "Faheem Ashraf" -> "F Ashraf"
    return parts[0][0] + ' ' + parts[parts.length - 1];
  }
  return name.substring(0, 10) + '...';
};
```

#### Step 8.5: Reduce left margin for bar chart
If using Recharts, update the layout:
```jsx
<BarChart
  layout="vertical"
  data={chartData}
  margin={{ top: 5, right: 20, left: 60, bottom: 5 }}  // Reduce left from ~100 to 60
>
  <YAxis 
    type="category" 
    dataKey="name" 
    width={55}  // Fixed narrow width
    tick={{ fontSize: 10 }}  // Smaller font
    tickFormatter={shortenName}
  />
  ...
</BarChart>
```

---

## Testing Checklist

After implementing each section, verify:

- [ ] Header shows logo, title, menu button, and close button correctly
- [ ] No "1/9" counter visible
- [ ] Progress bars span full width
- [ ] On iPhone Safari, bottom tab bar doesn't overlap content
- [ ] All card titles fit on single line
- [ ] Share button downloads/shares an image
- [ ] External links open in new tab with visual indicator
- [ ] Intro card shows toss win percentages
- [ ] All player rows show team abbreviation
- [ ] Pace vs Spin card labels are correctly positioned
- [ ] Player names don't wrap in charts
- [ ] Chart uses full available width

---

## File Summary

### Files to CREATE:
1. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/FilterMenu.jsx`
2. `/Users/adityabalaji/cdt/cricket-data-thing/src/utils/shareUtils.js`
3. `/Users/adityabalaji/cdt/cricket-data-thing/src/utils/teamAbbreviations.js`

### Files to MODIFY:
1. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/WrappedViewer.jsx`
2. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/IntroCard.jsx`
3. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/PaceVsSpinCard.jsx`
4. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/PowerplayBulliesCard.jsx`
5. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/MiddleMerchantsCard.jsx`
6. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/DeathHittersCard.jsx`
7. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/PowerplayThievesCard.jsx`
8. `/Users/adityabalaji/cdt/cricket-data-thing/src/components/wrapped/cards/NineteenthOverGodsCard.jsx`
9. `/Users/adityabalaji/cdt/cricket-data-thing/services/wrapped.py`

### NPM Package to Install:
```bash
cd /Users/adityabalaji/cdt/cricket-data-thing && npm install html2canvas
```

---

## Priority Order

Implement in this order for best development flow:

1. **Header Layout** (visual impact, foundational)
2. **Title Overflow** (quick fix, improves all cards)
3. **Intro Card Toss Stats** (backend + frontend)
4. **External Links** (quick fix, UX improvement)
5. **Pace vs Spin Fixes** (layout improvements)
6. **Player Team Affiliations** (backend + frontend)
7. **Share PNG Export** (optional enhancement)
8. **Mobile Safari Fix** (tricky, may need testing)
