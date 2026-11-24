import React, { useState } from 'react';
import { Autocomplete, Box, Button, TextField, Typography } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { getTeamColor, readableOnDark } from '../../utils/teamColors';
import {
  IPL_SIDES, TOP_INTERNATIONAL, dayLabel, ordinal, ratingsClaim, routeTeam, useSides,
} from '../landing/TeamRatings';

// /team with no team picked (landing round 2, 24 Nov 2026): the ten IPL sides and the 12 T20I sides the landing card
// ranks, each a row to its team page, so "All squads", the menu's Teams and a bare /team all land somewhere useful.
// The ratings come from the landing card's fetch (shared, one per scope); while they load, or if they fail, the sides
// are still listed and tappable. Any other side is behind "Search any team".

const IPL_NAMES = { CSK: 'Chennai Super Kings', DC: 'Delhi Capitals', GT: 'Gujarat Titans', KKR: 'Kolkata Knight Riders',
  LSG: 'Lucknow Super Giants', MI: 'Mumbai Indians', PBKS: 'Punjab Kings', RCB: 'Royal Challengers Bengaluru',
  RR: 'Rajasthan Royals', SRH: 'Sunrisers Hyderabad' };

const GROUPS = {
  ipl: { kicker: 'IPL · 10 sides', scopeLine: 'Elo rating after each side\'s latest IPL match',
    fallback: IPL_SIDES.map((abbr) => ({ abbr, name: IPL_NAMES[abbr], page: abbr })) },
  intl: { kicker: 'T20Is · top 12', scopeLine: 'Elo rating after each side\'s latest T20I',
    fallback: TOP_INTERNATIONAL.map((name) => ({ abbr: name, name, page: name })) },
};

// Which group leads: ?scope=t20i (or ?league= anything but the IPL) puts T20Is first; otherwise the IPL, India-first.
export const groupOrder = (search) => {
  const p = new URLSearchParams(search);
  const scope = (p.get('scope') || '').toLowerCase();
  const league = (p.get('league') || '').toLowerCase();
  if (['t20i', 'intl', 'international'].includes(scope) || (league && !/ipl|indian premier/.test(league))) return ['intl', 'ipl'];
  return ['ipl', 'intl'];
};

const TeamRow = ({ side, last }) => {
  const swatch = readableOnDark(getTeamColor(side.name) || getTeamColor(side.abbr) || colors.textLo);
  return (
    // The app keeps the scroll position across routes, so a row low on the list would open its page mid-way down.
    <Box component={Link} to={routeTeam(side.page)} onClick={() => window.scrollTo(0, 0)}
      aria-label={side.rating ? `${side.name}: rated ${side.rating}, ${ordinal(side.rank)}` : side.name}
      sx={{ display: 'flex', alignItems: 'center', gap: 1.25, minHeight: 44, textDecoration: 'none', color: colors.textHi,
        borderBottom: last ? 0 : `1px solid ${colors.border}`, '&:hover .name': { color: colors.accent } }}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textFaint, width: 18, textAlign: 'right', flexShrink: 0 }}>
        {side.rank || ''}
      </Typography>
      <Box aria-hidden sx={{ width: 4, height: 22, borderRadius: 2, bgcolor: swatch, flexShrink: 0 }} />
      <Typography className="name" sx={{ flex: 1, minWidth: 0, fontFamily: fonts.body, fontWeight: 600, fontSize: 15,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {side.name}
      </Typography>
      {side.rating ? (
        <Typography sx={{ fontFamily: fonts.mono, fontWeight: 600, fontSize: 13, color: colors.textMed, flexShrink: 0,
          fontVariantNumeric: 'tabular-nums' }}>
          {side.rating}
        </Typography>
      ) : null}
      <Box aria-hidden sx={{ color: colors.textFaint, fontSize: 16, flexShrink: 0, width: 10 }}>›</Box>
    </Box>
  );
};

const TeamGroup = ({ scope }) => {
  const g = GROUPS[scope];
  const { state, sides, retry } = useSides(scope);
  const ready = state.status === 'ready' && sides.length > 0;
  const rows = ready ? sides : g.fallback;
  const latest = sides.reduce((m, s) => (String(s.last || '') > m ? String(s.last) : m), '');
  return (
    <Box component="section" aria-label={g.kicker} sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`,
      borderRadius: '20px', px: { xs: 1.75, md: 2.5 }, pt: 1.75, pb: 1.5 }}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase',
        color: colors.accent }}>
        {g.kicker}
      </Typography>
      {/* Claim: the landing card's, without the auction frame. A blank line while loading keeps the height. */}
      <Typography component="h2" sx={{ m: 0, mt: 0.75, mb: 0.5, fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 19, md: 22 },
        lineHeight: 1.15, color: colors.textHi, minHeight: 44 }}>
        {ready ? ratingsClaim(sides, scope) : (state.status === 'error' ? 'Pick a side.' : ' ')}
      </Typography>
      <Box component="nav" aria-label={`${g.kicker} team pages`}>
        {rows.map((s, i) => <TeamRow key={s.abbr} side={s} last={i === rows.length - 1} />)}
      </Box>
      <Box sx={{ mt: 1, pt: 1, borderTop: `1px solid ${colors.border}` }}>
        <Typography sx={{ fontSize: 12, lineHeight: 1.4, color: colors.textLo }}>
          {state.status === 'error' ? (
            <>
              Ratings couldn&apos;t load; the sides are listed A–Z.{' '}
              <Button type="button" onClick={retry} sx={{ minHeight: 44, minWidth: 0, p: 0, px: 0.5, color: colors.accent, fontSize: 12,
                fontFamily: fonts.mono, textTransform: 'none' }}>
                Try again
              </Button>
            </>
          ) : (
            <>{g.scopeLine}{latest ? `, to ${dayLabel(latest)}` : ''}. Tap a side for its page.</>
          )}
        </Typography>
        <Typography sx={{ fontSize: 12, color: colors.textFaint, mt: 0.25 }}>hindsightcricket.com · Data: Cricsheet</Typography>
      </Box>
    </Box>
  );
};

// Every other side, by name. The full list (GET /teams/) is asked for only when the box is opened.
const TeamSearch = () => {
  const navigate = useNavigate();
  const [teams, setTeams] = useState(null);
  const load = () => {
    if (teams) return;
    setTeams([]);
    fetch(`${config.API_URL}/teams/`).then((r) => r.json())
      .then((d) => setTeams((Array.isArray(d) ? d : []).sort((a, b) => a.full_name.localeCompare(b.full_name))))
      .catch(() => setTeams(null));
  };
  return (
    <Box component="section" aria-label="Search any team">
      <Typography component="h2" sx={{ m: 0, mb: 1, fontFamily: fonts.display, fontWeight: 700, fontSize: 18, color: colors.textHi }}>
        Search any team
      </Typography>
      <Autocomplete options={teams || []} loading={teams !== null && teams.length === 0} onOpen={load}
        getOptionLabel={(t) => t.full_name}
        onChange={(_, v) => v && navigate(`/team?team=${encodeURIComponent(v.full_name)}`)}
        renderInput={(params) => <TextField {...params} label="Any side: BBL, PSL, Associates…" onFocus={load}
          inputProps={{ ...params.inputProps, style: { fontSize: 16 } }} />} />
    </Box>
  );
};

const TeamList = () => {
  const location = useLocation();
  const order = groupOrder(location.search);
  React.useEffect(() => { document.title = 'Teams · Hindsight'; }, []);
  return (
    <Box sx={{ px: 2, pt: 2, pb: 3, maxWidth: { xs: 560, md: 1040 }, mx: 'auto', color: colors.textHi }}>
      <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 28, md: 34 } }}>Teams</Box>
      <Box sx={{ color: colors.textLo, fontSize: 14, mt: 0.5, mb: 1.75 }}>How good is a side, phase by phase? Pick one.</Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1.75, alignItems: 'start' }}>
        {order.map((scope) => <TeamGroup key={scope} scope={scope} />)}
      </Box>
      <Box sx={{ mt: 2.5, maxWidth: 520 }}>
        <TeamSearch />
      </Box>
    </Box>
  );
};

export default TeamList;
