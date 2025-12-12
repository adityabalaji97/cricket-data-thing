/**
 * Utility functions for ContributionGraph component
 */

/**
 * Get color for a batter's fantasy score
 * @param {number} score - Fantasy points
 * @param {boolean} isDuck - Whether the batter scored 0 runs
 * @returns {string} - Hex color code
 */
export const getBatterColor = (score, isDuck) => {
  if (isDuck) return '#ebedf0'; // Light gray for ducks
  if (score <= 0) return '#ebedf0';
  if (score <= 30) return '#9be9a8';  // Light green
  if (score <= 50) return '#40c463';  // Medium green
  if (score <= 75) return '#30a14e';  // Dark green
  return '#216e39';                    // Darkest green
};

/**
 * Get color for a bowler's fantasy score
 * @param {number} score - Fantasy points
 * @returns {string} - Hex color code
 */
export const getBowlerColor = (score) => {
  if (score <= 0) return '#ebedf0';
  if (score <= 15) return '#9be9a8';
  if (score <= 30) return '#40c463';
  if (score <= 50) return '#30a14e';
  return '#216e39';
};

/**
 * Get the Sunday of the week containing the given date (to match GitHub-style)
 * @param {Date} date 
 * @returns {Date}
 */
export const getWeekStart = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  // Move to Sunday (start of week)
  const diff = -day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
};

// Removed unused utility functions - logic is now in ContributionGraph component
