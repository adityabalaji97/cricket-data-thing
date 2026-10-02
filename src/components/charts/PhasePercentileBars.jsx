import React from 'react';
import DivergingBars from './DivergingBars';

const PHASES = [['powerplay', 'Powerplay'], ['middle_overs', 'Middle'], ['death_overs', 'Death']];

const ordinal = (n) => {
  const v = Math.round(n);
  const s = ['th', 'st', 'nd', 'rd'];
  const m = v % 100;
  return `${v}${s[(m - 20) % 10] || s[m] || s[0]}`;
};

/**
 * Team percentiles by phase as bars either side of the median (50th). Replaced the team phase
 * radars: 6-9 vertices with a rotated 0-100 axis at 10px, and missing phases silently drawn at 50.
 * Percentiles here are already oriented so higher = better (bowling ones are inverted upstream).
 *
 * metrics: [{ key: 'normalized_strike_rate', label: 'Strike rate' }, ...]
 */
const PhasePercentileBars = ({ phaseStats, metrics, ariaLabel }) => {
  const rows = [];
  PHASES.forEach(([key, name]) => {
    const p = phaseStats?.[key];
    if (!p || !p.balls) return;
    metrics.forEach((m) => {
      const v = p[m.key];
      if (v === null || v === undefined) return;
      rows.push({ key: `${key}-${m.key}`, group: name, label: m.label, value: Number(v) - 50, pct: Number(v) });
    });
  });
  if (!rows.length) return null;
  return (
    <DivergingBars
      ariaLabel={ariaLabel}
      rows={rows}
      format={(v) => ordinal(v + 50)}
      labelWidth={84}
    />
  );
};

export default PhasePercentileBars;
