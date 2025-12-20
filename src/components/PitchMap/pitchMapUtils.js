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
 */
export function transformToPitchMapCells(data, mode) {
  const cells = [];
  
  if (mode === 'grid') {
    const lookup = {};
    data.forEach(row => {
      if (row.line && row.length) {
        const key = `${row.line}|${row.length}`;
        lookup[key] = row;
      }
    });
    
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
 */
export function getHeatColor(value, metricKey, dataRange) {
  if (value === null || value === undefined) {
    return HEAT_COLORS.noData;
  }
  
  const metric = METRICS[metricKey];
  if (!metric) return HEAT_COLORS.noData;
  
  const min = dataRange?.min ?? metric.range[0];
  const max = dataRange?.max ?? metric.range[1];
  
  let normalized = (value - min) / (max - min);
  normalized = Math.max(0, Math.min(1, normalized));
  
  if (metric.colorScale === 'descending') {
    normalized = 1 - normalized;
  }
  
  return interpolateHeatColor(normalized);
}

/**
 * Interpolate between bad (red) -> neutral (yellow) -> good (green).
 */
function interpolateHeatColor(t) {
  const bad = { r: 239, g: 68, b: 68 };
  const neutral = { r: 251, g: 191, b: 36 };
  const good = { r: 34, g: 197, b: 94 };
  
  let r, g, b;
  
  if (t < 0.5) {
    const t2 = t * 2;
    r = Math.round(bad.r + (neutral.r - bad.r) * t2);
    g = Math.round(bad.g + (neutral.g - bad.g) * t2);
    b = Math.round(bad.b + (neutral.b - bad.b) * t2);
  } else {
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
 * Orientation: Full toss at top (near stumps), short balls at bottom.
 */
export function getCellPosition(line, length, mode, dimensions) {
  const { padding, pitchWidth, pitchHeight } = dimensions;
  
  // Reverse length order so full toss is at top, short at bottom
  const reversedLengthOrder = [...LENGTH_ORDER].reverse();
  
  let x, y, width, height;
  
  if (mode === 'grid') {
    const lineIndex = LINE_ORDER.indexOf(line);
    const lengthIndex = reversedLengthOrder.indexOf(length);
    
    width = pitchWidth / LINE_ORDER.length;
    height = pitchHeight / LENGTH_ORDER.length;
    x = padding.left + lineIndex * width;
    y = padding.top + lengthIndex * height;
  } else if (mode === 'line-only') {
    const lineIndex = LINE_ORDER.indexOf(line);
    
    width = pitchWidth / LINE_ORDER.length;
    height = pitchHeight;
    x = padding.left + lineIndex * width;
    y = padding.top;
  } else if (mode === 'length-only') {
    const lengthIndex = reversedLengthOrder.indexOf(length);
    
    width = pitchWidth;
    height = pitchHeight / LENGTH_ORDER.length;
    x = padding.left;
    y = padding.top + lengthIndex * height;
  }
  
  return { x, y, width, height };
}
