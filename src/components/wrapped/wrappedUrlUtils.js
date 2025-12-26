/**
 * Wrapped URL Utility Functions
 * 
 * Provides consistent URL building for links from wrapped cards
 * to search, query builder, and other pages.
 */

// Default date range for 2025 Wrapped
export const WRAPPED_DATE_RANGE = {
  start: '2025-01-01',
  end: '2025-12-31'
};

/**
 * Build a search URL for a player with wrapped date filters
 * @param {string} playerName - The player's name
 * @param {object} options - Optional overrides for dates
 * @returns {string} - The complete URL
 */
export const buildPlayerSearchUrl = (playerName, options = {}) => {
  const startDate = options.startDate || WRAPPED_DATE_RANGE.start;
  const endDate = options.endDate || WRAPPED_DATE_RANGE.end;
  
  const params = new URLSearchParams();
  params.set('q', playerName);
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  
  return `/search?${params.toString()}`;
};

/**
 * Build a query builder URL with wrapped date filters
 * @param {object} queryParams - Query parameters for the query builder
 * @param {object} options - Optional overrides for dates
 * @returns {string} - The complete URL
 */
export const buildQueryBuilderUrl = (queryParams = {}, options = {}) => {
  const startDate = options.startDate || WRAPPED_DATE_RANGE.start;
  const endDate = options.endDate || WRAPPED_DATE_RANGE.end;
  
  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  
  // Add any additional query params
  Object.entries(queryParams).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach(v => params.append(key, v));
      } else {
        params.set(key, value);
      }
    }
  });
  
  return `/query?${params.toString()}`;
};

/**
 * Build a player profile URL with wrapped date filters
 * @param {string} playerName - The player's name
 * @param {string} type - 'player' for batting or 'bowler' for bowling profile
 * @param {object} options - Optional overrides for dates
 * @returns {string} - The complete URL
 */
export const buildPlayerProfileUrl = (playerName, type = 'player', options = {}) => {
  const startDate = options.startDate || WRAPPED_DATE_RANGE.start;
  const endDate = options.endDate || WRAPPED_DATE_RANGE.end;
  
  const params = new URLSearchParams();
  params.set('name', playerName);
  params.set('autoload', 'true');
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  
  const route = type === 'bowler' ? '/bowler' : '/player';
  return `${route}?${params.toString()}`;
};

/**
 * Open a URL in a new tab
 * @param {string} url - The URL to open
 */
export const openInNewTab = (url) => {
  window.open(url, '_blank', 'noopener,noreferrer');
};

/**
 * Handle player click - opens search page with wrapped date filters
 * @param {object} player - Player object with at least a 'name' property
 * @param {object} options - Optional overrides
 */
export const handleWrappedPlayerClick = (player, options = {}) => {
  const url = buildPlayerSearchUrl(player.name, options);
  openInNewTab(url);
};

export default {
  WRAPPED_DATE_RANGE,
  buildPlayerSearchUrl,
  buildQueryBuilderUrl,
  buildPlayerProfileUrl,
  openInNewTab,
  handleWrappedPlayerClick
};
