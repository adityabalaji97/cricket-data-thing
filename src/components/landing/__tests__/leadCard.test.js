import { ratingsFrame, todaysPost } from '../LeadCard';
import { currentSides, ratingsClaim } from '../TeamRatings';

jest.mock('react-router-dom', () => ({ Link: () => null }), { virtual: true });
jest.mock('axios', () => ({ get: jest.fn(), post: jest.fn() }));

test("the newest post planned for today or yesterday (IST) leads", () => {
  const posts = [{ id: 'a', planned_for: '2026-11-24' }, { id: 'b', planned_for: '2026-11-23' }];
  // 20:00 UTC on the 23rd is 01:30 IST on the 24th.
  expect(todaysPost(posts, Date.parse('2026-11-23T20:00:00Z'))?.id).toBe('a');
  expect(todaysPost(posts, Date.parse('2026-11-23T12:00:00Z'))?.id).toBe('b');
  expect(todaysPost(posts, Date.parse('2026-11-26T12:00:00Z'))).toBeNull();
  expect(todaysPost(undefined)).toBeNull();
});

test('a post planned for yesterday and marked after midnight still leads', () => {
  // 00:30 IST on the 25th: yesterday's post (planned the 24th) is the newest.
  const posts = [{ id: 'late', planned_for: '2026-11-24' }, { id: 'older', planned_for: '2026-11-20' }];
  expect(todaysPost(posts, Date.parse('2026-11-24T19:00:00Z'))?.id).toBe('late');
  // Two days on, it has gone stale.
  expect(todaysPost(posts, Date.parse('2026-11-26T06:00:00Z'))).toBeNull();
});

test('the ratings are framed by the auction until it happens', () => {
  expect(ratingsFrame(Date.parse('2026-11-24T06:00:00Z'))).toEqual({ kicker: 'IPL 2027 · auction 16\u00a0Dec', context: 'auction' });
  expect(ratingsFrame(Date.parse('2026-12-16T06:00:00Z')).kicker).toBe('IPL 2027 · auction today');
  expect(ratingsFrame(Date.parse('2026-12-17T06:00:00Z'))).toEqual({ kicker: 'IPL team ratings', context: null });
});

test('the auction claim names sides by city', () => {
  const sides = currentSides([
    { team_name: 'Royal Challengers Bengaluru', team_abbreviation: 'RCB', current_elo: 1626, last_match_date: '2026-05-31' },
    { team_name: 'Mumbai Indians', team_abbreviation: 'MI', current_elo: 1468, last_match_date: '2026-05-24' },
  ], 'ipl');
  expect(ratingsClaim(sides, 'ipl', 'auction')).toBe('Bengaluru go into the auction as the top-rated side. Mumbai are 2nd of 2.');
});
