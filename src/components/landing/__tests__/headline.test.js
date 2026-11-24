import { isHeadline } from '../../LandingPage';

jest.mock('react-router-dom', () => ({ Link: () => null, useNavigate: () => () => {} }), { virtual: true });
jest.mock('axios', () => ({ get: jest.fn(), post: jest.fn() }));

const m = (team1, team2, series) => ({ team1, team2, series });

test('India, men or women, always headline', () => {
  expect(isHeadline(m('India', 'New Zealand', 'New Zealand tour of India'))).toBe(true);
  expect(isHeadline(m('India Women', 'Australia Women', "Women's T20 World Cup"))).toBe(true);
});

test('major leagues and events headline; other bilaterals get the row', () => {
  expect(isHeadline(m('Mumbai Indians', 'Chennai Super Kings', 'Indian Premier League'))).toBe(true);
  expect(isHeadline(m('Sydney Sixers', 'Perth Scorchers', 'Big Bash League'))).toBe(true);
  expect(isHeadline(m('Australia', 'England', 'England tour of Australia'))).toBe(false);
  expect(isHeadline(m('Gulf Giants', 'MI Emirates', 'International League T20'))).toBe(false);
});

test('qualifiers and women\'s events without India do not', () => {
  expect(isHeadline(m('Nepal', 'Oman', 'ICC Men\'s T20 World Cup Asia Qualifier'))).toBe(false);
  expect(isHeadline(m('Australia Women', 'England Women', "Women's T20 World Cup"))).toBe(false);
  expect(isHeadline(m('Sydney Sixers Women', 'Perth Scorchers Women', "Women's Big Bash League"))).toBe(false);
});
