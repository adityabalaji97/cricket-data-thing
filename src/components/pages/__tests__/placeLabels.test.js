import { placeLabels } from '../ComparePage';

jest.mock('react-router-dom', () => ({ Link: () => null, useLocation: () => ({ search: '' }), useNavigate: () => () => {} }), { virtual: true });

const W = 343;
const noOverlap = ([a, b], [wa]) => a + wa <= b;

test('far apart: each label centred on its dot', () => {
  const [l1, l2] = placeLabels([80, 260], [60, 60], W);
  expect(l1).toBe(50);
  expect(l2).toBe(230);
});

test('close: labels part outwards, left one ending at its dot, right one starting at its', () => {
  const [l1, l2] = placeLabels([170, 190], [70, 70], W);
  expect(l1 + 70).toBe(172);
  expect(l2).toBe(188);
});

test('together at the right edge: side by side, inside the card, never touching', () => {
  const out = placeLabels([335, 338], [70, 70], W);
  expect(noOverlap(out, [70])).toBe(true);
  expect(out[1] + 70).toBeLessThanOrEqual(W);
  expect(out[0]).toBeGreaterThanOrEqual(0);
});

test('together at the left edge: inside the card, never touching', () => {
  const out = placeLabels([4, 8], [70, 70], W);
  expect(out[0]).toBeGreaterThanOrEqual(0);
  expect(noOverlap(out, [70])).toBe(true);
});
