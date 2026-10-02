import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
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
import DivergingBars from '../../charts/DivergingBars';

/**
 * A player's contextual numbers from Ganjoo's T20 Primer -- Impact, RAA/WAA, WPA -- by season.
 *
 * Not a new endpoint: it is the query builder's own query (this batter or bowler, men's T20,
 * grouped by year, with the page's dates, venue and competitions), so the numbers are exactly
 * what /query shows and the link opens that query there. Bowling rows come back from the
 * bowling side (grouped by bowler), so positive is good in both modes.
 */
const buildParams = ({ playerName, mode, dateRange, selectedVenue, competitionFilters, groupBy = ['year'] }) => {
  const params = new URLSearchParams();
  params.append(mode === 'bowling' ? 'bowlers' : 'batters', playerName);
  groupBy.forEach((g) => params.append('group_by', g));
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
  const [phaseRows, setPhaseRows] = useState(null);
  const [showTable, setShowTable] = useState(false);
  const params = useMemo(
    () => buildParams({ playerName, mode, dateRange, selectedVenue, competitionFilters }),
    [playerName, mode, dateRange, selectedVenue, competitionFilters],
  );

  // Impact by phase (and, for batters, v pace / v spin): where the value is added or lost.
  const phaseParams = useMemo(
    () => buildParams({
      playerName, mode, dateRange, selectedVenue, competitionFilters,
      groupBy: mode === 'bowling' ? ['phase'] : ['phase', 'bowl_kind'],
    }),
    [playerName, mode, dateRange, selectedVenue, competitionFilters],
  );
  useEffect(() => {
    if (!playerName) return undefined;
    let cancelled = false;
    setPhaseRows(null);
    fetch(`${config.API_URL}/query/deliveries?${phaseParams.toString()}`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((payload) => { if (!cancelled) setPhaseRows((payload?.data || []).filter((row) => row.metric_balls > 0)); })
      .catch(() => { if (!cancelled) setPhaseRows([]); });
    return () => { cancelled = true; };
  }, [playerName, phaseParams]);

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

  const PHASE_ORDER = ['powerplay', 'middle', 'death'];
  const PHASE_NAME = { powerplay: 'Powerplay', middle: 'Middle', death: 'Death' };
  const phaseChartRows = (phaseRows || [])
    .filter((row) => PHASE_ORDER.includes(row.phase) && (mode === 'bowling' || ['pace bowler', 'spin bowler'].includes(row.bowl_kind)))
    .sort((a, b) => PHASE_ORDER.indexOf(a.phase) - PHASE_ORDER.indexOf(b.phase) || String(a.bowl_kind).localeCompare(String(b.bowl_kind)))
    .map((row) => (mode === 'bowling'
      ? { key: row.phase, label: PHASE_NAME[row.phase], value: row.impact_per_100, sample: row.metric_balls }
      : {
        key: `${row.phase}-${row.bowl_kind}`,
        group: PHASE_NAME[row.phase],
        label: row.bowl_kind === 'pace bowler' ? 'v pace' : 'v spin',
        value: row.impact_per_100,
        sample: row.metric_balls,
      }));

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
      <Box sx={{ display: 'grid', gap: 2.5 }}>
        <Box>
          <Typography sx={{ fontWeight: 700, fontSize: 15 }}>Impact by season</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Runs {mode === 'bowling' ? 'saved' : 'added'} per 100 balls · overall {signed(total?.impact_per_100)}
          </Typography>
          <DivergingBars
            ariaLabel="Impact per 100 balls by season"
            rows={rows.map((row) => ({ key: String(row.year), label: String(row.year), value: row.impact_per_100, sample: row.metric_balls }))}
            labelWidth={44}
          />
        </Box>
        {phaseChartRows.length > 0 && (
          <Box>
            <Typography sx={{ fontWeight: 700, fontSize: 15 }}>Where the value comes from</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Impact per 100 balls by phase{mode === 'bowling' ? '' : ', against pace and spin'}
            </Typography>
            <DivergingBars ariaLabel="Impact per 100 balls by phase" rows={phaseChartRows} labelWidth={mode === 'bowling' ? 84 : 64} />
          </Box>
        )}
        <Box>
          <Typography sx={{ fontWeight: 700, fontSize: 15 }}>Matches won</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Win probability added by season (1.0 = one match won) · overall {signed(total?.wpa, 2)}
          </Typography>
          <DivergingBars
            ariaLabel="Win probability added by season"
            rows={rows.map((row) => ({ key: `wpa-${row.year}`, label: String(row.year), value: row.wpa, sample: row.metric_balls }))}
            format={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}`}
            labelWidth={44}
          />
        </Box>
        <Box>
          <Button size="small" onClick={() => setShowTable((prev) => !prev)} sx={{ minHeight: 36, px: 0 }}>
            {showTable ? 'Hide table' : 'Show table'}
          </Button>
          {showTable && (
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
          )}
        </Box>
      </Box>
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
