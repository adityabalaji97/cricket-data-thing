/**
 * Pitch Map Utilities
 * 
 * Data transformation and helper functions for pitch map visualization.
 */

import { 
  LINE_ORDER, 
  LENGTH_ORDER, 
  HEAT_COLORS,
  METRICS 
} from './pitchMapConstants';

/**
 * Determine pitch map mode based on groupBy columns.
 */
export function getPitchMapMode(groupBy) {
  const hasLine = groupBy.includes('line');
  const hasLength = groupBy.includes('length');
  
  if (hasLine && hasLength) return 'grid';
  if (hasLine) return 'line-only';
  if (hasLength) return 'length-only';
  return null;
}

/**
 * Get non-pitch dimensions from groupBy (e.g., batter, bowler, venue).
 */
export function getNonPitchDimensions(groupBy) {
  return groupBy.filter(col => col !== 'line' && col !== 'length');
}

/**
 * Get unique values for a dimension from data.
 */
export function getUniqueDimensionValues(data, dimension) {
  const values = new Set();
  data.forEach(row => {
    if (row[dimension] !== null && row[dimension] !== undefined) {
      values.add(row[dimension]);
    }
  });
  return Array.from(values).sort();
}

/**
 * Filter data by dimension selections.
 * @param {Array} data - Query result data
 * @param {Object} selections - { dimension: value } object
 */
export function filterDataBySelections(data, selections) {
  return data.filter(row => {
    return Object.entries(selections).every(([dim, value]) => {
      if (value === null || value === undefined || value === 'all') return true;
      return row[dim] === value;
    });
  });
}

/**
 * Transform query data to pitch map cell format.
 * @param {Array} data - Filtered query result data
 * @param {string} mode - 'grid', 'line-only', or 'length-only'
 */
export function transformToPitchMapCells(data, mode) {
  const cells = [];
  
  if (mode === 'grid') {
    // Create a lookup map for line+length combinations
    const lookup = {};
    data.forEach(row => {
      if (row.line && row.length) {
        const key = `${row.line}|${row.length}`;
        lookup[key] = row;
      }
    });
    
    // Generate cells for all line/length combinations
    LINE_ORDER.forEach(line => {
      LENGTH_ORDER.forEach(length => {
        const key = `${line}|${length}`;
        const row = lookup[key];
        cells.push({
          line,
          length,
          ...(row || { balls: 0 })
        });
      });
    });
  } else if (mode === 'line-only') {
    // Aggregate by line
    const lookup = {};
    data.forEach(row => {
      if (row.line) {
        lookup[row.line] = row;
      }
    });
    
    LINE_ORDER.forEach(line => {
      const row = lookup[line];
      cells.push({
        line,
        length: null,
        ...(row || { balls: 0 })
      });
    });
  } else if (mode === 'length-only') {
    // Aggregate by length
    const lookup = {};
    data.forEach(row => {
      if (row.length) {
        lookup[row.length] = row;
      }
    });
    
    LENGTH_ORDER.forEach(length => {
      const row = lookup[length];
      cells.push({
        line: null,
        length,
        ...(row || { balls: 0 })
      });
    });
  }
  
  return cells;
}

/**
 * Calculate color based on value and metric configuration.
 * @param {number} value - Metric value
 * @param {string} metricKey - Metric key from METRICS
 * @param {Object} dataRange - { min, max } calculated from data
 */
export function getHeatColor(value, metricKey, dataRange) {
  if (value === null || value === undefined) {
    return HEAT_COLORS.noData;
  }
  
  const metric = METRICS[metricKey];
  if (!metric) return HEAT_COLORS.noData;
  
  // Use data range if provided, otherwise use metric's default range
  const min = dataRange?.min ?? metric.range[0];
  const max = dataRange?.max ?? metric.range[1];
  
  // Normalize value to 0-1
  let normalized = (value - min) / (max - min);
  normalized = Math.max(0, Math.min(1, normalized)); // Clamp to 0-1
  
  // Flip for descending scales (where lower is better)
  if (metric.colorScale === 'descending') {
    normalized = 1 - normalized;
  }
  
  // Interpolate color (blue -> yellow -> red)
  return interpolateHeatColor(normalized);
}

/**
 * Interpolate between bad (red) -> neutral (yellow) -> good (green).
 * For batter-friendly metrics: higher = greener
 */
function interpolateHeatColor(t) {
  // t: 0 = bad (red), 0.5 = neutral (yellow), 1 = good (green)
  const bad = { r: 239, g: 68, b: 68 };      // #ef4444 - red
  const neutral = { r: 251, g: 191, b: 36 }; // #fbbf24 - yellow
  const good = { r: 34, g: 197, b: 94 };     // #22c55e - green
  
  let r, g, b;
  
  if (t < 0.5) {
    // Interpolate bad -> neutral
    const t2 = t * 2;
    r = Math.round(bad.r + (neutral.r - bad.r) * t2);
    g = Math.round(bad.g + (neutral.g - bad.g) * t2);
    b = Math.round(bad.b + (neutral.b - bad.b) * t2);
  } else {
    // Interpolate neutral -> good
    const t2 = (t - 0.5) * 2;
    r = Math.round(neutral.r + (good.r - neutral.r) * t2);
    g = Math.round(neutral.g + (good.g - neutral.g) * t2);
    b = Math.round(neutral.b + (good.b - neutral.b) * t2);
  }
  
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Calculate data range for a metric from cells.
 */
export function calculateDataRange(cells, metricKey, minBalls = 0) {
  const values = cells
    .filter(cell => cell.balls >= minBalls && cell[metricKey] !== null && cell[metricKey] !== undefined)
    .map(cell => cell[metricKey]);
  
  if (values.length === 0) return null;
  
  return {
    min: Math.min(...values),
    max: Math.max(...values)
  };
}

/**
 * Format cell content with multiple metrics.
 * @param {Object} cell - Cell data
 * @param {Array} metrics - Array of metric keys to display
 */
export function formatCellContent(cell, metrics) {
  if (!cell || cell.balls === 0) return null;
  
  return metrics.map(metricKey => {
    const metric = METRICS[metricKey];
    if (!metric) return null;
    
    const value = cell[metricKey];
    return {
      key: metricKey,
      label: metric.shortLabel,
      value: metric.format(value),
      raw: value
    };
  }).filter(Boolean);
}

/**
 * Get cell position in SVG coordinates.
 * Orientation: Stumps at top, full toss at stump level, short balls at bottom.
 */
export function getCellPosition(line, length, mode, dimensions) {
  const { padding, pitchWidth, pitchHeight, stumpOverlap = 0 } = dimensions;
  const contentWidth = pitchWidth;
  const contentHeight = pitchHeight;
  
  // Reverse length order so full toss is at top (near stumps), short at bottom
  const reversedLengthOrder = [...LENGTH_ORDER].reverse();
  
  let x, y, width, height;
  
  if (mode === 'grid') {
    const lineIndex = LINE_ORDER.indexOf(line);
    const lengthIndex = reversedLengthOrder.indexOf(length);
    
    width = contentWidth / LINE_ORDER.length;
    height = contentHeight / LENGTH_ORDER.length;
    x = padding.left + lineIndex * width;
    // Start from higher up (stumpOverlap) so full toss is at stump level
    y = (padding.top - stumpOverlap) + lengthIndex * height;
  } else if (mode === 'line-only') {
    const lineIndex = LINE_ORDER.indexOf(line);
    
    width = contentWidth / LINE_ORDER.length;
    height = contentHeight;
    x = padding.left + lineIndex * width;
    y = padding.top - stumpOverlap;
  } else if (mode === 'length-only') {
    const lengthIndex = reversedLengthOrder.indexOf(length);
    
    width = contentWidth;
    height = contentHeight / LENGTH_ORDER.length;
    x = padding.left;
    y = (padding.top - stumpOverlap) + lengthIndex * height;
  }
  
  return { x, y, width, height };
}
