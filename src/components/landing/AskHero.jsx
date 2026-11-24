import React, { useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { PROMISE, TAGLINE } from '../../brand';
import { track } from '../../utils/analytics';

// Landing plan L1: the promise and the ask box above everything. Plain-words questions outnumber filter runs about
// four to one, so the box is the page's one lime action. A question goes to /query?nl=, as the header search's
// fallback does. public/index.html draws the same block before the app loads (L6); keep the two in step.

// Shown when /query-recent has nothing usable: questions people have asked, India first.
export const FALLBACK_EXAMPLES = [
  { q: 'Rinku Singh vs pace', to: `/query?nl=${encodeURIComponent('Rinku Singh vs pace')}` },
  { q: 'Jurel vs Buttler, by phase', to: `/query?nl=${encodeURIComponent('Jurel vs Buttler, by phase')}` },
];

// A recent question makes a good chip if it reads as a question someone would tap: short, not truncated, not a
// filter-chip trail ("Sanju Samson … Batting at 3,4,5"), and capitalised as a name would be ("India vs australia"
// is someone's quick typing, not a showcase).
const LOWERCASE_SIDE = /\b(india|australia|england|pakistan|africa|zealand|lanka|indies|afghanistan|bangladesh|ireland|zimbabwe)\b/;
export const goodExample = (item) => {
  const q = String(item?.q || '').trim();
  return q.length >= 12 && q.length <= 40 && !q.includes('…') && /^[A-Z]/.test(q) && q.includes(' ')
    && !LOWERCASE_SIDE.test(q);
};

export const pickExamples = (items, n = 2) => {
  const seen = new Set();
  const picked = [];
  for (const item of items || []) {
    const key = String(item.q || '').trim().toLowerCase();
    // Two chips that are one question with a year added would waste the second slot.
    if (!goodExample(item) || [...seen].some((s) => s.startsWith(key) || key.startsWith(s))) continue;
    seen.add(key);
    // The stored search re-opens the parsed query without asking the model again.
    picked.push({ q: item.q.trim(), to: item.search ? `/query${item.search}` : `/query?nl=${encodeURIComponent(item.q.trim())}` });
    if (picked.length === n) break;
  }
  return picked.length === n ? picked : FALLBACK_EXAMPLES;
};

const AskHero = ({ source = 'home', headingLevel = 'h1' }) => {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [examples, setExamples] = useState(FALLBACK_EXAMPLES);

  useEffect(() => {
    let cancelled = false;
    fetch(`${config.API_URL}/query-recent`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled) setExamples(pickExamples(d?.items)); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

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
          placeholder="Ask anything: Rinku Singh vs pace" value={text} onChange={(e) => setText(e.target.value)}
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
