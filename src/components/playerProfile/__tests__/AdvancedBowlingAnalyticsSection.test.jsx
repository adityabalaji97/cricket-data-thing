import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import AdvancedBowlingAnalyticsSection from '../AdvancedBowlingAnalyticsSection';
import { clearAnalyticsCache } from '../../../utils/analyticsApi';

const buildResponse = (payload) => Promise.resolve({
  ok: true,
  json: async () => payload,
});

const mockEndpointFetch = ({
  contextPayload,
  formPayload,
  relativePayload,
  batterLeaderboard,
  bowlerLeaderboard,
}) => {
  global.fetch = jest.fn((url) => {
    if (url.includes('/bowling-context')) {
      return buildResponse(contextPayload);
    }
    if (url.includes('/rolling-form')) {
      return buildResponse(formPayload);
    }
    if (url.includes('/relative-metrics/player/')) {
      return buildResponse(relativePayload);
    }
    if (url.includes('/leaderboards/first-ball-boundaries') && url.includes('role=batter')) {
      return buildResponse(batterLeaderboard);
    }
    if (url.includes('/leaderboards/first-ball-boundaries') && url.includes('role=bowler')) {
      return buildResponse(bowlerLeaderboard);
    }
    return Promise.reject(new Error(`Unhandled URL in test: ${url}`));
  });
};

const defaultPayloads = () => ({
  contextPayload: {
    total_overs_analyzed: 20,
    insufficient_sample: true,
    resolved_names: {
      legacy_name: 'Test Bowler',
      details_name: 'Test Bowler',
    },
    previous_over_pressure_stats: {
      threshold_runs: 10,
      high_pressure: { economy: 9.8, wickets_per_over: 0.15, boundary_pct: 20.0 },
      low_pressure: { economy: 7.0, wickets_per_over: 0.4, boundary_pct: 11.0 },
    },
    spell_stats: {
      first_spell: { economy: 8.7, wickets_per_over: 0.2 },
      later_spells: { economy: 7.6, wickets_per_over: 0.4 },
    },
    first_ball_last_ball_stats: {
      first_ball_boundary_rate_pct: 18.0,
      last_ball_boundary_rate_pct: 11.0,
      overall_boundary_rate_pct: 14.0,
    },
  },
  formPayload: {
    form_flag: 'hot',
    bowling_innings: [
      {
        match_id: '1',
        date: '2026-04-01',
        wickets: 2,
        economy: 6.0,
        rolling_fantasy_points_avg: 53.4,
      },
    ],
  },
  relativePayload: {
    benchmark_window_matches: 10,
    effective_start_date: '2025-01-01',
    innings_1: {
      bowling: {
        wickets_per_innings: { value: 1.2, percentile: 62.4 },
        economy: { value: 7.5, percentile: 71.1 },
        bowling_strike_rate: { value: 18.2, percentile: 65.5 },
        fantasy_points_avg: { value: 39.0, percentile: 68.0 },
      },
    },
    innings_2: {
      bowling: {
        wickets_per_innings: { value: 1.1, percentile: 57.2 },
        economy: { value: 7.9, percentile: 63.0 },
        bowling_strike_rate: { value: 20.1, percentile: 58.2 },
        fantasy_points_avg: { value: 35.2, percentile: 60.4 },
      },
    },
  },
  batterLeaderboard: {
    leaderboard: [
      { player: 'Priyansh Arya', boundary_rate_pct: 36.92, wicket_rate_pct: 6.15, first_balls: 65 },
      { player: 'Suryakumar Yadav', boundary_rate_pct: 29.85, wicket_rate_pct: 2.99, first_balls: 67 },
    ],
  },
  bowlerLeaderboard: {
    leaderboard: [
      { rank: 42, player: 'Test Bowler', boundary_rate_pct: 14.3 },
    ],
  },
});

describe('AdvancedBowlingAnalyticsSection', () => {
  const baseProps = {
    playerName: 'Test Bowler',
    dateRange: { start: '2025-01-01', end: '2026-12-31' },
    selectedVenue: 'All Venues',
    competitionFilters: { leagues: [], international: false },
    isMobile: false,
    enabled: true,
  };

  beforeEach(() => {
    clearAnalyticsCache();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('renders analytics blocks and insufficient-sample warning', async () => {
    mockEndpointFetch(defaultPayloads());

    render(<AdvancedBowlingAnalyticsSection {...baseProps} />);

    await waitFor(() => {
      expect(screen.getByText(/Form: HOT/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Insufficient sample for stable contextual splits/i)).toBeInTheDocument();
    expect(screen.getByText(/High Pressure/i)).toBeInTheDocument();
    expect(screen.getByText(/Rolling Form \(window: 10 innings\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Player bowler rank: #42/i)).toBeInTheDocument();
    expect(screen.getByText(/Priyansh Arya/i)).toBeInTheDocument();
  });

  it('re-fetches when filter params change and includes new query params', async () => {
    mockEndpointFetch(defaultPayloads());

    const { rerender } = render(<AdvancedBowlingAnalyticsSection {...baseProps} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(5);
    });

    rerender(
      <AdvancedBowlingAnalyticsSection
        {...baseProps}
        dateRange={{ start: '2025-02-01', end: '2026-12-31' }}
      />,
    );

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(10);
    });

    const requestedUrls = global.fetch.mock.calls.map((call) => call[0]);
    expect(requestedUrls.some((url) => url.includes('start_date=2025-02-01'))).toBe(true);
  });

  it('uses cache on section reopen for identical params', async () => {
    mockEndpointFetch(defaultPayloads());

    const { rerender } = render(<AdvancedBowlingAnalyticsSection {...baseProps} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(5);
    });

    rerender(<AdvancedBowlingAnalyticsSection {...baseProps} enabled={false} />);
    rerender(<AdvancedBowlingAnalyticsSection {...baseProps} enabled />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(5);
    });
  });
});
