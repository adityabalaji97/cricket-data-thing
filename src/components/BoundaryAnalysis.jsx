import React, { useState, useEffect } from 'react';
import {
  Box, Typography, ToggleButtonGroup, ToggleButton, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  useMediaQuery, useTheme,
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import Card from './ui/Card';
import { fetchAnalyticsJson } from '../utils/analyticsApi';
import { colors as designColors } from '../theme/designSystem';

const MIN_BALLS = 30;

const PHASE_OPTIONS = [
  { value: 'overall', label: 'Overall' },
  { value: 'powerplay', label: 'Powerplay' },
  { value: 'middle', label: 'Middle' },
  { value: 'death', label: 'Death' },
];

const GROUP_COLORS = {
  pace: designColors.chart.blue,
  spin: designColors.chart.orange,
  RHB: designColors.chart.blue,
  LHB: designColors.chart.green,
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <Box sx={{ bgcolor: 'background.paper', p: 1, border: '1px solid #ccc', borderRadius: 1 }}>
      <Typography variant="subtitle2">{label}</Typography>
      {payload.map((entry) => (
        entry.value != null && (
          <Typography key={entry.name} variant="body2" sx={{ color: entry.color }}>
            {entry.name}: {entry.value} ({entry.payload[`${entry.dataKey}_pct`]?.toFixed(1) ?? '-'}%)
          </Typography>
        )
      ))}
    </Box>
  );
};

const buildChartData = (groups) => {
  if (!groups || Object.keys(groups).length === 0) return [];

  const groupKeys = Object.keys(groups);
  const allShots = new Map();

  groupKeys.forEach((gk) => {
    const shots = groups[gk]?.shots || {};
    Object.entries(shots).forEach(([shot, data]) => {
      if (!allShots.has(shot)) {
        allShots.set(shot, { shot, _totalBoundaries: 0 });
      }
      const entry = allShots.get(shot);
      entry[gk] = data.boundaries;
      entry[`${gk}_pct`] = data.boundary_pct;
      entry._totalBoundaries += data.boundaries;
    });
  });

  return Array.from(allShots.values())
    .filter((d) => d._totalBoundaries > 0)
    .sort((a, b) => b._totalBoundaries - a._totalBoundaries)
    .slice(0, 15);
};

const buildStyleChartData = (groups) => {
  if (!groups || Object.keys(groups).length === 0) return [];

  const allStyles = new Map();
  Object.values(groups).forEach((group) => {
    const styles = group?.styles || {};
    Object.entries(styles).forEach(([style, data]) => {
      if (!allStyles.has(style)) {
        allStyles.set(style, { style, boundaries: 0, total_balls: 0, boundary_pct: 0 });
      }
      const entry = allStyles.get(style);
      entry.boundaries += data.boundaries;
      entry.total_balls += data.total_balls;
    });
  });

  const result = Array.from(allStyles.values())
    .filter((d) => d.boundaries > 0)
    .map((d) => ({ ...d, boundary_pct: d.total_balls > 0 ? +(d.boundaries / d.total_balls * 100).toFixed(1) : 0 }))
    .sort((a, b) => b.boundaries - a.boundaries);

  return result;
};

const buildDetailRows = (groups) => {
  if (!groups) return [];
  return Object.entries(groups)
    .filter(([, data]) => data.total_balls > 0)
    .map(([key, data]) => ({ key, ...data }));
};

const getTotalBalls = (data) => {
  if (!data?.overall?.groups) return 0;
  return Object.values(data.overall.groups).reduce((sum, g) => sum + (g.total_balls || 0), 0);
};

const BoundaryAnalysis = ({ context, name, startDate, endDate, leagues, isMobile: isMobileProp }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPhase, setSelectedPhase] = useState('overall');
  const [drillDown, setDrillDown] = useState(false);

  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;

  useEffect(() => {
    if (!name || !context) return;

    setLoading(true);
    setError(null);

    const params = { context, name };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (leagues?.length) params.leagues = leagues;

    fetchAnalyticsJson('/boundary-analysis', params)
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [context, name, startDate, endDate, leagues]);

  if (loading) {
    return (
      <Card isMobile={isMobile}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      </Card>
    );
  }

  if (error) {
    return (
      <Card isMobile={isMobile}>
        <Alert severity="error" sx={{ mb: 1 }}>Failed to load boundary analysis</Alert>
      </Card>
    );
  }

  if (!data || getTotalBalls(data) < MIN_BALLS) return null;

  const phaseGroups = selectedPhase === 'overall'
    ? data.overall?.groups
    : data.phases?.[selectedPhase]?.groups;

  const groupKeys = phaseGroups ? Object.keys(phaseGroups) : [];
  const chartData = buildChartData(phaseGroups);
  const detailRows = buildDetailRows(phaseGroups);
  const showStyleDrill = context !== 'bowler' && drillDown;
  const styleData = showStyleDrill ? buildStyleChartData(phaseGroups) : [];

  const isBowlerCtx = context === 'bowler';
  const dimLabel = isBowlerCtx ? 'Bat Hand' : 'Bowl Type';

  return (
    <Card isMobile={isMobile}>
      <Typography variant="h6" gutterBottom>
        Boundary Analysis
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2, alignItems: 'center' }}>
        <ToggleButtonGroup
          value={selectedPhase}
          exclusive
          onChange={(_, v) => v && setSelectedPhase(v)}
          size="small"
        >
          {PHASE_OPTIONS.map((p) => (
            <ToggleButton key={p.value} value={p.value}>{p.label}</ToggleButton>
          ))}
        </ToggleButtonGroup>

        {context !== 'bowler' && (
          <ToggleButtonGroup
            value={drillDown ? 'style' : 'type'}
            exclusive
            onChange={(_, v) => v && setDrillDown(v === 'style')}
            size="small"
          >
            <ToggleButton value="type">Pace / Spin</ToggleButton>
            <ToggleButton value="style">Bowl Style</ToggleButton>
          </ToggleButtonGroup>
        )}
      </Box>

      {/* Grouped Bar Chart — Boundaries by Shot */}
      {!showStyleDrill && chartData.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Boundaries by Shot Type
          </Typography>
          <ResponsiveContainer width="100%" height={isMobile ? 280 : 350}>
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="shot"
                tick={{ fontSize: isMobile ? 9 : 11 }}
                interval={0}
                angle={isMobile ? -45 : -30}
                textAnchor="end"
                height={isMobile ? 70 : 60}
              />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {groupKeys.map((gk) => (
                <Bar key={gk} dataKey={gk} name={gk.toUpperCase()} fill={GROUP_COLORS[gk] || designColors.chart.purple} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* Bowl Style Drill-Down Chart */}
      {showStyleDrill && styleData.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Boundaries by Bowl Style
          </Typography>
          <ResponsiveContainer width="100%" height={isMobile ? 280 : 350}>
            <BarChart data={styleData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="style"
                tick={{ fontSize: isMobile ? 9 : 11 }}
                interval={0}
                angle={isMobile ? -45 : -30}
                textAnchor="end"
                height={isMobile ? 70 : 60}
              />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value, _name, props) => {
                  if (_name === 'boundary_pct') return `${value}%`;
                  return `${value} (${props.payload.boundary_pct}%)`;
                }}
              />
              <Legend />
              <Bar dataKey="boundaries" name="Boundaries" fill={designColors.chart.indigo} />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* Detail Table */}
      {detailRows.length > 0 && (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{dimLabel}</TableCell>
                <TableCell align="right">Balls</TableCell>
                <TableCell align="right">Runs</TableCell>
                <TableCell align="right">4s</TableCell>
                <TableCell align="right">6s</TableCell>
                <TableCell align="right">Boundaries</TableCell>
                <TableCell align="right">Boundary %</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {detailRows.map((row) => (
                <TableRow key={row.key}>
                  <TableCell sx={{ fontWeight: 500 }}>{row.key.toUpperCase()}</TableCell>
                  <TableCell align="right">{row.total_balls}</TableCell>
                  <TableCell align="right">{row.total_runs}</TableCell>
                  <TableCell align="right">{row.fours}</TableCell>
                  <TableCell align="right">{row.sixes}</TableCell>
                  <TableCell align="right">{row.boundaries}</TableCell>
                  <TableCell align="right">{row.boundary_pct}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Card>
  );
};

export default BoundaryAnalysis;
