import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import Matchups from '../Matchups';
import { postAnalyticsJson } from '../../utils/analyticsApi';

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
  get: jest.fn(),
}));
jest.mock('../../utils/analyticsApi', () => {
  const actual = jest.requireActual('../../utils/analyticsApi');
  return {
    ...actual,
    postAnalyticsJson: jest.fn(),
  };
});
const mockedAxios = require('axios').default;

const matchupPayload = {
  venue: 'Wankhede Stadium',
  team1: {
    name: 'CSK',
    players: ['Batter A', 'Bowler X'],
    batting_matchups: {
      'Batter A': {
        'Bowler Y': {
          runs: 24,
          wickets: 1,
          balls: 16,
          strike_rate: 150,
          average: 24,
          dot_percentage: 25,
          boundary_percentage: 31,
        },
        Overall: {
          runs: 40,
          wickets: 1,
          balls: 28,
          strike_rate: 142.9,
          average: 40,
          dot_percentage: 28,
          boundary_percentage: 26,
        },
      },
    },
    bowling_consolidated: {
      'Bowler X': {
        runs: 20,
        wickets: 2,
        balls: 18,
        economy: 6.67,
        average: 10,
        strike_rate: 9,
        dot_percentage: 42,
        boundary_percentage: 14,
      },
    },
  },
  team2: {
    name: 'MI',
    players: ['Batter B', 'Bowler Y'],
    batting_matchups: {
      'Batter B': {
        'Bowler X': {
          runs: 18,
          wickets: 2,
          balls: 20,
          strike_rate: 90,
          average: 9,
          dot_percentage: 35,
          boundary_percentage: 16,
        },
        Overall: {
          runs: 34,
          wickets: 3,
          balls: 36,
          strike_rate: 94.4,
          average: 11.3,
          dot_percentage: 39,
          boundary_percentage: 15,
        },
      },
    },
    bowling_consolidated: {
      'Bowler Y': {
        runs: 22,
        wickets: 2,
        balls: 24,
        economy: 5.5,
        average: 11,
        strike_rate: 12,
        dot_percentage: 46,
        boundary_percentage: 10,
      },
    },
  },
  fantasy_analysis: {
    top_fantasy_picks: [
      {
        player_name: 'Batter A',
        role: 'batting',
        expected_points: 58.4,
        confidence: 0.86,
        projected_balls: 22,
        balls_cap: 24,
        uncapped_balls: 37,
      },
      {
        player_name: 'Bowler Y',
        role: 'bowling',
        expected_points: 54.1,
        confidence: 0.79,
      },
    ],
  },
};

const buildRollingFormPayload = (playerName) => {
  if (playerName === 'Batter A') {
    return { form_flag: 'hot' };
  }
  if (playerName === 'Bowler Y') {
    return { form_flag: 'cold' };
  }
  return { form_flag: 'neutral' };
};

describe('Matchups analytics overlays', () => {
  beforeEach(() => {
    mockedAxios.get.mockResolvedValue({ data: matchupPayload });
    postAnalyticsJson.mockImplementation(async (_path, payload) => {
      const flags = {};
      (payload?.player_names || []).forEach((name) => {
        flags[name] = buildRollingFormPayload(name).form_flag;
      });
      return { flags };
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows form badges in fantasy picks and matchup labels and uses player route for bowler links', async () => {
    render(
      <Matchups
        team1="CSK"
        team2="MI"
        startDate="2025-01-01"
        endDate="2026-03-31"
        isMobile={false}
        enabled
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/Fantasy Analysis - Top Picks/i)).toBeInTheDocument();
    });

    expect(screen.queryByText('22.0/24.0')).not.toBeInTheDocument();

    const bowlerLink = screen.getByRole('link', { name: 'Bowler Y' });
    expect(bowlerLink.getAttribute('href')).toContain('/player?');
    expect(bowlerLink.getAttribute('href')).toContain('tab=bowling');

    expect(postAnalyticsJson).toHaveBeenCalledWith(
      '/players/form-flags',
      expect.objectContaining({
        player_names: expect.arrayContaining(['Batter A', 'Bowler Y']),
      }),
    );
  });
});
