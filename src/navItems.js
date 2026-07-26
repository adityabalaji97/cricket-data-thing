/**
 * The navigation, defined once.
 *
 * This list previously existed four times over in App.js — a path-to-tab-index map, a
 * path-to-title map, the desktop <Tabs>, and the mobile <Menu> — so adding or renaming a page
 * meant four edits and any missed one produced a wrong tab highlight or heading.
 *
 * `t20Only` marks the pages that are not being made multi-format. They stay reachable, but the
 * nav disables them when a non-T20 format is selected, because the endpoints behind them are
 * pinned to men's T20 and would otherwise render an empty page that looks broken rather than
 * out of scope.
 */

export const NAV_ITEMS = [
  { path: '/', label: 'Home', title: 'Home' },
  { path: '/search', label: 'Search', title: 'Search' },
  { path: '/venue', label: 'Match Preview', title: 'Match Preview' },
  { path: '/player', label: 'Player Profile', title: 'Player Profile', t20Only: true },
  { path: '/comparison', label: 'Batter Comparison', title: 'Batter Comparison', t20Only: true },
  { path: '/matchups', label: 'Matchups', title: 'Matchups', t20Only: true },
  { path: '/query', label: 'Query Builder', title: 'Query Builder' },
  { path: '/team', label: 'Team Profile', title: 'Team Profile', t20Only: true },
  { path: '/team-comparison', label: 'Team Comparison', title: 'Team Comparison', t20Only: true },
  { path: '/doppelgangers', label: 'Doppelgangers', title: 'Doppelgangers', t20Only: true },
  { path: '/ipl-predictions', label: 'IPL Predictions', title: 'IPL Predictions', t20Only: true },
  { path: '/rankings', label: 'Global Rankings', title: 'Global Rankings', t20Only: true },
  {
    path: '/games/guess-innings',
    label: '🎯 Guess the Innings',
    title: 'Guess the Innings',
    t20Only: true,
  },
  {
    path: '/games/player-journeys',
    label: '🛤️ Player Journeys',
    title: 'Player Journeys',
    t20Only: true,
  },
  { path: '/fantasy-planner', label: 'Fantasy Planner', title: 'Fantasy Planner', t20Only: true },
];

/** Pages reachable but absent from the nav, so they still get a heading. */
const UNLISTED_TITLES = [
  { match: (path) => path === '/credits', title: 'Credits & Acknowledgements' },
  { match: (path) => path.startsWith('/scorecard'), title: 'Match Scorecard' },
  { match: (path) => path.startsWith('/wrapped'), title: '2025 Wrapped' },
];

/** Tab index for a path, or `false` where no tab should appear selected. */
export const getCurrentTabForPath = (path) => {
  const index = NAV_ITEMS.findIndex((item) => item.path === path);
  if (index >= 0) return index;
  return UNLISTED_TITLES.some((entry) => entry.match(path)) ? false : 0;
};

export const getPageTitleForPath = (path) => {
  const item = NAV_ITEMS.find((entry) => entry.path === path);
  if (item) return item.title;
  const unlisted = UNLISTED_TITLES.find((entry) => entry.match(path));
  return unlisted ? unlisted.title : 'Home';
};

export default NAV_ITEMS;
