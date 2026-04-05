import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import {
  fetchAnalyticsJson,
  getFormFlagMeta,
  normalizeAnalyticsName,
} from '../../utils/analyticsApi';

const safeNum = (value, digits = 2) => (
  value === null || value === undefined || Number.isNaN(Number(value))
    ? '-'
    : Number(value).toFixed(digits)
);

const compactNum = (value) => (
  value === null || value === undefined || Number.isNaN(Number(value))
    ? '-'
    : Number(value)
);

const MetricCell = ({ label, value, percentile }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Stack direction="row" spacing={0.75} alignItems="center">
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {value}
      </Typography>
      {percentile !== null && percentile !== undefined && (
        <Chip size="small" variant="outlined" label={`P${Number(percentile).toFixed(1)}`} />
      )}
    </Stack>
  </Box>
);

const InningsRelativeCard = ({ title, data }) => {
  const bowling = data?.bowling || {};
  return (
    <Card variant="outlined">
      <CardContent sx={{ py: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
          {title}
        </Typography>
        <Stack spacing={0.75}>
          <MetricCell
            label="Wickets / innings"
            value={safeNum(bowling?.wickets_per_innings?.value, 2)}
            percentile={bowling?.wickets_per_innings?.percentile}
          />
          <MetricCell
            label="Economy"
            value={safeNum(bowling?.economy?.value, 2)}
            percentile={bowling?.economy?.percentile}
          />
          <MetricCell
            label="Bowling SR"
            value={safeNum(bowling?.bowling_strike_rate?.value, 2)}
            percentile={bowling?.bowling_strike_rate?.percentile}
          />
          <MetricCell
            label="Fantasy points"
            value={safeNum(bowling?.fantasy_points_avg?.value, 2)}
            percentile={bowling?.fantasy_points_avg?.percentile}
          />
        </Stack>
      </CardContent>
    </Card>
  );
};

const AdvancedBowlingAnalyticsSection = ({
  playerName,
  dateRange,
  selectedVenue,
  competitionFilters,
  isMobile = false,
  enabled = false,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [showRelativeDetails, setShowRelativeDetails] = useState(false);

  const [bowlingContext, setBowlingContext] = useState(null);
  const [rollingForm, setRollingForm] = useState(null);
  const [relativeMetrics, setRelativeMetrics] = useState(null);
  const [batterLeaderboard, setBatterLeaderboard] = useState(null);
  const [bowlerLeaderboard, setBowlerLeaderboard] = useState(null);
  const leaguesFilter = useMemo(
    () => competitionFilters?.leagues || [],
    [competitionFilters?.leagues],
  );
  const leaguesDependencyKey = useMemo(
    () => leaguesFilter.join(','),
    [leaguesFilter],
  );
  const includeInternational = Boolean(competitionFilters?.international);

  useEffect(() => {
    if (!enabled || !playerName) {
      return;
    }

    let cancelled = false;

    const baseFilters = {
      start_date: dateRange?.start,
      end_date: dateRange?.end,
      leagues: leaguesFilter,
      include_international: includeInternational,
      venue: selectedVenue && selectedVenue !== 'All Venues' ? selectedVenue : undefined,
    };

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [contextPayload, formPayload, relativePayload, batterLb, bowlerLb] = await Promise.all([
          fetchAnalyticsJson(`/player/${encodeURIComponent(playerName)}/bowling-context`, {
            ...baseFilters,
            min_overs: 10,
            pressure_threshold: 10,
          }),
          fetchAnalyticsJson(`/player/${encodeURIComponent(playerName)}/rolling-form`, {
            ...baseFilters,
            window: 10,
            role: 'bowling',
          }),
          fetchAnalyticsJson(`/relative-metrics/player/${encodeURIComponent(playerName)}`, {
            ...baseFilters,
            benchmark_window_matches: 10,
          }),
          fetchAnalyticsJson('/leaderboards/first-ball-boundaries', {
            ...baseFilters,
            role: 'batter',
            min_balls: 60,
            limit: 50,
          }),
          fetchAnalyticsJson('/leaderboards/first-ball-boundaries', {
            ...baseFilters,
            role: 'bowler',
            min_balls: 50,
            limit: 200,
          }),
        ]);

        if (cancelled) return;
        setBowlingContext(contextPayload);
        setRollingForm(formPayload);
        setRelativeMetrics(relativePayload);
        setBatterLeaderboard(batterLb);
        setBowlerLeaderboard(bowlerLb);
      } catch (fetchError) {
        if (cancelled) return;
        console.error('Error loading advanced bowling analytics:', fetchError);
        setError('Failed to load advanced analytics for this bowler.');
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [
    enabled,
    playerName,
    dateRange?.start,
    dateRange?.end,
    selectedVenue,
    includeInternational,
    leaguesFilter,
    leaguesDependencyKey,
    reloadToken,
  ]);

  const formMeta = getFormFlagMeta(rollingForm?.form_flag);

  const playerNameKeys = useMemo(() => {
    const keys = new Set();
    [playerName, bowlingContext?.resolved_names?.legacy_name, bowlingContext?.resolved_names?.details_name]
      .forEach((name) => {
        const normalized = normalizeAnalyticsName(name);
        if (normalized) keys.add(normalized);
      });
    return keys;
  }, [playerName, bowlingContext]);

  const playerFirstBallBowlerRow = useMemo(
    () => (bowlerLeaderboard?.leaderboard || []).find((row) => playerNameKeys.has(normalizeAnalyticsName(row.player))) || null,
    [bowlerLeaderboard, playerNameKeys],
  );

  const topBatterThreats = useMemo(
    () => (batterLeaderboard?.leaderboard || []).slice(0, 5),
    [batterLeaderboard],
  );

  const recentRollingRows = useMemo(() => {
    const rows = rollingForm?.bowling_innings || [];
    return rows.slice(-5).reverse();
  }, [rollingForm]);

  const pressureStats = bowlingContext?.previous_over_pressure_stats || {};
  const highPressure = pressureStats?.high_pressure || {};
  const lowPressure = pressureStats?.low_pressure || {};
  const firstSpell = bowlingContext?.spell_stats?.first_spell || {};
  const laterSpells = bowlingContext?.spell_stats?.later_spells || {};

  if (!enabled) {
    return (
      <Alert severity="info" sx={{ mt: 1 }}>
        Open this section to load advanced bowling analytics.
      </Alert>
    );
  }

  if (loading && !bowlingContext) {
    return (
      <Box sx={{ py: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={18} />
        <Typography variant="body2">Loading advanced bowling analytics…</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {error && (
        <Alert
          severity="error"
          action={(
            <Button color="inherit" size="small" onClick={() => setReloadToken((prev) => prev + 1)}>
              Retry
            </Button>
          )}
        >
          {error}
        </Alert>
      )}

      {bowlingContext?.insufficient_sample && (
        <Alert severity="warning">
          Insufficient sample for stable contextual splits. Treat trends directionally.
        </Alert>
      )}

      {bowlingContext?.data_quality_note && (
        <Alert severity="info">{bowlingContext.data_quality_note}</Alert>
      )}

      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ rowGap: 1 }}>
        <Chip label={`Form: ${formMeta.label}`} color={formMeta.color} size="small" />
        <Chip label={`Overs analyzed: ${compactNum(bowlingContext?.total_overs_analyzed)}`} size="small" variant="outlined" />
        <Chip label={`Pressure threshold: ${compactNum(pressureStats?.threshold_runs)}`} size="small" variant="outlined" />
      </Stack>

      <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' } }}>
        <Card variant="outlined">
          <CardContent sx={{ py: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>High Pressure</Typography>
            <Typography variant="body2">Economy: <strong>{safeNum(highPressure?.economy)}</strong></Typography>
            <Typography variant="body2">Wkts / over: <strong>{safeNum(highPressure?.wickets_per_over, 3)}</strong></Typography>
            <Typography variant="body2">Boundary%: <strong>{safeNum(highPressure?.boundary_pct)}</strong></Typography>
          </CardContent>
        </Card>
        <Card variant="outlined">
          <CardContent sx={{ py: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>Low Pressure</Typography>
            <Typography variant="body2">Economy: <strong>{safeNum(lowPressure?.economy)}</strong></Typography>
            <Typography variant="body2">Wkts / over: <strong>{safeNum(lowPressure?.wickets_per_over, 3)}</strong></Typography>
            <Typography variant="body2">Boundary%: <strong>{safeNum(lowPressure?.boundary_pct)}</strong></Typography>
          </CardContent>
        </Card>
        <Card variant="outlined">
          <CardContent sx={{ py: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>Pressure Delta</Typography>
            <Typography variant="body2">
              Econ Δ (high-low): <strong>{safeNum((highPressure?.economy ?? 0) - (lowPressure?.economy ?? 0))}</strong>
            </Typography>
            <Typography variant="body2">
              Wkts/over Δ: <strong>{safeNum((highPressure?.wickets_per_over ?? 0) - (lowPressure?.wickets_per_over ?? 0), 3)}</strong>
            </Typography>
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' } }}>
        <Card variant="outlined">
          <CardContent sx={{ py: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>Spell Shape</Typography>
            <Typography variant="body2">
              First spell: <strong>{safeNum(firstSpell?.economy)}</strong> econ / <strong>{safeNum(firstSpell?.wickets_per_over, 3)}</strong> wkts-over
            </Typography>
            <Typography variant="body2">
              Later spells: <strong>{safeNum(laterSpells?.economy)}</strong> econ / <strong>{safeNum(laterSpells?.wickets_per_over, 3)}</strong> wkts-over
            </Typography>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent sx={{ py: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>Over Start/Finish Control</Typography>
            <Typography variant="body2">
              First-ball boundary %: <strong>{safeNum(bowlingContext?.first_ball_last_ball_stats?.first_ball_boundary_rate_pct)}</strong>
            </Typography>
            <Typography variant="body2">
              Last-ball boundary %: <strong>{safeNum(bowlingContext?.first_ball_last_ball_stats?.last_ball_boundary_rate_pct)}</strong>
            </Typography>
            <Typography variant="body2">
              Overall boundary %: <strong>{safeNum(bowlingContext?.first_ball_last_ball_stats?.overall_boundary_rate_pct)}</strong>
            </Typography>
          </CardContent>
        </Card>
      </Box>

      <Card variant="outlined">
        <CardContent sx={{ py: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
            Rolling Form (window: 10 innings)
          </Typography>
          {recentRollingRows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No bowling innings found for current filters.</Typography>
          ) : (
            <Table size={isMobile ? 'small' : 'medium'}>
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Wkts</TableCell>
                  <TableCell align="right">Econ</TableCell>
                  <TableCell align="right">Rolling FP</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentRollingRows.map((row) => (
                  <TableRow key={`${row.match_id}-${row.date}`}>
                    <TableCell>{row.date || '-'}</TableCell>
                    <TableCell align="right">{compactNum(row.wickets)}</TableCell>
                    <TableCell align="right">{safeNum(row.economy)}</TableCell>
                    <TableCell align="right">{safeNum(row.rolling_fantasy_points_avg)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent sx={{ py: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
            First-Ball Boundary Context
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.75 }}>
            Top opener-pressure batters (global): {topBatterThreats.map((row) => `${row.player} (${safeNum(row.boundary_rate_pct)})`).join(', ') || 'No qualified sample'}
          </Typography>
          <Typography variant="body2">
            Player bowler rank: {
              playerFirstBallBowlerRow
                ? `#${playerFirstBallBowlerRow.rank} | ${safeNum(playerFirstBallBowlerRow.boundary_rate_pct)}% boundary rate`
                : 'No qualified sample'
            }
          </Typography>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent sx={{ py: 1.5 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Relative Percentiles (Bowling)</Typography>
            <Button size="small" onClick={() => setShowRelativeDetails((prev) => !prev)}>
              {showRelativeDetails ? 'Hide details' : 'Show details'}
            </Button>
          </Stack>

          <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' } }}>
            <InningsRelativeCard title="Innings 1" data={relativeMetrics?.innings_1} />
            <InningsRelativeCard title="Innings 2" data={relativeMetrics?.innings_2} />
          </Box>

          <Collapse in={showRelativeDetails}>
            <Divider sx={{ my: 1.25 }} />
            <Typography variant="caption" color="text.secondary">
              Benchmark window: {compactNum(relativeMetrics?.benchmark_window_matches)} matches
            </Typography>
            {relativeMetrics?.effective_start_date && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                Effective start date: {relativeMetrics.effective_start_date}
              </Typography>
            )}
          </Collapse>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AdvancedBowlingAnalyticsSection;
