import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import VenueBoundaryShape from './VenueBoundaryShape';

describe('VenueBoundaryShape', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('renders confidence and warning chips from API response', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        quality: {
          fours_total: 1200,
          nonzero_rate: 0.71,
        },
        sample: {
          matches_used: 42,
        },
        summary: {
          mean_boundary_r: 183.8,
          relative_sd: 0.034,
        },
        confidence: {
          confidence_score: 82.1,
          warning_flags: ['LOW_SAMPLE'],
        },
        diagnostics: {
          surface_regime_signal: 'single_likely',
          reason: 'Inter-match contour volatility is moderate for this venue sample.',
        },
        profile_bins: [
          { angle_bin: 0, angle_mid_deg: 7.5, r_median: 180, r_iqr: 6, bin_coverage_pct: 95 },
          { angle_bin: 1, angle_mid_deg: 22.5, r_median: 182, r_iqr: 7, bin_coverage_pct: 92 },
          { angle_bin: 2, angle_mid_deg: 37.5, r_median: 184, r_iqr: 8, bin_coverage_pct: 90 },
        ],
      }),
    });

    render(
      <VenueBoundaryShape
        venue="Wankhede Stadium, Mumbai"
        startDate="2024-01-01"
        endDate="2026-03-07"
        leagues={['IPL']}
        includeInternational={false}
        topTeams={null}
        isMobile={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Confidence 82.1\/100/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Matches used 42/i)).toBeInTheDocument();
    expect(screen.getByText(/LOW_SAMPLE/i)).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'boom' }),
    });

    render(
      <VenueBoundaryShape
        venue="Test Venue"
        startDate="2024-01-01"
        endDate="2026-03-07"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/boom/i)).toBeInTheDocument();
    });
  });
});
