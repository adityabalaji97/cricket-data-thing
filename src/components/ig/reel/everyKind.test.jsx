/**
 * Every visual kind, with and without the `motion` prop (MOTION_REEL_PLAN.md M2a): at the end of its motion a visual
 * must draw exactly what its carousel card draws, so carousels, the site and the goldens are untouched; at t = start
 * it must render without throwing. Payloads: one real payload per kind (__fixtures__/visual_payloads.json, taken from
 * posted carousels and local chart snapshots), plus small hand-made ones for kinds the snapshots lack.
 */
import React from 'react';
import { render } from '@testing-library/react';
import { MOTION_KINDS, POST_VISUALS } from '../../story/postVisuals';
import { VISUALS } from '../../story/visuals';
import FIXTURES from './__fixtures__/visual_payloads.json';
import DivergingBars from '../../charts/DivergingBars';

jest.mock('echarts-for-react', () => () => null);
// As StoryViewer.test: axios and react-router-dom 7 ship ES modules Jest doesn't transform.
jest.mock('axios', () => ({ post: jest.fn(), get: jest.fn() }));
jest.mock('react-router-dom', () => ({
  // eslint-disable-next-line jsx-a11y/anchor-has-content
  Link: ({ to, children, ...rest }) => <a href={to} {...rest}>{children}</a>,
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/', search: '' }),
  useParams: () => ({}),
}), { virtual: true });

const EXTRA = {
  stat: { payload: { value: '+1.98', caption: 'wins added since the 2025 auction' } },
  tiles: { payload: { tiles: [{ card: 'a', label: 'Par', value: '171', sub: 'first innings' }, { card: 'b', label: 'Chased', value: '54%', sub: 'of 52 games' }] } },
  rank_bars: { payload: { team1: 'Mumbai Indians', team2: 'Chennai Super Kings', rows: [
    { group: 'batting', phase: 'powerplay', team1: 2, team2: 7, of: 10 }, { group: 'bowling', phase: 'death', team1: 1, team2: 9, of: 10 }] } },
  bucket_bars: { payload: { metric: { label: 'Runs above par per 100 balls', format: 'signed1' }, buckets: [
    { label: '1-10', value: -4.2, n: 120 }, { label: '11-20', value: 6.1, n: 90 }, { label: '21+', value: 12.5, n: 40 }] } },
  par: { payload: { value: '182', caption: 'Par first-innings score here', series: [
    { year: 2024, value: 176, n: 7 }, { year: 2025, value: 179, n: 8 }, { year: 2026, value: 182, n: 7 }] } },
  chase_band: { payload: { chase_wins: 31, decided: 52, lo: 46, hi: 72, within_noise: false, notes: ['Dew from the 12th over'] } },
  phase_diverging: { payload: { comparison: 'IPL', rows: [
    { phase: 'powerplay', here: 9.1, all: 8.6, diff: 0.5 }, { phase: 'middle', here: 8.2, all: 8.7, diff: -0.5 },
    { phase: 'death', here: 11.9, all: 11.2, diff: 0.7 }] } },
  milestones: { teams: ['India', 'New Zealand'], payload: { rows: [
    { player: 'SA Yadav', stat: 'runs', text: 'needs 38 for 3,000 T20I runs', side: 'India', total: 2962, target: 3000 },
    { player: 'TA Boult', stat: 'wkts', text: 'needs 2 for 100 T20I wickets', side: 'New Zealand', total: 98, target: 100 }] } },
  bowling_plan: { payload: { team: 'India', mark: 18, rows: [
    { name: 'Jasprit Bumrah', short: 'Bumrah', kind: 'pace', left: 0, cells: [{ o: 1, runs: 4 }, { o: 6, runs: 7 }, { o: 16, runs: 5 }, { o: 18, runs: 3 }] },
    { name: 'Varun Chakaravarthy', short: 'Varun', kind: 'spin', left: 1, cells: [{ o: 8, runs: 6 }, { o: 10, runs: 9 }, { o: 12, runs: 4 }] }] } },
  suits_scatter: { teams: ['India', 'New Zealand'], payload: { ground: 'Eden Gardens', home: ['SA Yadav'], rows: [
    { name: 'SA Yadav', side: 'India', here: 18.2, elsewhere: 9.1, balls_here: 140 },
    { name: 'DP Conway', side: 'New Zealand', here: -4.5, elsewhere: 6.3, balls_here: 60 },
    { name: 'HH Pandya', side: 'India', here: 2.1, elsewhere: 1.4, balls_here: 90 }] } },
  worm: { payload: { overs: [5, 10, 15, 20], here: [48, 86, 132, 181], all: [50, 84, 126, 172], here_label: 'Here', all_label: 'All IPL grounds' } },
  elo_lines: { payload: { series: [
    { team: 'Mumbai Indians', points: [{ date: '2026-03-28', elo: 1510 }, { date: '2026-04-20', elo: 1532 }, { date: '2026-05-18', elo: 1548 }] },
    { team: 'Chennai Super Kings', points: [{ date: '2026-03-29', elo: 1500 }, { date: '2026-04-21', elo: 1488 }, { date: '2026-05-19', elo: 1471 }] }] } },
  score_race: { payload: { mark: 3, series: [
    { team: 'India', values: [9, 21, 30, 44, 58], wickets: [0, 1, 1, 2, 2] },
    { team: 'New Zealand', values: [12, 20, 33, 41, 49], wickets: [0, 0, 1, 2, 4] }] } },
  xis: { payload: { sides: [
    { team: 'Mumbai Indians', opponent: 'Chennai Super Kings', date: '2026-04-12', players: ['R Sharma', 'R Rickelton', 'SA Yadav'], earlier: {} },
    { team: 'Chennai Super Kings', opponent: 'Mumbai Indians', date: '2026-04-12', players: ['RD Gaikwad', 'D Conway', 'S Dube'], earlier: { 'D Conway': '2026-03-30' } }] } },
  round_stack: { payload: { metric: { label: 'Runs above par', format: 'signed1' },
    rounds: [{ key: '1', label: 'R1' }, { key: '2', label: 'R2' }, { key: '3', label: 'R3' }, { key: '4', label: 'R4' }],
    rows: [{ name: 'Yash Dhull', detail: '267 off 141', highlight: true, segments: [{ key: '1', value: 7 }, { key: '2', value: 10.4 }, { key: '3', value: 44.6 }, { key: '4', value: 3.3 }] },
      { name: 'Vikalp Tiwari', detail: '3 games', segments: [{ key: '1', value: 33.2 }, { key: '2', value: -0.8 }, { key: '3', value: 30.4 }, { key: '4', value: null, note: 'washed out' }] },
      { name: 'Shivalik Sharma', segments: [{ key: '1', value: -8.3 }, { key: '2', value: 55.3 }, { key: '3', value: 7 }, { key: '4', value: -0.7 }] }] } },
  recap_text: { payload: { headline: 'Won in the middle overs', bullets: ['Spin went for 5.1 an over', 'Two wickets in the 14th'] } },
};

const ALL = { ...VISUALS, ...POST_VISUALS };
const CASES = { ...FIXTURES, ...EXTRA };
const html = (Visual, c, motion, extra = {}) => {
  const { container, unmount } = render(
    <Visual payload={c.payload} teams={c.teams || undefined} isMobile motion={motion} {...extra} />,
  );
  // data-motion-key marks are written only under motion (the Reel camera finds marks by them); they draw nothing
  const out = container.innerHTML.replace(/:r[0-9a-z]+:/g, ':id:').replace(/ data-motion-(key|group)="[^"]*"/g, '');
  unmount();
  return out;
};

const kinds = Object.keys(ALL).filter((k) => CASES[k]).sort();

describe('every visual kind with and without motion', () => {
  test.each(kinds)('%s: motion at its end draws the card exactly; motion at its start renders', (kind) => {
    const Visual = ALL[kind];
    const c = CASES[kind];
    const plain = html(Visual, c, undefined);
    expect(html(Visual, c, { t: 999, start: 0, end: 5, lit: null, plan: {} })).toBe(plain);
    expect(() => html(Visual, c, { t: 0, start: 0, end: 5, lit: null, plan: {} })).not.toThrow();
  });

  test('below par draws the same on the card and in a Reel (red on both, owner 18 Nov), and a null still prints the dash', () => {
    const c = { payload: { metric: { label: 'Runs above par', format: 'signed1', signed: true },
      rows: [{ name: 'A', value: 5 }, { name: 'B', value: -3 }, { name: 'C', value: null }] } };
    const end = { t: 999, start: 0, end: 5, lit: null, plan: {} };
    expect(html(ALL.metric_bars, c, end)).toBe(html(ALL.metric_bars, c, undefined));
    const pos = { payload: { ...c.payload, rows: c.payload.rows.filter((r) => !(r.value < 0)) } };
    expect(html(ALL.metric_bars, c, undefined)).not.toBe(html(ALL.metric_bars, { payload: { ...c.payload, rows: [...pos.payload.rows.slice(0, 1), { name: 'B', value: 3 }, pos.payload.rows[1]] } }, undefined));
    expect(html(ALL.metric_bars, c, undefined)).toContain('–');
  });

  test('DivergingBars (a shared site chart) draws the same with no growRow and with a finished one', () => {
    const rows = [{ key: 'a', label: 'Powerplay', value: 0.6, sample: 300 }, { key: 'b', label: 'Death', value: -1.2, sample: 40 }];
    const plain = html(DivergingBars, { payload: null }, undefined, { rows, span: 3 });
    expect(html(DivergingBars, { payload: null }, undefined, { rows, span: 3, growRow: () => 1 })).toBe(plain);
    expect(html(DivergingBars, { payload: null }, undefined, { rows, span: 3, growRow: () => 0.5 })).not.toBe(plain);
  });

  test('every motion kind has a test payload', () => {
    expect([...MOTION_KINDS].filter((k) => !CASES[k])).toEqual([]);
  });

  test('motion actually changes a motion kind part way through', () => {
    [...MOTION_KINDS].filter((k) => CASES[k]).forEach((kind) => {
      const plain = html(ALL[kind], CASES[kind], undefined);
      expect([kind, html(ALL[kind], CASES[kind], { t: 0.2, start: 0, end: 5, lit: null, plan: {} }) !== plain]).toEqual([kind, true]);
    });
  });

  Object.keys(ALL).filter((k) => !CASES[k]).sort().forEach((k) => test.todo(`${k}: no payload yet (plays the fallback)`));
});

describe('round_stack geometry (form so far)', () => {
  // eslint-disable-next-line global-require
  const { roundStackGeometry } = require('../../story/postVisuals');
  const { rounds, rows } = EXTRA.round_stack.payload;
  const g = roundStackGeometry(rows, rounds);
  test('below-par rounds sit left of par, above-par right, and the total is the signed sum', () => {
    const shiv = g.rows[2];
    shiv.segs.filter((x) => x.value < 0).forEach((x) => expect(x.x + x.w).toBeLessThanOrEqual(g.zero + 1e-9));
    shiv.segs.filter((x) => x.value > 0).forEach((x) => expect(x.x).toBeGreaterThanOrEqual(g.zero - 1e-9));
    expect(shiv.total).toBeCloseTo(-8.3 + 55.3 + 7 - 0.7, 6);
  });
  test('a round with no data is a missing slot, not a zero', () => {
    const vik = g.rows[1];
    expect(vik.segs.find((x) => x.key === '4').missing).toBe(true);
    expect(vik.total).toBeCloseTo(33.2 - 0.8 + 30.4, 6);
  });
  test('no segment passes either edge', () => {
    g.rows.forEach((r) => r.segs.filter((x) => !x.missing).forEach((x) => {
      expect(x.x).toBeGreaterThanOrEqual(-1e-9); expect(x.x + x.w).toBeLessThanOrEqual(100 + 1e-9);
    }));
  });
});
