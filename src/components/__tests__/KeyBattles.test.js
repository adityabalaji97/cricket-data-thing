import { rankBattles } from '../KeyBattles';

const side = {
  battingTeam: 'CSK',
  bowlingTeam: 'MI',
  matchups: {
    'S Samson': {
      Overall: { balls: 200, runs: 300, wickets: 8, strike_rate: 150 },
      'M Santner': { balls: 27, runs: 18, wickets: 2, strike_rate: 66.7 },
      'Tiny Sample': { balls: 6, runs: 30, wickets: 0, strike_rate: 500 },
      'H Pandya': { balls: 24, runs: 49, wickets: 1, strike_rate: 204.2 },
    },
    'Q de Kock': {
      Overall: { balls: 300, runs: 450, wickets: 15, strike_rate: 150 },
      'A Hosein': { balls: 85, runs: 161, wickets: 8, strike_rate: 189.4 },
    },
  },
};

describe('rankBattles', () => {
  const ranked = rankBattles([side]);

  it('drops pairs under the minimum balls', () => {
    expect(ranked.find((b) => b.bowler === 'Tiny Sample')).toBeUndefined();
  });

  it('labels edges from strike rate and dismissals together', () => {
    const byPair = Object.fromEntries(ranked.map((b) => [`${b.batter}|${b.bowler}`, b.edge]));
    expect(byPair['S Samson|M Santner']).toBe('bowler');
    expect(byPair['S Samson|H Pandya']).toBe('batter');
    // Faster, but out every 10.6 balls against 20 overall.
    expect(byPair['Q de Kock|A Hosein']).toBe('trade-off');
  });

  it('ranks by edge size weighted by sample', () => {
    const scores = ranked.map((b) => b.score);
    expect(scores).toEqual([...scores].sort((a, b) => b - a));
    // 85 balls with double the usual dismissal rate outranks a 27-ball strike-rate squeeze.
    expect(ranked[0].bowler).toBe('A Hosein');
  });
});
