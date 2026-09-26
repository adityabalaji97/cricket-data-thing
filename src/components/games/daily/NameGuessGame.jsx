/**
 * The name-guessing daily games (Player Journeys, Guess the Innings) share everything but the clue:
 * paid hints, typed guesses checked by the server (close spellings and aliases count), a score of
 * max points minus hints taken minus wrong guesses, and practice puzzles that skip the streak.
 * The answer is never in the page until it is solved or revealed.
 */
import React, { useCallback, useState } from 'react';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import config from '../../../config';
import { colors } from '../../../theme/hindsightDark';
import { track } from '../../../utils/analytics';
import DailyGameShell from './DailyGameShell';
import NameGuessInput from './NameGuessInput';
import usePuzzle from './usePuzzle';
import { recordFinish, saveProgress } from './dailyStorage';

const MAX_GUESSES = 6;
const emptyProgress = () => ({ hints: {}, misses: [], solved: false, gaveUp: false, answer: null });
const isDone = (s) => s.solved || s.gaveUp || s.misses.length >= MAX_GUESSES;

const NameGuessGame = ({ game, title, rules, path, puzzlePath, hints, maxPoints, shareUrl, renderClue }) => {
  const {
    puzzle, progress: state, setProgress: setState, stats, setStats, error, practice, daily,
  } = usePuzzle(game, `${path}/${puzzlePath}`, emptyProgress);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(null);

  const api = useCallback(
    (endpoint, params = {}) => {
      const query = new URLSearchParams({ ...params, puzzle: puzzle.puzzle }).toString();
      return fetch(`${config.API_URL}${path}/${endpoint}?${query}`).then((r) => (r.ok ? r.json() : Promise.reject(r.status)));
    },
    [path, puzzle],
  );

  if (error) return <Typography sx={{ p: 3, color: colors.textMed, textAlign: 'center' }}>{error}</Typography>;
  if (!puzzle || !state || !stats) return <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>;

  const finished = isDone(state);
  const scoreOf = (s) => (s.solved ? Math.max(1, maxPoints - Object.keys(s.hints).length - s.misses.length) : 0);

  const persist = (next) => {
    setState(next);
    if (puzzle.daily) saveProgress(game, puzzle.puzzle, next);
    if (isDone(next)) {
      const score = scoreOf(next);
      if (puzzle.daily) setStats(recordFinish(game, puzzle.puzzle, score));
      track('game_finish', { game, number: puzzle.number, score, practice: !puzzle.daily });
    }
  };

  const run = async (work) => {
    setBusy(true);
    setFailure(null);
    try {
      return await work();
    } catch {
      setFailure('Something went wrong. Try again.');
      return null;
    } finally {
      setBusy(false);
    }
  };

  const takeHint = (key) => run(async () => {
    const { value } = await api('hint', { key });
    persist({ ...state, hints: { ...state.hints, [key]: value } });
  });

  const guess = (text) => run(async () => {
    const result = await api('check', { guess: text });
    if (result.correct) {
      const { hints: revealed } = await api('reveal');
      persist({ ...state, solved: true, answer: result.answer, revealed });
      return true;
    }
    const next = { ...state, misses: [...state.misses, text.trim()] };
    if (next.misses.length >= MAX_GUESSES) Object.assign(next, await revealAll());
    persist(next);
    return false;
  });

  // Once the puzzle is over, every hint is shown (the unpaid ones dimmed) so the answer makes sense.
  const revealAll = async () => {
    const { answer, hints: revealed } = await api('reveal');
    return { answer, revealed };
  };

  const giveUp = () => run(async () => {
    persist({ ...state, gaveUp: true, ...(await revealAll()) });
  });

  const score = scoreOf(state);
  const misses = state.misses.length;
  const hintIcons = hints.map((h) => (state.hints[h.key] ? h.icon : '⬜')).join('');
  const shareText = `${title} #${puzzle.number} ${state.solved ? '✅' : '❌'} ${score}/${maxPoints}\n`
    + `${hintIcons}${misses ? ` · ${misses} miss${misses === 1 ? '' : 'es'}` : ''}\n${window.location.origin}${shareUrl}`;
  const resultLine = state.solved ? `${state.answer} · ${score}/${maxPoints}` : `It was ${state.answer}`;

  return (
    <DailyGameShell
      game={game}
      title={title}
      number={puzzle.daily ? puzzle.number : null}
      rules={rules}
      stats={stats}
      finished={finished}
      resultLine={resultLine}
      shareText={shareText}
      practice={!puzzle.daily}
      onPractice={practice}
      onBackToDaily={daily}
    >
      {renderClue(puzzle)}

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1, mt: 1.5 }}>
        {hints.map((h) => (
          <Box key={h.key} sx={{ p: 1.25, borderRadius: 2, border: `1px solid ${colors.border}`, bgcolor: state.hints[h.key] ? colors.surface2 : 'transparent', minHeight: 64 }}>
            <Typography sx={{ fontSize: 12, color: colors.textLo }}>{h.icon} {h.label}</Typography>
            {state.hints[h.key] || (finished && state.revealed?.[h.key]) ? (
              <Typography sx={{ color: state.hints[h.key] ? colors.textHi : colors.textLo, fontSize: 14, fontWeight: 600, mt: 0.25 }}>
                {state.hints[h.key] || state.revealed[h.key]}
              </Typography>
            ) : (
              <Button size="small" disabled={busy || finished} onClick={() => takeHint(h.key)} sx={{ mt: 0.25, px: 0, minHeight: 32 }}>
                Reveal (−1)
              </Button>
            )}
          </Box>
        ))}
      </Box>

      <Box sx={{ mt: 2.5 }}>
        {finished ? null : (
          <NameGuessInput
            key={puzzle.puzzle}
            shape={puzzle.name_shape}
            initials={state.hints.initials}
            disabled={busy}
            onGuess={guess}
            onGiveUp={giveUp}
            guessesLeft={MAX_GUESSES - misses}
          />
        )}
        {misses > 0 && (
          <Typography sx={{ color: colors.textLo, fontSize: 13, mt: 0.75 }}>Not {state.misses.join(', not ')}</Typography>
        )}
        {failure && <Typography sx={{ color: colors.red, fontSize: 13, mt: 0.75 }}>{failure}</Typography>}
      </Box>
    </DailyGameShell>
  );
};

export default NameGuessGame;
