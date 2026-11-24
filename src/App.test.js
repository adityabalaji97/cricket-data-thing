import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import LandingPage from './components/LandingPage';
import { FormatProvider } from './context/FormatContext';

// ChartExportButton imports axios, which ships as ESM that Jest doesn't transform.
jest.mock('axios', () => ({ get: jest.fn(), post: jest.fn() }));

// react-router-dom 7 ships ES modules Jest can't resolve; plain anchors stand in for Link.
jest.mock('react-router-dom', () => {
  const React = require('react');
  return {
    Link: React.forwardRef(({ children, to, ...props }, ref) => (
      <a ref={ref} href={typeof to === 'string' ? to : '#'} {...props}>{children}</a>
    )),
    useNavigate: () => jest.fn(),
    useLocation: () => ({ pathname: '/', search: '', hash: '' }),
  };
}, { virtual: true });

const mockResponse = (payload) => Promise.resolve({
  ok: true,
  json: () => Promise.resolve(payload),
});

beforeEach(() => {
  window.matchMedia = window.matchMedia || (() => ({
    matches: false,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    addListener: jest.fn(),
    removeListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));

  global.fetch = jest.fn((url) => {
    const target = String(url);
    if (target.includes('/fixtures/upcoming')) {
      return mockResponse([]);
    }
    if (target.includes('/recent-matches/discover')) {
      return mockResponse({
        mode: 'grouped',
        competition: 'all',
        matches: [{
          match_id: 'match-1',
          date: '2026-07-10',
          venue: 'Eden Gardens',
          team1: 'KKR',
          team2: 'CSK',
          team1_full: 'Kolkata Knight Riders',
          team2_full: 'Chennai Super Kings',
          winner: 'KKR',
          competition_abbr: 'IPL',
          innings1_score: '189/4 (20.0)',
          innings2_score: '172/8 (20.0)',
          result_text: 'KKR won by 17 runs',
        }],
        competition_stats: {
          IPL: {
            competition: 'IPL',
            competition_key: 'IPL',
            competition_display: 'IPL',
            match_count: 1,
            latest_date: '2026-07-10',
          },
        },
        filters: [
          { key: 'all', label: 'All', match_count: 1 },
          { key: 'IPL', label: 'IPL', latest_date: '2026-07-10' },
        ],
        filter_options: {
          competitions: [
            { key: 'all', label: 'All', match_count: 1 },
            { key: 'IPL', label: 'IPL', latest_date: '2026-07-10' },
          ],
          teams: [{ value: 'KKR', label: 'KKR' }, { value: 'CSK', label: 'CSK' }],
        },
      });
    }
    if (target.includes('/landing/featured-innings')) {
      return mockResponse([]);
    }
    if (target.includes('/teams/elo-rankings')) {
      return mockResponse({ rankings: [] });
    }
    return mockResponse({});
  });
});

test('renders redesigned landing sections and explore drawer', async () => {
  render(<FormatProvider><LandingPage /></FormatProvider>);

  expect(await screen.findByText("Today's Matches")).toBeInTheDocument();
  // L1: the promise and the ask box come first.
  expect(screen.getByText('Hindsight shows you why.')).toBeInTheDocument();
  expect(screen.getByRole('searchbox', { name: /ask a cricket question/i })).toBeInTheDocument();
  const chips = screen.getAllByRole('link').filter((a) => (a.getAttribute('href') || '').startsWith('/query?'));
  expect(chips).toHaveLength(2);
  chips.forEach((a) => expect(a.getAttribute('href')).not.toContain('nl='));
  expect(screen.getByText('Recent Matches')).toBeInTheDocument();
  expect(screen.getByText('Recent Standout Innings')).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: 'IPL' })).toBeInTheDocument();

  await waitFor(() => {
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('competition=all'));
  });

  fireEvent.click(screen.getByRole('button', { name: /explore/i }));

  expect(screen.getByText('Hindsight tools')).toBeInTheDocument();
  expect(screen.getByText('Himanish Ganjoo & TechRadar')).toBeInTheDocument();
  expect(screen.getByText('@himganj153')).toBeInTheDocument();
});

test('a failed fixtures request shows an error with a retry, not "No match today"', async () => {
  const ok = global.fetch.getMockImplementation();
  let fail = true;
  global.fetch.mockImplementation((url) => (String(url).includes('/fixtures/upcoming') && fail
    ? Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({}) })
    : ok(url)));
  render(<FormatProvider><LandingPage /></FormatProvider>);

  expect(await screen.findByText("Couldn't load the fixtures.")).toBeInTheDocument();
  expect(screen.queryByText(/No match today/)).not.toBeInTheDocument();

  fail = false;
  fireEvent.click(screen.getAllByRole('button', { name: 'Try again' })[0]);
  await waitFor(() => expect(screen.queryByText("Couldn't load the fixtures.")).not.toBeInTheDocument());
});
