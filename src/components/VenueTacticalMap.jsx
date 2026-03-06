import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
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
import FilterListIcon from '@mui/icons-material/FilterList';
import Card from './ui/Card';
import { AlertBanner, EmptyState } from './ui';
import { PitchMapVisualization } from './PitchMap';
import config from '../config';
import { colors as designColors } from '../theme/designSystem';

const DEFAULT_FILTERS = {
  phase: 'overall',
  bowlKind: 'all',
  bowlStyle: 'all',
  batHand: 'all',
  line: 'all',
  length: 'all',
  shot: 'all',
  pitchMetric: 'strike_rate',
  wagonView: 'zones',
  wagonMetric: 'boundary_pct',
  selectedZone: 'all',
  baselineMode: 'league',
  sortBy: 'econ_delta',
  sortOrder: 'desc',
};

const WAGON_METRIC_OPTIONS = [
  { value: 'boundary_pct', label: 'Boundary%' },
  { value: 'boundary_count', label: 'Boundary Count' },
  { value: 'run_pct', label: 'Run%' },
  { value: 'runs', label: 'Runs' },
  { value: 'wickets', label: 'Wkts' },
  { value: 'balls', label: 'Balls' },
  { value: 'strike_rate', label: 'SR' },
];

const EDGE_SORT_OPTIONS = [
  { value: 'econ_delta', label: 'Δ Econ' },
  { value: 'dot_delta', label: 'Δ Dot%' },
  { value: 'wicket_delta', label: 'Δ Wkt%' },
  { value: 'boundary_delta', label: 'Δ Bnd%' },
];

const toNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const fmt = (value, digits = 1, suffix = '') => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return `${Number(value).toFixed(digits)}${suffix}`;
};

const appendSharedParams = (params, {
  startDate,
  endDate,
  includeInternational,
  topTeams,
  leagues,
}) => {
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (includeInternational !== null && includeInternational !== undefined) {
    params.append('include_international', String(includeInternational));
  }
  if (includeInternational && topTeams) {
    params.append('top_teams', String(topTeams));
  }
  (Array.isArray(leagues) ? leagues : []).forEach((league) => params.append('leagues', league));
};

const appendDeliveryFilters = (params, filters) => {
  if (filters.phase !== 'overall') params.append('phase', filters.phase);
  if (filters.bowlKind !== 'all') params.append('bowl_kind', filters.bowlKind);
  if (filters.bowlStyle !== 'all') params.append('bowl_style', filters.bowlStyle);
  if (filters.batHand !== 'all') params.append('bat_hand', filters.batHand);
  if (filters.line !== 'all') params.append('line', filters.line);
  if (filters.length !== 'all') params.append('length', filters.length);
  if (filters.shot !== 'all') params.append('shot', filters.shot);
};

const VenueTacticalMap = ({
  venue,
  startDate,
  endDate,
  isMobile = false,
  leagues,
  includeInternational = false,
  topTeams = null,
  forcedView = null,
  showTabs = true,
}) => {
  const [tab, setTab] = useState(0);
  const [loadingWagon, setLoadingWagon] = useState(false);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [error, setError] = useState(null);
  const [pitchData, setPitchData] = useState(null);
  const [wagonData, setWagonData] = useState(null);
  const [tacticalEdgesData, setTacticalEdgesData] = useState(null);

  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [draftFilters, setDraftFilters] = useState(DEFAULT_FILTERS);
  const [filterOpen, setFilterOpen] = useState(false);

  const leaguesKey = Array.isArray(leagues) ? leagues.join('|') : '';
  const leaguesList = useMemo(() => (leaguesKey ? leaguesKey.split('|').filter(Boolean) : []), [leaguesKey]);
  const chartContainerRef = useRef(null);
  const [wagonSize, setWagonSize] = useState(360);
  const loading = loadingWagon || loadingInsights;
  const deliveryFilters = useMemo(() => ({
    phase: filters.phase,
    bowlKind: filters.bowlKind,
    bowlStyle: filters.bowlStyle,
    batHand: filters.batHand,
    line: filters.line,
    length: filters.length,
    shot: filters.shot,
  }), [
    filters.phase,
    filters.bowlKind,
    filters.bowlStyle,
    filters.batHand,
    filters.line,
    filters.length,
    filters.shot,
  ]);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWagonSize(Math.max(240, Math.floor(entry.contentRect.width)));
      }
    });
    ro.observe(chartContainerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!venue) return;
    let cancelled = false;

    const fetchWagonData = async () => {
      setLoadingWagon(true);
      setError(null);
      try {
        const baseParams = new URLSearchParams();
        appendSharedParams(baseParams, {
          startDate,
          endDate,
          includeInternational,
          topTeams,
          leagues: leaguesList,
        });
        const base = `${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}`;
        const wagonResp = await fetch(`${base}/wagon-wheel?${baseParams.toString()}`);
        if (!wagonResp.ok) throw new Error('Failed to fetch venue wagon wheel');
        const wagonJson = await wagonResp.json();

        if (!cancelled) {
          setWagonData(wagonJson);
        }
      } catch (err) {
        console.error('Error fetching venue wagon wheel data:', err);
        if (!cancelled) {
          setError(err.message || 'Failed to load tactical explorer');
        }
      } finally {
        if (!cancelled) {
          setLoadingWagon(false);
        }
      }
    };

    fetchWagonData();
    return () => {
      cancelled = true;
    };
  }, [
    venue,
    startDate,
    endDate,
    includeInternational,
    topTeams,
    leaguesList,
  ]);

  useEffect(() => {
    if (!venue) return;
    let cancelled = false;

    const fetchPitchAndEdges = async () => {
      setLoadingInsights(true);
      setError(null);
      try {
        const commonParams = new URLSearchParams();
        appendSharedParams(commonParams, {
          startDate,
          endDate,
          includeInternational,
          topTeams,
          leagues: leaguesList,
        });
        appendDeliveryFilters(commonParams, deliveryFilters);

        const tacticalParams = new URLSearchParams(commonParams.toString());
        tacticalParams.append('baseline_mode', filters.baselineMode);
        tacticalParams.append('sort_by', filters.sortBy);
        tacticalParams.append('sort_order', filters.sortOrder);
        tacticalParams.append('min_balls', '24');
        tacticalParams.append('top_n_similar', '5');

        const base = `${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}`;
        const [pitchResp, edgesResp] = await Promise.all([
          fetch(`${base}/pitch-map?${commonParams.toString()}`),
          fetch(`${base}/tactical-edges?${tacticalParams.toString()}`),
        ]);

        if (!pitchResp.ok) throw new Error('Failed to fetch venue pitch map');
        if (!edgesResp.ok) throw new Error('Failed to fetch tactical edges');

        const [pitchJson, edgesJson] = await Promise.all([
          pitchResp.json(),
          edgesResp.json(),
        ]);

        if (!cancelled) {
          const totalBalls = pitchJson.total_balls || 0;
          const cells = (pitchJson.cells || []).map((cell) => ({
            ...cell,
            percent_balls: totalBalls > 0 ? (cell.balls * 100) / totalBalls : 0,
          }));
          setPitchData({ ...pitchJson, cells });
          setTacticalEdgesData(edgesJson);
        }
      } catch (err) {
        console.error('Error fetching venue pitch/edge data:', err);
        if (!cancelled) {
          setError(err.message || 'Failed to load tactical explorer');
        }
      } finally {
        if (!cancelled) {
          setLoadingInsights(false);
        }
      }
    };

    fetchPitchAndEdges();
    return () => {
      cancelled = true;
    };
  }, [
    venue,
    startDate,
    endDate,
    deliveryFilters,
    filters.baselineMode,
    filters.sortBy,
    filters.sortOrder,
    includeInternational,
    topTeams,
    leaguesList,
  ]);

  const allDeliveries = useMemo(() => wagonData?.deliveries ?? [], [wagonData]);
  const deliveries = useMemo(() => {
    return allDeliveries.filter((delivery) => {
      if (filters.phase !== 'overall' && delivery.phase !== filters.phase) return false;
      if (filters.bowlKind !== 'all' && delivery.bowl_kind !== filters.bowlKind) return false;
      if (filters.bowlStyle !== 'all' && delivery.bowl_style !== filters.bowlStyle) return false;
      if (filters.batHand !== 'all' && delivery.bat_hand !== filters.batHand) return false;
      if (filters.line !== 'all' && delivery.line !== filters.line) return false;
      if (filters.length !== 'all' && delivery.length !== filters.length) return false;
      if (filters.shot !== 'all' && delivery.shot !== filters.shot) return false;
      return true;
    });
  }, [
    allDeliveries,
    filters.phase,
    filters.bowlKind,
    filters.bowlStyle,
    filters.batHand,
    filters.line,
    filters.length,
    filters.shot,
  ]);

  const options = useMemo(() => {
    const uniq = (key) => [...new Set(allDeliveries.map((d) => d[key]).filter(Boolean))].sort();
    return {
      bowlKinds: uniq('bowl_kind'),
      bowlStyles: uniq('bowl_style'),
      batHands: uniq('bat_hand'),
      lines: uniq('line'),
      lengths: uniq('length'),
      shots: uniq('shot'),
    };
  }, [allDeliveries]);

  const zoneStatsWithDerived = useMemo(() => {
    const zoneStats = {};
    for (const delivery of deliveries) {
      if (delivery.wagon_zone == null) continue;
      const key = String(delivery.wagon_zone);
      if (!zoneStats[key]) {
        zoneStats[key] = {
          balls: 0,
          runs: 0,
          wickets: 0,
          boundaries: 0,
        };
      }
      zoneStats[key].balls += 1;
      zoneStats[key].runs += toNumber(delivery.runs);
      zoneStats[key].wickets += delivery.is_wicket ? 1 : 0;
      if (toNumber(delivery.runs) === 4 || toNumber(delivery.runs) === 6) {
        zoneStats[key].boundaries += 1;
      }
    }

    const totalRuns = Object.values(zoneStats).reduce((sum, zone) => sum + toNumber(zone.runs), 0);
    const totalBalls = Object.values(zoneStats).reduce((sum, zone) => sum + toNumber(zone.balls), 0);
    const out = {};
    for (let zone = 1; zone <= 8; zone += 1) {
      const key = String(zone);
      const row = zoneStats[key] || { balls: 0, runs: 0, wickets: 0, boundaries: 0 };
      out[key] = {
        ...row,
        strike_rate: row.balls > 0 ? (row.runs * 100) / row.balls : 0,
        boundary_pct: totalBalls > 0 ? (row.boundaries * 100) / totalBalls : 0,
        boundary_count: row.boundaries,
        run_pct: totalRuns > 0 ? (row.runs * 100) / totalRuns : 0,
      };
    }
    return out;
  }, [deliveries]);

  const visibleWagonDeliveries = useMemo(() => {
    if (filters.selectedZone === 'all') return deliveries;
    return deliveries.filter((delivery) => String(delivery.wagon_zone) === String(filters.selectedZone));
  }, [deliveries, filters.selectedZone]);

  useEffect(() => {
    if (filters.selectedZone !== 'all' && !zoneStatsWithDerived[filters.selectedZone]) {
      setFilters((prev) => ({ ...prev, selectedZone: 'all', wagonView: 'zones' }));
    }
  }, [filters.selectedZone, zoneStatsWithDerived]);

  const activeFilterCount = useMemo(() => {
    return Object.entries(filters).filter(([key, value]) => {
      if (!(key in DEFAULT_FILTERS)) return false;
      return value !== DEFAULT_FILTERS[key];
    }).length;
  }, [filters]);

  const activeTab = forcedView === 'pitch'
    ? 0
    : forcedView === 'wagon'
      ? 1
      : forcedView === 'topBuckets'
        ? 2
        : tab;

  const noData = (pitchData?.total_balls || 0) === 0 && allDeliveries.length === 0;

  const openFilters = () => {
    setDraftFilters(filters);
    setFilterOpen(true);
  };

  const applyFilters = () => {
    setFilters(draftFilters);
    setFilterOpen(false);
  };

  const clearFilters = () => {
    setDraftFilters(DEFAULT_FILTERS);
  };

  const renderSelect = (label, key, selectOptions) => (
    <FormControl size="small" fullWidth key={key}>
      <InputLabel>{label}</InputLabel>
      <Select
        label={label}
        value={draftFilters[key] ?? DEFAULT_FILTERS[key]}
        onChange={(event) => {
          const next = event.target.value;
          setDraftFilters((prev) => {
            const updated = { ...prev, [key]: next };
            if (key === 'bowlKind') {
              updated.bowlStyle = 'all';
            }
            return updated;
          });
        }}
      >
        {selectOptions.map((option) => (
          <MenuItem key={`${key}-${option.value}`} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );

  const renderFilterContent = () => {
    const filteredBowlStyles = (draftFilters.bowlKind && draftFilters.bowlKind !== 'all')
      ? [...new Set(allDeliveries
        .filter((delivery) => delivery.bowl_kind === draftFilters.bowlKind)
        .map((delivery) => delivery.bowl_style)
        .filter(Boolean))].sort()
      : options.bowlStyles;

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.2, mt: 0.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Common</Typography>
        {renderSelect('Phase', 'phase', [
          { value: 'overall', label: 'Overall' },
          { value: 'powerplay', label: 'Powerplay' },
          { value: 'middle', label: 'Middle' },
          { value: 'death', label: 'Death' },
        ])}
        {renderSelect('Pace/Spin', 'bowlKind', [{ value: 'all', label: 'All' }, ...options.bowlKinds.map((v) => ({ value: v, label: v }))])}
        {renderSelect('Bowler Type', 'bowlStyle', [{ value: 'all', label: 'All' }, ...filteredBowlStyles.map((v) => ({ value: v, label: v }))])}
        {renderSelect('Bat Hand', 'batHand', [{ value: 'all', label: 'All' }, ...options.batHands.map((v) => ({ value: v, label: v }))])}
        {renderSelect('Line', 'line', [{ value: 'all', label: 'All' }, ...options.lines.map((v) => ({ value: v, label: v }))])}
        {renderSelect('Length', 'length', [{ value: 'all', label: 'All' }, ...options.lengths.map((v) => ({ value: v, label: v }))])}
        {renderSelect('Shot', 'shot', [{ value: 'all', label: 'All' }, ...options.shots.map((v) => ({ value: v, label: v }))])}

        <Divider sx={{ my: 0.2 }} />
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Pitch Map</Typography>
        {renderSelect('Pitch Color', 'pitchMetric', [
          { value: 'runs', label: 'Runs' },
          { value: 'wickets', label: 'Wkts' },
          { value: 'strike_rate', label: 'SR' },
          { value: 'control_percentage', label: 'Control%' },
          { value: 'balls', label: 'Balls' },
          { value: 'percent_balls', label: '% Balls' },
        ])}

        <Divider sx={{ my: 0.2 }} />
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Wagon Wheel</Typography>
        {renderSelect('Wagon View', 'wagonView', [
          { value: 'zones', label: 'Zones' },
          { value: 'rays', label: 'Rays' },
        ])}
        {renderSelect('Zone Metric', 'wagonMetric', WAGON_METRIC_OPTIONS)}
        {renderSelect('Zone Filter', 'selectedZone', [{ value: 'all', label: 'All Zones' }, ...Array.from({ length: 8 }, (_, i) => ({ value: String(i + 1), label: `Zone ${i + 1}` }))])}

        <Divider sx={{ my: 0.2 }} />
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Tactical Edges</Typography>
        {renderSelect('Baseline', 'baselineMode', [
          { value: 'league', label: 'League Average' },
          { value: 'similar', label: 'Similar Venues' },
        ])}
        {renderSelect('Sort By', 'sortBy', EDGE_SORT_OPTIONS)}
        {renderSelect('Sort Order', 'sortOrder', [
          { value: 'desc', label: 'High to Low' },
          { value: 'asc', label: 'Low to High' },
        ])}
      </Box>
    );
  };

  const renderWagonWheel = () => {
    if (!deliveries.length) return null;

    const width = Math.min(wagonSize, isMobile ? 360 : 420);
    const height = width;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = width * 0.4;
    const scale = maxRadius / 300;

    const zoneLines = Array.from({ length: 8 }).map((_, index) => {
      const angle = (index * Math.PI / 4) - Math.PI / 2;
      const x2 = centerX + maxRadius * Math.cos(angle);
      const y2 = centerY + maxRadius * Math.sin(angle);
      return (
        <line
          key={`zone-line-${index}`}
          x1={centerX}
          y1={centerY}
          x2={x2}
          y2={y2}
          stroke="#ddd"
          strokeDasharray="4,4"
        />
      );
    });

    const linesSvg = visibleWagonDeliveries
      .filter((delivery) => delivery.wagon_x != null && delivery.wagon_y != null && Number(delivery.wagon_zone) !== 0)
      .slice(-1200)
      .map((delivery, index) => {
        let x = centerX + (delivery.wagon_x - 150) * scale;
        let y = centerY + (delivery.wagon_y - 150) * scale;

        if (delivery.runs === 4 || delivery.runs === 6) {
          const dx = x - centerX;
          const dy = y - centerY;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          x = centerX + (dx / dist) * maxRadius;
          y = centerY + (dy / dist) * maxRadius;
        }

        const color = delivery.is_wicket
          ? designColors.chart.red
          : delivery.runs === 6
            ? designColors.chart.pink
            : delivery.runs === 4
              ? designColors.chart.blue
              : delivery.runs > 0
                ? designColors.chart.green
                : designColors.neutral[400];

        const opacity = delivery.is_wicket ? 0.8 : delivery.runs >= 4 ? 0.6 : 0.35;
        const strokeWidth = delivery.is_wicket ? 2.5 : delivery.runs >= 4 ? 1.8 : 1;

        return (
          <line
            key={`ray-${index}-${delivery.match_id}-${delivery.over}`}
            x1={centerX}
            y1={centerY}
            x2={x}
            y2={y}
            stroke={color}
            strokeWidth={strokeWidth}
            opacity={opacity}
            strokeLinecap="round"
          />
        );
      });

    const zoneMetricMax = Math.max(
      1,
      ...Object.values(zoneStatsWithDerived).map((zone) => Number(zone[filters.wagonMetric] || 0)),
    );

    const zoneWedges = Array.from({ length: 8 }).map((_, index) => {
      const zoneNum = index + 1;
      const stat = zoneStatsWithDerived[String(zoneNum)] || {
        balls: 0,
        runs: 0,
        wickets: 0,
        boundaries: 0,
        boundary_pct: 0,
        boundary_count: 0,
        run_pct: 0,
        strike_rate: 0,
      };

      const value = Number(stat[filters.wagonMetric] || 0);
      const intensity = value / zoneMetricMax;
      const isActive = filters.selectedZone !== 'all' ? String(filters.selectedZone) === String(zoneNum) : true;
      const startAngle = -Math.PI / 2 + index * (Math.PI / 4);
      const endAngle = startAngle + (Math.PI / 4);
      const x1 = centerX + maxRadius * Math.cos(startAngle);
      const y1 = centerY + maxRadius * Math.sin(startAngle);
      const x2 = centerX + maxRadius * Math.cos(endAngle);
      const y2 = centerY + maxRadius * Math.sin(endAngle);

      const fill = filters.wagonMetric === 'wickets'
        ? `rgba(211,47,47,${0.12 + intensity * 0.6})`
        : filters.wagonMetric === 'balls'
          ? `rgba(30,136,229,${0.10 + intensity * 0.55})`
          : filters.wagonMetric === 'strike_rate'
            ? `rgba(76,175,80,${0.10 + intensity * 0.55})`
            : `rgba(46,125,50,${0.10 + intensity * 0.6})`;

      const zoneTooltip = `Zone ${zoneNum}\nBalls: ${stat.balls}\nRuns: ${stat.runs}\nBoundaries: ${stat.boundaries}\nWkts: ${stat.wickets}\nBoundary%: ${fmt(stat.boundary_pct, 1, '%')}\nRun%: ${fmt(stat.run_pct, 1, '%')}`;

      return (
        <path
          key={`zone-wedge-${zoneNum}`}
          d={`M ${centerX} ${centerY} L ${x1} ${y1} A ${maxRadius} ${maxRadius} 0 0 1 ${x2} ${y2} Z`}
          fill={fill}
          stroke={filters.selectedZone === String(zoneNum) ? '#333' : '#ddd'}
          strokeWidth={filters.selectedZone === String(zoneNum) ? 2 : 1}
          opacity={isActive ? 1 : 0.35}
          style={{ cursor: 'pointer' }}
          onClick={() => {
            setFilters((prev) => ({
              ...prev,
              selectedZone: String(zoneNum),
              wagonView: 'rays',
            }));
          }}
        >
          <title>{zoneTooltip}</title>
        </path>
      );
    });

    const zoneLabels = Object.entries(zoneStatsWithDerived).map(([zone, stats]) => {
      if (!stats.balls || Number(zone) === 0) return null;
      const angle = ((Number(zone) - 1) * Math.PI / 4) - Math.PI / 2 + Math.PI / 8;
      const r = maxRadius * 0.72;
      const value = stats[filters.wagonMetric] || 0;
      const labelValue = filters.wagonMetric.endsWith('_pct') || filters.wagonMetric === 'run_pct'
        ? `${Math.round(value)}%`
        : Math.round(value);

      return (
        <text
          key={`zone-label-${zone}`}
          x={centerX + r * Math.cos(angle)}
          y={centerY + r * Math.sin(angle)}
          textAnchor="middle"
          fontSize={isMobile ? 10 : 11}
          fill="#444"
          fontWeight={600}
        >
          {labelValue}
        </text>
      );
    });

    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: '100%' }}>
        <circle cx={centerX} cy={centerY} r={maxRadius} fill="#fafafa" stroke="#ddd" strokeWidth="2" />
        {filters.wagonView === 'zones' && zoneWedges}
        {zoneLines}
        {filters.wagonView === 'rays' && linesSvg}
        <circle cx={centerX} cy={centerY} r={6} fill="#333" />
        {zoneLabels}
      </svg>
    );
  };

  if (!venue) return null;

  if (loading && !pitchData && !wagonData && !tacticalEdgesData) {
    return (
      <Card isMobile={isMobile}>
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
          <Typography sx={{ mt: 1.5 }}>Loading venue tactical explorer...</Typography>
        </Box>
      </Card>
    );
  }

  if (error) {
    return (
      <Card isMobile={isMobile}>
        <AlertBanner severity="error">{error}</AlertBanner>
      </Card>
    );
  }

  if (noData) {
    return (
      <Card isMobile={isMobile}>
        <EmptyState
          title="No tactical map data"
          description="No pitch-map or wagon-wheel data is available for the selected venue and filters."
          isMobile={isMobile}
          minHeight={260}
        />
      </Card>
    );
  }

  return (
    <Card isMobile={isMobile}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center', mb: 1.5 }}>
        <Typography variant={isMobile ? 'h6' : 'h5'} sx={{ fontWeight: 600 }}>
          Venue Tactical Explorer
        </Typography>
        <IconButton onClick={openFilters} aria-label="Open filters" size="small">
          <Badge badgeContent={activeFilterCount} color="primary" invisible={activeFilterCount === 0}>
            <FilterListIcon />
          </Badge>
        </IconButton>
      </Box>

      {showTabs ? (
        <Tabs value={activeTab} onChange={(_, value) => setTab(value)} sx={{ mt: 0.75, mb: 1 }}>
          <Tab label="Pitch Map" />
          <Tab label="Wagon Wheel" />
          <Tab label="Tactical Edges" />
        </Tabs>
      ) : null}

      {loading && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Refreshing...
        </Typography>
      )}

      {activeTab === 0 && (
        <Box sx={{ maxWidth: isMobile ? 360 : 440, mx: 'auto' }}>
          {pitchData?.total_balls ? (
            <PitchMapVisualization
              cells={pitchData.cells}
              mode="grid"
              colorMetric={filters.pitchMetric}
              displayMetrics={['average', 'strike_rate']}
              secondaryMetrics={['boundary_percentage', 'dot_percentage', 'control_percentage']}
              minBalls={3}
              title={venue}
              subtitle={`${filters.phase === 'overall' ? 'All phases' : filters.phase}${filters.bowlKind !== 'all' ? ` • ${filters.bowlKind}` : ''}${filters.bowlStyle !== 'all' ? ` • ${filters.bowlStyle}` : ''}`}
              hideStumps={true}
              hideLegend={true}
              compactMode={isMobile}
            />
          ) : (
            <EmptyState title="No pitch map data" description="No line/length-tagged deliveries for these filters." isMobile={isMobile} minHeight={240} />
          )}
        </Box>
      )}

      {activeTab === 1 && (
        <Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5, mb: 1 }}>
            <Chip size="small" label={filters.batHand === 'all' ? 'All batters' : filters.batHand} />
            <Chip size="small" label={filters.wagonMetric} variant="outlined" />
            {filters.selectedZone !== 'all' && (
              <Chip
                size="small"
                color="primary"
                label={`Zone ${filters.selectedZone}`}
                onDelete={() => setFilters((prev) => ({ ...prev, selectedZone: 'all' }))}
              />
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Zone view shows where boundaries and runs cluster. Click a zone to drill into rays.
          </Typography>
          <Box ref={chartContainerRef} sx={{ display: 'flex', justifyContent: 'center', minHeight: 280 }}>
            {deliveries.length ? renderWagonWheel() : (
              <EmptyState title="No wagon wheel data" description="No wagon coordinates available for these filters." isMobile={isMobile} minHeight={240} />
            )}
          </Box>
        </Box>
      )}

      {activeTab === 2 && (
        <Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.2 }}>
            <Chip size="small" label={`Baseline: ${filters.baselineMode === 'league' ? 'League' : 'Similar'}`} />
            <Chip size="small" variant="outlined" label={`Sort: ${filters.sortBy}`} />
          </Box>
          <TableContainer sx={{ maxHeight: 460, overflow: 'auto' }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Line</TableCell>
                  <TableCell>Length</TableCell>
                  <TableCell>Pace/Spin</TableCell>
                  <TableCell align="right">Balls</TableCell>
                  <TableCell align="right">Econ</TableCell>
                  <TableCell align="right">Dot%</TableCell>
                  <TableCell align="right">Wkt%</TableCell>
                  <TableCell align="right">Bnd%</TableCell>
                  <TableCell align="right">ΔEcon</TableCell>
                  <TableCell align="right">ΔDot</TableCell>
                  <TableCell align="right">ΔWkt</TableCell>
                  <TableCell align="right">ΔBnd</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(tacticalEdgesData?.rows || []).map((row, index) => (
                  <TableRow key={`${row.line}-${row.length}-${row.bowl_kind}-${index}`}>
                    <TableCell>{row.line}</TableCell>
                    <TableCell>{row.length}</TableCell>
                    <TableCell>{row.bowl_kind}</TableCell>
                    <TableCell align="right">{row.target?.balls || 0}</TableCell>
                    <TableCell align="right">{fmt(row.target?.economy, 2)}</TableCell>
                    <TableCell align="right">{fmt(row.target?.dot_pct, 1, '%')}</TableCell>
                    <TableCell align="right">{fmt(row.target?.wicket_pct, 1, '%')}</TableCell>
                    <TableCell align="right">{fmt(row.target?.boundary_pct, 1, '%')}</TableCell>
                    <TableCell align="right">{fmt(row.deltas?.econ_delta, 2)}</TableCell>
                    <TableCell align="right">{fmt(row.deltas?.dot_delta, 1, '%')}</TableCell>
                    <TableCell align="right">{fmt(row.deltas?.wicket_delta, 1, '%')}</TableCell>
                    <TableCell align="right">{fmt(row.deltas?.boundary_delta, 1, '%')}</TableCell>
                  </TableRow>
                ))}
                {(tacticalEdgesData?.rows || []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={12} align="center">No tactical edge rows for this filter set</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {isMobile ? (
        <Drawer
          anchor="bottom"
          open={filterOpen}
          onClose={() => setFilterOpen(false)}
          sx={{
            '& .MuiDrawer-paper': {
              borderTopLeftRadius: 16,
              borderTopRightRadius: 16,
              maxHeight: '85vh',
            },
          }}
        >
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>Filters</Typography>
            <Box sx={{ maxHeight: '65vh', overflow: 'auto', pr: 0.5 }}>
              {renderFilterContent()}
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, mt: 2 }}>
              <Button variant="outlined" onClick={clearFilters} fullWidth>Clear all</Button>
              <Button variant="contained" onClick={applyFilters} fullWidth>Apply</Button>
            </Box>
          </Box>
        </Drawer>
      ) : (
        <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth maxWidth="sm">
          <DialogTitle sx={{ fontWeight: 700 }}>Filters</DialogTitle>
          <DialogContent dividers sx={{ maxHeight: '70vh' }}>
            {renderFilterContent()}
          </DialogContent>
          <DialogActions>
            <Button onClick={clearFilters}>Clear all</Button>
            <Button variant="contained" onClick={applyFilters}>Apply</Button>
          </DialogActions>
        </Dialog>
      )}
    </Card>
  );
};

export default VenueTacticalMap;
