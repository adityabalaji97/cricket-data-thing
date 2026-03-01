/**
 * Query Builder Link Generator
 *
 * This utility creates pre-filled Query Builder URLs for contextual prompts.
 * Each function returns an array of objects with:
 *   - question: Human-readable question to display
 *   - url: The Query Builder URL with pre-filled parameters
 *   - tags: Category tags for filtering/styling
 *   - priority: Display order (lower = higher priority)
 */

import { filtersToUrlParams } from './urlParamParser';

// Base URL for Query Builder
const QUERY_BUILDER_PATH = '/query';

/**
 * Builds a Query Builder URL from filters and groupBy arrays
 * Reuses the existing filtersToUrlParams logic
 *
 * @param {Object} filters - Filter object (batters, bowlers, dates, etc.)
 * @param {Array} groupBy - Array of columns to group by
 * @returns {string} Complete URL path with query parameters
 */
export const buildQueryUrl = (filters, groupBy = []) => {
  const queryString = filtersToUrlParams(filters, groupBy);
  return `${QUERY_BUILDER_PATH}?${queryString}`;
};

/**
 * Helper to extract short name from full player name
 * "V Kohli" -> "Kohli"
 * "JJ Bumrah" -> "Bumrah"
 */
const getShortName = (fullName) => {
  if (!fullName) return '';
  return fullName.split(' ').pop();
};

/**
 * Helper to extract short venue name
 * "M Chinnaswamy Stadium, Bengaluru" -> "M Chinnaswamy Stadium"
 */
const getShortVenue = (venueName) => {
  if (!venueName) return '';
  return venueName.split(',')[0];
};

/**
 * Generate contextual queries for a BATTER profile
 *
 * @param {string} playerName - The batter's name (e.g., "V Kohli")
 * @param {Object} context - Additional context from the page
 * @param {string} context.startDate - Start date filter
 * @param {string} context.endDate - End date filter
 * @param {Array} context.leagues - Selected leagues
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

  const shortName = getShortName(playerName);

  const queries = [
    // Query 1: Performance vs Spin by Phase
    {
      question: `How does ${shortName} perform against spin in each phase?`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          bowl_kind: ['spin bowler'],
          min_balls: 10,
        },
        ['phase']
      ),
      tags: ['spin', 'phase', 'matchup'],
      priority: 1,
    },

    // Query 2: Performance vs Pace by Phase
    {
      question: `How does ${shortName} handle pace bowling by phase?`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          bowl_kind: ['pace bowler'],
          min_balls: 10,
        },
        ['phase']
      ),
      tags: ['pace', 'phase', 'matchup'],
      priority: 2,
    },

    // Query 3: Performance by Ball Direction
    {
      question: `Where does ${shortName} score most runs? (ball direction)`,
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
      question: `${shortName}'s death overs: spin vs pace`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 16,
          over_max: 19,
          min_balls: 10,
        },
        ['bowl_kind']
      ),
      tags: ['death', 'phase', 'finishing'],
      priority: 4,
    },

    // Query 5: Powerplay Performance
    {
      question: `${shortName} in powerplay: spin vs pace`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 0,
          over_max: 5,
          min_balls: 10,
        },
        ['bowl_kind']
      ),
      tags: ['powerplay', 'phase'],
      priority: 5,
    },

    // Query 6: Year-over-Year Trend
    {
      question: `${shortName}'s performance trend by year`,
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
 * @param {Object} context - Additional context
 * @param {string} context.startDate - Start date filter
 * @param {string} context.endDate - End date filter
 * @param {Array} context.leagues - Selected leagues
 * @param {Object} context.team1 - Team 1 object (optional)
 * @param {Object} context.team2 - Team 2 object (optional)
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

  const shortVenue = getShortVenue(venueName);

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
        ['bowl_kind']
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
      question: `Death overs at ${shortVenue}: spin vs pace`,
      url: buildQueryUrl(
        {
          ...baseFilters,
          over_min: 16,
          over_max: 19,
          min_balls: 50,
        },
        ['bowl_kind']
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
 *
 * @param {Object|string} team1 - Team 1 object or name
 * @param {Object|string} team2 - Team 2 object or name
 * @param {Object} context - Additional context
 * @param {string} context.startDate - Start date filter
 * @param {string} context.endDate - End date filter
 * @param {Array} context.leagues - Selected leagues
 * @returns {Array} Array of query objects
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
        ['batter', 'bowl_kind']
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
        ['batter', 'bowl_kind']
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

/**
 * Generate contextual queries for a BOWLER profile
 *
 * @param {string} playerName - The bowler's name
 * @param {Object} context - Additional context
 * @param {string} context.startDate - Start date filter
 * @param {string} context.endDate - End date filter
 * @param {Array} context.leagues - Selected leagues
 * @param {string} context.venue - Selected venue (optional)
 * @returns {Array} Array of query objects
 */
export const getBowlerContextualQueries = (playerName, context = {}) => {
  const { startDate, endDate, leagues = [], venue } = context;

  const baseFilters = {
    bowlers: [playerName],
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
    ...(leagues.length > 0 && { leagues }),
    ...(venue && venue !== 'All Venues' && { venue }),
  };

  const shortName = getShortName(playerName);

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
