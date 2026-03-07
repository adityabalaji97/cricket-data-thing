import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import CaughtDismissalScatterMap from './charts/CaughtDismissalScatterMap';
import ExploreLink from './ui/ExploreLink';
import { buildQueryUrl } from '../utils/queryBuilderLinks';
import config from '../config';
import {
  getScoringZoneLabel,
  isLeftHandBat,
  normalizeScoringZone,
  SCORING_ZONE_CLOCKWISE_FROM_TOP,
} from '../utils/wagonZones';

const DEFAULT_FILTERS = {
  phase: 'overall',
  bowlKind: 'all',
  bowlStyle: 'all',
  batHand: 'all',
  selectedZone: 'all',
};

const PHASE_LABELS = {
  powerplay: 'Powerplay',
  middle: 'Middle',
  death: 'Death',
};

const toCountMap = (deliveries, key) => {
  const map = {};
  deliveries.forEach((delivery) => {
    const value = delivery?.[key];
    if (!value) return;
    map[value] = (map[value] || 0) + 1;
  });
  return map;
};

const topEntry = (countMap) => (
  Object.entries(countMap)
    .sort((a, b) => b[1] - a[1])[0] || [null, 0]
);

const DismissalFieldDesigner = ({
  context,
  playerName,
  venue,
  selectedVenue = 'All Venues',
  startDate,
  endDate,
  leagues = [],
  includeInternational = false,
  topTeams = null,
  isMobile = false,
  summaryData = null,
}) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [draftFilters, setDraftFilters] = useState(DEFAULT_FILTERS);
  const [filterOpen, setFilterOpen] = useState(false);
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const targetValue = context === 'venue' ? venue : playerName;
  const endpoint = useMemo(() => {
    if (!targetValue) return null;
    if (context === 'venue') {
      return `${config.API_URL}/visualizations/venue/${encodeURIComponent(targetValue)}/wagon-wheel`;
    }
    if (context === 'player_bowling') {
      return `${config.API_URL}/visualizations/bowler/${encodeURIComponent(targetValue)}/wagon-wheel`;
    }
    return `${config.API_URL}/visualizations/player/${encodeURIComponent(targetValue)}/wagon-wheel`;
  }, [context, targetValue]);

  useEffect(() => {
    if (!endpoint) return;
    let cancelled = false;

    const fetchCaughtDeliveries = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        const scopedVenue = context === 'venue' ? venue : selectedVenue;
        if (scopedVenue && scopedVenue !== 'All Venues') {
          params.append('venue', scopedVenue);
        }

        (leagues || []).forEach((league) => params.append('leagues', league));
        params.append('include_international', String(!!includeInternational));
        if (includeInternational && topTeams) params.append('top_teams', String(topTeams));

        if (filters.phase !== 'overall') params.append('phase', filters.phase);
        if (filters.bowlKind !== 'all') params.append('bowl_kind', filters.bowlKind);
        if (filters.bowlStyle !== 'all') params.append('bowl_style', filters.bowlStyle);
        if (filters.batHand !== 'all') params.append('bat_hand', filters.batHand);

        params.append('dismissal', 'caught');
        params.append('dismissal_mode', 'exact');
        params.append('max_points', '2000');

        const response = await fetch(`${endpoint}?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to load caught dismissal points');
        const payload = await response.json();
        if (cancelled) return;
        setDeliveries(Array.isArray(payload?.deliveries) ? payload.deliveries : []);
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError.message || 'Failed to load caught dismissal points');
          setDeliveries([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchCaughtDeliveries();
    return () => {
      cancelled = true;
    };
  }, [
    endpoint,
    context,
    venue,
    selectedVenue,
    startDate,
    endDate,
    leagues,
    includeInternational,
    topTeams,
    filters.phase,
    filters.bowlKind,
    filters.bowlStyle,
    filters.batHand,
  ]);

  const deliveriesWithZone = useMemo(() => (
    deliveries.map((delivery) => ({
      ...delivery,
      __zone: normalizeScoringZone(delivery),
    }))
  ), [deliveries]);

  const visibleDeliveries = useMemo(() => {
    if (filters.selectedZone === 'all') return deliveriesWithZone;
    return deliveriesWithZone.filter((delivery) => delivery.__zone === filters.selectedZone);
  }, [deliveriesWithZone, filters.selectedZone]);

  const options = useMemo(() => {
    const unique = (key) => [...new Set(deliveries.map((delivery) => delivery?.[key]).filter(Boolean))].sort();
    return {
      bowlKinds: unique('bowl_kind'),
      bowlStyles: unique('bowl_style'),
      batHands: unique('bat_hand'),
    };
  }, [deliveries]);

  const bowlStylesForKind = useMemo(() => {
    if (draftFilters.bowlKind === 'all') return options.bowlStyles;
    return [...new Set(
      deliveries
        .filter((delivery) => delivery?.bowl_kind === draftFilters.bowlKind)
        .map((delivery) => delivery?.bowl_style)
        .filter(Boolean)
    )].sort();
  }, [deliveries, draftFilters.bowlKind, options.bowlStyles]);

  const activeLabelBatHand = useMemo(() => (
    isLeftHandBat(filters.batHand) ? 'LHB' : 'RHB'
  ), [filters.batHand]);

  const draftLabelBatHand = useMemo(() => (
    isLeftHandBat(draftFilters.batHand) ? 'LHB' : 'RHB'
  ), [draftFilters.batHand]);

  const zoneStats = useMemo(() => {
    const counts = {};
    visibleDeliveries.forEach((delivery) => {
      if (!delivery.__zone) return;
      counts[delivery.__zone] = (counts[delivery.__zone] || 0) + 1;
    });
    const total = visibleDeliveries.length || 1;
    return Object.entries(counts)
      .map(([zone, count]) => ({
        zone,
        count,
        pct: (count * 100) / total,
      }))
      .sort((a, b) => b.count - a.count);
  }, [visibleDeliveries]);

  const recommendations = useMemo(() => {
    const sample = visibleDeliveries.length;
    const lowSample = sample < 12;
    if (sample === 0) {
      return {
        lowSample: false,
        tips: [],
      };
    }

    const [topZone = { zone: '1', count: 0, pct: 0 }] = zoneStats;
    const phaseCounts = toCountMap(visibleDeliveries, 'phase');
    const [topPhase, topPhaseCount] = topEntry(phaseCounts);
    const bowlKindCounts = toCountMap(visibleDeliveries, 'bowl_kind');
    const [topKind, topKindCount] = topEntry(bowlKindCounts);
    const batHandCounts = toCountMap(visibleDeliveries, 'bat_hand');
    const [topHand, topHandCount] = topEntry(batHandCounts);

    const zoneLabel = getScoringZoneLabel(topZone.zone, activeLabelBatHand);
    const phaseLabel = PHASE_LABELS[topPhase] || topPhase || 'overall';

    const tip1 = `${lowSample ? 'Directional:' : 'Primary arc:'} ${zoneLabel} (${topZone.count}/${sample}, ${topZone.pct.toFixed(1)}%).`;
    const tip2 = topPhase
      ? `${lowSample ? 'Directional:' : 'Phase focus:'} ${phaseLabel} holds ${topPhaseCount} of ${sample} catches; bias catchers for this window.`
      : `${lowSample ? 'Directional:' : 'Phase focus:'} Keep a balanced ring with one deep catcher each side.`;

    let tip3 = `${lowSample ? 'Directional:' : 'Matchup focus:'} Keep one catcher square and one straighter to cover miscued lofts.`;
    if (filters.bowlKind !== 'all') {
      tip3 = `${lowSample ? 'Directional:' : 'Matchup focus:'} For ${filters.bowlKind}, protect ${zoneLabel} first, then mirror with one square-side catcher.`;
    } else if (topKind) {
      tip3 = `${lowSample ? 'Directional:' : 'Matchup focus:'} ${topKind} accounts for ${topKindCount}/${sample} catches; start with that bowling type field template.`;
    } else if (topHand) {
      tip3 = `${lowSample ? 'Directional:' : 'Matchup focus:'} ${topHand} batters account for ${topHandCount}/${sample} catches; shift the ring accordingly.`;
    }

    return {
      lowSample,
      tips: [tip1, tip2, tip3],
    };
  }, [visibleDeliveries, zoneStats, filters.bowlKind, activeLabelBatHand]);

  const summary = useMemo(() => {
    const totalDismissals = Number(summaryData?.total_dismissals ?? summaryData?.total_wickets ?? 0);
    const caughtOverall = Number(
      (summaryData?.dismissals || []).find((item) => String(item?.type || '').toLowerCase() === 'caught')?.count
      || 0
    );
    const caughtPct = totalDismissals > 0 ? (caughtOverall * 100) / totalDismissals : 0;

    const phaseCaught = ['powerplay', 'middle', 'death'].map((phase) => {
      const entry = (summaryData?.by_phase?.[phase] || [])
        .find((item) => String(item?.type || '').toLowerCase() === 'caught');
      return {
        phase,
        count: Number(entry?.count || 0),
      };
    });

    return {
      totalDismissals,
      caughtOverall,
      caughtPct,
      phaseCaught,
    };
  }, [summaryData]);

  const activeFilterCount = useMemo(() => (
    Object.keys(DEFAULT_FILTERS).filter((key) => filters[key] !== DEFAULT_FILTERS[key]).length
  ), [filters]);

  const totalLabel = context === 'player_bowling'
    ? `${summary.totalDismissals} total wickets`
    : `${summary.totalDismissals} total dismissals`;

  const queryBuilderUrl = useMemo(() => {
    const queryFilters = {
      ...(context === 'venue' ? { venue } : {}),
      ...(context === 'player_batting' ? { batters: [playerName] } : {}),
      ...(context === 'player_bowling' ? { bowlers: [playerName] } : {}),
      ...(context !== 'venue' && selectedVenue && selectedVenue !== 'All Venues' ? { venue: selectedVenue } : {}),
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
      ...(leagues?.length ? { leagues } : {}),
      ...(includeInternational ? { include_international: true } : {}),
      ...(includeInternational && topTeams ? { top_teams: topTeams } : {}),
      dismissal: ['caught'],
      ...(filters.bowlKind !== 'all' ? { bowl_kind: [filters.bowlKind] } : {}),
      ...(filters.bowlStyle !== 'all' ? { bowl_style: [filters.bowlStyle] } : {}),
      ...(filters.batHand !== 'all' ? { bat_hand: filters.batHand } : {}),
    };

    if (filters.phase === 'powerplay') {
      queryFilters.over_min = 0;
      queryFilters.over_max = 5;
    } else if (filters.phase === 'middle') {
      queryFilters.over_min = 6;
      queryFilters.over_max = 14;
    } else if (filters.phase === 'death') {
      queryFilters.over_min = 15;
      queryFilters.over_max = 19;
    }

    return buildQueryUrl(queryFilters, ['dismissal', 'wagon_zone']);
  }, [
    context,
    playerName,
    venue,
    selectedVenue,
    startDate,
    endDate,
    leagues,
    includeInternational,
    topTeams,
    filters.phase,
    filters.bowlKind,
    filters.bowlStyle,
    filters.batHand,
  ]);

  const renderSelect = (label, key, values, includeAll = true) => {
    const options = values.map((value) => {
      if (typeof value === 'object' && value !== null) return value;
      return { value, label: value };
    });

    return (
      <FormControl size="small" fullWidth>
        <InputLabel>{label}</InputLabel>
        <Select
          label={label}
          value={draftFilters[key]}
          onChange={(event) => {
            const value = event.target.value;
            setDraftFilters((prev) => {
              const next = { ...prev, [key]: value };
              if (key === 'bowlKind') next.bowlStyle = 'all';
              return next;
            });
          }}
        >
          {includeAll && <MenuItem value="all">All</MenuItem>}
          {options.map((option) => (
            <MenuItem key={`${key}-${option.value}`} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  };

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

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={totalLabel} size="small" />
        <Chip
          label={`${summary.caughtOverall} caught (${summary.caughtPct.toFixed(1)}%)`}
          size="small"
          color="error"
          variant="outlined"
        />
        {summary.phaseCaught.map((item) => (
          <Chip
            key={item.phase}
            label={`${PHASE_LABELS[item.phase]} ${item.count}`}
            size="small"
            variant="outlined"
          />
        ))}
        <IconButton onClick={openFilters} size="small" aria-label="Open filters">
          <Badge badgeContent={activeFilterCount} color="primary" invisible={activeFilterCount === 0}>
            <FilterListIcon />
          </Badge>
        </IconButton>
      </Stack>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
          <CircularProgress size={26} />
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && (
        <>
          <CaughtDismissalScatterMap
            deliveries={visibleDeliveries}
            isMobile={isMobile}
            dotMode="caught"
            batHand={activeLabelBatHand}
            selectedZone={filters.selectedZone}
            onZoneSelect={(zone) => setFilters((prev) => ({ ...prev, selectedZone: zone }))}
          />

          <Box>
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Hotspots</Typography>
            {zoneStats.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No caught dismissal points for the current filters.
              </Typography>
            ) : (
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {zoneStats.slice(0, 3).map((item) => (
                  <Chip
                    key={`hotspot-${item.zone}`}
                    size="small"
                    label={`${getScoringZoneLabel(item.zone, activeLabelBatHand)}: ${item.count} (${item.pct.toFixed(1)}%)`}
                    color={item.zone === zoneStats[0].zone ? 'primary' : 'default'}
                    variant={item.zone === zoneStats[0].zone ? 'filled' : 'outlined'}
                  />
                ))}
              </Stack>
            )}
          </Box>

          <Box>
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Field Design Recommendations</Typography>
            {recommendations.lowSample && (
              <Typography variant="caption" color="warning.main" sx={{ display: 'block', mb: 0.5 }}>
                Low sample; directional only.
              </Typography>
            )}
            {recommendations.tips.length ? (
              <Box component="ol" sx={{ pl: 2, m: 0 }}>
                {recommendations.tips.map((tip) => (
                  <li key={tip}>
                    <Typography variant="body2" color="text.secondary">{tip}</Typography>
                  </li>
                ))}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Add broader filters to generate tactical recommendations.
              </Typography>
            )}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <ExploreLink label="Explore caught dismissal map in Query Builder" to={queryBuilderUrl} />
          </Box>
        </>
      )}

      {isMobile ? (
        <Drawer
          anchor="bottom"
          open={filterOpen}
          onClose={() => setFilterOpen(false)}
          sx={{ '& .MuiDrawer-paper': { borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '85vh' } }}
        >
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>Filters</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.2 }}>
              {renderSelect('Phase', 'phase', ['overall', 'powerplay', 'middle', 'death'], false)}
              {renderSelect('Pace/Spin', 'bowlKind', options.bowlKinds)}
              {renderSelect('Bowler Type', 'bowlStyle', bowlStylesForKind)}
              {renderSelect('Bat Hand', 'batHand', options.batHands)}
              {renderSelect(
                'Zone',
                'selectedZone',
                SCORING_ZONE_CLOCKWISE_FROM_TOP.map((zone) => ({
                  value: zone,
                  label: `${zone} - ${getScoringZoneLabel(zone, draftLabelBatHand)}`,
                }))
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
              <Button variant="outlined" fullWidth onClick={clearFilters}>Clear</Button>
              <Button variant="contained" fullWidth onClick={applyFilters}>Apply</Button>
            </Box>
          </Box>
        </Drawer>
      ) : (
        <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth maxWidth="sm">
          <DialogTitle sx={{ fontWeight: 700 }}>Filters</DialogTitle>
          <DialogContent dividers>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.2, mt: 0.5 }}>
              {renderSelect('Phase', 'phase', ['overall', 'powerplay', 'middle', 'death'], false)}
              {renderSelect('Pace/Spin', 'bowlKind', options.bowlKinds)}
              {renderSelect('Bowler Type', 'bowlStyle', bowlStylesForKind)}
              {renderSelect('Bat Hand', 'batHand', options.batHands)}
              {renderSelect(
                'Zone',
                'selectedZone',
                SCORING_ZONE_CLOCKWISE_FROM_TOP.map((zone) => ({
                  value: zone,
                  label: `${zone} - ${getScoringZoneLabel(zone, draftLabelBatHand)}`,
                }))
              )}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={clearFilters}>Clear</Button>
            <Button variant="contained" onClick={applyFilters}>Apply</Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
};

export default DismissalFieldDesigner;
