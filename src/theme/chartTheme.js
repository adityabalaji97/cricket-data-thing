/**
 * Shared chart styling for the dark theme.
 *
 * Recharts renders SVG and sets colours as presentation attributes, which any CSS rule
 * overrides — so its axes, grid, legend and default tooltip are restyled once, globally, in
 * src/index.css (the `.recharts-*` block) rather than per chart. Note CSS also beats colours
 * passed as Recharts props (tick={{ fill }}, stroke=...), which were almost all light-theme greys;
 * a chart that genuinely needs a custom axis colour must set it through the `style` prop.
 *
 * ECharts renders to canvas, which CSS cannot reach, so it gets a registered theme. Pass
 * `theme={ECHARTS_THEME}` to <ReactECharts>.
 */
import * as echarts from 'echarts';
import { colors, fonts } from './hindsightDark';

export const ECHARTS_THEME = 'hindsight';

const axisCommon = {
  axisLine: { lineStyle: { color: colors.borderStrong } },
  axisTick: { lineStyle: { color: colors.borderStrong } },
  axisLabel: { color: colors.textLo },
  splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
  nameTextStyle: { color: colors.textLo },
};

echarts.registerTheme(ECHARTS_THEME, {
  backgroundColor: 'transparent',
  textStyle: { color: colors.textMed, fontFamily: fonts.body },
  title: { textStyle: { color: colors.textHi }, subtextStyle: { color: colors.textLo } },
  legend: { textStyle: { color: colors.textMed } },
  tooltip: {
    backgroundColor: colors.surface2,
    borderColor: colors.borderStrong,
    textStyle: { color: colors.textHi },
  },
  categoryAxis: axisCommon,
  valueAxis: axisCommon,
  logAxis: axisCommon,
  timeAxis: axisCommon,
  radar: {
    axisName: { color: colors.textLo },
    axisLine: { lineStyle: { color: colors.borderStrong } },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
  },
});

/** Props for Recharts tooltips that set their own content styles. */
export const rechartsTooltipProps = {
  contentStyle: {
    backgroundColor: colors.surface2,
    border: `1px solid ${colors.borderStrong}`,
    borderRadius: 8,
    color: colors.textHi,
  },
  labelStyle: { color: colors.textHi },
  itemStyle: { color: colors.textMed },
  cursor: { fill: 'rgba(255,255,255,0.04)' },
};
