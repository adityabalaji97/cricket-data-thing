/**
 * Guess the Innings (daily). Name the batter from one innings: the score line and a wagon wheel of
 * every scoring shot. Hints (venue, season, opposition, team, initials) and wrong guesses each
 * cost a point; see NameGuessGame for the shared mechanics.
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';
import NameGuessGame from './daily/NameGuessGame';

const HINTS = [
  { key: 'season', icon: '📅', label: 'Season' },
  { key: 'team', icon: '👕', label: 'Team' },
  { key: 'opposition', icon: '⚔️', label: 'Opposition' },
  { key: 'venue', icon: '🏟️', label: 'Venue' },
  { key: 'initials', icon: '🔤', label: 'Initials' },
];

const RUN_COLORS = { 1: '#8b95a7', 2: '#5aa9e6', 3: '#a78bfa', 4: colors.accent, 6: '#f5a524' };

// Wagon coordinates are centred on (150, 150). Only the direction is reliable across feeds, so
// boundaries go to the rope and other shots are scaled by distance within the inner ring.
const WagonWheel = ({ deliveries }) => {
  const size = 280;
  const c = size / 2;
  const rope = size * 0.46;
  const shots = deliveries.filter((d) => d.runs > 0 && d.x != null && d.y != null && (d.x !== 150 || d.y !== 150));
  const far = Math.max(1, ...shots.filter((d) => d.runs < 4).map((d) => Math.hypot(d.x - 150, d.y - 150)));
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
      <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ maxWidth: size }} role="img" aria-label="Wagon wheel of scoring shots">
        <circle cx={c} cy={c} r={rope} fill="#12301c" stroke="rgba(255,255,255,0.25)" />
        <circle cx={c} cy={c} r={rope * 0.55} fill="none" stroke="rgba(255,255,255,0.12)" strokeDasharray="3 4" />
        <rect x={c - 5} y={c - 16} width={10} height={32} rx={2} fill="#c9b27c" opacity={0.7} />
        {shots.map((d, i) => {
          const dx = d.x - 150;
          const dy = d.y - 150;
          const dist = Math.hypot(dx, dy);
          const r = d.runs >= 4 ? rope : (dist / far) * rope * 0.72;
          return (
            <line
              key={i}
              x1={c}
              y1={c}
              x2={c + (dx / dist) * r}
              y2={c + (dy / dist) * r}
              stroke={RUN_COLORS[d.runs] || RUN_COLORS[1]}
              strokeWidth={d.runs >= 4 ? 2 : 1.4}
              strokeLinecap="round"
              opacity={0.9}
            />
          );
        })}
      </svg>
    </Box>
  );
};

const InningsClue = ({ puzzle }) => (
  <Box sx={{ p: 2.25, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.border}` }}>
    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap' }}>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 34, color: colors.textHi, lineHeight: 1 }}>
        {puzzle.runs}
        <span style={{ fontSize: 20, color: colors.textMed }}> ({puzzle.balls})</span>
      </Typography>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, color: colors.textLo }}>
        SR {puzzle.strike_rate} · {puzzle.fours}×4 · {puzzle.sixes}×6 · {puzzle.bat_hand}
      </Typography>
    </Box>
    <Box sx={{ mt: 1.5 }}>
      <WagonWheel deliveries={puzzle.deliveries} />
    </Box>
    <Box sx={{ display: 'flex', gap: 1.5, justifyContent: 'center', flexWrap: 'wrap', mt: 1 }}>
      {[1, 2, 3, 4, 6].map((runs) => (
        <Box key={runs} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 12, height: 3, borderRadius: 1, bgcolor: RUN_COLORS[runs] }} />
          <Typography sx={{ fontSize: 12, color: colors.textLo }}>{runs}</Typography>
        </Box>
      ))}
    </Box>
  </Box>
);

const GuessInningsGame = () => (
  <NameGuessGame
    game="guess_innings"
    title="Guess the Innings"
    rules="Whose innings was this? Each hint, and each wrong guess, costs a point."
    path="/games/guess-innings"
    puzzlePath="daily"
    hints={HINTS}
    maxPoints={6}
    shareUrl="/games/guess-innings"
    renderClue={(puzzle) => <InningsClue puzzle={puzzle} />}
  />
);

export default GuessInningsGame;
