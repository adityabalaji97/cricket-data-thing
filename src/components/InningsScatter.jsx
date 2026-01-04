import React, { useState } from 'react';
import { Typography, Box, useMediaQuery, useTheme } from '@mui/material';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { colors as designColors } from '../theme/designSystem';

const InningsScatter = ({ innings }) => {
  const [xMetric, setXMetric] = useState('balls');
  const [yMetric, setYMetric] = useState('strike_rate');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const getPhase = (over) => {
    if (over < 6) return 0;
    if (over < 10) return 1;
    if (over < 15) return 2;
    return 3;
  };

  const data = innings.map(inning => ({
    balls: inning.balls_faced,
    position: inning.batting_position,
    entry_over: inning.entry_point.overs,
    phase: getPhase(inning.entry_point.overs),
    runs: inning.runs,
    strike_rate: inning.strike_rate,
    sr_diff: inning.team_comparison.sr_diff,
    average: inning.runs / (inning.wickets || 1),
    date: inning.date,
    competition: inning.competition,
    team_sr: inning.team_comparison.team_sr_excl_batter
  }));

  const xAxisMetrics = {
    balls: { key: 'balls', label: isMobile ? 'Balls' : 'Balls Faced' },
    position: { key: 'position', label: isMobile ? 'Position' : 'Batting Position' },
    entry: { key: 'entry_over', label: isMobile ? 'Entry' : 'Entry Point (overs)' },
    phase: { key: 'phase', label: isMobile ? 'Phase' : 'Entry Phase' }
  };

  const yAxisMetrics = {
    runs: { key: 'runs', label: 'Runs' },
    strike_rate: { key: 'strike_rate', label: isMobile ? 'SR' : 'Strike Rate' },
    sr_diff: { key: 'sr_diff', label: isMobile ? 'SR vs Team' : 'SR vs Team' },
    average: { key: 'average', label: isMobile ? 'Avg' : 'Average' }
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const inning = payload[0].payload;
      const phaseNames = ['0-6', '6-10', '10-15', '15-20'];

      return (
        <Card sx={{ p: isMobile ? 0.75 : 1, bgcolor: 'background.paper' }}>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.75rem' : '0.875rem', fontWeight: 600 }}>
            {`${inning.runs} (${inning.balls})`}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            {`SR: ${inning.strike_rate.toFixed(1)}`}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            {`Team SR: ${inning.team_sr.toFixed(1)} (Diff: ${inning.sr_diff.toFixed(1)})`}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            {`Position: ${inning.position}`}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            {`Entry: Over ${inning.entry_over.toFixed(1)} (${phaseNames[inning.phase]})`}
          </Typography>
          <Typography variant="caption" display="block" sx={{ fontSize: isMobile ? '0.65rem' : '0.7rem' }}>
            {inning.competition}
          </Typography>
          <Typography variant="caption" display="block" sx={{ fontSize: isMobile ? '0.65rem' : '0.7rem' }}>
            {new Date(inning.date).toLocaleDateString()}
          </Typography>
        </Card>
      );
    }
    return null;
  };

  const getAxisProps = (metric) => {
    if (metric === 'phase') {
      return {
        type: 'number',
        domain: [-0.5, 3.5],
        ticks: [0, 1, 2, 3],
        tickFormatter: (value) => ['0-6', '6-10', '10-15', '15-20'][value]
      };
    }
    return {
      type: 'number'
    };
  };

  // Responsive height calculation - fits in mobile viewport for screenshots
  const chartHeight = isMobile ?
    Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.55 : 400, 450) :
    400;

  const filterConfig = [
    {
      key: 'xAxis',
      label: 'X-Axis',
      options: Object.entries(xAxisMetrics).map(([key, { label }]) => ({ value: key, label }))
    },
    {
      key: 'yAxis',
      label: 'Y-Axis',
      options: Object.entries(yAxisMetrics).map(([key, { label }]) => ({ value: key, label }))
    }
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'xAxis') setXMetric(value);
    else if (key === 'yAxis') setYMetric(value);
  };

  return (
    <Card isMobile={isMobile}>
      <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, mb: 2 }}>
        Balls Faced vs Runs
      </Typography>

      <Box sx={{ mb: isMobile ? 2 : 3 }}>
        <FilterBar
          filters={filterConfig}
          activeFilters={{ xAxis: xMetric, yAxis: yMetric }}
          onFilterChange={handleFilterChange}
          isMobile={isMobile}
        />
      </Box>

      <Box sx={{ height: chartHeight, width: '100%' }}>
        <ResponsiveContainer>
          <ScatterChart margin={{
            top: 10,
            right: isMobile ? 5 : 20,
            bottom: isMobile ? 30 : 45,
            left: isMobile ? 10 : 50
          }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              {...getAxisProps(xMetric)}
              dataKey={xAxisMetrics[xMetric].key}
              name={xAxisMetrics[xMetric].label}
              label={isMobile ? undefined : { value: xAxisMetrics[xMetric].label, position: 'bottom', offset: 0 }}
              tick={{ fontSize: isMobile ? 9 : 12 }}
            />
            <YAxis
              type="number"
              dataKey={yAxisMetrics[yMetric].key}
              name={yAxisMetrics[yMetric].label}
              label={isMobile ? undefined : {
                value: yAxisMetrics[yMetric].label,
                angle: -90,
                position: 'insideLeft',
                offset: 10
              }}
              tick={{ fontSize: isMobile ? 9 : 12 }}
            />
            {yMetric === 'strike_rate' && <ReferenceLine y={100} stroke="#666" strokeDasharray="3 3" />}
            {yMetric === 'sr_diff' && <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />}
            <Tooltip content={<CustomTooltip />} />
            <Scatter
              name="Innings"
              data={data}
              fill={designColors.primary[500]}
              opacity={0.6}
              r={isMobile ? 5 : 6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </Box>
    </Card>
  );
};

export default InningsScatter;