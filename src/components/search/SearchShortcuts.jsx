import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';
import { Link } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { readRecentEntities } from '../../utils/recentEntities';

// Under the search box: what this device opened last, and what people opened this week (GET /search/popular,
// crawlers excluded), for players, teams and venues. A type with nothing popular yet falls back to a few staples.

const FALLBACK = {
  players: ['Virat Kohli', 'Jasprit Bumrah', 'Abhishek Sharma', 'Hardik Pandya'],
  teams: ['India', 'Chennai Super Kings', 'Mumbai Indians', 'Royal Challengers Bengaluru'],
  venues: ['Wankhede Stadium', 'M Chinnaswamy Stadium', 'Eden Gardens', 'MA Chidambaram Stadium'],
};
const KINDS = [['players', 'Players', 'player'], ['teams', 'Teams', 'team'], ['venues', 'Venues', 'venue']];
const href = (type, name) => (type === 'player' ? `/player?name=${encodeURIComponent(name)}`
  : type === 'team' ? `/team?team=${encodeURIComponent(name)}` : `/venue?venue=${encodeURIComponent(name)}`);

const Eyebrow = ({ children }) => (
  <Box sx={{ fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.textLo, mb: 0.75 }}>{children}</Box>
);

const Pill = ({ to, children, tone }) => (
  <Box component={Link} to={to}
    sx={{ border: `1px solid ${tone === 'recent' ? colors.borderStrong : 'rgba(182,242,74,0.4)'}`, color: tone === 'recent' ? colors.textHi : colors.accent,
      borderRadius: '999px', px: 1.4, py: 0.6, fontSize: 14, textDecoration: 'none', whiteSpace: 'nowrap', maxWidth: '100%',
      overflow: 'hidden', textOverflow: 'ellipsis', '&:hover': { borderColor: colors.accent } }}>
    {children}
  </Box>
);

const SearchShortcuts = () => {
  const [recent] = useState(readRecentEntities);
  const [popular, setPopular] = useState(null);
  useEffect(() => {
    fetch(`${config.API_URL}/search/popular`).then((r) => (r.ok ? r.json() : null)).then(setPopular).catch(() => setPopular(null));
  }, []);
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.25, maxWidth: 640, mx: 'auto', width: '100%' }}>
      {recent.length > 0 && (
        <Box>
          <Eyebrow>Your recent</Eyebrow>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {recent.map((e) => <Pill key={`${e.type}-${e.name}`} to={href(e.type, e.name)} tone="recent">{e.name}</Pill>)}
          </Box>
        </Box>
      )}
      {KINDS.map(([key, label, type]) => {
        const names = (popular?.[key] || []).map((x) => x.name);
        const list = names.length >= 3 ? names : [...new Set([...names, ...FALLBACK[key]])].slice(0, 6);
        return (
          <Box key={key}>
            <Eyebrow>{`Popular this week · ${label}`}</Eyebrow>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {list.map((n) => <Pill key={n} to={href(type, n)}>{n}</Pill>)}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
};

export default SearchShortcuts;
