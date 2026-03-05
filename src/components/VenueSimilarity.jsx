import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
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

const getActiveFilterCount = (filters) => {
  if (!filters) return 0;
  let count = 0;
  if (filters.zoneMetric && filters.zoneMetric !== 'boundary_pct') count += 1;
  if (filters.batHand) count += 1;
  if (filters.bowlKind) count += 1;
  if (filters.bowlStyle) count += 1;
  return count;
};

const buildZoneRadarOption = (targetZoneProfile, similarZoneProfile, zoneMetric = 'boundary_pct') => {
  const metricKey = zoneMetric === 'run_pct' ? 'run_pct' : 'boundary_pct';
  const metricLabel = metricKey === 'run_pct' ? 'Run %' : 'Boundary %';

  const targetValues = [];
  const similarValues = [];
  for (let zone = 1; zone <= 8; zone += 1) {
    targetValues.push(Number(targetZoneProfile?.[String(zone)]?.[metricKey] || 0));
    similarValues.push(Number(similarZoneProfile?.[String(zone)]?.[metricKey] || 0));
  }
  const maxValue = Math.max(10, Math.ceil(Math.max(...targetValues, ...similarValues, 1) / 5) * 5);

  return {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const rows = params.value
          .map((value, index) => `Zone ${index + 1}: ${Number(value).toFixed(1)}%`)
          .join('<br/>');
        return `<strong>${params.seriesName}</strong><br/>${metricLabel}<br/>${rows}`;
      },
    },
    legend: {
      bottom: 0,
      data: ['Target Venue', 'Similar Venues Avg'],
    },
    radar: {
      radius: '68%',
      startAngle: 90,
      clockwise: true,
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
        name: `${metricLabel} Distribution`,
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
            lineStyle: { type: 'dashed' },
            areaStyle: { opacity: 0.08 },
          },
        ],
      },
    ],
  };
};

export const useVenueSimilarityData = ({
  venue,
  startDate,
  endDate,
  leagues = [],
  includeInternational = false,
  topTeams = null,
  zoneFilters,
}) => {
  const [data, setData] = useState(null);
  const [tacticalEdgesData, setTacticalEdgesData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const effectiveLeagues = useMemo(() => (Array.isArray(leagues) ? leagues : []), [leagues]);

  useEffect(() => {
    if (!venue) return;
    let cancelled = false;

    const fetchSimilarity = async () => {
      setLoading(true);
      setError(null);
      try {
        const similarParams = new URLSearchParams();
        if (startDate) similarParams.append('start_date', startDate);
        if (endDate) similarParams.append('end_date', endDate);
        similarParams.append('min_matches', '10');
        similarParams.append('top_n', '5');
        if (includeInternational !== null && includeInternational !== undefined) {
          similarParams.append('include_international', String(includeInternational));
        }
        if (includeInternational && topTeams) {
          similarParams.append('top_teams', String(topTeams));
        }
        effectiveLeagues.forEach((league) => similarParams.append('leagues', league));

        if (zoneFilters?.batHand) similarParams.append('bat_hand', zoneFilters.batHand);
        if (zoneFilters?.bowlKind) similarParams.append('bowl_kind', zoneFilters.bowlKind);
        if (zoneFilters?.bowlStyle) similarParams.append('bowl_style', zoneFilters.bowlStyle);
        similarParams.append('zone_metric', zoneFilters?.zoneMetric === 'run_pct' ? 'run_pct' : 'boundary_pct');

        const edgesParams = new URLSearchParams(similarParams.toString());
        edgesParams.set('baseline_mode', 'league');
        edgesParams.set('sort_by', 'econ_delta');
        edgesParams.set('sort_order', 'desc');
        edgesParams.set('min_balls', '24');
        edgesParams.set('top_n_similar', '5');

        const [similarResponse, edgesResponse] = await Promise.all([
          axios.get(`${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}/similar?${similarParams.toString()}`),
          axios.get(`${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}/tactical-edges?${edgesParams.toString()}`),
        ]);

        if (!cancelled) {
          setData(similarResponse.data);
          setTacticalEdgesData(edgesResponse.data);
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setTacticalEdgesData(null);
          setError(err?.response?.data?.detail || 'Failed to load similar venues');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchSimilarity();
    return () => {
      cancelled = true;
    };
  }, [
    venue,
    startDate,
    endDate,
    includeInternational,
    topTeams,
    effectiveLeagues,
    zoneFilters?.zoneMetric,
    zoneFilters?.batHand,
    zoneFilters?.bowlKind,
    zoneFilters?.bowlStyle,
  ]);

  return { data, tacticalEdgesData, loading, error };
};

const ZoneFilterModal = ({
  open,
  onClose,
  onApply,
  filters,
  options,
}) => {
  const [draft, setDraft] = useState(filters || {
    zoneMetric: 'boundary_pct',
    batHand: null,
    bowlKind: null,
    bowlStyle: null,
  });

  useEffect(() => {
    if (open) {
      setDraft(filters || {
        zoneMetric: 'boundary_pct',
        batHand: null,
        bowlKind: null,
        bowlStyle: null,
      });
    }
  }, [open, filters]);

  const clearAll = () => {
    setDraft({
      zoneMetric: 'boundary_pct',
      batHand: null,
      bowlKind: null,
      bowlStyle: null,
    });
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle sx={{ fontWeight: 700 }}>Zone Filters</DialogTitle>
      <DialogContent dividers>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.1 }}>
          <FormControl size="small" fullWidth>
            <InputLabel>Metric</InputLabel>
            <Select
              label="Metric"
              value={draft.zoneMetric || 'boundary_pct'}
              onChange={(event) => setDraft((prev) => ({ ...prev, zoneMetric: event.target.value }))}
            >
              <MenuItem value="boundary_pct">Boundary %</MenuItem>
              <MenuItem value="run_pct">Run %</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" fullWidth>
            <InputLabel>Bat Hand</InputLabel>
            <Select
              label="Bat Hand"
              value={draft.batHand || ''}
              onChange={(event) => setDraft((prev) => ({ ...prev, batHand: event.target.value || null }))}
            >
              <MenuItem value="">All</MenuItem>
              {(options?.bat_hand || []).map((value) => (
                <MenuItem key={`bat-${value}`} value={value}>{value}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" fullWidth>
            <InputLabel>Pace/Spin</InputLabel>
            <Select
              label="Pace/Spin"
              value={draft.bowlKind || ''}
              onChange={(event) => {
                const nextKind = event.target.value || null;
                setDraft((prev) => ({ ...prev, bowlKind: nextKind, bowlStyle: null }));
              }}
            >
              <MenuItem value="">All</MenuItem>
              {(options?.bowl_kind || []).map((value) => (
                <MenuItem key={`kind-${value}`} value={value}>{value}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" fullWidth>
            <InputLabel>Bowling Style</InputLabel>
            <Select
              label="Bowling Style"
              value={draft.bowlStyle || ''}
              onChange={(event) => setDraft((prev) => ({ ...prev, bowlStyle: event.target.value || null }))}
            >
              <MenuItem value="">All</MenuItem>
              {(options?.bowl_style || []).map((value) => (
                <MenuItem key={`style-${value}`} value={value}>{value}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={clearAll}>Clear all</Button>
        <Button variant="contained" onClick={() => onApply(draft)}>Apply</Button>
      </DialogActions>
    </Dialog>
  );
};

const SimilarityInsightsView = ({
  data,
  tacticalEdgesData,
  loading,
  error,
  isMobile,
  zoneFilters,
  onZoneFiltersChange,
}) => {
  const [filterOpen, setFilterOpen] = useState(false);
  const [edgeBaselineMode, setEdgeBaselineMode] = useState('league');

  const radarOption = useMemo(() => {
    const similarZoneProfile = data?.similar_aggregate_insights?.zone_profile || {};
    const metric = data?.zone_metric || zoneFilters?.zoneMetric || 'boundary_pct';
    return buildZoneRadarOption(data?.target_zone_profile || {}, similarZoneProfile, metric);
  }, [data, zoneFilters?.zoneMetric]);

  if (loading && !data) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1 }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Finding similar venues...
        </Typography>
      </Box>
    );
  }

  if (error && !loading) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!data) return null;
  const edgeRows = tacticalEdgesData?.rows_by_baseline?.[edgeBaselineMode] || tacticalEdgesData?.rows || [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        <Chip size="small" label={`${data.qualified_venues} qualified venues`} />
        <Chip size="small" label={`Min matches: ${data.min_matches}`} />
      </Box>

      <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.8 }}>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            Scoring Zone Shape: Target vs Similar Avg
          </Typography>
          <IconButton size="small" onClick={() => setFilterOpen(true)} aria-label="zone filters">
            <Badge badgeContent={getActiveFilterCount(zoneFilters)} color="primary" invisible={getActiveFilterCount(zoneFilters) === 0}>
              <FilterListIcon fontSize="small" />
            </Badge>
          </IconButton>
        </Box>
        <Box sx={{ width: '100%', height: isMobile ? 340 : 380 }}>
          <ReactECharts option={radarOption} style={{ height: '100%', width: '100%' }} />
        </Box>
      </Card>

      <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
        <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.75 }}>
          Tactical Edges at This Venue
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Positive deltas indicate better bowling outcomes at this venue vs selected baseline.
        </Typography>
        <Box sx={{ mt: 1, mb: 0.6, display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
          <Chip
            size="small"
            color={edgeBaselineMode === 'league' ? 'primary' : 'default'}
            variant={edgeBaselineMode === 'league' ? 'filled' : 'outlined'}
            label="League Baseline"
            onClick={() => setEdgeBaselineMode('league')}
          />
          <Chip
            size="small"
            color={edgeBaselineMode === 'similar' ? 'primary' : 'default'}
            variant={edgeBaselineMode === 'similar' ? 'filled' : 'outlined'}
            label="Similar Baseline"
            onClick={() => setEdgeBaselineMode('similar')}
          />
        </Box>

        <TableContainer sx={{ mt: 1.2, overflowX: 'auto' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Line</TableCell>
                <TableCell>Length</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Balls</TableCell>
                <TableCell align="right">ΔEcon</TableCell>
                <TableCell align="right">ΔDot</TableCell>
                <TableCell align="right">ΔWkt</TableCell>
                <TableCell align="right">ΔBnd</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {edgeRows.slice(0, 12).map((row, index) => (
                <TableRow key={`edge-${row.line}-${row.length}-${row.bowl_kind}-${index}`}>
                  <TableCell>{row.line}</TableCell>
                  <TableCell>{row.length}</TableCell>
                  <TableCell>{row.bowl_kind}</TableCell>
                  <TableCell align="right">{row.target?.balls || 0}</TableCell>
                  <TableCell align="right">{fmt(row.deltas?.econ_delta, 2)}</TableCell>
                  <TableCell align="right">{fmt(row.deltas?.dot_delta, 1, '%')}</TableCell>
                  <TableCell align="right">{fmt(row.deltas?.wicket_delta, 1, '%')}</TableCell>
                  <TableCell align="right">{fmt(row.deltas?.boundary_delta, 1, '%')}</TableCell>
                </TableRow>
              ))}
              {edgeRows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8}>
                    <Typography variant="body2" color="text.secondary">
                      No tactical edge rows available for this filter set.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      <ZoneFilterModal
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        onApply={(nextFilters) => {
          if (onZoneFiltersChange) {
            onZoneFiltersChange(nextFilters);
          }
          setFilterOpen(false);
        }}
        filters={zoneFilters}
        options={data?.filter_options || {}}
      />
    </Box>
  );
};

const VenueTwinsCardsView = ({ data, loading, error }) => {
  if (loading && !data) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1 }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Finding venue twins...
        </Typography>
      </Box>
    );
  }

  if (error && !loading) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!data) return null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.8 }}>
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.8 }}>
          Most Similar Venues
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 1.2 }}>
          {(data.most_similar || []).map((item) => {
            const topDiffs = getTopDifferences(data.target_metrics, item.metrics);
            return (
              <Card key={`${item.venue}-${item.distance}`} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
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
                  Bat 1st Win: {fmt(item.metrics?.bat_first_win_pct, 1, '%')} · Avg 1st Inns: {fmt(item.metrics?.avg_first_innings_score, 1)}
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
            );
          })}
        </Box>
      </Box>

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
    </Box>
  );
};

const VenueSimilarity = ({
  mode = 'insights',
  data,
  tacticalEdgesData,
  loading,
  error,
  isMobile = false,
  zoneFilters,
  onZoneFiltersChange,
}) => {
  if (mode === 'cards') {
    return <VenueTwinsCardsView data={data} loading={loading} error={error} />;
  }

  return (
    <SimilarityInsightsView
      data={data}
      tacticalEdgesData={tacticalEdgesData}
      loading={loading}
      error={error}
      isMobile={isMobile}
      zoneFilters={zoneFilters}
      onZoneFiltersChange={onZoneFiltersChange}
    />
  );
};

export default VenueSimilarity;
