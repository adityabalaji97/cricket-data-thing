/**
 * Team Colors Utility
 * Comprehensive color mapping for cricket teams (IPL + International)
 */

const TEAM_COLORS = {
  // IPL Teams
  'Chennai Super Kings': '#eff542',
  'CSK': '#eff542',
  'Royal Challengers Bangalore': '#f54242',
  'Royal Challengers Bengaluru': '#f54242',
  'RCB': '#f54242',
  'Mumbai Indians': '#42a7f5',
  'MI': '#42a7f5',
  'Rajasthan Royals': '#FF2AA8',
  'Rising Pune Supergiants': '#FF2AA8',
  'Rising Pune Supergiant': '#FF2AA8',
  'RR': '#FF2AA8',
  'RPSG': '#FF2AA8',
  'Kolkata Knight Riders': '#610048',
  'KKR': '#610048',
  'Kings XI Punjab': '#FF004D',
  'Punjab Kings': '#FF004D',
  'PBKS': '#FF004D',
  'Sunrisers Hyderabad': '#FF7C01',
  'SRH': '#FF7C01',
  'Lucknow Super Giants': '#00BBB3',
  'Pune Warriors': '#00BBB3',
  'LSG': '#00BBB3',
  'Delhi Capitals': '#004BC5',
  'Delhi Daredevils': '#004BC5',
  'DC': '#004BC5',
  'Deccan Chargers': '#04378C',
  'DCh': '#04378C',
  'Gujarat Lions': '#FF5814',
  'GL': '#FF5814',
  'Gujarat Titans': '#01295B',
  'GT': '#01295B',
  'Kochi Tuskers Kerala': '#008080',
  'KTK': '#008080',
  
  // International Teams
  'Australia': '#eff542',
  'AUS': '#eff542',
  'England': '#f54242',
  'ENG': '#f54242',
  'India': '#42a7f5',
  'IND': '#42a7f5',
  'South Africa': '#1cba2e',
  'SA': '#1cba2e',
  'Pakistan': '#02450a',
  'PAK': '#02450a',
  'West Indies': '#450202',
  'WI': '#450202',
  'New Zealand': '#050505',
  'NZ': '#050505',
  'Bangladesh': '#022b07',
  'BAN': '#022b07',
  'Afghanistan': '#058bf2',
  'AFG': '#058bf2',
  'Sri Lanka': '#031459',
  'SL': '#031459',
  'Ireland': '#90EE90',
  'IRE': '#90EE90',
  'Netherlands': '#FF7C01',
  'NED': '#FF7C01',
  'Zimbabwe': '#FF7C01',
  'ZIM': '#FF7C01',
  'Scotland': '#4169E1',
  'SCO': '#4169E1',
  'Nepal': '#DC143C',
  'NEP': '#DC143C',
  'USA': '#B22222',
  'Oman': '#8B0000',
  'OMA': '#8B0000',
  'UAE': '#2F4F4F',
  'Papua New Guinea': '#228B22',
  'PNG': '#228B22',
  'Namibia': '#CD853F',
  'NAM': '#CD853F'
};

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

/**
 * Get color for a team name
 * @param {string} teamName - The team name (full or abbreviation)
 * @returns {string|null} - Hex color code or null if not found
 */
export const getTeamColor = (teamName) => {
  if (!teamName) return null;
  
  // Try exact match first
  if (TEAM_COLORS[teamName]) {
    return TEAM_COLORS[teamName];
  }
  
  // Try case-insensitive match
  const lowerName = teamName.toLowerCase();
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (key.toLowerCase() === lowerName) {
      return color;
    }
  }
  
  // Try partial match (for cases like "Chennai Super Kings / CSK")
  const parts = teamName.split(/[\/\-]/);
  for (const part of parts) {
    const trimmed = part.trim();
    if (TEAM_COLORS[trimmed]) {
      return TEAM_COLORS[trimmed];
    }
  }
  
  return null;
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
  getFallbackColor,
  getDataPointColor,
  hasTeamGrouping,
  TEAM_COLORS,
  FALLBACK_COLORS
};
