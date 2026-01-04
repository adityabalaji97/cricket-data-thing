/**
 * Pitch Map Constants
 * 
 * Coordinates and mappings for pitch map visualization.
 * Mobile-first design with stumps centered in full toss row.
 */

// Line values from delivery_details (left to right from bowler's view for RHB)
export const LINE_ORDER = [
  'WIDE_OUTSIDE_OFFSTUMP',
  'OUTSIDE_OFFSTUMP', 
  'ON_THE_STUMPS',
  'DOWN_LEG',
  'WIDE_DOWN_LEG'
];

export const LINE_LABELS = {
  'WIDE_OUTSIDE_OFFSTUMP': 'Wide Off',
  'OUTSIDE_OFFSTUMP': 'Outside Off',
  'ON_THE_STUMPS': 'Stumps',
  'DOWN_LEG': 'Down Leg',
  'WIDE_DOWN_LEG': 'Wide Leg'
};

export const LINE_SHORT_LABELS = {
  'WIDE_OUTSIDE_OFFSTUMP': 'W.Off',
  'OUTSIDE_OFFSTUMP': 'Off',
  'ON_THE_STUMPS': 'Stumps',
  'DOWN_LEG': 'Leg',
  'WIDE_DOWN_LEG': 'W.Leg'
};

// Length values (SHORT at bottom, FULL_TOSS at top near stumps)
export const LENGTH_ORDER = [
  'SHORT',
  'SHORT_OF_A_GOOD_LENGTH',
  'GOOD_LENGTH',
  'FULL',
  'YORKER',
  'FULL_TOSS'
];

export const LENGTH_LABELS = {
  'SHORT': 'Short',
  'SHORT_OF_A_GOOD_LENGTH': 'Back of Length',
  'GOOD_LENGTH': 'Good Length',
  'FULL': 'Full',
  'YORKER': 'Yorker',
  'FULL_TOSS': 'Full Toss'
};

export const LENGTH_SHORT_LABELS = {
  'SHORT': 'Short',
  'SHORT_OF_A_GOOD_LENGTH': 'Back',
  'GOOD_LENGTH': 'Good',
  'FULL': 'Full',
  'YORKER': 'Yorker',
  'FULL_TOSS': 'F.Toss'
};

// SVG dimensions and layout - mobile-first
export const PITCH_DIMENSIONS = {
  width: 360,
  height: 520,
  padding: { top: 50, right: 45, bottom: 40, left: 15 },
  pitchWidth: 280,
  pitchHeight: 420,
  stumpHeight: 40,
  stumpWidth: 6,
  stumpGap: 9,
};

// Available metrics for visualization
export const METRICS = {
  strike_rate: {
    key: 'strike_rate',
    label: 'Strike Rate',
    shortLabel: 'SR',
    format: (v) => v?.toFixed(1) ?? '-',
    colorScale: 'ascending',
    range: [60, 200]
  },
  average: {
    key: 'average',
    label: 'Average',
    shortLabel: 'Avg',
    format: (v) => v?.toFixed(1) ?? '-',
    colorScale: 'ascending',
    range: [10, 60]
  },
  dot_percentage: {
    key: 'dot_percentage',
    label: 'Dot %',
    shortLabel: 'Dot%',
    format: (v) => v != null ? v.toFixed(1) + '%' : '-',
    colorScale: 'descending',
    range: [20, 60]
  },
  boundary_percentage: {
    key: 'boundary_percentage',
    label: 'Boundary %',
    shortLabel: 'Bnd%',
    format: (v) => v != null ? v.toFixed(1) + '%' : '-',
    colorScale: 'ascending',
    range: [5, 30]
  },
  percent_balls: {
    key: 'percent_balls',
    label: '% of Balls',
    shortLabel: '%Balls',
    format: (v) => v != null ? v.toFixed(1) + '%' : '-',
    colorScale: 'neutral',
    range: [0, 50]
  },
  balls: {
    key: 'balls',
    label: 'Balls',
    shortLabel: 'Balls',
    format: (v) => v?.toString() ?? '-',
    colorScale: 'neutral',
    range: [0, 500]
  },
  runs: {
    key: 'runs',
    label: 'Runs',
    shortLabel: 'Runs',
    format: (v) => v?.toString() ?? '-',
    colorScale: 'ascending',
    range: [0, 500]
  },
  wickets: {
    key: 'wickets',
    label: 'Wickets',
    shortLabel: 'Wkts',
    format: (v) => v?.toString() ?? '-',
    colorScale: 'descending',
    range: [0, 20]
  },
  control_percentage: {
    key: 'control_percentage',
    label: 'Control %',
    shortLabel: 'Ctrl%',
    format: (v) => v != null ? v.toFixed(1) + '%' : '-',
    colorScale: 'ascending',
    range: [50, 95]
  }
};

// Default metrics to display in cells
export const DEFAULT_CELL_METRICS = ['average', 'strike_rate'];

// Secondary metrics (shown on second line)
export const DEFAULT_SECONDARY_METRICS = ['dot_percentage', 'boundary_percentage'];

// Default metric for color scale
export const DEFAULT_COLOR_METRIC = 'strike_rate';

// Heat map color scale (red=bad for batter, green=good for batter)
export const HEAT_COLORS = {
  bad: '#ef4444',
  neutral: '#fbbf24',
  good: '#22c55e',
  noData: '#e5e7eb'
};

// Minimum balls threshold options
export const MIN_BALLS_OPTIONS = [0, 5, 10, 20, 50, 100];
export const DEFAULT_MIN_BALLS = 10;
