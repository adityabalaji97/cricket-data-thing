import { currentSides, ratingsClaim } from '../TeamRatings';

jest.mock('react-router-dom', () => ({ Link: () => null }), { virtual: true });

const row = (team_name, team_abbreviation, current_elo, last_match_date) => ({ team_name, team_abbreviation, current_elo, last_match_date });

test('IPL: renamed sides count once at their latest, defunct sides go, ranks restart', () => {
  const sides = currentSides([
    row('Royal Challengers Bangalore', 'RCB', 1700, '2023-05-21'),
    row('Royal Challengers Bengaluru', 'RCB', 1626, '2026-05-31'),
    row('Rising Pune Supergiants', 'RPSG', 1690, '2017-05-21'),
    row('Kochi Tuskers Kerala', 'Kochi Tuskers Kerala', 1650, '2011-05-20'),
    row('Mumbai Indians', 'MI', 1468, '2026-05-20'),
    row('Kings XI Punjab', 'PBKS', 1400, '2020-11-01'),
    row('Punjab Kings', 'PBKS', 1506, '2026-05-25'),
  ], 'ipl');
  expect(sides.map((s) => [s.rank, s.abbr, s.rating])).toEqual([[1, 'RCB', 1626], [2, 'PBKS', 1506], [3, 'MI', 1468]]);
  expect(sides[2].page).toBe('MI');
});

test('internationals: the top 12 only, short codes, the country name for the team page', () => {
  const sides = currentSides([row('India', 'India', 1656, '2026-09-01'), row('Nepal', 'Nepal', 1700, '2026-09-01'),
    row('South Africa', 'South Africa', 1603, '2026-09-01')], 'intl');
  expect(sides.map((s) => s.abbr)).toEqual(['IND', 'SA']);
  expect(sides[1].page).toBe('South Africa');
});

test('the claim names the leader and the last', () => {
  const sides = currentSides([row('Mumbai Indians', 'MI', 1468, '2026-05-20'), row('Royal Challengers Bengaluru', 'RCB', 1626, '2026-05-31')], 'ipl');
  expect(ratingsClaim(sides, 'ipl')).toBe('Bengaluru are the top-rated IPL side. Mumbai are 2nd of 2.');
});
