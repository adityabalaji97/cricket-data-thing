import { useLocation } from 'react-router-dom';

// Utility function to parse URL parameters and convert them to filter object
export const parseUrlParams = (search) => {
  const params = new URLSearchParams(search);
  const filters = {};
  
  // Helper function to parse array parameters (multiple values with same key)
  const getArrayParam = (key) => {
    const values = params.getAll(key);
    return values.length > 0 ? values : [];
  };
  
  // Helper function to parse integer array parameters
  const getIntArrayParam = (key) => {
    const values = params.getAll(key);
    return values.length > 0 ? values.map(v => parseInt(v, 10)) : [];
  };
  
  // Helper function to parse single value parameters
  const getSingleParam = (key, defaultValue = null) => {
    const value = params.get(key);
    return value !== null ? value : defaultValue;
  };
  
  // Helper function to parse integer parameters
  const getIntParam = (key, defaultValue = null) => {
    const value = params.get(key);
    return value !== null ? parseInt(value, 10) : defaultValue;
  };
  
  // Helper function to parse boolean parameters
  const getBoolParam = (key, defaultValue = false) => {
    const value = params.get(key);
    return value !== null ? value === 'true' : defaultValue;
  };

  // Helper to parse optional boolean parameters (null when omitted)
  const getNullableBoolParam = (key) => {
    const value = params.get(key);
    if (value === null) return null;
    return value === 'true';
  };
  
  // Basic filters
  filters.venue = getSingleParam('venue');
  filters.start_date = getSingleParam('start_date');
  filters.end_date = getSingleParam('end_date');
  // Accept both 'leagues' and 'league' for backwards compatibility
  const leaguesPlural = getArrayParam('leagues');
  const leaguesSingular = getArrayParam('league');
  filters.leagues = [...leaguesPlural, ...leaguesSingular];
  filters.teams = getArrayParam('teams');
  filters.batting_teams = getArrayParam('batting_teams');
  filters.bowling_teams = getArrayParam('bowling_teams');
  filters.players = getArrayParam('players');
  filters.batters = getArrayParam('batters');
  filters.bowlers = getArrayParam('bowlers');
  
  // Match context filters
  filters.innings = getIntParam('innings');
  filters.over_min = getIntParam('over_min');
  filters.over_max = getIntParam('over_max');
  filters.match_outcome = getArrayParam('match_outcome');
  filters.is_chase = getNullableBoolParam('is_chase');
  filters.chase_outcome = getArrayParam('chase_outcome');
  filters.toss_decision = getArrayParam('toss_decision');
  filters.day_or_night = getSingleParam('day_or_night');
  filters.query_mode = getSingleParam('query_mode', 'delivery');
  
  // Batter filters
  filters.bat_hand = getSingleParam('bat_hand');
  
  // Bowler filters
  filters.bowl_style = getArrayParam('bowl_style');
  filters.bowl_kind = getArrayParam('bowl_kind');
  
  // Delivery detail filters (NEW)
  filters.line = getArrayParam('line');
  filters.length = getArrayParam('length');
  filters.shot = getArrayParam('shot');
  filters.control = getIntParam('control');
  filters.wagon_zone = getIntArrayParam('wagon_zone');
  filters.dismissal = getArrayParam('dismissal');
  
  // Grouped result filters
  filters.min_balls = getIntParam('min_balls');
  filters.max_balls = getIntParam('max_balls');
  filters.min_runs = getIntParam('min_runs');
  filters.max_runs = getIntParam('max_runs');
  filters.min_wickets = getIntParam('min_wickets');
  filters.max_wickets = getIntParam('max_wickets');
  
  // Pagination
  filters.limit = getIntParam('limit', 1000);
  filters.offset = getIntParam('offset', 0);
  
  // International matches
  filters.include_international = getBoolParam('include_international', false);
  filters.top_teams = getIntParam('top_teams', 10);
  
  // Summary rows
  filters.show_summary_rows = getBoolParam('show_summary_rows', false);
  
  return filters;
};

// Utility function to convert filters to URL parameters
export const filtersToUrlParams = (filters, groupBy = []) => {
  const params = new URLSearchParams();
  
  // Add filters
  Object.entries(filters).forEach(([key, value]) => {
    if (key === 'query_mode' && value === 'delivery') {
      return;
    }
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
  
  return params.toString();
};

// Hook to use URL parameters in QueryBuilder
export const useUrlParams = () => {
  const location = useLocation();
  
  const getFiltersFromUrl = () => {
    return parseUrlParams(location.search);
  };
  
  const getGroupByFromUrl = () => {
    const params = new URLSearchParams(location.search);
    return params.getAll('group_by');
  };
  
  return {
    getFiltersFromUrl,
    getGroupByFromUrl,
    currentParams: location.search
  };
};
