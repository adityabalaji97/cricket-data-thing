import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, CircularProgress, Slider, Typography } from '@mui/material';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';
import DailyGameShell from './daily/DailyGameShell';
import { loadProgress, loadStats, recordFinish, saveProgress } from './daily/dailyStorage';

const GAME = 'call_it';

// Per moment: how close the call was (100 x (1 - squared error)), whether the winner was picked,
// and whether it beat the model's own number on the same ball.
const grade = (guess, answer) => {
  const outcome = answer.chasing_side_won ? 1 : 0;
  const p = guess / 100;
  const userErr = (p - outcome) ** 2;
  const modelErr = (answer.model_win_probability - outcome) ** 2;
  const pickedWinner = guess !== 50 && (guess > 50) === answer.chasing_side_won;
  return {
    points: Math.round(100 * (1 - userErr)),
    pickedWinner,
    beatModel: userErr < modelErr,
    tile: pickedWinner ? (userErr < modelErr ? '🟩' : '🟨') : '🟥',
  };
};

const MomentCard = ({ moment, guess, onGuess, onLock, answer, locking }) => {
  const chaser = moment.batting_team;
  const result = answer ? grade(guess, answer) : null;
  return (
    <Box sx={{ p: 2.25, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.border}` }}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        {moment.competition} {moment.season} · {moment.venue?.split(',')[0]}
      </Typography>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, color: colors.textHi, mt: 0.75, lineHeight: 1.2 }}>
        {chaser} need {moment.runs_needed} off {moment.balls_left}
      </Typography>
      <Typography sx={{ color: colors.textMed, fontSize: 14, mt: 0.5 }}>
        {moment.score} chasing {moment.target} against {moment.bowling_team} · {moment.wickets_left} wicket{moment.wickets_left === 1 ? '' : 's'} left
      </Typography>

      <Box sx={{ mt: 2.5, px: 1 }}>
        <Typography sx={{ color: colors.textHi, fontWeight: 700, mb: 0.5 }}>
          {chaser} win chance: <span style={{ color: colors.accent }}>{guess}%</span>
        </Typography>
        <Slider
          value={guess}
          onChange={(_, value) => onGuess(value)}
          min={0}
          max={100}
          step={5}
          disabled={Boolean(answer)}
          aria-label={`${chaser} win chance`}
        />
      </Box>

      {!answer ? (
        <Button fullWidth variant="contained" onClick={onLock} disabled={locking} sx={{ mt: 1, minHeight: 44 }}>
          {locking ? 'Checking…' : 'Lock it in'}
        </Button>
      ) : (
        <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 2, bgcolor: colors.surface2 }}>
          <Typography sx={{ fontWeight: 700, color: result.pickedWinner ? colors.accent : colors.red }}>
            {result.tile} {answer.winner} won · +{result.points}
          </Typography>
          <Typography sx={{ color: colors.textMed, fontSize: 14, mt: 0.5 }}>
            You said {guess}% · Hindsight&apos;s model said {Math.round(answer.model_win_probability * 100)}%
            {result.beatModel ? ' · you beat the model' : ''}
          </Typography>
          <Box component={RouterLink} to={`/scorecard/${answer.match_id}`} sx={{ color: colors.accent, fontSize: 13, display: 'inline-block', mt: 0.75 }}>
            See how it played out →
          </Box>
        </Box>
      )}
    </Box>
  );
};

const CallItGame = () => {
  const [puzzle, setPuzzle] = useState(null);
  const [error, setError] = useState(null);
  const [guesses, setGuesses] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [current, setCurrent] = useState(0);
  const [locking, setLocking] = useState(false);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${config.API_URL}/games/call-it/daily`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        setPuzzle(data);
        const saved = loadProgress(GAME, data.date);
        const n = data.moments.length;
        setGuesses(saved?.guesses || Array(n).fill(50));
        setAnswers(saved?.answers || Array(n).fill(null));
        setCurrent(saved?.current || 0);
        setStats(loadStats(GAME, data.date));
        if (!saved) track('game_start', { game: GAME, number: data.number });
      })
      .catch(() => setError("Couldn't load today's Call It. Try again in a minute."));
  }, []);

  const finished = puzzle && answers.length > 0 && answers.every(Boolean);
  const graded = useMemo(
    () => (finished ? answers.map((a, i) => grade(guesses[i], a)) : []),
    [finished, answers, guesses],
  );
  const total = graded.reduce((sum, g) => sum + g.points, 0);
  const beat = graded.filter((g) => g.beatModel).length;

  const lock = async (index) => {
    setLocking(true);
    try {
      const r = await fetch(`${config.API_URL}/games/call-it/reveal?index=${index}&date=${puzzle.date}`);
      const answer = await r.json();
      const nextAnswers = answers.map((a, i) => (i === index ? answer : a));
      setAnswers(nextAnswers);
      // Stay on this moment so the reveal is seen; "Next moment" moves on.
      saveProgress(GAME, puzzle.date, { guesses, answers: nextAnswers, current: index });
      if (nextAnswers.every(Boolean)) {
        const score = nextAnswers.reduce((sum, a, i) => sum + grade(guesses[i], a).points, 0);
        setStats(recordFinish(GAME, puzzle.date, score));
        track('game_finish', { game: GAME, number: puzzle.number, score });
      }
    } catch {
      setError('Something went wrong revealing that one. Try again.');
    } finally {
      setLocking(false);
    }
  };

  if (error) return <Typography sx={{ p: 3, color: colors.textMed, textAlign: 'center' }}>{error}</Typography>;
  if (!puzzle || !stats) return <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>;

  const shareText = `Call It #${puzzle.number} ${graded.map((g) => g.tile).join('')}\n${total}/${puzzle.moments.length * 100} · beat the model ${beat}/${puzzle.moments.length}\n${window.location.origin}/games/call-it`;

  return (
    <DailyGameShell
      game={GAME}
      title="Call It"
      number={puzzle.number}
      rules="Five real run chases, frozen mid-game. How likely was the chasing side to win? Closer to what happened scores more; beat Hindsight's win-probability model if you can."
      stats={stats}
      finished={finished}
      resultLine={`${total} / ${puzzle.moments.length * 100}`}
      shareText={shareText}
    >
      <Box sx={{ display: 'flex', gap: 0.75, mb: 2 }}>
        {puzzle.moments.map((m, i) => (
          <Box
            key={m.index}
            component="button"
            type="button"
            onClick={() => (answers[i] || i <= current ? setCurrent(i) : null)}
            aria-label={`Moment ${i + 1}`}
            sx={{
              flex: 1, height: 8, borderRadius: 4, border: 0, p: 0, cursor: 'pointer',
              bgcolor: answers[i] ? (grade(guesses[i], answers[i]).pickedWinner ? colors.accent : colors.red) : i === current ? colors.textMed : colors.borderStrong,
            }}
          />
        ))}
      </Box>
      <MomentCard
        key={current}
        moment={puzzle.moments[current]}
        guess={guesses[current]}
        onGuess={(value) => setGuesses((prev) => prev.map((g, i) => (i === current ? value : g)))}
        onLock={() => lock(current)}
        answer={answers[current]}
        locking={locking}
      />
      {answers[current] && !finished && (
        <Button fullWidth variant="outlined" sx={{ mt: 1.5, minHeight: 44 }} onClick={() => setCurrent(answers.findIndex((a) => !a))}>
          Next moment
        </Button>
      )}
    </DailyGameShell>
  );
};

export default CallItGame;
