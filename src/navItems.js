/**
 * The navigation, defined once.
 *
 * This list previously existed four times over in App.js — a path-to-tab-index map, a
 * path-to-title map, the desktop <Tabs>, and the mobile <Menu> — so adding or renaming a page
 * meant four edits and any missed one produced a wrong tab highlight or heading.
 *
 * `t20Only` marks the pages that are not being made multi-format. They are always reachable:
 * App.js wraps their routes in FormatContext `MensT20Scope`, so they run as men's T20 whatever
 * the site-wide format is (an ODI preview sets it to ODI, and it persists). The nav only adds a
 * "Men's T20" note when another format is selected. (They used to be disabled then, which after
 * one ODI preview greyed out most of the More sheet.)
 */

export const NAV_ITEMS = [
  { path: '/', label: 'Home', title: 'Home', group: 'primary', short: 'Home' },
  { path: '/search', label: 'Search', title: 'Search', group: 'primary', short: 'Search' },
  { path: '/venue', label: 'Match Preview', title: 'Match Preview', group: 'primary', short: 'Preview' },
  { path: '/player', label: 'Player Profile', title: 'Player Profile', t20Only: true, group: 'explore' },
  { path: '/comparison', label: 'Batter Comparison', title: 'Batter Comparison', t20Only: true, group: 'compare' },
  { path: '/matchups', label: 'Matchups', title: 'Matchups', t20Only: true, group: 'compare' },
  { path: '/query', label: 'Query Builder', title: 'Query Builder', group: 'primary', short: 'Query' },
  { path: '/team', label: 'Team Profile', title: 'Team Profile', t20Only: true, group: 'explore' },
  { path: '/team-comparison', label: 'Team Comparison', title: 'Team Comparison', t20Only: true, group: 'compare' },
  { path: '/doppelgangers', label: 'Doppelgangers', title: 'Doppelgangers', t20Only: true, group: 'compare' },
  { path: '/ipl-predictions', label: 'IPL Predictions', title: 'IPL Predictions', t20Only: true, group: 'play' },
  { path: '/rankings', label: 'Global Rankings', title: 'Global Rankings', t20Only: true, group: 'explore' },
  {
    path: '/games/guess-innings',
    label: '🎯 Guess the Innings',
    title: 'Guess the Innings',
    t20Only: true,
    group: 'play',
  },
  {
    path: '/games/player-journeys',
    label: '🛤️ Player Journeys',
    title: 'Player Journeys',
    t20Only: true,
    group: 'play',
  },
  { path: '/fantasy-planner', label: 'Fantasy Planner', title: 'Fantasy Planner', t20Only: true, group: 'play' },
];

/**
 * Mobile navigation grouping. `primary` items sit in the bottom bar (in this order); the rest
 * appear under these headings in the "More" sheet. Defined here, beside the items, so the desktop
 * tabs and the mobile nav cannot drift apart again.
 */
export const PRIMARY_NAV_PATHS = ['/', '/search', '/venue', '/query'];

export const MORE_NAV_GROUPS = [
  { key: 'explore', label: 'Explore' },
  { key: 'compare', label: 'Compare' },
  { key: 'play', label: 'Play' },
];

/** Linked from the More sheet but not a nav item of their own. */
export const MORE_EXTRA_LINKS = [
  { path: '/wrapped/2025', label: '2025 Wrapped', group: 'play' },
  { path: '/credits', label: 'Credits & Acknowledgements', group: null },
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
