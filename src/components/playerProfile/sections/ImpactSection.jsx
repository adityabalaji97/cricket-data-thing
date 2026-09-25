import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import config from '../../../config';
import ScrollTable from '../../ui/ScrollTable';

/**
 * A player's contextual numbers from Ganjoo's T20 Primer -- Impact, RAA/WAA, WPA -- by season.
 *
 * Not a new endpoint: it is the query builder's own query (this batter or bowler, men's T20,
 * grouped by year, with the page's dates, venue and competitions), so the numbers are exactly
 * what /query shows and the link opens that query there. Bowling rows come back from the
 * bowling side (grouped by bowler), so positive is good in both modes.
 */
const buildParams = ({ playerName, mode, dateRange, selectedVenue, competitionFilters }) => {
  const params = new URLSearchParams();
  params.append(mode === 'bowling' ? 'bowlers' : 'batters', playerName);
  params.append('group_by', 'year');
  if (mode === 'bowling') params.append('group_by', 'bowler');
  params.set('format', 'T20');
  params.set('gender', 'male');
  if (dateRange?.start) params.set('start_date', dateRange.start);
  if (dateRange?.end) params.set('end_date', dateRange.end);
  if (selectedVenue && selectedVenue !== 'All Venues') params.set('venue', selectedVenue);
  (competitionFilters?.leagues || []).forEach((league) => params.append('leagues', league));
  if (competitionFilters?.international) {
    params.set('include_international', 'true');
    if (competitionFilters.topTeams) params.set('top_teams', String(competitionFilters.topTeams));
  }
  params.set('limit', '100');
  return params;
};

const signed = (value, digits = 1) => {
  if (value === null || value === undefined) return '–';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}`;
};

const tone = (value) => (value === null || value === undefined ? 'text.secondary' : value >= 0 ? 'success.main' : 'error.main');

const ImpactSection = ({ playerName, mode = 'batting', dateRange, selectedVenue, competitionFilters }) => {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(false);
  const params = useMemo(
    () => buildParams({ playerName, mode, dateRange, selectedVenue, competitionFilters }),
    [playerName, mode, dateRange, selectedVenue, competitionFilters],
  );

  useEffect(() => {
    if (!playerName) return undefined;
    let cancelled = false;
    setRows(null);
    setError(false);
    fetch(`${config.API_URL}/query/deliveries?${params.toString()}`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((payload) => {
        if (cancelled) return;
        const data = (payload?.data || []).filter((row) => row.metric_balls > 0);
        data.sort((a, b) => Number(a.year) - Number(b.year));
        setRows(data);
      })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [playerName, params]);

  const total = useMemo(() => {
    if (!rows?.length) return null;
    const sum = (key) => rows.reduce((acc, row) => acc + (Number(row[key]) || 0), 0);
    const balls = sum('metric_balls');
    const innings = sum('innings_count');
    return {
      year: 'All',
      metric_balls: balls,
      innings_count: innings,
      impact: sum('impact'),
      impact_per_100: balls ? (sum('impact') * 100) / balls : null,
      raa_per_100: balls ? (sum('raa') * 100) / balls : null,
      waa_per_100: balls ? (sum('waa') * 100) / balls : null,
      wpa: sum('wpa'),
    };
  }, [rows]);

  if (error) {
    return <Typography variant="body2" color="text.secondary">Couldn&apos;t load contextual metrics.</Typography>;
  }
  if (rows === null) {
    return <Box sx={{ py: 2, display: 'flex', justifyContent: 'center' }}><CircularProgress size={22} /></Box>;
  }
  if (!rows.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No contextual metrics for this window. They cover men&apos;s T20 from 2015 (not the Hundred).
      </Typography>
    );
  }

  const queryLink = `/query?${params.toString()}`;
  const cell = (value, digits, colored = true) => (
    <TableCell align="right" sx={{ color: colored ? tone(value) : undefined, fontVariantNumeric: 'tabular-nums' }}>
      {signed(value, digits)}
    </TableCell>
  );

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        <b>Impact</b> is runs added to the {mode === 'bowling' ? 'bowling side (runs saved)' : "batting side's projected total"};{' '}
        <b>RAA / WAA</b> are runs and wickets above average for the game state; <b>WPA</b> is win probability added
        (1.0 = one match won). Men&apos;s T20, method from Himanish Ganjoo&apos;s <i>T20 Metrics: A Primer</i>.
      </Typography>
      <ScrollTable paper stickyFirstColumn>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Season</TableCell>
              <TableCell align="right">Balls</TableCell>
              <TableCell align="right">Impact</TableCell>
              <TableCell align="right">Imp/100</TableCell>
              <TableCell align="right">RAA/100</TableCell>
              <TableCell align="right">WAA/100</TableCell>
              <TableCell align="right">WPA</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {[...rows, total].map((row) => (
              <TableRow key={row.year} sx={row.year === 'All' ? { '& td': { fontWeight: 700, borderTop: 1, borderColor: 'divider' } } : undefined}>
                <TableCell>{row.year}</TableCell>
                <TableCell align="right">{row.metric_balls}</TableCell>
                {cell(row.impact, 1)}
                {cell(row.impact_per_100, 1)}
                {cell(row.raa_per_100, 1)}
                {cell(row.waa_per_100, 2)}
                {cell(row.wpa, 2)}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollTable>
      <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
        <Box component={RouterLink} to={queryLink} sx={{ color: 'primary.main' }}>
          Open in the query builder
        </Box>{' '}
        to split it further (by phase, bowler type, venue...).
      </Typography>
    </Box>
  );
};

export default ImpactSection;
