import React, { useState } from 'react';
import { Typography, Box, useMediaQuery, useTheme } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { colors as designColors } from '../theme/designSystem';

const metrics = [
  { value: 'strike_rate', label: 'Strike Rate' },
  { value: 'average', label: 'Average' },
  { value: 'boundary_percentage', label: 'Boundary %' },
  { value: 'dot_percentage', label: 'Dot Ball %' }
];

const transformData = (stats, selectedMetric) => {
  const phases = ['All Overs', 'powerplay', 'middle', 'death'];
  return phases.map(phase => {
    if (phase === 'All Overs') {
      return {
        phase,
        pace: stats.phase_stats.pace.overall[selectedMetric],
        spin: stats.phase_stats.spin.overall[selectedMetric],
        overall: stats.overall[selectedMetric]
      };
    }
    return {
      phase: phase.charAt(0).toUpperCase() + phase.slice(1),
      pace: stats.phase_stats.pace[phase][selectedMetric],
      spin: stats.phase_stats.spin[phase][selectedMetric],
      overall: stats.phase_stats.overall[phase][selectedMetric]
    };
  });
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Box sx={{ bgcolor: 'background.paper', p: 1, border: '1px solid #ccc', borderRadius: 1 }}>
        <Typography variant="subtitle2">{label}</Typography>
        {payload.map((entry) => (
          entry.value !== null && (
            <Typography key={entry.name} variant="body2" sx={{ color: entry.color }}>
              {entry.name}: {entry.value.toFixed(2)}
            </Typography>
          )
        ))}
      </Box>
    );
  }
  return null;
};

const PaceSpinBreakdown = ({ stats, isMobile: isMobileProp }) => {
  const [selectedMetric, setSelectedMetric] = useState('strike_rate');
  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;

  // Null safety check
  if (!stats?.phase_stats?.pace?.overall || !stats?.phase_stats?.spin?.overall) {
    return (
      <Card isMobile={isMobile}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, mb: 2 }}>
          Pace vs Spin Analysis
        </Typography>
        <Typography color="text.secondary">
          Pace/Spin breakdown data not available
        </Typography>
      </Card>
    );
  }

  const data = transformData(stats, selectedMetric);

  const maxValue = Math.max(
    ...data.flatMap(d => [d.pace, d.spin, d.overall].filter(v => v !== null))
  );

  const filterConfig = [
    {
      key: 'metric',
      label: 'Metric',
      options: metrics.map(m => ({ value: m.value, label: m.label }))
    }
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'metric') setSelectedMetric(value);
  };

  const chartHeight = isMobile ? 350 : 400;

  return (
    <Card isMobile={isMobile}>
      <Box sx={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        justifyContent: 'space-between',
        alignItems: isMobile ? 'flex-start' : 'center',
        mb: 2,
        gap: isMobile ? 1.5 : 0
      }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600 }}>
          Pace vs Spin Analysis
        </Typography>
        <FilterBar
          filters={filterConfig}
          activeFilters={{ metric: selectedMetric }}
          onFilterChange={handleFilterChange}
          isMobile={isMobile}
        />
      </Box>

      <Box sx={{ width: '100%', height: chartHeight, mt: 2 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 20, right: isMobile ? 10 : 30, left: isMobile ? 40 : 50, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              domain={[0, maxValue * 1.1]}
              tickFormatter={(value) => Number(value.toFixed(2))}
              tick={{ fontSize: isMobile ? 10 : 12 }}
            />
            <YAxis type="category" dataKey="phase" axisLine={false} tick={{ fontSize: isMobile ? 10 : 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }} />
            <Bar dataKey="pace" name="vs Pace" fill={designColors.primary[500]} barSize={20} />
            <Bar dataKey="spin" name="vs Spin" fill={designColors.chart[2]} barSize={20} />
            <Bar dataKey="overall" name="Overall" fill={designColors.chart[5]} barSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 2, fontSize: isMobile ? '0.7rem' : undefined }}>
        {selectedMetric === 'strike_rate'
          ? 'Higher values indicate faster scoring'
          : selectedMetric === 'average'
          ? 'Higher values indicate better consistency'
          : selectedMetric === 'boundary_percentage'
          ? 'Higher values indicate more boundaries'
          : 'Higher values indicate more dot balls'}
      </Typography>
    </Card>
  );
};

export default PaceSpinBreakdown;