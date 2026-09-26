import React, { useEffect, useState } from 'react';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { track } from '../../utils/analytics';
import DailyGameShell from './daily/DailyGameShell';
import { loadProgress, loadStats, recordFinish, saveProgress } from './daily/dailyStorage';

const GAME = 'higher_lower';
const signed = (v) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}`;

const PlayerCard = ({ card, hidden, label }) => (
  <Box sx={{ p: 2, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.border}`, flex: 1, minWidth: 0 }}>
    <Typography sx={{ fontFamily: fonts.mono, fontSize: 11, color: colors.textLo, letterSpacing: '0.08em', textTransform: 'uppercase' }}>{label}</Typography>
    <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, color: colors.textHi, mt: 0.5, lineHeight: 1.15 }}>{card.player}</Typography>
    <Typography sx={{ color: colors.textMed, fontSize: 14 }}>
      {card.competition} {card.season} · {card.runs} off {card.balls} (SR {card.strike_rate})
    </Typography>
    <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 34, mt: 1, color: hidden ? colors.textFaint : (card.impact >= 0 ? colors.accent : colors.red) }}>
      {hidden ? 'Impact ?' : `Impact ${signed(card.impact)}`}
    </Typography>
    {!hidden && card.raa !== undefined && (
      <Typography sx={{ color: colors.textLo, fontSize: 13 }}>RAA {signed(card.raa)} · WPA {card.wpa > 0 ? '+' : ''}{card.wpa}</Typography>
    )}
  </Box>
);

const HigherLowerGame = () => {
  const [puzzle, setPuzzle] = useState(null);
  const [revealed, setRevealed] = useState([]); // cards with impact, index 0.. current
  const [calls, setCalls] = useState([]); // 'up' | 'down' per guess
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${config.API_URL}/games/higher-lower/daily`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        setPuzzle(data);
        const saved = loadProgress(GAME, data.date);
        setRevealed(saved?.revealed || [data.cards[0]]);
        setCalls(saved?.calls || []);
        setOver(Boolean(saved?.over));
        setStats(loadStats(GAME, data.date));
        if (!saved) track('game_start', { game: GAME, number: data.number });
      })
      .catch(() => setError("Couldn't load today's Higher or Lower. Try again in a minute."));
  }, []);

  if (error) return <Typography sx={{ p: 3, color: colors.textMed, textAlign: 'center' }}>{error}</Typography>;
  if (!puzzle || !stats) return <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>;

  const total = puzzle.cards.length - 1;
  const correct = calls.filter((c) => c.right).length;
  const current = revealed[revealed.length - 1];
  const nextIndex = revealed.length;
  const next = puzzle.cards[nextIndex];

  const guess = async (direction) => {
    setBusy(true);
    try {
      const r = await fetch(`${config.API_URL}/games/higher-lower/reveal?index=${nextIndex}&date=${puzzle.date}`);
      const card = await r.json();
      const right = direction === 'up' ? card.impact >= current.impact : card.impact <= current.impact;
      const nextCalls = [...calls, { direction, right }];
      const nextRevealed = [...revealed, card];
      const finished = !right || nextIndex >= total;
      setCalls(nextCalls);
      setRevealed(nextRevealed);
      setOver(finished);
      saveProgress(GAME, puzzle.date, { revealed: nextRevealed, calls: nextCalls, over: finished });
      if (finished) {
        const score = nextCalls.filter((c) => c.right).length;
        setStats(recordFinish(GAME, puzzle.date, score));
        track('game_finish', { game: GAME, number: puzzle.number, score });
      }
    } catch {
      setError('Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const trail = calls.map((c) => (c.right ? (c.direction === 'up' ? '⬆️' : '⬇️') : '❌')).join('');
  const shareText = `Higher or Lower #${puzzle.number} · ${correct}/${total}${correct >= 5 ? ' 🔥' : ''}\n${trail}\n${window.location.origin}/games/higher-lower`;
  const lastCall = calls[calls.length - 1];

  return (
    <DailyGameShell
      game={GAME}
      title="Higher or Lower"
      number={puzzle.number}
      rules="Impact is the runs a batter added to their team's projected total, given the game situation. Is the next player-season's Impact higher or lower? One wrong call ends the run."
      stats={stats}
      finished={over}
      resultLine={`${correct} / ${total}`}
      shareText={shareText}
    >
      <Typography sx={{ fontFamily: fonts.mono, color: colors.textLo, fontSize: 13, mb: 1.5 }}>
        {correct} in a row {trail ? `· ${trail}` : ''}
      </Typography>
      {over ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {revealed.length > 1 && <PlayerCard card={revealed[revealed.length - 2]} label="Previous" />}
          <PlayerCard card={current} label={lastCall?.right ? 'Last one' : 'The one that got you'} />
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <PlayerCard card={current} label="Known" />
          <PlayerCard card={next} hidden label="Next: higher or lower?" />
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button fullWidth variant="contained" disabled={busy} onClick={() => guess('up')} sx={{ minHeight: 48 }}>⬆️ Higher</Button>
            <Button fullWidth variant="outlined" disabled={busy} onClick={() => guess('down')} sx={{ minHeight: 48 }}>⬇️ Lower</Button>
          </Box>
          {lastCall && (
            <Typography sx={{ color: colors.accent, fontSize: 14 }}>
              Right: {revealed[revealed.length - 2]?.player}&apos;s Impact was {signed(revealed[revealed.length - 2]?.impact ?? 0)}, {current.player}&apos;s {signed(current.impact)}.
            </Typography>
          )}
        </Box>
      )}
    </DailyGameShell>
  );
};

export default HigherLowerGame;
