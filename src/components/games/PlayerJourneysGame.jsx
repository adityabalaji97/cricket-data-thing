/**
 * Player Journeys (daily). Guess the IPL player from their franchise path, shown up front in team
 * colours (pre-2015 seasons included, under the names the teams had then). Hints and wrong
 * guesses each cost a point; see NameGuessGame for the shared mechanics.
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';
import { getTeamColor, textOn } from '../../utils/teamColors';
import NameGuessGame from './daily/NameGuessGame';

const HINTS = [
  { key: 'style', icon: '🏏', label: 'Batting & bowling' },
  { key: 'country', icon: '🌍', label: 'Country' },
  { key: 'numbers', icon: '📊', label: 'IPL numbers' },
  { key: 'initials', icon: '🔤', label: 'Initials' },
];

const JourneyTimeline = ({ journey, seasons }) => (
  <Box sx={{ p: 2.25, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.border}` }}>
    <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 1.5 }}>
      IPL journey · {seasons} seasons
    </Typography>
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {journey.map((stint) => {
        const color = getTeamColor(stint.team) || colors.surface2;
        return (
          <Box
            key={`${stint.team}-${stint.years}`}
            sx={{ display: 'flex', alignItems: 'center', gap: 1.5, borderRadius: 2, bgcolor: color, color: textOn(color), px: 1.5, py: 1 }}
          >
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, width: 84, flexShrink: 0, opacity: 0.85, color: 'inherit' }}>{stint.years}</Typography>
            <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 17, lineHeight: 1.2, color: 'inherit' }}>{stint.team}</Typography>
          </Box>
        );
      })}
    </Box>
  </Box>
);

const PlayerJourneysGame = () => (
  <NameGuessGame
    game="player_journeys"
    title="Player Journeys"
    rules="Who is it? Their IPL journey is below. Each hint, and each wrong guess, costs a point."
    path="/games/player-journey"
    puzzlePath="puzzle"
    hints={HINTS}
    maxPoints={5}
    shareUrl="/games/player-journeys"
    renderClue={(puzzle) => <JourneyTimeline journey={puzzle.journey} seasons={puzzle.seasons} />}
  />
);

export default PlayerJourneysGame;
