import config from '../../config';

// Default search parameters
const today = new Date();
const lastYear = new Date(today.getFullYear() - 1, 0, 1);

export const DEFAULT_SEARCH_PARAMS = {
  start_date: lastYear.toISOString().split('T')[0],
  end_date: today.toISOString().split('T')[0],
  leagues: [],
  include_international: true,
  top_teams: 20
};

// API base URL from config
export const API_BASE_URL = config.API_URL;

// Search debounce delay (ms)
export const SEARCH_DEBOUNCE_MS = 300;

// Min characters to trigger search
export const MIN_SEARCH_LENGTH = 2;

// Max recent searches to store
export const MAX_RECENT_SEARCHES = 10;

// Entity type icons
export const ENTITY_ICONS = {
  player: '👤',
  team: '🏏',
  venue: '🏟️'
};

// Entity type labels  
export const ENTITY_LABELS = {
  player: 'Player',
  team: 'Team',
  venue: 'Venue'
};
