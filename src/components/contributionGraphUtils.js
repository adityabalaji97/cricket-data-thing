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
  if (isDuck) return '#ebedf0'; // Light gray for ducks (emoji will be shown)
  if (score <= 0) return '#ebedf0';
  if (score <= 20) return '#9be9a8';
  if (score <= 40) return '#40c463';
  if (score <= 70) return '#30a14e';
  return '#216e39';
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
 * Get the Monday of the week containing the given date
 * @param {Date} date 
 * @returns {Date}
 */
export const getWeekStart = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Sunday
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
};

/**
 * Generate array of weeks between start and end date
 * @param {Date} startDate 
 * @param {Date} endDate 
 * @returns {Date[]} - Array of week start dates (Mondays)
 */
export const getWeeksBetween = (startDate, endDate) => {
  const weeks = [];
  let current = getWeekStart(new Date(startDate));
  const end = new Date(endDate);
  
  while (current <= end) {
    weeks.push(new Date(current));
    current.setDate(current.getDate() + 7);
  }
  
  return weeks;
};

/**
 * Format date as YYYY-MM-DD for comparison
 * @param {Date} date 
 * @returns {string}
 */
export const formatDateKey = (date) => {
  const d = new Date(date);
  return d.toISOString().split('T')[0];
};

/**
 * Get month labels for the graph header
 * @param {Date[]} weeks - Array of week start dates
 * @returns {Array<{month: string, colSpan: number}>}
 */
export const getMonthLabels = (weeks) => {
  if (!weeks.length) return [];
  
  const labels = [];
  let currentMonth = null;
  let colSpan = 0;
  
  weeks.forEach((week, index) => {
    const month = week.toLocaleDateString('en-US', { month: 'short' });
    
    if (month !== currentMonth) {
      if (currentMonth !== null) {
        labels.push({ month: currentMonth, colSpan });
      }
      currentMonth = month;
      colSpan = 1;
    } else {
      colSpan++;
    }
    
    // Handle last week
    if (index === weeks.length - 1) {
      labels.push({ month: currentMonth, colSpan });
    }
  });
  
  return labels;
};

/**
 * Create a map of date -> innings data for quick lookup
 * @param {Array} innings - Array of innings objects
 * @returns {Map<string, object>}
 */
export const createInningsMap = (innings) => {
  const map = new Map();
  
  innings.forEach(inning => {
    const dateKey = inning.date?.split('T')[0] || inning.date;
    if (dateKey) {
      // If multiple innings on same day, keep the one with higher fantasy points
      const existing = map.get(dateKey);
      if (!existing || (inning.fantasy_points || 0) > (existing.fantasy_points || 0)) {
        map.set(dateKey, inning);
      }
    }
  });
  
  return map;
};

/**
 * Day labels for the left axis
 */
export const DAY_LABELS = ['Mon', '', 'Wed', '', 'Fri', '', 'Sun'];
