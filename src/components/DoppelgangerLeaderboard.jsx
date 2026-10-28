import React, { useEffect, useState } from 'react';
import { Autocomplete, Box, Skeleton, TextField } from '@mui/material';
import { Link } from 'react-router-dom';
import config from '../config';
import { colors, fonts } from '../theme/hindsightDark';
import TwinsSection from './playerProfile/TwinsSection';

// Doppelgängers (DOPPELGANGER_PLAN.md): the statistical twins engine as a page. Pick any player for his twin map, or
// browse the closest pairs and the players with no close twin, per role. Careers since Jan 2024 against strong sides
// (major leagues + top-12 T20Is), matched on how a player plays: usage, scoring shape, shot mix and pace v spin for
// batters; usage, lengths, lines and outcomes for bowlers.

const ROLES = [['bat', 'Batters'], ['bowl', 'Bowlers'], ['allround', 'All-rounders']];
const COMMON_SURNAMES = new Set(['Sharma', 'Yadav', 'Singh', 'Kumar', 'Patel', 'Khan', 'Iyer', 'Pandya']);
const short = (name) => {
  const parts = name.split(' ');
  const last = parts[parts.length - 1];
  return parts.length > 1 && !COMMON_SURNAMES.has(last) ? last : parts[0];
};

const playerLink = (name) => `/player?name=${encodeURIComponent(name)}&autoload=true`;

const Row = ({ left, right, gap, note, accent }) => (
  <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, py: 1, borderBottom: `1px solid ${colors.border}` }}>
    <Box sx={{ flex: 1, minWidth: 0 }}>
      <Box sx={{ fontFamily: fonts.display, fontWeight: 600, fontSize: 15.5 }}>
        <Box component={Link} to={playerLink(left)} sx={{ color: colors.textHi, textDecoration: 'none', '&:hover': { color: colors.accent } }}>{left}</Box>
        {right && (
          <>
            <Box component="span" sx={{ color: colors.textLo, fontWeight: 500 }}>{' and '}</Box>
            <Box component={Link} to={playerLink(right)} sx={{ color: colors.textHi, textDecoration: 'none', '&:hover': { color: colors.accent } }}>{right}</Box>
          </>
        )}
      </Box>
      {note && <Box sx={{ fontSize: 12, color: colors.textLo, mt: 0.25 }}>{note}</Box>}
    </Box>
    <Box sx={{ fontFamily: fonts.mono, fontSize: 12, color: accent ? colors.accent : colors.textMed, whiteSpace: 'nowrap' }}>{gap} pts</Box>
  </Box>
);

const Block = ({ title, sub, children }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column' }}>
    <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 19 }}>{title}</Box>
    <Box sx={{ color: colors.textLo, fontSize: 12.5, mb: 0.5 }}>{sub}</Box>
    {children}
  </Box>
);

const DoppelgangerLeaderboard = () => {
  const [board, setBoard] = useState(null);
  const [failed, setFailed] = useState(false);
  const [role, setRole] = useState('bat');
  const [players, setPlayers] = useState([]);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    fetch(`${config.API_URL}/twins/board`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setBoard)
      .catch(() => setFailed(true));
    fetch(`${config.API_URL}/players`).then((r) => r.json()).then(setPlayers).catch(() => {});
  }, []);

  const b = board?.[role];
  const who = role === 'bowl' ? 'bowlers' : role === 'allround' ? 'all-rounders' : 'batters';

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto', px: 2, py: 2, display: 'flex', flexDirection: 'column', gap: 2.5, color: colors.textHi }}>
      <Box>
        <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 30, lineHeight: 1.1 }}>Doppelgängers</Box>
        <Box sx={{ color: colors.textMed, fontSize: 14, mt: 0.75, maxWidth: '62ch' }}>
          Who plays like whom. Each player is placed on how he plays (when he bats or bowls, how he scores or what he
          concedes, his shot mix, lengths and lines) as percentiles of everyone in the pool, and matched to the
          nearest. Careers since January 2024, in the major leagues and T20Is between top-12 sides.
        </Box>
      </Box>

      <Autocomplete
        options={players}
        value={picked}
        onChange={(_, v) => setPicked(v)}
        renderInput={(params) => <TextField {...params} label="Find a player's doppelgängers" size="small" />}
        sx={{ maxWidth: 420 }}
      />
      {picked && (
        <Box sx={{ border: `1px solid ${colors.borderStrong}`, borderRadius: '16px', p: 1.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 1 }}>
            <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{picked}</Box>
            <Box component={Link} to={playerLink(picked)} sx={{ fontSize: 12.5, color: colors.accent }}>Profile →</Box>
          </Box>
          <TwinsSection playerName={picked}
            fallback={<Box sx={{ color: colors.textLo, fontSize: 13.5 }}>{`${picked} hasn't played enough against strong sides since 2024 (120+ balls in two seasons) to be matched.`}</Box>} />
        </Box>
      )}

      <Box role="tablist" aria-label="Role" sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
        {ROLES.map(([key, name]) => (
          <Box key={key} component="button" role="tab" aria-selected={role === key} onClick={() => setRole(key)}
            sx={{
              all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13.5, px: 1.75, py: '4px',
              borderRadius: '999px', bgcolor: role === key ? colors.accent : 'transparent', color: role === key ? colors.bg : colors.textLo,
              '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
            }}>
            {name}
          </Box>
        ))}
      </Box>

      {failed && <Box sx={{ color: colors.textLo }}>The doppelgängers board couldn't load. Try again in a minute.</Box>}
      {!board && !failed && <Skeleton variant="rounded" height={320} sx={{ bgcolor: colors.surface2 }} />}
      {b && (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
          <Block title="Closest pairs" sub={`The most alike ${who}, of ${b.pool}. Most have a twin within ${b.typical_gap_points} points.`}>
            {b.pairs.map((p, i) => (
              <Row key={`${p.player}-${p.twin}`} left={p.player} right={p.twin} gap={p.gap_points} accent={i < 3}
                note={p.same?.length ? `Same: ${p.same.join(', ')}` : null} />
            ))}
          </Block>
          <Block title="No close twin" sub={`The ${who} furthest from anyone else: their game is their own.`}>
            {b.unique.map((u) => (
              <Row key={u.player} left={u.player} gap={u.gap_points} note={`Nearest: ${short(u.twin)}`} />
            ))}
          </Block>
        </Box>
      )}
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
        Gap: the typical percentile-point difference across the features compared, each group weighted equally. Shot-tracked
        players are matched with each other. Data: Hindsight · Himanish Ganjoo &amp; TechRadar, Cricsheet.
      </Box>
    </Box>
  );
};

export default DoppelgangerLeaderboard;
