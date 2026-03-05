import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Box,
  Card,
  Chip,
  CircularProgress,
  Grid,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material';
import ReactECharts from 'echarts-for-react';
import config from '../config';

const METRIC_META = {
  bat_first_win_pct: { label: 'Bat 1st Win%', digits: 1, suffix: '%' },
  avg_first_innings_score: { label: 'Avg 1st Inns', digits: 1, suffix: '' },
  avg_second_innings_score: { label: 'Avg 2nd Inns', digits: 1, suffix: '' },
  pp_run_rate: { label: 'PP RR', digits: 2, suffix: '' },
  middle_run_rate: { label: 'Middle RR', digits: 2, suffix: '' },
  death_run_rate: { label: 'Death RR', digits: 2, suffix: '' },
  pace_economy: { label: 'Pace Econ', digits: 2, suffix: '' },
  spin_economy: { label: 'Spin Econ', digits: 2, suffix: '' },
};

const PHASE_TABS = [
  { key: 'overall', label: 'Overall' },
  { key: 'powerplay', label: 'PP' },
  { key: 'middle', label: 'Middle' },
  { key: 'death', label: 'Death' },
];

const fmt = (value, digits = 2, suffix = '') => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return `${Number(value).toFixed(digits)}${suffix}`;
};

const getTopDifferences = (targetMetrics, compareMetrics) => {
  if (!targetMetrics || !compareMetrics) return [];
  const keys = [
    'bat_first_win_pct',
    'avg_first_innings_score',
    'pp_run_rate',
    'middle_run_rate',
    'death_run_rate',
    'pace_economy',
    'spin_economy',
  ];

  return keys
    .map((key) => {
      const target = Number(targetMetrics[key]);
      const compare = Number(compareMetrics[key]);
      if (!Number.isFinite(target) || !Number.isFinite(compare)) return null;
      return {
        key,
        diff: compare - target,
        absDiff: Math.abs(compare - target),
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.absDiff - a.absDiff)
    .slice(0, 2);
};

const buildZoneRadarOption = (targetZoneProfile, similarZoneProfile) => {
  const targetValues = [];
  const similarValues = [];
  for (let zone = 1; zone <= 8; zone += 1) {
    targetValues.push(Number(targetZoneProfile?.[String(zone)]?.run_pct || 0));
    similarValues.push(Number(similarZoneProfile?.[String(zone)]?.run_pct || 0));
  }
  const maxValue = Math.max(10, Math.ceil(Math.max(...targetValues, ...similarValues, 1) / 5) * 5);

  return {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const rows = params.value
          .map((value, index) => `Zone ${index + 1}: ${Number(value).toFixed(1)}%`)
          .join('<br/>');
        return `<strong>${params.seriesName}</strong><br/>${rows}`;
      },
    },
    legend: {
      bottom: 0,
      data: ['Target Venue', 'Similar Venues Avg'],
    },
    radar: {
      radius: '68%',
      indicator: Array.from({ length: 8 }, (_, index) => ({
        name: `Zone ${index + 1}`,
        max: maxValue,
      })),
      axisName: {
        color: '#374151',
      },
    },
    series: [
      {
        name: 'Zone Run Distribution',
        type: 'radar',
        data: [
          {
            value: targetValues,
            name: 'Target Venue',
            areaStyle: { opacity: 0.18 },
          },
          {
            value: similarValues,
            name: 'Similar Venues Avg',
            areaStyle: { opacity: 0.18 },
          },
        ],
      },
    ],
  };
};

const VenueSimilarity = ({
  venue,
  startDate,
  endDate,
  isMobile = false,
  leagues = [],
  includeInternational = false,
  topTeams = null,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [phaseTab, setPhaseTab] = useState('overall');

  const effectiveLeagues = useMemo(() => (Array.isArray(leagues) ? leagues : []), [leagues]);

  useEffect(() => {
    if (!venue) return;
    let cancelled = false;

    const fetchSimilarity = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        params.append('min_matches', '10');
        params.append('top_n', '5');
        if (includeInternational !== null && includeInternational !== undefined) {
          params.append('include_international', String(includeInternational));
        }
        if (includeInternational && topTeams) {
          params.append('top_teams', String(topTeams));
        }
        effectiveLeagues.forEach((league) => params.append('leagues', league));

        const response = await axios.get(
          `${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}/similar?${params.toString()}`
        );
        if (!cancelled) {
          setData(response.data);
          setPhaseTab('overall');
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setError(err?.response?.data?.detail || 'Failed to load similar venues');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchSimilarity();
    return () => {
      cancelled = true;
    };
  }, [venue, startDate, endDate, includeInternational, topTeams, effectiveLeagues]);

  const radarOption = useMemo(() => {
    const similarZoneProfile = data?.similar_aggregate_insights?.zone_profile || {};
    return buildZoneRadarOption(data?.target_zone_profile || {}, similarZoneProfile);
  }, [data]);

  const byStyleRows = useMemo(() => {
    const byStyle = data?.similar_aggregate_insights?.by_style || {};
    return Object.entries(byStyle).map(([style, stats]) => ({ style, ...stats }));
  }, [data]);

  const phaseInsight = data?.similar_aggregate_insights?.by_phase?.[phaseTab] || {};

  if (!venue) return null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Finding similar venues...
          </Typography>
        </Box>
      )}

      {error && !loading && <Alert severity="error">{error}</Alert>}

      {data && !loading && (
        <>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip size="small" label={`${data.qualified_venues} qualified venues`} />
            <Chip size="small" label={`Min matches: ${data.min_matches}`} />
          </Box>

          <Grid container spacing={1.5}>
            {(data.most_similar || []).map((item) => {
              const topDiffs = getTopDifferences(data.target_metrics, item.metrics);
              return (
                <Grid item xs={12} md={6} key={`${item.venue}-${item.distance}`}>
                  <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {item.venue}
                      </Typography>
                      <Chip size="small" color="primary" label={`d=${fmt(item.distance, 2)}`} />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {item.total_matches || 0} matches
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.75 }}>
                      Bat 1st Win: {fmt(item.metrics?.bat_first_win_pct, 1, '%')} · Avg 1st Inns:{' '}
                      {fmt(item.metrics?.avg_first_innings_score, 1)}
                    </Typography>
                    <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {topDiffs.map((diffRow) => {
                        const meta = METRIC_META[diffRow.key] || { label: diffRow.key, digits: 2, suffix: '' };
                        const sign = diffRow.diff > 0 ? '+' : '';
                        return (
                          <Chip
                            key={`${item.venue}-${diffRow.key}`}
                            size="small"
                            variant="outlined"
                            label={`${meta.label} ${sign}${Number(diffRow.diff).toFixed(meta.digits)}${meta.suffix}`}
                          />
                        );
                      })}
                    </Box>
                  </Card>
                </Grid>
              );
            })}
          </Grid>

          {(data.most_dissimilar || []).length > 0 && (
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.8 }}>
                Most Different
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                {data.most_dissimilar.map((item) => (
                  <Chip
                    key={`dissimilar-${item.venue}`}
                    size="small"
                    variant="outlined"
                    color="warning"
                    label={`${item.venue} · ${fmt(item.distance, 2)}`}
                  />
                ))}
              </Box>
            </Box>
          )}

          <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
            <Typography variant="body2" sx={{ fontWeight: 700, mb: 1 }}>
              Scoring Zone Shape: Target vs Similar Avg
            </Typography>
            <Box sx={{ width: '100%', height: isMobile ? 340 : 380 }}>
              <ReactECharts option={radarOption} style={{ height: '100%', width: '100%' }} />
            </Box>
          </Card>

          <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              Bowling at Similar Venues
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {data?.similar_aggregate_insights?.description || ''}
            </Typography>

            <Box sx={{ borderBottom: 1, borderColor: 'divider', mt: 1 }}>
              <Tabs
                value={PHASE_TABS.findIndex((tab) => tab.key === phaseTab)}
                onChange={(_, value) => setPhaseTab(PHASE_TABS[value].key)}
                variant={isMobile ? 'scrollable' : 'standard'}
                allowScrollButtonsMobile
              >
                {PHASE_TABS.map((tab) => (
                  <Tab key={tab.key} label={tab.label} />
                ))}
              </Tabs>
            </Box>

            {phaseTab === 'overall' ? (
              <>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1.25 }}>
                  <Chip
                    size="small"
                    label={`Pace Econ ${fmt(data?.similar_aggregate_insights?.pace?.economy, 2)}`}
                  />
                  <Chip
                    size="small"
                    label={`Spin Econ ${fmt(data?.similar_aggregate_insights?.spin?.economy, 2)}`}
                  />
                  <Chip
                    size="small"
                    label={`Pace Dot% ${fmt(data?.similar_aggregate_insights?.pace?.dot_pct, 1, '%')}`}
                  />
                  <Chip
                    size="small"
                    label={`Spin Dot% ${fmt(data?.similar_aggregate_insights?.spin?.dot_pct, 1, '%')}`}
                  />
                </Box>

                <TableContainer sx={{ mt: 1.2, overflowX: 'auto' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Style</TableCell>
                        <TableCell align="right">Econ</TableCell>
                        <TableCell align="right">Dot%</TableCell>
                        <TableCell align="right">Avg</TableCell>
                        <TableCell align="right">Wk/Match</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {byStyleRows.map((row) => (
                        <TableRow key={row.style}>
                          <TableCell>{row.style}</TableCell>
                          <TableCell align="right">{fmt(row.economy, 2)}</TableCell>
                          <TableCell align="right">{fmt(row.dot_pct, 1, '%')}</TableCell>
                          <TableCell align="right">{fmt(row.avg, 1)}</TableCell>
                          <TableCell align="right">{fmt(row.wickets_per_match, 2)}</TableCell>
                        </TableRow>
                      ))}
                      {byStyleRows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={5}>
                            <Typography variant="body2" color="text.secondary">
                              No style-level bowling data available.
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </>
            ) : (
              <Box sx={{ mt: 1.2 }}>
                <TableContainer sx={{ overflowX: 'auto' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Type</TableCell>
                        <TableCell align="right">Economy</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      <TableRow>
                        <TableCell>Pace</TableCell>
                        <TableCell align="right">{fmt(phaseInsight.pace_economy, 2)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Spin</TableCell>
                        <TableCell align="right">{fmt(phaseInsight.spin_economy, 2)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </Card>
        </>
      )}
    </Box>
  );
};

export default VenueSimilarity;
