/**
 * Team Colors Utility
 * Brand colours for IPL, international and the other major T20 league teams. The palette lives in
 * teamPalette.json so Python (post renderers, scripts) reads the same values as the app.
 */
import PALETTE from './teamPalette.json';

const TEAMS = PALETTE.teams;

// Team name or alias -> canonical team name.
const CANONICAL = Object.fromEntries([
  ...Object.keys(TEAMS).map((name) => [name, name]),
  ...Object.entries(PALETTE.aliases),
]);

// Every name and alias -> primary colour (the flat map components have always imported).
const TEAM_COLORS = Object.fromEntries(
  Object.entries(CANONICAL).map(([key, name]) => [key, TEAMS[name].primary])
);

// Vibrant fallback colors for non-team data
const FALLBACK_COLORS = [
  '#E91E63', // Pink
  '#4CAF50', // Green
  '#2196F3', // Blue
  '#FF9800', // Orange
  '#9C27B0', // Purple
  '#F44336', // Red
  '#00BCD4', // Cyan
  '#8BC34A', // Light Green
  '#3F51B5', // Indigo
  '#FF5722', // Deep Orange
  '#607D8B', // Blue Grey
  '#795548', // Brown
  '#009688', // Teal
  '#CDDC39', // Lime
  '#FFC107', // Amber
  '#673AB7', // Deep Purple
  '#FF1744', // Pink Accent
  '#00E676', // Green Accent
  '#2979FF', // Blue Accent
  '#FF6D00'  // Orange Accent
];

const LOWER = Object.fromEntries(Object.keys(CANONICAL).map((key) => [key.toLowerCase(), CANONICAL[key]]));

/** Canonical team name for a full name, old name or IPL/international abbreviation, else null. */
const resolveTeam = (teamName) => {
  if (!teamName) return null;
  if (CANONICAL[teamName]) return CANONICAL[teamName];
  const lower = String(teamName).toLowerCase();
  if (LOWER[lower]) return LOWER[lower];
  // Combined labels such as "Chennai Super Kings / CSK": the first part that names a team.
  for (const part of String(teamName).split(/[/-]/)) {
    const trimmed = part.trim();
    if (CANONICAL[trimmed]) return CANONICAL[trimmed];
  }
  return null;
};

/**
 * Get color for a team name
 * @param {string} teamName - The team name (full or abbreviation)
 * @returns {string|null} - Hex color code or null if not found
 */
export const getTeamColor = (teamName) => {
  const name = resolveTeam(teamName);
  return name ? TEAMS[name].primary : null;
};

/** The team's trim colour (borders, stripes, a second series for the same team), or null. */
export const getTeamSecondary = (teamName) => {
  const name = resolveTeam(teamName);
  return name ? TEAMS[name].secondary : null;
};

/** { name, primary, secondary, league } for a team, or null. */
export const getTeamPalette = (teamName) => {
  const name = resolveTeam(teamName);
  return name ? { name, ...TEAMS[name] } : null;
};

/**
 * Get a fallback color by index (for non-team data)
 * @param {number} index - Index for color selection
 * @returns {string} - Hex color code
 */
export const getFallbackColor = (index) => {
  return FALLBACK_COLORS[index % FALLBACK_COLORS.length];
};

/**
 * Get color for a data point, preferring team color if available
 * @param {object} row - Data row object
 * @param {number} index - Row index for fallback color
 * @param {string[]} teamColumns - Column names to check for team values
 * @returns {string} - Hex color code
 */
export const getDataPointColor = (row, index, teamColumns = ['batting_team', 'bowling_team', 'team']) => {
  // Try each team column
  for (const col of teamColumns) {
    const teamValue = row[col];
    if (teamValue) {
      const teamColor = getTeamColor(teamValue);
      if (teamColor) {
        return teamColor;
      }
    }
  }
  
  // Fall back to indexed color
  return getFallbackColor(index);
};

/**
 * Check if a grouping includes team-related columns
 * @param {string[]} groupBy - Array of grouping column names
 * @returns {boolean}
 */
export const hasTeamGrouping = (groupBy) => {
  if (!groupBy || !Array.isArray(groupBy)) return false;
  
  const teamColumns = ['batting_team', 'bowling_team', 'team', 'team_bat', 'team_bowl'];
  return groupBy.some(col => teamColumns.includes(col));
};

export default {
  getTeamColor,
  getTeamSecondary,
  getTeamPalette,
  getFallbackColor,
  getDataPointColor,
  hasTeamGrouping,
  TEAM_COLORS,
  FALLBACK_COLORS
};

/**
 * Lighten a colour until it reads as text on the dark app background.
 *
 * Team brand colours were picked for white pages; several (navy, maroon, near-black) vanish on
 * the dark surfaces. Mixes toward white only as far as needed to reach a minimum relative
 * luminance, so bright brand colours pass through unchanged. Non-hex input is returned as-is.
 */
export const readableOnDark = (color, minLuminance = 0.28) => {
  if (typeof color !== 'string' || !/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(color)) return color;
  let hex = color.slice(1);
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
  const rgb = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const channel = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const luminance = (c) => 0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2]);
  if (luminance(rgb) >= minLuminance) return color;
  for (let t = 0.1; t <= 1.0001; t += 0.1) {
    const mixed = rgb.map((v) => Math.round(v + (255 - v) * t));
    if (luminance(mixed) >= minLuminance) {
      return `#${mixed.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
    }
  }
  return '#ffffff';
};

const DARK_TEXT = '#0a0c11';

/**
 * Text colour for a label sitting ON a filled colour: the app's near-black or white, whichever
 * contrasts more. White-on-anything was the old default, and on bright fills (sky blue, light
 * green, amber, teal) it fell to 1.5-2.5:1. Non-hex input gets white.
 */
export const textOn = (color) => {
  if (typeof color !== 'string' || !/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(color)) return '#ffffff';
  let hex = color.slice(1);
  if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
  const channel = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const [r, g, b] = [0, 2, 4].map((i) => channel(parseInt(hex.slice(i, i + 2), 16)));
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const onWhite = 1.05 / (lum + 0.05);
  const onDark = (lum + 0.05) / 0.0536;
  return onDark > onWhite ? DARK_TEXT : '#ffffff';
};
