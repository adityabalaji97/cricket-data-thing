import React, { useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, Button, Chip, CircularProgress, MenuItem, TextField, Typography } from '@mui/material';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';

/**
 * /scorecards: every past scorecard, newest first (GET /recent-matches/browse, services/match_browse.py), filtered by
 * competition, team, opponent, year, or "on this day" (today's month and day in every year). Filters live in the URL,
 * so any view can be shared: /scorecards?team=India&opponent=West%20Indies, /scorecards?on=10-16.
 * Each card opens the scorecard and shows the match's biggest Impact (none before 2015, when Impact starts).
 */

const PAGE = 24;
const FIRST_YEAR = 2005;
const FILTER_KEYS = ['competition', 'team', 'opponent', 'year', 'on'];

const todayMonthDay = () => {
  const d = new Date();
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const formatDate = (iso) => (iso
  ? new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  : '');

const monthDayLabel = (md) => {
  const [m, d] = md.split('-').map(Number);
  return new Date(2000, m - 1, d).toLocaleDateString('en-GB', { day: 'numeric', month: 'long' });
};

const signed = (v) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}`;

const fieldSx = {
  '& .MuiOutlinedInput-root': { bgcolor: colors.input, borderRadius: '10px', fontSize: 14 },
  '& .MuiInputLabel-root': { fontSize: 14 },
};

const MatchRow = ({ match }) => {
  const scores = match.innings_scores || [];
  const line = (i) => scores[i] ? `${scores[i].runs}/${scores[i].wickets}` : null;
  return (
    <Box component={Link} to={`/scorecard/${match.match_id}`} sx={{
      display: 'block', textDecoration: 'none', color: 'inherit', p: 1.75, borderRadius: '14px',
      bgcolor: colors.surface2, border: `1px solid ${colors.border}`,
      '&:hover': { borderColor: colors.borderStrong },
    }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography sx={{ fontSize: 11.5, fontWeight: 700, letterSpacing: '0.06em', color: colors.accent, textTransform: 'uppercase' }}>
          {match.competition_display || match.competition}
        </Typography>
        <Typography sx={{ fontSize: 12, color: colors.textLo }}>{formatDate(match.date)}</Typography>
      </Box>
      {[0, 1].map((i) => {
        // innings_scores carry full names; the card shows the short ones (match.team1/team2), in batting order.
        const full = scores[i]?.team;
        const name = full === match.team1_full ? match.team1 : full === match.team2_full ? match.team2
          : full || (i === 0 ? match.team1 : match.team2);
        const won = match.winner && (name === match.winner);
        return (
          <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
            <Typography noWrap sx={{ fontSize: 15, fontWeight: won ? 700 : 500, color: won ? colors.textHi : colors.textMed }}>{name}</Typography>
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 14, color: won ? colors.textHi : colors.textMed, whiteSpace: 'nowrap' }}>
              {line(i) || ''}
              {scores[i] && <Box component="span" sx={{ color: colors.textLo, fontSize: 12 }}>{` (${scores[i].overs})`}</Box>}
            </Typography>
          </Box>
        );
      })}
      <Typography sx={{ fontSize: 12.5, color: colors.textLo, mt: 0.75 }}>{match.result_text}</Typography>
      {match.top && (
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75, mt: 1, pt: 1, borderTop: `1px solid ${colors.border}` }}>
          <Typography sx={{ fontSize: 12, color: colors.textLo }}>Top Impact</Typography>
          <Typography noWrap sx={{ fontSize: 13, color: colors.textHi, fontWeight: 600 }}>{match.top.name}</Typography>
          <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, color: match.top.impact >= 0 ? colors.accent : colors.red, ml: 'auto' }}>
            {signed(match.top.impact)}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

const ScorecardsBrowse = () => {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) || ''])), [params]);
  const [options, setOptions] = useState({ competitions: [], teams: [] });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${config.API_URL}/recent-matches/discover`, { params: { competition: 'all', per_group: 1, limit: 1 } })
      .then((r) => setOptions({
        competitions: r.data?.filter_options?.competitions || [],
        teams: (r.data?.filter_options?.teams || []).map((t) => t.full_name || t.value),
      }))
      .catch(() => {});
  }, []);

  const query = useMemo(() => ({
    competition: filters.competition || 'all',
    team: filters.team || undefined,
    opponent: filters.opponent || undefined,
    year: filters.year || undefined,
    month_day: filters.on || undefined,
  }), [filters]);

  const load = (offset) => {
    setLoading(true);
    setError(null);
    return axios.get(`${config.API_URL}/recent-matches/browse`, { params: { ...query, limit: PAGE, offset } })
      .then((r) => setResult((prev) => (offset && prev ? { ...r.data, matches: [...prev.matches, ...r.data.matches] } : r.data)))
      .catch(() => setError('Could not load scorecards. Try again in a moment.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(0); }, [query]); // eslint-disable-line react-hooks/exhaustive-deps

  const setFilter = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  const years = useMemo(() => {
    const now = new Date().getFullYear();
    return Array.from({ length: now - FIRST_YEAR + 1 }, (_, i) => String(now - i));
  }, []);
  const today = todayMonthDay();
  const active = FILTER_KEYS.some((k) => filters[k]);

  return (
    <Box sx={{ maxWidth: 760, mx: 'auto', px: { xs: 2, sm: 3 }, py: 2.5 }}>
      <Typography component="h1" sx={{ fontSize: 26, fontWeight: 800, color: colors.textHi }}>Scorecards</Typography>
      <Typography sx={{ fontSize: 14, color: colors.textLo, mt: 0.5, mb: 2 }}>
        Every match we have, with Impact and win probability from 2015 on. Filter by competition, team, year or date.
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Chip label={`On this day · ${monthDayLabel(today)}`} clickable
          onClick={() => setFilter('on', filters.on === today ? '' : today)}
          sx={{ bgcolor: filters.on === today ? colors.accent : colors.surface2, color: filters.on === today ? colors.bg : colors.textMed, fontWeight: 600 }} />
        {filters.on && filters.on !== today && (
          <Chip label={`On ${monthDayLabel(filters.on)}`} onDelete={() => setFilter('on', '')} sx={{ bgcolor: colors.accent, color: colors.bg }} />
        )}
        {active && <Chip label="Clear filters" variant="outlined" onClick={() => setParams(new URLSearchParams(), { replace: true })} />}
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: '1.2fr 0.8fr 1.5fr 1.5fr' }, gap: 1.25, mb: 2.5 }}>
        <TextField select size="small" label="Competition" value={filters.competition || 'all'} sx={fieldSx}
          onChange={(e) => setFilter('competition', e.target.value === 'all' ? '' : e.target.value)}>
          {(options.competitions.length ? options.competitions : [{ key: 'all', label: 'All' }]).map((c) => (
            <MenuItem key={c.key} value={c.key}>{c.label}</MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Year" value={filters.year} sx={fieldSx}
          onChange={(e) => setFilter('year', e.target.value)}>
          <MenuItem value="">Any</MenuItem>
          {years.map((y) => <MenuItem key={y} value={y}>{y}</MenuItem>)}
        </TextField>
        <Autocomplete size="small" options={options.teams} value={filters.team || null} sx={{ ...fieldSx, gridColumn: { xs: '1 / -1', sm: 'auto' } }}
          onChange={(_, v) => setFilter('team', v || '')}
          renderInput={(p) => <TextField {...p} label="Team" />} />
        <Autocomplete size="small" options={options.teams} value={filters.opponent || null} sx={{ ...fieldSx, gridColumn: { xs: '1 / -1', sm: 'auto' } }}
          onChange={(_, v) => setFilter('opponent', v || '')} disabled={!filters.team}
          renderInput={(p) => <TextField {...p} label="Against" />} />
      </Box>

      {result && (
        <Typography sx={{ fontSize: 13, color: colors.textLo, mb: 1.25 }}>
          {`${result.total.toLocaleString('en-US')} ${result.total === 1 ? 'match' : 'matches'}`}
        </Typography>
      )}
      {error && <Typography sx={{ color: colors.red, fontSize: 14, mb: 2 }}>{error}</Typography>}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1.25 }}>
        {(result?.matches || []).map((m) => <MatchRow key={m.match_id} match={m} />)}
      </Box>

      {result && !result.matches.length && !loading && (
        <Typography sx={{ color: colors.textLo, fontSize: 14, mt: 2 }}>No matches for these filters.</Typography>
      )}
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2.5 }}>
        {loading ? <CircularProgress size={26} sx={{ color: colors.accent }} />
          : result?.has_more && (
            <Button variant="outlined" onClick={() => load(result.next_offset)}
              sx={{ color: colors.textHi, borderColor: colors.borderStrong, textTransform: 'none' }}>
              Show more
            </Button>
          )}
      </Box>
    </Box>
  );
};

export default ScorecardsBrowse;
