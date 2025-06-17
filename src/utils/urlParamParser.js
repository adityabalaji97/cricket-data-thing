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
  
  // Basic filters
  filters.venue = getSingleParam('venue');
  filters.start_date = getSingleParam('start_date');
  filters.end_date = getSingleParam('end_date');
  filters.leagues = getArrayParam('leagues');
  filters.teams = getArrayParam('teams');
  filters.batting_teams = getArrayParam('batting_teams');
  filters.bowling_teams = getArrayParam('bowling_teams');
  filters.players = getArrayParam('players');
  filters.batters = getArrayParam('batters');
  filters.bowlers = getArrayParam('bowlers');
  
  // Column-specific filters
  filters.crease_combo = getSingleParam('crease_combo');
  filters.ball_direction = getSingleParam('ball_direction');
  filters.bowler_type = getArrayParam('bowler_type');
  filters.striker_batter_type = getSingleParam('striker_batter_type');
  filters.non_striker_batter_type = getSingleParam('non_striker_batter_type');
  filters.innings = getIntParam('innings');
  filters.over_min = getIntParam('over_min');
  filters.over_max = getIntParam('over_max');
  filters.wicket_type = getSingleParam('wicket_type');
  
  // Grouped result filters
  filters.min_balls = getIntParam('min_balls');
  filters.max_balls = getIntParam('max_balls');
  filters.min_runs = getIntParam('min_runs');
  filters.max_runs = getIntParam('max_runs');
  
  // Pagination
  filters.limit = getIntParam('limit', 1000);
  filters.offset = getIntParam('offset', 0);
  
  // International matches
  filters.include_international = getBoolParam('include_international', false);
  filters.top_teams = getIntParam('top_teams', 10);
  
  return filters;
};

// Utility function to convert filters to URL parameters
export const filtersToUrlParams = (filters, groupBy = []) => {
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
