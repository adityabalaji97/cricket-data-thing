import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import TeamRelativeMetricsSection from '../TeamRelativeMetricsSection';

const payload = {
  benchmark_window_matches: 10,
  effective_start_date: '2025-01-01',
  innings_1: {
    batting: {
      innings_count: 9,
      strike_rate: { value: 149.3, percentile: 72.1 },
      avg_runs: { value: 34.2, percentile: 68.7 },
    },
    bowling: {
      innings_count: 9,
      economy: { value: 7.15, percentile: 79.3 },
      wickets_per_innings: { value: 1.46, percentile: 74.9 },
    },
  },
  innings_2: {
    batting: {
      innings_count: 8,
      strike_rate: { value: 156.7, percentile: 78.5 },
      avg_runs: { value: 31.5, percentile: 63.4 },
    },
    bowling: {
      innings_count: 8,
      economy: { value: 8.05, percentile: 58.2 },
      wickets_per_innings: { value: 1.21, percentile: 60.1 },
    },
  },
};

describe('TeamRelativeMetricsSection', () => {
  it('renders innings cards and expands details on demand', () => {
    render(
      <TeamRelativeMetricsSection
        data={payload}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText(/Innings 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Innings 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Benchmark: 10 matches/i)).toBeInTheDocument();
    expect(screen.getByText(/Batting \(innings: 9\)/i)).not.toBeVisible();

    userEvent.click(screen.getByRole('button', { name: /Show details/i }));

    expect(screen.getByText(/Batting \(innings: 9\)/i)).toBeVisible();
    expect(screen.getByText(/Bowling \(innings: 8\)/i)).toBeVisible();
    screen.getAllByText(/Metric/i).forEach((node) => {
      expect(node).toBeVisible();
    });
  });

  it('shows retry state when no payload and endpoint fails', () => {
    const onRetry = jest.fn();

    render(
      <TeamRelativeMetricsSection
        data={null}
        loading={false}
        error="Failed to load relative metrics."
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText(/Failed to load relative metrics\./i)).toBeInTheDocument();
    userEvent.click(screen.getByRole('button', { name: /Retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
