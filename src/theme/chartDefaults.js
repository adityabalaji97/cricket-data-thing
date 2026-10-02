/**
 * Phone-first presets for Recharts charts. Spread these instead of hand-tuning each chart.
 *
 * Early charts were sized for a desktop card: 30px bottom margins, rotated axis titles, -45°
 * tick labels, 36px legends and ~10px ticks. On a 390px phone that leaves a plot a third of the
 * card wide. These presets encode the sweep's rules (MOBILE_VIZ_SWEEP.md, "CARTA"):
 *   - ticks never smaller than 11px and never rotated; Recharts drops colliding ticks instead
 *   - no rotated axis titles on phones: put the unit in the chart title or the tick formatter
 *   - one y-axis; two measures of different scale are two charts, not a dual axis
 *   - legend above the plot, compact, only when there are 2+ series
 *
 * Colours: SERIES is the validated categorical order (dataviz validator, dark mode, against
 * surface1 #101319: every adjacent pair clears CVD ΔE 8; the first three clear it all-pairs, so
 * scatters cap at three colours). Assign slots by entity in this fixed order; never cycle, and
 * never let a filter repaint the survivors. Lime `colors.accent` is reserved for "this player /
 * this team" highlights, never a series slot.
 */
import { colors } from './hindsightDark';
import { rechartsTooltipProps } from './chartTheme';

export const SERIES = [
  '#3987e5', // blue
  '#d95926', // orange
  '#199e70', // aqua
  '#c98500', // yellow
  '#d55181', // magenta
  '#008300', // green
  '#9085e9', // violet
  '#e66767', // red
];

/** Diverging (batter-good ↔ bowler-good, above ↔ below baseline). Gray means "no edge". */
export const DIVERGING = {
  positive: '#3987e5',
  neutral: '#383835',
  negative: '#e66767',
};

/** Pace / spin are on almost every chart; fix their colours app-wide. */
export const KIND_COLORS = { pace: SERIES[1], spin: SERIES[0] };

/** Phase colours, in order powerplay → middle → death. */
export const PHASE_COLORS = [SERIES[0], SERIES[2], SERIES[1]];

export const HIGHLIGHT = colors.accent;
export const MUTED_MARK = 'rgba(255,255,255,0.18)';

const tickFont = (isMobile) => (isMobile ? 11 : 12);

/** Standard chart heights. Pick by how much the chart needs to show, not per-chart numbers. */
export const chartHeight = (isMobile, size = 'md') => {
  const heights = {
    sm: [180, 220],
    md: [240, 300],
    lg: [300, 380],
  };
  const [mobile, desktop] = heights[size] || heights.md;
  return isMobile ? mobile : desktop;
};

/** Plot margins. Recharts axes reserve their own width, so these only pad the edges. */
export const chartMargin = (isMobile, { legend = false } = {}) => ({
  top: legend ? 4 : 8,
  right: isMobile ? 8 : 16,
  bottom: 4,
  left: isMobile ? 0 : 4,
});

export const xAxisProps = (isMobile, overrides = {}) => ({
  tick: { fontSize: tickFont(isMobile) },
  tickLine: false,
  interval: 'preserveStartEnd',
  minTickGap: isMobile ? 6 : 4,
  angle: 0,
  height: isMobile ? 22 : 26,
  ...overrides,
});

export const yAxisProps = (isMobile, overrides = {}) => ({
  tick: { fontSize: tickFont(isMobile) },
  tickLine: false,
  axisLine: false,
  width: isMobile ? 34 : 44,
  ...overrides,
});

/** Category axis for horizontal bar charts (names on the left). */
export const categoryYAxisProps = (isMobile, overrides = {}) => ({
  type: 'category',
  tick: { fontSize: tickFont(isMobile) },
  tickLine: false,
  axisLine: false,
  width: isMobile ? 72 : 96,
  interval: 0,
  ...overrides,
});

/**
 * A rotated axis title, desktop only. On phones it costs ~20px of a ~340px plot, so the unit
 * belongs in the chart title ("Economy by over") instead.
 */
export const axisLabel = (isMobile, value, { side = 'left' } = {}) => {
  if (isMobile || !value) return undefined;
  if (side === 'bottom') {
    return { value, position: 'insideBottom', offset: -2, style: { fontSize: 12, fill: colors.textLo } };
  }
  return {
    value,
    angle: side === 'right' ? 90 : -90,
    position: side === 'right' ? 'insideRight' : 'insideLeft',
    style: { textAnchor: 'middle', fontSize: 12, fill: colors.textLo },
  };
};

export const legendProps = (isMobile, overrides = {}) => ({
  verticalAlign: 'top',
  align: 'left',
  iconType: 'circle',
  iconSize: 8,
  height: isMobile ? 22 : 26,
  wrapperStyle: { fontSize: tickFont(isMobile), lineHeight: '16px', paddingBottom: 4 },
  ...overrides,
});

/**
 * Tooltips. Recharts already shows a tooltip on tap; these keep it inside the chart on a narrow
 * screen and above neighbouring marks.
 */
export const tooltipProps = (isMobile, overrides = {}) => ({
  ...rechartsTooltipProps,
  allowEscapeViewBox: { x: false, y: false },
  wrapperStyle: { zIndex: 5, outline: 'none', maxWidth: isMobile ? 220 : 280 },
  contentStyle: {
    ...rechartsTooltipProps.contentStyle,
    fontSize: isMobile ? 12 : 13,
    padding: isMobile ? '6px 8px' : '8px 10px',
  },
  ...overrides,
});

export const gridProps = { vertical: false, strokeDasharray: '0' };

/** Bars: thin, rounded data end, a surface-coloured gap between neighbours. */
export const barProps = (isMobile, { horizontal = false } = {}) => ({
  radius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
  maxBarSize: isMobile ? 18 : 28,
  stroke: colors.surface1,
  strokeWidth: 2,
});

export const lineProps = {
  strokeWidth: 2,
  dot: false,
  activeDot: { r: 5, strokeWidth: 2, stroke: colors.surface1 },
};

/** Compact number formatters for ticks. */
export const fmt = {
  int: (v) => (v == null || Number.isNaN(v) ? '' : Math.round(v).toString()),
  one: (v) => (v == null || Number.isNaN(v) ? '' : Number(v).toFixed(1)),
  pct: (v) => (v == null || Number.isNaN(v) ? '' : `${Math.round(v)}%`),
  signed: (v) => (v == null || Number.isNaN(v) ? '' : `${v > 0 ? '+' : ''}${Number(v).toFixed(1)}`),
};

/** Below this many balls a value is shown muted and flagged "small sample". */
export const MIN_BALLS = 30;
