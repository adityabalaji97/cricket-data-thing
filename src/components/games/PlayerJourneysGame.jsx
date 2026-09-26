/**
 * Player Journeys (daily). Guess the IPL player from their franchise path.
 *
 * The timeline (teams and years, pre-2015 seasons included) is shown up front. Four hints cost a
 * point each -- style, country, IPL numbers, initials -- and so does each wrong guess. Guesses
 * are picked from the pool's names (no spelling test) and checked server-side, so the answer is
 * never in the page until it is revealed. After the daily, "play a random one" is practice: it
 * does not touch the streak.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, Button, CircularProgress, TextField, Typography } from '@mui/material';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';
import DailyGameShell from './daily/DailyGameShell';
import { loadProgress, loadStats, recordFinish, saveProgress } from './daily/dailyStorage';

const GAME = 'player_journeys';
const MAX_POINTS = 5;
const MAX_GUESSES = 6;
const HINTS = [
  { key: 'style', icon: '🏏', label: 'Playing style' },
  { key: 'country', icon: '🌍', label: 'Country' },
  { key: 'numbers', icon: '📊', label: 'IPL numbers' },
  { key: 'initials', icon: '🔤', label: 'Initials' },
];

const api = (path) => fetch(`${config.API_URL}/games/player-journey${path}`).then((r) => (r.ok ? r.json() : Promise.reject(r.status)));

const isDone = (s) => s.solved || s.gaveUp || s.misses.length >= MAX_GUESSES;

const scoreOf = (s) => (s.solved ? Math.max(1, MAX_POINTS - Object.keys(s.hints).length - s.misses.length) : 0);

const JourneyTimeline = ({ journey }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
    {journey.map((stint, i) => (
      <Box key={`${stint.team}-${stint.years}`} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: i === journey.length - 1 ? colors.accent : colors.textFaint, flexShrink: 0 }} />
        <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, color: colors.textLo, width: 84, flexShrink: 0 }}>{stint.years}</Typography>
        <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18, color: colors.textHi }}>{stint.team}</Typography>
      </Box>
    ))}
  </Box>
);

const emptyState = () => ({ hints: {}, misses: [], solved: false, gaveUp: false, answer: null });

const PlayerJourneysGame = () => {
  const [puzzle, setPuzzle] = useState(null);
  const [names, setNames] = useState([]);
  const [state, setState] = useState(emptyState());
  const [pick, setPick] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  const load = (token) => {
    setPuzzle(null);
    setPick(null);
    api(`/puzzle${token ? `?puzzle=${token}` : ''}`)
      .then((data) => {
        setPuzzle(data);
        const saved = data.daily ? loadProgress(GAME, data.puzzle) : null;
        setState(saved || emptyState());
        if (data.daily) setStats(loadStats(GAME, data.puzzle));
        if (!saved) track('game_start', { game: GAME, number: data.number, practice: !data.daily });
      })
      .catch(() => setError("Couldn't load Player Journeys. Try again in a minute."));
  };

  useEffect(() => {
    load(null);
    api('/names').then((d) => setNames(d.names || [])).catch(() => {});
  }, []);

  const finished = isDone(state);
  const query = useMemo(() => (puzzle ? `puzzle=${encodeURIComponent(puzzle.puzzle)}` : ''), [puzzle]);

  const persist = (next) => {
    const wasDone = isDone(state);
    setState(next);
    if (puzzle?.daily) saveProgress(GAME, puzzle.puzzle, next);
    if (isDone(next) && !wasDone) {
      const score = scoreOf(next);
      if (puzzle?.daily) setStats(recordFinish(GAME, puzzle.puzzle, score));
      track('game_finish', { game: GAME, number: puzzle?.number, score, practice: !puzzle?.daily });
    }
  };

  const takeHint = async (key) => {
    if (state.hints[key] || finished) return;
    setBusy(true);
    try {
      const { value } = await api(`/hint?key=${key}&${query}`);
      persist({ ...state, hints: { ...state.hints, [key]: value } });
    } catch {
      setError('Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const guess = async () => {
    if (!pick || finished) return;
    setBusy(true);
    try {
      const result = await api(`/check?guess=${encodeURIComponent(pick)}&${query}`);
      if (result.correct) {
        persist({ ...state, solved: true, answer: result.answer });
      } else {
        const next = { ...state, misses: [...state.misses, pick] };
        if (next.misses.length >= MAX_GUESSES) {
          next.answer = (await api(`/reveal?${query}`)).answer;
        }
        persist(next);
      }
      setPick(null);
    } catch {
      setError('Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const giveUp = async () => {
    setBusy(true);
    try {
      const reveal = await api(`/reveal?${query}`);
      persist({ ...state, gaveUp: true, answer: reveal.answer });
    } finally {
      setBusy(false);
    }
  };

  const playPractice = () => load(`p${Math.random().toString(36).slice(2, 10)}`);

  if (error) return <Typography sx={{ p: 3, color: colors.textMed, textAlign: 'center' }}>{error}</Typography>;
  if (!puzzle || !stats) return <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>;

  const score = scoreOf(state);
  const misses = state.misses.length;
  const hintIcons = HINTS.map((h) => (state.hints[h.key] ? h.icon : '⬜')).join('');
  const shareText = `Player Journeys #${puzzle.number || ''} ${state.solved ? '✅' : '❌'} ${score}/${MAX_POINTS}\n`
    + `${hintIcons}${misses ? ` · ${misses} miss${misses === 1 ? '' : 'es'}` : ''}\n${window.location.origin}/games/player-journeys`;
  const resultLine = state.solved ? `${state.answer} · ${score}/${MAX_POINTS}` : `It was ${state.answer}`;

  return (
    <DailyGameShell
      game={GAME}
      title={puzzle.daily ? 'Player Journeys' : 'Player Journeys · practice'}
      number={puzzle.daily ? puzzle.number : null}
      rules="Who is it? Their IPL journey is below. Each hint, and each wrong guess, costs a point."
      stats={stats}
      finished={finished && puzzle.daily}
      resultLine={resultLine}
      shareText={shareText}
    >
      <Box sx={{ p: 2.25, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.border}` }}>
        <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo, letterSpacing: '0.08em', textTransform: 'uppercase', mb: 1.5 }}>
          IPL journey · {puzzle.seasons} seasons
        </Typography>
        <JourneyTimeline journey={puzzle.journey} />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1, mt: 1.5 }}>
        {HINTS.map((h) => (
          <Box key={h.key} sx={{ p: 1.25, borderRadius: 2, border: `1px solid ${colors.border}`, bgcolor: state.hints[h.key] ? colors.surface2 : 'transparent', minHeight: 64 }}>
            <Typography sx={{ fontSize: 12, color: colors.textLo }}>{h.icon} {h.label}</Typography>
            {state.hints[h.key] ? (
              <Typography sx={{ color: colors.textHi, fontSize: 14, fontWeight: 600, mt: 0.25 }}>{state.hints[h.key]}</Typography>
            ) : (
              <Button size="small" disabled={busy || finished} onClick={() => takeHint(h.key)} sx={{ mt: 0.25, px: 0, minHeight: 32 }}>
                Reveal (−1)
              </Button>
            )}
          </Box>
        ))}
      </Box>

      {!finished ? (
        <Box sx={{ mt: 2 }}>
          <Autocomplete
            options={names}
            value={pick}
            onChange={(_, value) => setPick(value)}
            renderInput={(params) => <TextField {...params} label="Search for a player" />}
            autoHighlight
          />
          <Box sx={{ display: 'flex', gap: 1, mt: 1.25 }}>
            <Button fullWidth variant="contained" disabled={!pick || busy} onClick={guess} sx={{ minHeight: 44 }}>Guess</Button>
            <Button variant="outlined" disabled={busy} onClick={giveUp} sx={{ minHeight: 44, flexShrink: 0 }}>Give up</Button>
          </Box>
          <Typography sx={{ color: colors.textLo, fontSize: 13, mt: 1 }}>
            {MAX_GUESSES - misses} guess{MAX_GUESSES - misses === 1 ? '' : 'es'} left{misses ? ` · not ${state.misses.join(', not ')}` : ''}
          </Typography>
        </Box>
      ) : !puzzle.daily ? (
        <Box sx={{ mt: 2, p: 2, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.borderStrong}` }}>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: colors.textHi }}>{resultLine}</Typography>
        </Box>
      ) : null}

      {finished && (
        <Button fullWidth variant="outlined" onClick={playPractice} sx={{ mt: 2, minHeight: 44 }}>
          Play a random one (practice)
        </Button>
      )}
    </DailyGameShell>
  );
};

export default PlayerJourneysGame;
