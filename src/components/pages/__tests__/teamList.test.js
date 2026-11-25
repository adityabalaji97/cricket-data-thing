import { groupOrder } from '../TeamList';

// react-router v7 doesn't resolve under this Jest setup (as in the landing tests).
jest.mock('react-router-dom', () => ({ Link: () => null, useLocation: () => ({}), useNavigate: () => () => {} }), { virtual: true });

test('the IPL leads by default and from the IPL tab', () => {
  expect(groupOrder('')).toEqual(['ipl', 'intl']);
  expect(groupOrder('?league=IPL')).toEqual(['ipl', 'intl']);
  expect(groupOrder('?league=Indian+Premier+League')).toEqual(['ipl', 'intl']);
});

test('T20Is lead from the T20Is tab', () => {
  expect(groupOrder('?scope=t20i')).toEqual(['intl', 'ipl']);
  expect(groupOrder('?scope=T20I')).toEqual(['intl', 'ipl']);
});
