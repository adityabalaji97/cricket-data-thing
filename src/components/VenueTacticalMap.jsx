import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Tabs,
  Tab,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { AlertBanner, EmptyState } from './ui';
import { PitchMapVisualization } from './PitchMap';
import config from '../config';
import { colors as designColors } from '../theme/designSystem';

const VenueTacticalMap = ({
  venue,
  startDate,
  endDate,
  isMobile = false,
  leagues,
  includeInternational = false,
  topTeams = null,
}) => {
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pitchData, setPitchData] = useState(null);
  const [wagonData, setWagonData] = useState(null);

  const [phase, setPhase] = useState('overall');
  const [bowlKind, setBowlKind] = useState('all');
  const [bowlStyle, setBowlStyle] = useState('all');
  const [line, setLine] = useState('all');
  const [length, setLength] = useState('all');
  const [shot, setShot] = useState('all');
  const [pitchMetric, setPitchMetric] = useState('runs');
  const [groupBy, setGroupBy] = useState('line');
  const [sortMetric, setSortMetric] = useState('runs');

  const leaguesKey = Array.isArray(leagues) ? leagues.join('|') : '';
  const chartContainerRef = useRef(null);
  const [wagonSize, setWagonSize] = useState(360);

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

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (phase !== 'overall') params.append('phase', phase);
        if (bowlKind !== 'all') params.append('bowl_kind', bowlKind);
        if (bowlStyle !== 'all') params.append('bowl_style', bowlStyle);
        if (line !== 'all') params.append('line', line);
        if (length !== 'all') params.append('length', length);
        if (shot !== 'all') params.append('shot', shot);
        if (includeInternational) params.append('include_international', 'true');
        if (includeInternational && topTeams) params.append('top_teams', topTeams);
        (Array.isArray(leagues) ? leagues : []).forEach((l) => params.append('leagues', l));

        const base = `${config.API_URL}/visualizations/venue/${encodeURIComponent(venue)}`;
        const [pitchResp, wagonResp] = await Promise.all([
          fetch(`${base}/pitch-map?${params.toString()}`),
          fetch(`${base}/wagon-wheel?${params.toString()}`),
        ]);

        if (!pitchResp.ok) throw new Error('Failed to fetch venue pitch map');
        if (!wagonResp.ok) throw new Error('Failed to fetch venue wagon wheel');

        const [pitchJson, wagonJson] = await Promise.all([pitchResp.json(), wagonResp.json()]);
        if (!cancelled) {
          const totalBalls = pitchJson.total_balls || 0;
          const cells = (pitchJson.cells || []).map((c) => ({
            ...c,
            percent_balls: totalBalls > 0 ? (c.balls * 100) / totalBalls : 0,
          }));
          setPitchData({ ...pitchJson, cells });
          setWagonData(wagonJson);
        }
      } catch (err) {
        console.error('Error fetching venue tactical maps:', err);
        if (!cancelled) setError(err.message || 'Failed to load tactical maps');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [
    venue,
    startDate,
    endDate,
    phase,
    bowlKind,
    bowlStyle,
    line,
    length,
    shot,
    includeInternational,
    topTeams,
    leaguesKey,
  ]);

  const deliveries = wagonData?.deliveries || [];
  const totalBalls = wagonData?.total_deliveries || 0;

  const options = useMemo(() => {
    const uniq = (key) => [...new Set(deliveries.map((d) => d[key]).filter(Boolean))].sort();
    return {
      bowlKinds: uniq('bowl_kind'),
      bowlStyles: uniq('bowl_style'),
      lines: uniq('line'),
      lengths: uniq('length'),
      shots: uniq('shot'),
    };
  }, [deliveries]);

  const groupedRows = useMemo(() => {
    if (!deliveries.length) return [];
    const map = new Map();
    for (const d of deliveries) {
      const key = d[groupBy] ?? 'Unknown';
      if (!map.has(key)) {
        map.set(key, { group: key, balls: 0, runs: 0, wickets: 0 });
      }
      const row = map.get(key);
      row.balls += 1;
      row.runs += d.runs || 0;
      row.wickets += d.is_wicket ? 1 : 0;
    }
    return [...map.values()]
      .map((r) => ({
        ...r,
        strike_rate: r.balls ? (r.runs * 100) / r.balls : 0,
        pct_balls: totalBalls ? (r.balls * 100) / totalBalls : 0,
      }))
      .sort((a, b) => {
        if (sortMetric === 'group') return String(a.group).localeCompare(String(b.group));
        return (b[sortMetric] || 0) - (a[sortMetric] || 0);
      });
  }, [deliveries, groupBy, sortMetric, totalBalls]);

  const zoneStats = useMemo(() => {
    const zones = {};
    for (const d of deliveries) {
      if (d.wagon_zone == null) continue;
      const key = d.wagon_zone;
      if (!zones[key]) zones[key] = { balls: 0, runs: 0, wickets: 0 };
      zones[key].balls += 1;
      zones[key].runs += d.runs || 0;
      zones[key].wickets += d.is_wicket ? 1 : 0;
    }
    return zones;
  }, [deliveries]);

  const filterConfig = [
    {
      key: 'phase',
      label: 'Phase',
      options: [
        { value: 'overall', label: 'Overall' },
        { value: 'powerplay', label: isMobile ? 'PP' : 'Powerplay' },
        { value: 'middle', label: 'Middle' },
        { value: 'death', label: 'Death' },
      ],
    },
    {
      key: 'bowlKind',
      label: 'Pace/Spin',
      options: [{ value: 'all', label: 'All' }, ...options.bowlKinds.map((v) => ({ value: v, label: v }))],
    },
    {
      key: 'bowlStyle',
      label: 'Bowler Type',
      options: [{ value: 'all', label: 'All' }, ...options.bowlStyles.map((v) => ({ value: v, label: v }))],
    },
    {
      key: 'line',
      label: 'Line',
      options: [{ value: 'all', label: 'All' }, ...options.lines.map((v) => ({ value: v, label: v }))],
    },
    {
      key: 'length',
      label: 'Length',
      options: [{ value: 'all', label: 'All' }, ...options.lengths.map((v) => ({ value: v, label: v }))],
    },
    {
      key: 'shot',
      label: 'Shot',
      options: [{ value: 'all', label: 'All' }, ...options.shots.map((v) => ({ value: v, label: v }))],
    },
    {
      key: 'pitchMetric',
      label: 'Pitch Color',
      options: [
        { value: 'runs', label: 'Runs' },
        { value: 'wickets', label: 'Wkts' },
        { value: 'strike_rate', label: 'SR' },
        { value: 'control_percentage', label: 'Control%' },
        { value: 'balls', label: 'Balls' },
        { value: 'percent_balls', label: '% Balls' },
      ],
    },
  ];

  const topTableFilters = [
    {
      key: 'groupBy',
      label: 'Group By',
      options: [
        { value: 'line', label: 'Line' },
        { value: 'length', label: 'Length' },
        { value: 'shot', label: 'Shot' },
        { value: 'phase', label: 'Phase' },
        { value: 'bowl_kind', label: 'Pace/Spin' },
        { value: 'bowl_style', label: 'Bowler Type' },
      ],
    },
    {
      key: 'sortMetric',
      label: 'Sort',
      options: [
        { value: 'runs', label: 'Runs' },
        { value: 'wickets', label: 'Wickets' },
        { value: 'strike_rate', label: 'SR' },
        { value: 'balls', label: 'Balls' },
        { value: 'pct_balls', label: '% Balls' },
      ],
    },
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'phase') setPhase(value);
    if (key === 'bowlKind') {
      setBowlKind(value);
      setBowlStyle('all');
    }
    if (key === 'bowlStyle') setBowlStyle(value);
    if (key === 'line') setLine(value);
    if (key === 'length') setLength(value);
    if (key === 'shot') setShot(value);
    if (key === 'pitchMetric') setPitchMetric(value);
    if (key === 'groupBy') setGroupBy(value);
    if (key === 'sortMetric') setSortMetric(value);
  };

  const renderWagonWheel = () => {
    if (!deliveries.length) return null;
    const width = Math.min(wagonSize, isMobile ? 360 : 420);
    const height = width;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = width * 0.4;
    const scale = maxRadius / 300;

    const zoneLines = Array.from({ length: 8 }).map((_, i) => {
      const angle = (i * Math.PI / 4) - Math.PI / 2;
      const x2 = centerX + maxRadius * Math.cos(angle);
      const y2 = centerY + maxRadius * Math.sin(angle);
      return <line key={i} x1={centerX} y1={centerY} x2={x2} y2={y2} stroke="#ddd" strokeDasharray="4,4" />;
    });

    const linesSvg = deliveries
      .filter((d) => d.wagon_x != null && d.wagon_y != null)
      .slice(-1200)
      .map((d, idx) => {
        let x = centerX + (d.wagon_x - 150) * scale;
        let y = centerY + (d.wagon_y - 150) * scale;
        if (d.runs === 4 || d.runs === 6) {
          const dx = x - centerX;
          const dy = y - centerY;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          x = centerX + (dx / dist) * maxRadius;
          y = centerY + (dy / dist) * maxRadius;
        }
        const color = d.is_wicket
          ? designColors.chart.red
          : d.runs === 6
          ? designColors.chart.pink
          : d.runs === 4
          ? designColors.chart.blue
          : d.runs > 0
          ? designColors.chart.green
          : designColors.neutral[400];
        const opacity = d.is_wicket ? 0.8 : d.runs >= 4 ? 0.6 : 0.35;
        const strokeWidth = d.is_wicket ? 2.5 : d.runs >= 4 ? 1.8 : 1;
        return (
          <line
            key={`${idx}-${d.match_id}-${d.over}`}
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

    const zoneLabels = Object.entries(zoneStats).map(([zone, z]) => {
      if (!z.balls) return null;
      const angle = ((Number(zone) - 1) * Math.PI / 4) - Math.PI / 2 + Math.PI / 8;
      const r = maxRadius * 0.72;
      return (
        <text
          key={`label-${zone}`}
          x={centerX + r * Math.cos(angle)}
          y={centerY + r * Math.sin(angle)}
          textAnchor="middle"
          fontSize={isMobile ? 10 : 11}
          fill="#444"
        >
          {z.runs}
        </text>
      );
    });

    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: '100%' }}>
        <circle cx={centerX} cy={centerY} r={maxRadius} fill="#fafafa" stroke="#ddd" strokeWidth="2" />
        {zoneLines}
        {linesSvg}
        <circle cx={centerX} cy={centerY} r={6} fill="#333" />
        {zoneLabels}
      </svg>
    );
  };

  if (!venue) return null;

  if (loading && !pitchData && !wagonData) {
    return (
      <Card isMobile={isMobile}>
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
          <Typography sx={{ mt: 1.5 }}>Loading venue tactical maps...</Typography>
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

  const noData = (pitchData?.total_balls || 0) === 0 && (wagonData?.total_deliveries || 0) === 0;
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 1.5 }}>
        <Typography variant={isMobile ? 'h6' : 'h5'} sx={{ fontWeight: 600 }}>
          Venue Tactical Explorer
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip size="small" label={`${pitchData?.total_balls || 0} pitch-map balls`} />
          <Chip size="small" label={`${wagonData?.total_deliveries || 0} wagon deliveries`} />
        </Box>
      </Box>

      <FilterBar
        filters={filterConfig}
        activeFilters={{ phase, bowlKind, bowlStyle, line, length, shot, pitchMetric }}
        onFilterChange={handleFilterChange}
        isMobile={isMobile}
      />

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mt: 1.5, mb: 1 }}>
        <Tab label="Pitch Map" />
        <Tab label="Wagon Wheel" />
        <Tab label="Top Buckets" />
      </Tabs>

      {loading && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Refreshing...
        </Typography>
      )}

      {tab === 0 && (
        <Box sx={{ maxWidth: isMobile ? 360 : 440, mx: 'auto' }}>
          {pitchData?.total_balls ? (
            <PitchMapVisualization
              cells={pitchData.cells}
              mode="grid"
              colorMetric={pitchMetric}
              displayMetrics={['runs', 'wickets']}
              secondaryMetrics={['balls', 'strike_rate']}
              minBalls={3}
              title={venue}
              subtitle={`${phase === 'overall' ? 'All phases' : phase}${bowlKind !== 'all' ? ` • ${bowlKind}` : ''}${bowlStyle !== 'all' ? ` • ${bowlStyle}` : ''}`}
              hideStumps={true}
              compactMode={isMobile}
            />
          ) : (
            <EmptyState title="No pitch map data" description="No line/length-tagged deliveries for these filters." isMobile={isMobile} minHeight={240} />
          )}
        </Box>
      )}

      {tab === 1 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Colors: wickets (red), sixes (pink), fours (blue), singles/twos/threes (green), dots (gray). Zone labels show total runs.
          </Typography>
          <Box ref={chartContainerRef} sx={{ display: 'flex', justifyContent: 'center', minHeight: 280 }}>
            {wagonData?.total_deliveries ? renderWagonWheel() : (
              <EmptyState title="No wagon wheel data" description="No wagon coordinates available for these filters." isMobile={isMobile} minHeight={240} />
            )}
          </Box>
        </Box>
      )}

      {tab === 2 && (
        <Box>
          <FilterBar
            filters={topTableFilters}
            activeFilters={{ groupBy, sortMetric }}
            onFilterChange={handleFilterChange}
            isMobile={isMobile}
          />
          <TableContainer sx={{ mt: 1.5, maxHeight: 420 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>{groupBy}</TableCell>
                  <TableCell align="right">Balls</TableCell>
                  <TableCell align="right">Runs</TableCell>
                  <TableCell align="right">Wkts</TableCell>
                  <TableCell align="right">SR</TableCell>
                  <TableCell align="right">% Balls</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {groupedRows.slice(0, 20).map((row) => (
                  <TableRow key={String(row.group)}>
                    <TableCell>{row.group || 'Unknown'}</TableCell>
                    <TableCell align="right">{row.balls}</TableCell>
                    <TableCell align="right">{row.runs}</TableCell>
                    <TableCell align="right">{row.wickets}</TableCell>
                    <TableCell align="right">{row.strike_rate.toFixed(1)}</TableCell>
                    <TableCell align="right">{row.pct_balls.toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
                {groupedRows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">No grouped data</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Card>
  );
};

export default VenueTacticalMap;
