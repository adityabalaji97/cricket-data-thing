import React from 'react';
import { render, screen } from '@testing-library/react';

import BattingScatterChart from '../BattingScatterChart';

// Recharts' ResponsiveContainer needs ResizeObserver, which jsdom lacks.
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const rows = [
  { name: 'Average Batter', batting_team: '', innings: 10, total_runs: 300, avg: 30, sr: 135, dot_percent: 35, boundary_percent: 15 },
  { name: 'V Kohli', batting_team: 'RCB', innings: 12, total_runs: 520, avg: 47.3, sr: 141.2, dot_percent: 30, boundary_percent: 17 },
];

describe('BattingScatterChart', () => {
  it('renders once data arrives after an empty first render', () => {
    const { rerender } = render(<BattingScatterChart data={[]} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();

    // Used to throw "Rendered more hooks than during the previous render" because
    // useMemo sat behind the empty-data early return.
    rerender(<BattingScatterChart data={rows} />);
    expect(screen.getByText('Batting Performance Analysis')).toBeInTheDocument();
  });

  it('falls back to the empty state when data is cleared', () => {
    const { rerender } = render(<BattingScatterChart data={rows} />);
    rerender(<BattingScatterChart data={[]} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });
});
