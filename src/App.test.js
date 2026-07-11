import { fireEvent, render, screen } from '@testing-library/react';
import LandingPage from './components/LandingPage';

jest.mock('react-router-dom', () => {
  const React = require('react');
  return {
    Link: React.forwardRef(({ children, to, ...props }, ref) => (
      <a ref={ref} href={typeof to === 'string' ? to : '#'} {...props}>{children}</a>
    )),
    useNavigate: () => jest.fn(),
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
        mode: 'filtered',
        competition: 'Indian Premier League',
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
          'Indian Premier League': {
            competition: 'Indian Premier League',
            competition_key: 'Indian Premier League',
            competition_display: 'IPL',
            match_count: 1,
            latest_date: '2026-07-10',
          },
        },
        filters: [{ key: 'Indian Premier League', label: 'IPL', latest_date: '2026-07-10' }],
        filter_options: {
          competitions: [{ key: 'Indian Premier League', label: 'IPL', latest_date: '2026-07-10' }],
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
  render(<LandingPage />);

  expect(await screen.findByText("Today's Matches")).toBeInTheDocument();
  expect(screen.getByText('Recent Matches')).toBeInTheDocument();
  expect(screen.getByText('Recent Standout Innings')).toBeInTheDocument();
  expect(screen.getByText('ELO Team Rankings')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /explore/i }));

  expect(screen.getByText('Hindsight tools')).toBeInTheDocument();
  expect(screen.getByText('Batter Profiles')).toBeInTheDocument();
  expect(screen.getByText('Query Builder')).toBeInTheDocument();
});
