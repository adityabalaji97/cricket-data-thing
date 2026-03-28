import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';

import FantasyPlanner from '../FantasyPlanner';

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

const FIXTURES = [
  { match_num: 1, date: '2099-01-01', team1: 'RCB', team2: 'SRH', venue: 'Bengaluru' },
  { match_num: 2, date: '2099-01-02', team1: 'MI', team2: 'KKR', venue: 'Mumbai' },
  { match_num: 3, date: '2099-01-03', team1: 'RR', team2: 'CSK', venue: 'Jaipur' },
  { match_num: 4, date: '2099-01-04', team1: 'PBKS', team2: 'GT', venue: 'Chandigarh' },
  { match_num: 5, date: '2099-01-05', team1: 'LSG', team2: 'DC', venue: 'Lucknow' },
];

const ALL_PLAYERS = [
  { name: 'Legacy Player', team: 'RCB', role: 'BAT', credits: 8.5 },
  { name: 'Virat Kohli', team: 'RCB', role: 'BAT', credits: 9.0 },
  { name: 'Jasprit Bumrah', team: 'MI', role: 'BOWL', credits: 9.0 },
];

const buildRecommendedSquad = () => (
  Array.from({ length: 11 }, (_, idx) => ({
    name: `Filler ${idx + 1}`,
    team: idx % 2 === 0 ? 'MI' : 'CSK',
    role: idx === 0 ? 'WK' : idx < 6 ? 'BAT' : idx < 8 ? 'AR' : 'BOWL',
    credits: 8.0,
    total_expected_points: 30 + idx,
    match_count: 3,
    matches: [],
  }))
);

const buildRecommendations = (matchesAhead = 3, recommendedSquad = buildRecommendedSquad()) => ({
  points_model: 'per_match_normalized_v1',
  recommended_squad: recommendedSquad,
  all_players: recommendedSquad.map((player) => ({
    name: player.name,
    team: player.team,
    role: player.role,
    credits: player.credits,
    total_expected_points: player.total_expected_points,
    match_count: player.match_count,
  })),
  captain: recommendedSquad[0]?.name || null,
  vice_captain: recommendedSquad[1]?.name || null,
  transfers_needed: 0,
  match_details: Array.from({ length: matchesAhead }, (_, idx) => ({
    match_num: idx + 1,
    team1: FIXTURES[idx].team1,
    team2: FIXTURES[idx].team2,
    player_points: [
      { name: `P${idx + 1}-A`, team: FIXTURES[idx].team1, expected_points: 42.3 },
      { name: `P${idx + 1}-B`, team: FIXTURES[idx].team2, expected_points: 37.8 },
    ],
  })),
});

const setupAxios = ({ recommendationHandler, allPlayers = ALL_PLAYERS }) => {
  axios.get.mockImplementation((url, requestConfig = {}) => {
    if (url.includes('/fantasy-planner/schedule')) {
      return Promise.resolve({ data: { fixtures: FIXTURES } });
    }
    if (url.includes('/fantasy-planner/all-players')) {
      return Promise.resolve({ data: { total: allPlayers.length, players: allPlayers } });
    }
    if (url.includes('/fantasy-planner/recommendations')) {
      return recommendationHandler(requestConfig.params || {});
    }
    if (url.includes('/fantasy-planner/transfer-plan')) {
      return Promise.resolve({ data: { plan: [] } });
    }
    return Promise.reject(new Error(`Unhandled URL in test: ${url}`));
  });
};

describe('FantasyPlanner', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('retries recommendations on first load and renders top picks after recovery', async () => {
    let recommendationAttempts = 0;
    setupAxios({
      recommendationHandler: (params) => {
        recommendationAttempts += 1;
        if (recommendationAttempts < 3) {
          return Promise.reject({ response: { status: 503, data: { detail: 'Temporary outage' } } });
        }
        return Promise.resolve({ data: buildRecommendations(params.matches_ahead || 3) });
      },
    });

    render(<FantasyPlanner isMobile={false} />);

    await waitFor(() => {
      expect(screen.getByText(/P1-A/i)).toBeInTheDocument();
      expect(screen.getByText(/P2-A/i)).toBeInTheDocument();
      expect(screen.getByText(/P3-A/i)).toBeInTheDocument();
    });

    expect(recommendationAttempts).toBe(3);
    expect(screen.queryByText(/Failed to fetch recommendations/i)).not.toBeInTheDocument();
  });

  it('shows an error after recommendation retries are exhausted', async () => {
    let recommendationAttempts = 0;
    setupAxios({
      recommendationHandler: () => {
        recommendationAttempts += 1;
        return Promise.reject({ response: { status: 504, data: { detail: 'Gateway timeout' } } });
      },
    });

    render(<FantasyPlanner isMobile={false} />);

    await waitFor(() => {
      expect(screen.getByText(/Gateway timeout/i)).toBeInTheDocument();
    });

    expect(recommendationAttempts).toBe(3);
  });

  it('renders exactly matchesAhead fixtures and updates to 5 with projections', async () => {
    const recommendationCalls = [];
    setupAxios({
      recommendationHandler: (params) => {
        recommendationCalls.push(params.matches_ahead);
        return Promise.resolve({ data: buildRecommendations(params.matches_ahead || 3) });
      },
    });

    render(<FantasyPlanner isMobile={false} />);

    await waitFor(() => {
      expect(screen.getByText(/Match 3/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Match 4/i)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/P3-A/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Matches ahead/i), { target: { value: '5' } });

    await waitFor(() => {
      expect(screen.getByText(/Match 5/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/P5-A/i)).toBeInTheDocument();
    });
    expect(recommendationCalls).toContain(5);
  });

  it('keeps manually selected players when auto-pick fills the rest of the squad', async () => {
    let autoPickParams = null;
    setupAxios({
      recommendationHandler: (params) => {
        if (params.current_team) {
          autoPickParams = params;
        }
        const recommended = buildRecommendedSquad();
        return Promise.resolve({ data: buildRecommendations(params.matches_ahead || 3, recommended) });
      },
    });

    render(<FantasyPlanner isMobile={false} />);

    const addPlayerInput = await screen.findByLabelText(/Add player/i);
    await userEvent.click(addPlayerInput);
    await userEvent.type(addPlayerInput, 'Legacy');
    await userEvent.click(await screen.findByText(/Legacy Player \(RCB\) - 8.5 cr/i));

    await waitFor(() => {
      expect(screen.getByText('Legacy Player')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Auto-pick/i }));

    await waitFor(() => {
      expect(screen.getByText(/Squad \(11\/11\)/i)).toBeInTheDocument();
    });

    expect(autoPickParams.current_team).toContain('Legacy Player');
    expect(screen.getByText('Legacy Player')).toBeInTheDocument();
    expect(screen.getAllByText('Filler 1').length).toBeGreaterThan(0);
  });
});
