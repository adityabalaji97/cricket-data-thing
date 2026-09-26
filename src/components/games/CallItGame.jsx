/**
 * Call It (daily). Five real chase moments with the batters at the crease and the model's win
 * probability; call whether the chasing side won. A point for each right call, and a ⭐ when the
 * right call went against the model (an upset).
 */
import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { getTeamColor, readableOnDark } from '../../utils/teamColors';
import { track } from '../../utils/analytics';
import DailyGameShell from './daily/DailyGameShell';
import usePuzzle from './daily/usePuzzle';
import { recordFinish, saveProgress } from './daily/dailyStorage';

const GAME = 'call_it';
const emptyProgress = () => ({ calls: [] }); // { call, answer, right, upset } per moment

const tileOf = (c) => (c.right ? (c.upset ? '⭐' : '🟩') : '🟥');

const WinBar = ({ team, probability }) => {
  const pct = Math.round(probability * 100);
  const color = readableOnDark(getTeamColor(team) || colors.accent);
  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography sx={{ fontSize: 13, color: colors.textLo }}>Model win probability</Typography>
        <Typography sx={{ fontFamily: fonts.mono, fontSize: 14, fontWeight: 700, color: colors.textHi }}>{pct}%</Typography>
      </Box>
      <Box sx={{ height: 10, borderRadius: 5, bgcolor: colors.surface2, overflow: 'hidden' }}>
        <Box sx={{ width: `${pct}%`, height: '100%', bgcolor: color }} />
      </Box>
    </Box>
  );
};

const MomentCard = ({ moment }) => (
  <Box sx={{ p: 2.25, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.border}` }}>
    <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
      {moment.competition} {moment.season} · {moment.venue?.split(',')[0]}
    </Typography>
    <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, color: colors.textHi, mt: 0.75, lineHeight: 1.2 }}>
      {moment.batting_team} need {moment.runs_needed} off {moment.balls_left}
    </Typography>
    <Typography sx={{ color: colors.textMed, fontSize: 14, mt: 0.5 }}>
      {moment.score} chasing {moment.target} against {moment.bowling_team} · {moment.wickets_left} wicket{moment.wickets_left === 1 ? '' : 's'} left
    </Typography>
    {moment.batters?.length > 0 && (
      <Box sx={{ mt: 1.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {moment.batters.map((b) => (
          <Box key={b.name} sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
            <Typography sx={{ color: colors.textHi, fontSize: 15 }}>🏏 {b.name}</Typography>
            <Typography sx={{ fontFamily: fonts.mono, color: colors.textMed, fontSize: 15 }}>{b.runs}* ({b.balls})</Typography>
          </Box>
        ))}
      </Box>
    )}
    <WinBar team={moment.batting_team} probability={moment.model_win_probability} />
  </Box>
);

const CallItGame = () => {
  const {
    puzzle, progress, setProgress, stats, setStats, error, practice, daily,
  } = usePuzzle(GAME, '/games/call-it/daily', emptyProgress);
  const [showing, setShowing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(null);

  if (error) return <Typography sx={{ p: 3, color: colors.textMed, textAlign: 'center' }}>{error}</Typography>;
  if (!puzzle || !progress || !stats) return <Box sx={{ py: 6, textAlign: 'center' }}><CircularProgress /></Box>;

  const total = puzzle.moments.length;
  const { calls } = progress;
  const finished = calls.length >= total;
  const index = showing ?? (finished ? total - 1 : calls.length);
  const moment = puzzle.moments[index];
  const current = calls[index];
  const correct = calls.filter((c) => c.right).length;
  const upsets = calls.filter((c) => c.right && c.upset).length;

  const makeCall = async (call) => {
    if (current || busy) return;
    setBusy(true);
    setFailure(null);
    try {
      const r = await fetch(`${config.API_URL}/games/call-it/reveal?index=${index}&puzzle=${encodeURIComponent(puzzle.puzzle)}`);
      if (!r.ok) throw new Error(r.status);
      const answer = await r.json();
      const right = call === answer.chasing_side_won;
      const modelFavoured = answer.model_win_probability >= 0.5;
      const upset = answer.chasing_side_won !== modelFavoured;
      const next = { calls: [...calls, { call, answer, right, upset }] };
      setProgress(next);
      setShowing(index);
      if (puzzle.daily) saveProgress(GAME, puzzle.puzzle, next);
      if (next.calls.length >= total) {
        const score = next.calls.filter((c) => c.right).length;
        if (puzzle.daily) setStats(recordFinish(GAME, puzzle.puzzle, score));
        track('game_finish', { game: GAME, number: puzzle.number, score, practice: !puzzle.daily });
      }
    } catch {
      setFailure('Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const tiles = calls.map(tileOf).join('');
  const shareText = `Call It #${puzzle.number} ${tiles}\n${correct}/${total}${upsets ? ` · called ${upsets} upset${upsets === 1 ? '' : 's'}` : ''}\n${window.location.origin}/games/call-it`;

  return (
    <DailyGameShell
      game={GAME}
      title="Call It"
      number={puzzle.daily ? puzzle.number : null}
      rules="Five real run chases, frozen mid-chase. The model gives its win probability; did the chasing side actually win? ⭐ for calling an upset."
      stats={stats}
      finished={finished}
      resultLine={`${correct} / ${total}${upsets ? ` · ${upsets} ⭐` : ''}`}
      shareText={shareText}
      practice={!puzzle.daily}
      onPractice={() => { setShowing(null); practice(); }}
      onBackToDaily={() => { setShowing(null); daily(); }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography sx={{ fontFamily: fonts.mono, color: colors.textLo, fontSize: 13 }}>Moment {index + 1} of {total}</Typography>
        <Typography sx={{ fontFamily: fonts.mono, color: colors.textLo, fontSize: 13 }}>{correct} right {tiles}</Typography>
      </Box>

      <MomentCard key={index} moment={moment} />

      {!current ? (
        <Box sx={{ mt: 2 }}>
          <Typography sx={{ color: colors.textHi, fontWeight: 700, mb: 1, textAlign: 'center' }}>
            Did {moment.batting_team} win it?
          </Typography>
          <Box sx={{ display: 'flex', gap: 1.25 }}>
            <Button fullWidth variant="contained" disabled={busy} onClick={() => makeCall(true)} sx={{ minHeight: 52, fontSize: 16 }}>Yes, they won</Button>
            <Button fullWidth variant="outlined" disabled={busy} onClick={() => makeCall(false)} sx={{ minHeight: 52, fontSize: 16 }}>No, they lost</Button>
          </Box>
          {failure && <Typography sx={{ color: colors.red, fontSize: 13, mt: 1 }}>{failure}</Typography>}
        </Box>
      ) : (
        <Box sx={{ mt: 2, p: 2, borderRadius: 3, border: `1px solid ${current.right ? colors.accent : colors.red}` }}>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: current.right ? colors.accent : colors.red }}>
            {current.right ? (current.upset ? '⭐ Upset called!' : 'Right call') : 'Wrong call'}
          </Typography>
          <Typography sx={{ color: colors.textMed, fontSize: 14, mt: 0.5 }}>
            {current.answer.winner} won
            {current.upset ? `, against the model's ${Math.round((current.answer.chasing_side_won ? current.answer.model_win_probability : 1 - current.answer.model_win_probability) * 100)}% for them` : ''}.
            {' '}{current.answer.date}
          </Typography>
          <Box component={RouterLink} to={`/scorecard/${current.answer.match_id}`} sx={{ color: colors.accent, fontSize: 13, display: 'inline-block', mt: 0.75 }}>
            See the scorecard →
          </Box>
          {!finished && (
            <Button fullWidth variant="contained" onClick={() => setShowing(null)} sx={{ mt: 1.5, minHeight: 48 }}>
              Next moment
            </Button>
          )}
        </Box>
      )}

      {finished && (
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 2 }}>
          {calls.map((c, i) => (
            <Button key={i} size="small" variant={i === index ? 'contained' : 'outlined'} onClick={() => setShowing(i)} sx={{ minWidth: 40, minHeight: 36, px: 0 }}>
              {tileOf(c)}
            </Button>
          ))}
        </Box>
      )}
    </DailyGameShell>
  );
};

export default CallItGame;
