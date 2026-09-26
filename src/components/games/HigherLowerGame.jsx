/**
 * Higher or Lower: Impact (daily). Ten independent pairs of player-seasons; tap the one with the
 * higher Impact. Both values are revealed after each tap, and every pair is played.
 */
import React, { useState } from 'react';
import { Box, Button, ButtonBase, CircularProgress, Typography } from '@mui/material';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';
import DailyGameShell from './daily/DailyGameShell';
import usePuzzle from './daily/usePuzzle';
import { recordFinish, saveProgress } from './daily/dailyStorage';

const GAME = 'higher_lower';
const signed = (v) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}`;
const emptyProgress = () => ({ picks: [] }); // { choice, cards (with impact), right } per round

const PlayerCard = ({ card, revealed, chosen, winner, disabled, onTap }) => {
  let border = colors.border;
  if (revealed && winner) border = colors.accent;
  else if (revealed && chosen) border = colors.red;
  return (
    <ButtonBase
      onClick={onTap}
      disabled={disabled}
      focusRipple
      sx={{
        flex: 1, minWidth: 0, display: 'block', textAlign: 'left', p: 2, borderRadius: 3,
        bgcolor: colors.surface1, border: `2px solid ${border}`,
        transition: 'border-color 120ms, transform 120ms',
        '&:not(:disabled):hover': { borderColor: colors.borderStrong, transform: 'translateY(-1px)' },
      }}
      aria-label={`${card.player}, ${card.competition} ${card.season}`}
    >
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: colors.textHi, lineHeight: 1.15 }}>{card.player}</Typography>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo, mt: 0.5, letterSpacing: '0.04em' }}>
        {card.competition} {card.season}
      </Typography>
      <Typography sx={{ color: colors.textMed, fontSize: 14, mt: 0.5 }}>
        {card.runs} off {card.balls} · SR {card.strike_rate}
      </Typography>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 28, mt: 1, color: revealed ? (card.impact >= 0 ? colors.accent : colors.red) : colors.textFaint }}>
        {revealed ? signed(card.impact) : '?'}
      </Typography>
      <Typography sx={{ color: colors.textLo, fontSize: 12 }}>
        {revealed ? `Impact · RAA ${signed(card.raa)} · WPA ${card.wpa > 0 ? '+' : ''}${card.wpa}` : 'Impact'}
      </Typography>
      {revealed && chosen && (
        <Typography sx={{ fontSize: 12, fontWeight: 700, mt: 0.5, color: winner ? colors.accent : colors.red }}>Your pick</Typography>
      )}
    </ButtonBase>
  );
};

const HigherLowerGame = () => {
  const {
    puzzle, progress, setProgress, stats, setStats, error, practice, daily,
  } = usePuzzle(GAME, '/games/higher-lower/daily', emptyProgress);
  const [showing, setShowing] = useState(null); // round whose answer is on screen
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(null);

  if (error) return <Typography sx={{ p: 3, color: colors.textMed, textAlign: 'center' }}>{error}</Typography>;
  if (!puzzle || !progress || !stats) return <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>;

  const total = puzzle.rounds.length;
  const { picks } = progress;
  const finished = picks.length >= total;
  const correct = picks.filter((p) => p.right).length;
  const roundIndex = showing ?? (finished ? total - 1 : picks.length);
  const pick = picks[roundIndex];
  const round = puzzle.rounds[roundIndex];

  const tap = async (choice) => {
    if (pick || busy) return;
    setBusy(true);
    setFailure(null);
    try {
      const r = await fetch(`${config.API_URL}/games/higher-lower/reveal?index=${roundIndex}&puzzle=${encodeURIComponent(puzzle.puzzle)}`);
      if (!r.ok) throw new Error(r.status);
      const { cards } = await r.json();
      const right = cards[choice].impact >= cards[1 - choice].impact;
      const next = { picks: [...picks, { choice, cards, right }] };
      setProgress(next);
      setShowing(roundIndex);
      if (puzzle.daily) saveProgress(GAME, puzzle.puzzle, next);
      if (next.picks.length >= total) {
        const score = next.picks.filter((p) => p.right).length;
        if (puzzle.daily) setStats(recordFinish(GAME, puzzle.puzzle, score));
        track('game_finish', { game: GAME, number: puzzle.number, score, practice: !puzzle.daily });
      }
    } catch {
      setFailure('Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const trail = picks.map((p) => (p.right ? '🟩' : '🟥')).join('');
  const shareText = `Higher or Lower #${puzzle.number} · ${correct}/${total}${correct >= 8 ? ' 🔥' : ''}\n${trail}\n${window.location.origin}/games/higher-lower`;
  const cards = pick ? pick.cards : round.cards;
  const winnerIndex = pick ? (cards[0].impact >= cards[1].impact ? 0 : 1) : null;

  return (
    <DailyGameShell
      game={GAME}
      title="Higher or Lower"
      number={puzzle.daily ? puzzle.number : null}
      rules="Impact is the runs a batter added to their team's projected total, given the game situation. Tap the player-season with the higher Impact. Ten pairs a day."
      stats={stats}
      finished={finished}
      resultLine={`${correct} / ${total}`}
      shareText={shareText}
      practice={!puzzle.daily}
      onPractice={() => { setShowing(null); practice(); }}
      onBackToDaily={() => { setShowing(null); daily(); }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography sx={{ fontFamily: fonts.mono, color: colors.textLo, fontSize: 13 }}>
          Pair {roundIndex + 1} of {total}
        </Typography>
        <Typography sx={{ fontFamily: fonts.mono, color: colors.textLo, fontSize: 13 }}>
          {correct} right {trail}
        </Typography>
      </Box>

      <Typography sx={{ color: colors.textHi, fontWeight: 700, mb: 1 }}>
        {pick ? (pick.right ? 'Right.' : 'Not this time.') : 'Who had the higher Impact?'}
      </Typography>
      <Box sx={{ display: 'flex', gap: 1.25, alignItems: 'stretch' }}>
        {cards.map((card, i) => (
          <PlayerCard
            key={`${roundIndex}-${card.player}`}
            card={card}
            revealed={Boolean(pick)}
            chosen={pick?.choice === i}
            winner={winnerIndex === i}
            disabled={Boolean(pick) || busy}
            onTap={() => tap(i)}
          />
        ))}
      </Box>
      {failure && <Typography sx={{ color: colors.red, fontSize: 13, mt: 1 }}>{failure}</Typography>}

      {pick && !finished && (
        <Button fullWidth variant="contained" onClick={() => setShowing(null)} sx={{ mt: 2, minHeight: 48 }}>
          Next pair
        </Button>
      )}
      {finished && (
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 2 }}>
          {picks.map((p, i) => (
            <Button
              key={i}
              size="small"
              variant={i === roundIndex ? 'contained' : 'outlined'}
              onClick={() => setShowing(i)}
              sx={{ minWidth: 40, minHeight: 36, px: 0 }}
              aria-label={`Pair ${i + 1}, ${p.right ? 'right' : 'wrong'}`}
            >
              {p.right ? '🟩' : '🟥'}
            </Button>
          ))}
        </Box>
      )}
    </DailyGameShell>
  );
};

export default HigherLowerGame;
