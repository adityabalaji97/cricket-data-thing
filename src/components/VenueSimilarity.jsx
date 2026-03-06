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
  Popover,
  Select,
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

const ZONE_LABELS_RHB = ['Point', 'Cover', 'Long Off', 'Long On', 'Midwicket', 'Sq Leg', 'Fine Leg', 'Behind'];
const ZONE_LABELS_LHB = ['Sq Leg', 'Midwicket', 'Long On', 'Long Off', 'Cover', 'Point', 'Third Man', 'Fine Leg'];

const EDGE_LINE_GROUPS = [
  { key: 'OFF', label: 'Off' },
  { key: 'MIDDLE', label: 'Middle' },
  { key: 'LEG', label: 'Leg' },
];

const EDGE_LENGTH_GROUPS = [
  { key: 'YORKER', label: 'Yorker' },
  { key: 'FULL', label: 'Full' },
  { key: 'GOOD', label: 'Good' },
  { key: 'BOAL', label: 'Back of Length' },
  { key: 'SHORT', label: 'Short' },
];

const PITCH_PROFILE_LENGTH_GROUPS = [
  { key: 'YORKER', label: 'Yorker' },
  { key: 'FULL', label: 'Full' },
  { key: 'GOOD', label: 'Good' },
  { key: 'BOAL', label: 'Back of Length' },
  { key: 'SHORT', label: 'Short' },
];

const EDGE_MIN_BALLS_THRESHOLD = 15;
const PITCH_MIN_BALLS_THRESHOLD = 20;

const EDGE_METRICS = {
  dot_delta: { label: 'Dot%', digits: 1, suffix: '%', metricKey: 'dot_pct' },
  econ_delta: { label: 'Economy', digits: 2, suffix: '', metricKey: 'economy' },
  boundary_delta: { label: 'Boundary%', digits: 1, suffix: '%', metricKey: 'boundary_pct' },
  wicket_delta: { label: 'Wicket%', digits: 1, suffix: '%', metricKey: 'wicket_pct' },
};

const PITCH_METRICS = {
  sr: { label: 'SR', digits: 0, suffix: '', higherIsBowlerFriendly: false },
  dot_pct: { label: 'Dot%', digits: 1, suffix: '%', higherIsBowlerFriendly: true },
  boundary_pct: { label: 'Boundary%', digits: 1, suffix: '%', higherIsBowlerFriendly: false },
};

const fmt = (value, digits = 2, suffix = '') => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return `${Number(value).toFixed(digits)}${suffix}`;
};

const toNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatSigned = (value, digits = 1, suffix = '') => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  const numeric = Number(value);
  const sign = numeric > 0 ? '+' : '';
  return `${sign}${numeric.toFixed(digits)}${suffix}`;
};

const normalizeAxisToken = (value) => String(value || '').trim().toUpperCase().replace(/[-\s]+/g, '_');

const bucketBowlKind = (value) => {
  const token = normalizeAxisToken(value).toLowerCase();
  if (!token) return 'unknown';
  if (token.includes('pace') || token.includes('fast') || token.includes('seam') || token.includes('medium')) {
    return 'pace';
  }
  if (token.includes('spin') || token.includes('slow')) {
    return 'spin';
  }
  return token;
};

const mapLineGroup = (value) => {
  const token = normalizeAxisToken(value);
  if (!token) return null;
  if (token.includes('DOWN_LEG') || token.includes('LEGSTUMP') || token.includes('LEG_STUMP') || token.includes('OUTSIDE_LEG') || token.includes('WIDE_DOWN_LEG') || token === 'LEG') {
    return 'LEG';
  }
  if (token.includes('OUTSIDE_OFF') || token.includes('OFFSTUMP') || token.includes('OFF_STUMP') || token.includes('WIDE_OUTSIDE_OFF') || token === 'OFF') {
    return 'OFF';
  }
  if (token.includes('MIDDLE') || token.includes('ON_THE_STUMPS') || token.includes('ON_STUMPS') || token.includes('STUMPS') || token === 'ON_THE_STUMP' || token === 'ON_STUMP') {
    return 'MIDDLE';
  }
  return null;
};

const mapLengthGroup = (value) => {
  const token = normalizeAxisToken(value);
  if (!token) return null;
  if (token.includes('YORKER')) return 'YORKER';
  if (
    token.includes('BACK_OF_A_LENGTH')
    || token.includes('BACK_OF_LENGTH')
    || token.includes('SHORT_OF_A_GOOD_LENGTH')
    || token.includes('SHORT_OF_GOOD_LENGTH')
    || token.includes('SHORT_OF_A_LENGTH')
    || token.includes('SHORT_OF_LENGTH')
    || token.includes('BOAL')
  ) {
    return 'BOAL';
  }
  if (token === 'SHORT' || token.startsWith('SHORT_') || token === 'BOUNCER') return 'SHORT';
  if (token === 'GOOD' || token === 'GOOD_LENGTH' || (token.includes('GOOD') && !token.includes('SHORT_OF'))) return 'GOOD';
  if (token === 'FULL' || token === 'FULL_TOSS' || token.startsWith('FULL_')) return 'FULL';
  return null;
};

const mapProfileLengthGroup = (value) => {
  return mapLengthGroup(value);
};

const getDivergingCellColors = (value, maxAbs, forceNeutral = false) => {
  if (forceNeutral || value === null || value === undefined) {
    return {
      backgroundColor: 'rgba(148, 163, 184, 0.12)',
      color: '#475569',
      borderColor: 'rgba(148, 163, 184, 0.25)',
    };
  }

  const absValue = Math.abs(Number(value));
  const intensity = maxAbs > 0 ? Math.min(absValue / maxAbs, 1) : 0;
  const alpha = 0.14 + (0.34 * intensity);

  if (value > 0) {
    return {
      backgroundColor: `rgba(22, 163, 74, ${alpha})`,
      color: '#14532d',
      borderColor: 'rgba(22, 163, 74, 0.38)',
    };
  }
  if (value < 0) {
    return {
      backgroundColor: `rgba(220, 38, 38, ${alpha})`,
      color: '#7f1d1d',
      borderColor: 'rgba(220, 38, 38, 0.35)',
    };
  }
  return {
    backgroundColor: 'rgba(148, 163, 184, 0.16)',
    color: '#475569',
    borderColor: 'rgba(148, 163, 184, 0.28)',
  };
};

const aggregateTacticalGrid = (rows, bowlKindFilter = 'all') => {
  const buckets = {};

  (rows || []).forEach((row) => {
    const lineGroup = mapLineGroup(row?.line);
    const lengthGroup = mapLengthGroup(row?.length);
    if (!lineGroup || !lengthGroup) return;

    const rowKind = bucketBowlKind(row?.bowl_kind);
    if (bowlKindFilter !== 'all' && rowKind !== bowlKindFilter) return;

    const key = `${lengthGroup}_${lineGroup}`;
    if (!buckets[key]) {
      buckets[key] = {
        key,
        lineGroup,
        lengthGroup,
        targetBalls: 0,
        baselineBalls: 0,
        targetRuns: 0,
        baselineRuns: 0,
        targetDots: 0,
        baselineDots: 0,
        targetWickets: 0,
        baselineWickets: 0,
        targetBoundaries: 0,
        baselineBoundaries: 0,
      };
    }

    const bucket = buckets[key];
    const targetBalls = Math.max(0, Number(row?.target?.balls) || 0);
    const baselineBalls = Math.max(0, Number(row?.baseline?.balls) || 0);

    const targetEcon = toNumber(row?.target?.economy);
    const baselineEcon = toNumber(row?.baseline?.economy);
    const targetDotPct = toNumber(row?.target?.dot_pct);
    const baselineDotPct = toNumber(row?.baseline?.dot_pct);
    const targetWicketPct = toNumber(row?.target?.wicket_pct);
    const baselineWicketPct = toNumber(row?.baseline?.wicket_pct);
    const targetBoundaryPct = toNumber(row?.target?.boundary_pct);
    const baselineBoundaryPct = toNumber(row?.baseline?.boundary_pct);

    bucket.targetBalls += targetBalls;
    bucket.baselineBalls += baselineBalls;

    if (targetBalls > 0 && targetEcon !== null) bucket.targetRuns += (targetEcon * targetBalls) / 6;
    if (baselineBalls > 0 && baselineEcon !== null) bucket.baselineRuns += (baselineEcon * baselineBalls) / 6;

    if (targetBalls > 0 && targetDotPct !== null) bucket.targetDots += (targetDotPct * targetBalls) / 100;
    if (baselineBalls > 0 && baselineDotPct !== null) bucket.baselineDots += (baselineDotPct * baselineBalls) / 100;

    if (targetBalls > 0 && targetWicketPct !== null) bucket.targetWickets += (targetWicketPct * targetBalls) / 100;
    if (baselineBalls > 0 && baselineWicketPct !== null) bucket.baselineWickets += (baselineWicketPct * baselineBalls) / 100;

    if (targetBalls > 0 && targetBoundaryPct !== null) bucket.targetBoundaries += (targetBoundaryPct * targetBalls) / 100;
    if (baselineBalls > 0 && baselineBoundaryPct !== null) bucket.baselineBoundaries += (baselineBoundaryPct * baselineBalls) / 100;
  });

  const output = {};
  Object.entries(buckets).forEach(([key, bucket]) => {
    const targetBalls = bucket.targetBalls;
    const baselineBalls = bucket.baselineBalls;

    const targetMetrics = {
      economy: targetBalls > 0 ? (bucket.targetRuns * 6) / targetBalls : null,
      dot_pct: targetBalls > 0 ? (bucket.targetDots * 100) / targetBalls : null,
      wicket_pct: targetBalls > 0 ? (bucket.targetWickets * 100) / targetBalls : null,
      boundary_pct: targetBalls > 0 ? (bucket.targetBoundaries * 100) / targetBalls : null,
    };

    const baselineMetrics = {
      economy: baselineBalls > 0 ? (bucket.baselineRuns * 6) / baselineBalls : null,
      dot_pct: baselineBalls > 0 ? (bucket.baselineDots * 100) / baselineBalls : null,
      wicket_pct: baselineBalls > 0 ? (bucket.baselineWickets * 100) / baselineBalls : null,
      boundary_pct: baselineBalls > 0 ? (bucket.baselineBoundaries * 100) / baselineBalls : null,
    };

    output[key] = {
      ...bucket,
      targetMetrics,
      baselineMetrics,
      deltas: {
        econ_delta: targetMetrics.economy !== null && baselineMetrics.economy !== null
          ? baselineMetrics.economy - targetMetrics.economy
          : null,
        dot_delta: targetMetrics.dot_pct !== null && baselineMetrics.dot_pct !== null
          ? targetMetrics.dot_pct - baselineMetrics.dot_pct
          : null,
        wicket_delta: targetMetrics.wicket_pct !== null && baselineMetrics.wicket_pct !== null
          ? targetMetrics.wicket_pct - baselineMetrics.wicket_pct
          : null,
        boundary_delta: targetMetrics.boundary_pct !== null && baselineMetrics.boundary_pct !== null
          ? baselineMetrics.boundary_pct - targetMetrics.boundary_pct
          : null,
      },
    };
  });

  return output;
};

const parseLineLengthGridEntry = (gridKey, value) => {
  const explicitLine = normalizeAxisToken(value?.line_group);
  const explicitLength = normalizeAxisToken(value?.length_group);
  if (explicitLine && explicitLength) {
    return { lineGroup: explicitLine, lengthGroup: explicitLength };
  }

  const parts = String(gridKey || '').split('_');
  if (parts.length < 2) return { lineGroup: '', lengthGroup: '' };
  return {
    lineGroup: normalizeAxisToken(parts[0]),
    lengthGroup: normalizeAxisToken(parts.slice(1).join('_')),
  };
};

const aggregatePitchProfileGrid = (gridData) => {
  const buckets = {};

  Object.entries(gridData || {}).forEach(([gridKey, value]) => {
    if (!value) return;

    const parsed = parseLineLengthGridEntry(gridKey, value);
    const lineGroup = parsed.lineGroup === 'MID' ? 'MIDDLE' : parsed.lineGroup;
    const mappedLineGroup = EDGE_LINE_GROUPS.some((entry) => entry.key === lineGroup)
      ? lineGroup
      : mapLineGroup(lineGroup);
    const lengthGroup = mapProfileLengthGroup(parsed.lengthGroup);

    if (!mappedLineGroup || !lengthGroup) return;

    const balls = Math.max(0, Number(value?.balls) || 0);
    if (!balls) return;

    const runs = toNumber(value?.runs) ?? ((toNumber(value?.sr) ?? 0) * balls) / 100;
    const boundaries = toNumber(value?.boundaries) ?? ((toNumber(value?.boundary_pct) ?? 0) * balls) / 100;
    const dots = toNumber(value?.dots) ?? ((toNumber(value?.dot_pct) ?? 0) * balls) / 100;
    const wickets = toNumber(value?.wickets) ?? ((toNumber(value?.wicket_pct) ?? 0) * balls) / 100;

    const key = `${lengthGroup}_${mappedLineGroup}`;
    if (!buckets[key]) {
      buckets[key] = {
        key,
        lengthGroup,
        lineGroup: mappedLineGroup,
        balls: 0,
        runs: 0,
        boundaries: 0,
        dots: 0,
        wickets: 0,
      };
    }

    buckets[key].balls += balls;
    buckets[key].runs += runs;
    buckets[key].boundaries += boundaries;
    buckets[key].dots += dots;
    buckets[key].wickets += wickets;
  });

  const output = {};
  Object.entries(buckets).forEach(([key, bucket]) => {
    const balls = bucket.balls;
    output[key] = {
      ...bucket,
      sr: balls > 0 ? (bucket.runs * 100) / balls : null,
      dot_pct: balls > 0 ? (bucket.dots * 100) / balls : null,
      boundary_pct: balls > 0 ? (bucket.boundaries * 100) / balls : null,
      wicket_pct: balls > 0 ? (bucket.wickets * 100) / balls : null,
      economy: balls > 0 ? (bucket.runs * 6) / balls : null,
    };
  });

  return output;
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

const buildZoneRadarOption = (targetZoneProfile, similarZoneProfile, zoneMetric = 'boundary_pct', batHand = null) => {
  const metricKey = zoneMetric === 'run_pct' ? 'run_pct' : 'boundary_pct';
  const metricLabel = metricKey === 'run_pct' ? 'Run %' : 'Boundary %';
  const zoneLabels = batHand === 'LHB' ? ZONE_LABELS_LHB : ZONE_LABELS_RHB;

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
          .map((value, index) => `${zoneLabels[index]}: ${Number(value).toFixed(1)}%`)
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
      startAngle: 135,
      clockwise: true,
      indicator: zoneLabels.map((label) => ({
        name: label,
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

        const similarResponse = await axios.get(`${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}/similar?${similarParams.toString()}`);
        if (cancelled) return;

        setData(similarResponse.data);

        const edgesParams = new URLSearchParams(similarParams.toString());
        edgesParams.set('baseline_mode', 'league');
        edgesParams.set('sort_by', 'econ_delta');
        edgesParams.set('sort_order', 'desc');
        edgesParams.set('min_balls', '24');
        edgesParams.set('top_n_similar', '5');

        const similarVenueNames = (similarResponse.data.most_similar || [])
          .map((v) => v.venue)
          .filter(Boolean)
          .join(',');
        if (similarVenueNames) {
          edgesParams.set('similar_venues', similarVenueNames);
        }

        const edgesResponse = await axios.get(`${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}/tactical-edges?${edgesParams.toString()}`);

        if (!cancelled) {
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
  const [edgeMetric, setEdgeMetric] = useState('dot_delta');
  const [edgeBowlKind, setEdgeBowlKind] = useState('all');
  const [edgeDetail, setEdgeDetail] = useState({ anchorEl: null, key: null });
  const [pitchMetric, setPitchMetric] = useState('sr');
  const [pitchDetail, setPitchDetail] = useState({ anchorEl: null, key: null });

  const radarOption = useMemo(() => {
    const similarZoneProfile = data?.similar_aggregate_insights?.zone_profile || {};
    const metric = data?.zone_metric || zoneFilters?.zoneMetric || 'boundary_pct';
    const activeBatHand = zoneFilters?.batHand || data?.active_zone_filters?.bat_hand || null;
    return buildZoneRadarOption(data?.target_zone_profile || {}, similarZoneProfile, metric, activeBatHand);
  }, [data, zoneFilters?.zoneMetric, zoneFilters?.batHand]);

  const edgeRows = useMemo(
    () => tacticalEdgesData?.rows_by_baseline?.[edgeBaselineMode] || tacticalEdgesData?.rows || [],
    [tacticalEdgesData, edgeBaselineMode],
  );

  const tacticalGrid = useMemo(
    () => aggregateTacticalGrid(edgeRows, edgeBowlKind),
    [edgeRows, edgeBowlKind],
  );

  const tacticalMaxAbs = useMemo(() => {
    const values = Object.values(tacticalGrid)
      .filter((cell) => Number(cell?.targetBalls || 0) >= EDGE_MIN_BALLS_THRESHOLD)
      .map((cell) => toNumber(cell?.deltas?.[edgeMetric]))
      .filter((value) => value !== null)
      .map((value) => Math.abs(Number(value)));
    return values.length ? Math.max(...values, 0.5) : 0.5;
  }, [tacticalGrid, edgeMetric]);

  const similarPitchProfile = useMemo(
    () => aggregatePitchProfileGrid(data?.similar_aggregate_insights?.line_length_grid || {}),
    [data?.similar_aggregate_insights?.line_length_grid],
  );

  const targetPitchProfile = useMemo(
    () => aggregatePitchProfileGrid(data?.target_line_length_grid || {}),
    [data?.target_line_length_grid],
  );

  const pitchScale = useMemo(() => {
    const values = Object.values(similarPitchProfile)
      .map((cell) => ({
        value: toNumber(cell?.[pitchMetric]),
        balls: Math.max(1, Number(cell?.balls) || 1),
      }))
      .filter((entry) => entry.value !== null);

    if (!values.length) {
      return { center: 0, maxDeviation: 1 };
    }

    let weightedSum = 0;
    let weight = 0;
    values.forEach((entry) => {
      weightedSum += Number(entry.value) * entry.balls;
      weight += entry.balls;
    });

    const center = weight > 0 ? weightedSum / weight : 0;
    const maxDeviation = Math.max(
      1,
      ...values.map((entry) => Math.abs(Number(entry.value) - center)),
    );
    return { center, maxDeviation };
  }, [similarPitchProfile, pitchMetric]);

  useEffect(() => {
    setEdgeDetail({ anchorEl: null, key: null });
  }, [edgeBaselineMode, edgeMetric, edgeBowlKind, tacticalEdgesData]);

  useEffect(() => {
    setPitchDetail({ anchorEl: null, key: null });
  }, [pitchMetric, data]);

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

  const edgeMetricMeta = EDGE_METRICS[edgeMetric] || EDGE_METRICS.dot_delta;
  const edgeDetailCell = edgeDetail.key ? tacticalGrid[edgeDetail.key] : null;
  const edgeDetailLineLabel = EDGE_LINE_GROUPS.find((entry) => entry.key === edgeDetailCell?.lineGroup)?.label || edgeDetailCell?.lineGroup;
  const edgeDetailLengthLabel = EDGE_LENGTH_GROUPS.find((entry) => entry.key === edgeDetailCell?.lengthGroup)?.label || edgeDetailCell?.lengthGroup;
  const baselineLabel = edgeBaselineMode === 'similar' ? 'Similar Baseline' : 'League Baseline';

  const pitchMetricMeta = PITCH_METRICS[pitchMetric] || PITCH_METRICS.sr;
  const pitchDetailSimilarCell = pitchDetail.key ? similarPitchProfile[pitchDetail.key] : null;
  const pitchDetailTargetCell = pitchDetail.key ? targetPitchProfile[pitchDetail.key] : null;

  const getPitchCellColors = (value, balls) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return getDivergingCellColors(null, 1, true);
    }
    if ((balls || 0) < PITCH_MIN_BALLS_THRESHOLD) {
      return getDivergingCellColors(null, 1, true);
    }

    const deviation = Number(value) - pitchScale.center;
    const normalized = pitchScale.maxDeviation > 0 ? deviation / pitchScale.maxDeviation : 0;
    const bowlerScore = pitchMetricMeta.higherIsBowlerFriendly ? normalized : -normalized;
    return getDivergingCellColors(bowlerScore, 1, false);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        <Chip size="small" label={`${data.qualified_venues} qualified venues`} />
        <Chip size="small" label={`Min matches: ${data.min_matches}`} />
      </Box>

      <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none', order: 2 }}>
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

      <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none', order: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.75 }}>
          Similar Venues Pitch Profile
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Green indicates bowler-friendly zones for the selected metric across similar venues.
        </Typography>

        <Box sx={{ mt: 1, mb: 1.1, display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
          {Object.entries(PITCH_METRICS).map(([metricKey, metricMeta]) => (
            <Chip
              key={`pitch-metric-${metricKey}`}
              size="small"
              color={pitchMetric === metricKey ? 'primary' : 'default'}
              variant={pitchMetric === metricKey ? 'filled' : 'outlined'}
              label={metricMeta.label}
              onClick={() => setPitchMetric(metricKey)}
            />
          ))}
        </Box>

        <Box sx={{ mt: 0.6, border: '1px solid', borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: '84px repeat(3, minmax(70px, 1fr))' }}>
            <Box sx={{ borderRight: '1px solid', borderColor: 'divider', bgcolor: 'grey.50' }} />
            {EDGE_LINE_GROUPS.map((line) => (
              <Box
                key={`pitch-head-${line.key}`}
                sx={{
                  p: 0.8,
                  textAlign: 'center',
                  borderRight: line.key === 'LEG' ? 'none' : '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'grey.50',
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 700 }}>{line.label}</Typography>
              </Box>
            ))}

            {PITCH_PROFILE_LENGTH_GROUPS.map((length) => (
              <React.Fragment key={`pitch-row-${length.key}`}>
                <Box
                  sx={{
                    minHeight: 52,
                    px: 0.9,
                    display: 'flex',
                    alignItems: 'center',
                    borderTop: '1px solid',
                    borderRight: '1px solid',
                    borderColor: 'divider',
                    bgcolor: 'grey.50',
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>{length.label}</Typography>
                </Box>
                {EDGE_LINE_GROUPS.map((line) => {
                  const key = `${length.key}_${line.key}`;
                  const cell = similarPitchProfile[key];
                  const value = toNumber(cell?.[pitchMetric]);
                  const balls = Number(cell?.balls || 0);
                  const colors = getPitchCellColors(value, balls);
                  const display = value === null
                    ? '--'
                    : `${pitchMetric === 'sr' ? 'SR ' : ''}${Number(value).toFixed(pitchMetricMeta.digits)}${pitchMetricMeta.suffix}`;

                  return (
                    <Box
                      key={`pitch-cell-${key}`}
                      role={value !== null ? 'button' : undefined}
                      tabIndex={value !== null ? 0 : -1}
                      onClick={value !== null ? (event) => setPitchDetail({ anchorEl: event.currentTarget, key }) : undefined}
                      onKeyDown={(event) => {
                        if (value !== null && (event.key === 'Enter' || event.key === ' ')) {
                          event.preventDefault();
                          setPitchDetail({ anchorEl: event.currentTarget, key });
                        }
                      }}
                      sx={{
                        minHeight: 52,
                        p: 0.8,
                        borderTop: '1px solid',
                        borderRight: line.key === 'LEG' ? 'none' : '1px solid',
                        borderColor: 'divider',
                        cursor: value !== null ? 'pointer' : 'default',
                        backgroundColor: colors.backgroundColor,
                        color: colors.color,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        textAlign: 'center',
                        gap: 0.2,
                        opacity: balls < PITCH_MIN_BALLS_THRESHOLD ? 0.72 : 1,
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 700 }}>{display}</Typography>
                      <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>{balls || 0} balls</Typography>
                    </Box>
                  );
                })}
              </React.Fragment>
            ))}
          </Box>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.7, display: 'block' }}>
          Cells under {PITCH_MIN_BALLS_THRESHOLD} balls are dimmed.
        </Typography>
      </Card>

      <Card sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', boxShadow: 'none' }}>
        <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.75 }}>
          Tactical Edges at This Venue
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Green cells are bowler-favorable deltas vs baseline; red cells are batter-favorable.
        </Typography>

        <Box sx={{ mt: 1, display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
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

        <Box sx={{ mt: 1, display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
          {Object.entries(EDGE_METRICS).map(([metricKey, metricMeta]) => (
            <Chip
              key={`edge-metric-${metricKey}`}
              size="small"
              color={edgeMetric === metricKey ? 'primary' : 'default'}
              variant={edgeMetric === metricKey ? 'filled' : 'outlined'}
              label={metricMeta.label}
              onClick={() => setEdgeMetric(metricKey)}
            />
          ))}
        </Box>

        <Box sx={{ mt: 1, display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
          <Chip
            size="small"
            color={edgeBowlKind === 'all' ? 'primary' : 'default'}
            variant={edgeBowlKind === 'all' ? 'filled' : 'outlined'}
            label="All"
            onClick={() => setEdgeBowlKind('all')}
          />
          <Chip
            size="small"
            color={edgeBowlKind === 'pace' ? 'primary' : 'default'}
            variant={edgeBowlKind === 'pace' ? 'filled' : 'outlined'}
            label="Pace"
            onClick={() => setEdgeBowlKind('pace')}
          />
          <Chip
            size="small"
            color={edgeBowlKind === 'spin' ? 'primary' : 'default'}
            variant={edgeBowlKind === 'spin' ? 'filled' : 'outlined'}
            label="Spin"
            onClick={() => setEdgeBowlKind('spin')}
          />
        </Box>

        <Box sx={{ mt: 1.1, border: '1px solid', borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: '84px repeat(3, minmax(70px, 1fr))' }}>
            <Box sx={{ borderRight: '1px solid', borderColor: 'divider', bgcolor: 'grey.50' }} />
            {EDGE_LINE_GROUPS.map((line) => (
              <Box
                key={`edge-head-${line.key}`}
                sx={{
                  p: 0.8,
                  textAlign: 'center',
                  borderRight: line.key === 'LEG' ? 'none' : '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'grey.50',
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 700 }}>{line.label}</Typography>
              </Box>
            ))}

            {EDGE_LENGTH_GROUPS.map((length) => (
              <React.Fragment key={`edge-row-${length.key}`}>
                <Box
                  sx={{
                    minHeight: 52,
                    px: 0.9,
                    display: 'flex',
                    alignItems: 'center',
                    borderTop: '1px solid',
                    borderRight: '1px solid',
                    borderColor: 'divider',
                    bgcolor: 'grey.50',
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>{length.label}</Typography>
                </Box>
                {EDGE_LINE_GROUPS.map((line) => {
                  const key = `${length.key}_${line.key}`;
                  const cell = tacticalGrid[key];
                  const value = toNumber(cell?.deltas?.[edgeMetric]);
                  const targetBalls = Number(cell?.targetBalls || 0);
                  const lowSample = targetBalls > 0 && targetBalls < EDGE_MIN_BALLS_THRESHOLD;
                  const colors = getDivergingCellColors(value, tacticalMaxAbs, lowSample || value === null);

                  return (
                    <Box
                      key={`edge-cell-${key}`}
                      role={value !== null ? 'button' : undefined}
                      tabIndex={value !== null ? 0 : -1}
                      onClick={value !== null ? (event) => setEdgeDetail({ anchorEl: event.currentTarget, key }) : undefined}
                      onKeyDown={(event) => {
                        if (value !== null && (event.key === 'Enter' || event.key === ' ')) {
                          event.preventDefault();
                          setEdgeDetail({ anchorEl: event.currentTarget, key });
                        }
                      }}
                      sx={{
                        minHeight: 52,
                        p: 0.8,
                        borderTop: '1px solid',
                        borderRight: line.key === 'LEG' ? 'none' : '1px solid',
                        borderColor: colors.borderColor,
                        cursor: value !== null ? 'pointer' : 'default',
                        backgroundColor: colors.backgroundColor,
                        color: colors.color,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        textAlign: 'center',
                        gap: 0.2,
                      }}
                    >
                      <Typography variant="caption" sx={{ fontWeight: 700 }}>
                        {formatSigned(value, edgeMetricMeta.digits, edgeMetricMeta.suffix)}
                      </Typography>
                      <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>
                        {targetBalls || 0} balls
                      </Typography>
                    </Box>
                  );
                })}
              </React.Fragment>
            ))}
          </Box>
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.75, display: 'block' }}>
          Cells under {EDGE_MIN_BALLS_THRESHOLD} balls are dimmed.
        </Typography>
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

      <Popover
        open={Boolean(edgeDetail.anchorEl && edgeDetailCell)}
        anchorEl={edgeDetail.anchorEl}
        onClose={() => setEdgeDetail({ anchorEl: null, key: null })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        transformOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        {edgeDetailCell && (
          <Box sx={{ p: 1.2, minWidth: 230, maxWidth: 280 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {edgeDetailLengthLabel} • {edgeDetailLineLabel}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.8 }}>
              {edgeMetricMeta.label} delta ({baselineLabel})
            </Typography>

            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {formatSigned(edgeDetailCell.deltas?.[edgeMetric], edgeMetricMeta.digits, edgeMetricMeta.suffix)}
            </Typography>

            <Typography variant="caption" sx={{ display: 'block', mt: 0.8 }}>
              This venue: {fmt(edgeDetailCell.targetMetrics?.[edgeMetricMeta.metricKey], edgeMetricMeta.digits, edgeMetricMeta.suffix)}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block' }}>
              {baselineLabel}: {fmt(edgeDetailCell.baselineMetrics?.[edgeMetricMeta.metricKey], edgeMetricMeta.digits, edgeMetricMeta.suffix)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.6 }}>
              Balls: {edgeDetailCell.targetBalls || 0} (target) / {edgeDetailCell.baselineBalls || 0} (baseline)
            </Typography>
          </Box>
        )}
      </Popover>

      <Popover
        open={Boolean(pitchDetail.anchorEl && pitchDetailSimilarCell)}
        anchorEl={pitchDetail.anchorEl}
        onClose={() => setPitchDetail({ anchorEl: null, key: null })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        transformOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        {pitchDetailSimilarCell && (
          <Box sx={{ p: 1.2, minWidth: 245, maxWidth: 300 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              {PITCH_PROFILE_LENGTH_GROUPS.find((entry) => entry.key === pitchDetailSimilarCell.lengthGroup)?.label || pitchDetailSimilarCell.lengthGroup}
              {' • '}
              {EDGE_LINE_GROUPS.find((entry) => entry.key === pitchDetailSimilarCell.lineGroup)?.label || pitchDetailSimilarCell.lineGroup}
            </Typography>

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.4 }}>
              Similar venues
            </Typography>
            <Typography variant="caption" sx={{ display: 'block' }}>
              Balls: {pitchDetailSimilarCell.balls || 0}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block' }}>
              SR: {fmt(pitchDetailSimilarCell.sr, 1)}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block' }}>
              Dot%: {fmt(pitchDetailSimilarCell.dot_pct, 1, '%')}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block' }}>
              Boundary%: {fmt(pitchDetailSimilarCell.boundary_pct, 1, '%')}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block' }}>
              Wicket%: {fmt(pitchDetailSimilarCell.wicket_pct, 1, '%')}
            </Typography>

            {pitchDetailTargetCell && (
              <>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.8 }}>
                  Target venue
                </Typography>
                <Typography variant="caption" sx={{ display: 'block' }}>
                  Balls: {pitchDetailTargetCell.balls || 0}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block' }}>
                  SR: {fmt(pitchDetailTargetCell.sr, 1)}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block' }}>
                  Dot%: {fmt(pitchDetailTargetCell.dot_pct, 1, '%')}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block' }}>
                  Boundary%: {fmt(pitchDetailTargetCell.boundary_pct, 1, '%')}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block' }}>
                  Wicket%: {fmt(pitchDetailTargetCell.wicket_pct, 1, '%')}
                </Typography>
              </>
            )}
          </Box>
        )}
      </Popover>
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
