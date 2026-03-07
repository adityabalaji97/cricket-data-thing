import React from 'react';
import { Box, Typography } from '@mui/material';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const DISMISSAL_COLORS = [
  '#003f5c', '#2f4b7c', '#665191', '#a05195',
  '#d45087', '#f95d6a', '#ff7c43', '#ffa600'
];

const DISMISSAL_LABELS = {
  'bowled': 'Bowled',
  'caught': 'Caught',
  'caught and bowled': 'Caught & Bowled',
  'lbw': 'LBW',
  'stumped': 'Stumped',
  'run out': 'Run Out',
  'hit wicket': 'Hit Wicket',
  'retired hurt': 'Retired Hurt',
  'retired out': 'Retired Out',
  'obstructing the field': 'Obstructing'
};

const DismissalDonutChart = ({ data, title, isMobile }) => {
  if (!data || data.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">No dismissal data available</Typography>
      </Box>
    );
  }

  const chartData = data.map(d => ({
    name: DISMISSAL_LABELS[d.type] || d.type,
    value: d.count,
    percentage: d.percentage
  }));

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={isMobile ? 10 : 12}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      const d = payload[0].payload;
      return (
        <Box sx={{ bgcolor: 'white', p: 1.5, border: '1px solid #ccc', borderRadius: 1 }}>
          <Typography variant="subtitle2">{d.name}</Typography>
          <Typography variant="body2">{d.value} ({d.percentage}%)</Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box sx={{ width: '100%' }}>
      {title && (
        <Typography variant="h6" gutterBottom align="center">
          {title}
        </Typography>
      )}
      <Box sx={{ width: '100%', height: isMobile ? 280 : 320 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={isMobile ? 40 : 60}
              outerRadius={isMobile ? 80 : 110}
              paddingAngle={2}
              dataKey="value"
              nameKey="name"
              labelLine={false}
              label={renderCustomizedLabel}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={DISMISSAL_COLORS[index % DISMISSAL_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 1, mt: 1 }}>
        {chartData.map((entry, index) => (
          <Box key={entry.name} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{
              width: 10, height: 10, borderRadius: '50%',
              bgcolor: DISMISSAL_COLORS[index % DISMISSAL_COLORS.length]
            }} />
            <Typography variant="caption">{entry.name}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default DismissalDonutChart;
