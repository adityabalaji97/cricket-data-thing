import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import { colors, fonts } from '../../theme/hindsightDark';
import { PROMISE, TAGLINE } from '../../brand';
import { track } from '../../utils/analytics';

// Landing plan L1: the promise and the ask box above everything. Plain-words questions outnumber filter runs about
// four to one, so the box is the page's one lime action. A question goes to /query?nl=, as the header search's
// fallback does. public/index.html draws the same block before the app loads (L6); keep the two in step.

// The example chips: a hand-kept list, never visitors' raw text (it sits on the most-viewed spot on the site). Each
// is a question people asked (the Fable review's picks and the query log, Nov 2026), paired with a stored query
// checked to answer exactly what its label says, so a tap opens the answer without a model call.
// Owner: curate this list (LANDING_BUILD_LOG.md).
const q = (label, search) => ({ q: label, to: `/query?${search}&q=${encodeURIComponent(label)}` });
export const EXAMPLES = [
  q('Rinku Singh vs pace', 'batters=Rinku+Singh&bowl_kind=pace+bowler&group_by=year&fmt=mens-t20'),
  q('Jurel vs Buttler, by phase', 'batters=Dhruv+Jurel&batters=Jos+Buttler&group_by=batter&group_by=phase&fmt=mens-t20'),
  q('Sanju Samson vs pace', 'batters=Sanju+Samson&bowl_kind=pace+bowler&group_by=year&fmt=mens-t20'),
  q('Tilak Varma at the death, by length', 'batters=Tilak+Varma&over_min=15&over_max=19&group_by=length&fmt=mens-t20'),
  q('Shubman Gill since 2024, by phase', 'batters=Shubman+Gill&start_date=2024-01-01&group_by=phase&fmt=mens-t20'),
  q('New Zealand bowling at the death since 2024', 'bowling_teams=New+Zealand&start_date=2024-01-01&over_min=15&over_max=19&group_by=bowler&fmt=mens-t20'),
];

// Two a day, in IST, cycling through the list.
export const examplesFor = (now = Date.now(), n = 2) => {
  const day = Math.floor((now + 5.5 * 3600e3) / 864e5);
  const start = (day * n) % EXAMPLES.length;
  return Array.from({ length: n }, (_, i) => EXAMPLES[(start + i) % EXAMPLES.length]);
};

const AskHero = ({ source = 'home', headingLevel = 'h1' }) => {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [examples] = useState(() => examplesFor());

  const submit = (event) => {
    event.preventDefault();
    const q = text.trim();
    if (!q) return;
    track('landing_ask', { source });
    navigate(`/query?nl=${encodeURIComponent(q)}`);
  };

  return (
    <Box component="section" aria-label="Ask Hindsight" sx={{ mb: { xs: 3, md: 4.5 } }}>
      <Typography component={headingLevel} sx={{ m: 0, color: colors.textHi, fontFamily: fonts.display, fontWeight: 700,
        fontSize: { xs: 27, md: 38 }, lineHeight: 1.1, letterSpacing: '-0.005em' }}>
        Cricket, ball by ball.{' '}
        <Box component="span" sx={{ color: colors.accent }}>{TAGLINE}.</Box>
      </Typography>
      <Typography sx={{ color: colors.textLo, fontFamily: fonts.body, fontSize: { xs: 14, md: 16 }, mt: 0.75 }}>
        {PROMISE}
      </Typography>
      <Box component="form" role="search" onSubmit={submit}
        sx={{ mt: 1.75, maxWidth: 640, height: 54, display: 'flex', alignItems: 'center', gap: 1, pl: 1.75, pr: 0.5,
          borderRadius: '14px', border: `1.5px solid ${colors.accent}`, bgcolor: colors.input,
          '&:focus-within': { boxShadow: '0 0 0 3px rgba(182,242,74,0.18)' } }}>
        <Box component="input" type="search" enterKeyHint="search" aria-label="Ask a cricket question in plain words"
          placeholder="Ask about a player, phase or matchup" value={text} onChange={(e) => setText(e.target.value)}
          sx={{ flex: 1, minWidth: 0, height: '100%', border: 0, outline: 0, bgcolor: 'transparent', color: colors.textHi,
            fontFamily: fonts.body, fontSize: 16, '&::placeholder': { color: colors.textLo, opacity: 1 },
            '&::-webkit-search-cancel-button': { display: 'none' } }} />
        <Box component="button" type="submit" aria-label="Ask"
          sx={{ flexShrink: 0, width: 44, height: 44, display: 'grid', placeItems: 'center', border: 0, borderRadius: '10px',
            bgcolor: colors.accent, color: colors.bg, cursor: 'pointer', '&:hover': { bgcolor: colors.accentHover } }}>
          <ArrowForwardRoundedIcon />
        </Box>
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1.25 }}>
        {examples.map((ex) => (
          <Box key={ex.q} component={Link} to={ex.to} onClick={() => track('landing_example', { source })}
            sx={{ display: 'inline-flex', alignItems: 'center', minHeight: 44, px: 1.5, maxWidth: '100%', borderRadius: 999,
              border: `1px solid ${colors.borderStrong}`, color: colors.textMed, fontFamily: fonts.body, fontSize: 14,
              textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              '&:hover': { borderColor: 'rgba(182,242,74,0.45)', color: colors.textHi } }}>
            {ex.q}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default AskHero;
