import React, { useEffect, useState } from 'react';
import { Box, Button, Snackbar, Typography } from '@mui/material';
import IosShareRoundedIcon from '@mui/icons-material/IosShareRounded';
import { colors, fonts } from '../../../theme/hindsightDark';
import { track } from '../../../utils/analytics';
import { timeToNextPuzzle } from './dailyStorage';

/**
 * Frame shared by the daily games: title and puzzle number, a one-line "how to play", the game
 * itself, and -- once finished -- the result, a spoiler-free share and the countdown to tomorrow.
 */
const DailyGameShell = ({
  game, title, number, rules, stats, finished, resultLine, shareText, children,
  practice = false, onPractice, onBackToDaily,
}) => {
  const [countdown, setCountdown] = useState(timeToNextPuzzle());
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setCountdown(timeToNextPuzzle()), 30000);
    return () => clearInterval(id);
  }, []);

  const share = async () => {
    track('share', { kind: 'game', game });
    try {
      if (navigator.share) {
        await navigator.share({ text: shareText });
        return;
      }
    } catch (error) {
      if (error?.name === 'AbortError') return;
    }
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
    } catch {
      // nothing else to try
    }
  };

  const statBox = (label, value) => (
    <Box sx={{ flex: 1, textAlign: 'center' }}>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 24, color: colors.textHi }}>{value}</Typography>
      <Typography sx={{ fontSize: 11, color: colors.textLo, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</Typography>
    </Box>
  );

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: { xs: 2, sm: 0 }, py: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 1, mb: 0.5 }}>
        <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 28, color: colors.textHi }}>
          {title}{practice ? <span style={{ color: colors.textLo, fontSize: 18 }}> · practice</span> : null}
        </Typography>
        {number ? <Typography sx={{ fontFamily: fonts.mono, color: colors.accent, fontSize: 14 }}>#{number}</Typography> : null}
      </Box>
      <Typography sx={{ color: colors.textLo, fontSize: 14, mb: 2 }}>{rules}</Typography>

      {children}

      {practice && (
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          {finished && onPractice && (
            <Button fullWidth variant="contained" onClick={onPractice} sx={{ minHeight: 44 }}>Another one</Button>
          )}
          {onBackToDaily && (
            <Button fullWidth variant="outlined" onClick={onBackToDaily} sx={{ minHeight: 44 }}>Back to today&apos;s</Button>
          )}
        </Box>
      )}
      {finished && practice && (
        <Typography sx={{ mt: 1.5, textAlign: 'center', fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: colors.textHi }}>
          {resultLine}
        </Typography>
      )}
      {finished && !practice && (
        <Box sx={{ mt: 3, p: 2.5, borderRadius: 3, bgcolor: colors.surface1, border: `1px solid ${colors.borderStrong}` }}>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, color: colors.textHi, mb: 0.5 }}>{resultLine}</Typography>
          <Typography component="pre" sx={{ fontFamily: fonts.mono, fontSize: 15, color: colors.textMed, whiteSpace: 'pre-wrap', m: 0, mb: 2 }}>
            {shareText.split('\n').slice(0, 2).join('\n')}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            {statBox('Played', stats.played)}
            {statBox('Streak', stats.currentStreak)}
            {statBox('Best streak', stats.maxStreak)}
          </Box>
          <Button fullWidth variant="contained" startIcon={<IosShareRoundedIcon />} onClick={share} sx={{ minHeight: 44 }}>
            Share result
          </Button>
          <Typography sx={{ textAlign: 'center', color: colors.textLo, fontSize: 13, mt: 1.5 }}>
            Next puzzle in {countdown}
          </Typography>
          {onPractice && (
            <Button fullWidth variant="outlined" onClick={onPractice} sx={{ mt: 1.5, minHeight: 44 }}>
              Play a random one (practice)
            </Button>
          )}
        </Box>
      )}
      <Snackbar open={copied} autoHideDuration={2000} onClose={() => setCopied(false)} message="Result copied" />
    </Box>
  );
};

export default DailyGameShell;
