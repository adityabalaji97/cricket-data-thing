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

// The menu overhaul (5 Nov 2026): 19 entries down to 8, by use over the previous 60 days. Rankings, Doppelgangers,
// Batter Comparison, Matchups and Team Comparison went (their routes redirect; Compare replaces the comparisons);
// Make a Graphic is reached from the query builder; IPL Predictions and the Fantasy Planner are off the menu until the
// IPL; 2025 Wrapped is off until the next one. Their URLs still work.
export const NAV_ITEMS = [
  { path: '/', label: 'Home', title: 'Home', group: 'primary', short: 'Home' },
  { path: '/search', label: 'Search', title: 'Search', group: 'primary', short: 'Search' },
  { path: '/venue', label: 'Match Preview', title: 'Match Preview', group: 'primary', short: 'Preview' },
  { path: '/query', label: 'Query Builder', title: 'Query Builder', group: 'primary', short: 'Query' },
  { path: '/player', label: 'Players', title: 'Player Profile', group: 'explore' },
  { path: '/team', label: 'Teams', title: 'Team', group: 'explore' },
  { path: '/venues', label: 'Venues', title: 'Venues', group: 'explore' },
  { path: '/scorecards', label: 'Scorecards', title: 'Scorecards', group: 'explore' },
  { path: '/notes', label: 'Notes', title: 'Notes', group: 'explore' },
  { path: '/compare', label: 'Compare', title: 'Compare', group: 'compare' },
  { path: '/games', label: 'Daily games', title: 'Daily games', group: 'play' },
];

/**
 * Mobile navigation grouping. `primary` items sit in the bottom bar (in this order); the rest
 * appear under these headings in the "More" sheet. Defined here, beside the items, so the desktop
 * tabs and the mobile nav cannot drift apart again.
 */
export const PRIMARY_NAV_PATHS = ['/', '/search', '/venue', '/query'];
// Shown in the desktop menu's Main group right after the bottom-bar pages, without becoming a tab.
export const MAIN_MENU_EXTRA = [];

export const MORE_NAV_GROUPS = [
  { key: 'explore', label: 'Explore' },
  { key: 'compare', label: 'Compare' },
  { key: 'play', label: 'Play' },
];

/** Linked from the More sheet but not a nav item of their own. */
export const MORE_EXTRA_LINKS = [];  // Credits sit in the site footer

/** Pages reachable but absent from the nav, so they still get a heading. */
const UNLISTED_TITLES = [
  { match: (path) => path === '/graphics', title: 'Make a Graphic' },
  { match: (path) => path === '/ipl-predictions', title: 'IPL Predictions' },
  { match: (path) => path === '/fantasy-planner', title: 'Fantasy Planner' },
  { match: (path) => path === '/games/call-it', title: 'Call It' },
  { match: (path) => path === '/games/higher-lower', title: 'Higher or Lower' },
  { match: (path) => path === '/games/guess-innings', title: 'Guess the Innings' },
  { match: (path) => path === '/games/player-journeys', title: 'Player Journeys' },
  { match: (path) => path === '/credits', title: 'Credits & Acknowledgements' },
  { match: (path) => path.startsWith('/scorecard'), title: 'Match Scorecard' },
  { match: (path) => path.startsWith('/wrapped'), title: '2025 Wrapped' },
  { match: (path) => path.startsWith('/notes/'), title: 'Notes' },
  { match: (path) => path === '/admin/notes', title: 'Notes queue' },
  { match: (path) => path === '/admin', title: 'Social queue' },
  { match: (path) => path === '/links', title: 'Hindsight links' },
  { match: (path) => path.startsWith('/g/'), title: 'Graphic' },
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
