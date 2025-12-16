import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { useNavigate } from 'react-router-dom';

const PaceVsSpinCard = ({ data }) => {
  const navigate = useNavigate();

  if ((!data.pace_crushers || data.pace_crushers.length === 0) && 
      (!data.spin_crushers || data.spin_crushers.length === 0)) {
    return <Typography>No pace vs spin data available</Typography>;
  }

  // Combine and prepare data for diverging bar chart
  const chartData = [
    ...(data.pace_crushers || []).map(p => ({
      name: p.name,
      value: p.sr_delta,
      category: 'Pace Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    })),
    ...(data.spin_crushers || []).map(p => ({
      name: p.name,
      value: p.sr_delta,
      category: 'Spin Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    }))
  ].sort((a, b) => b.value - a.value);

  const handlePlayerClick = (playerName) => {
    navigate(`/player?name=${encodeURIComponent(playerName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">{player.name}</Typography>
          <Typography variant="body2">vs Pace: {player.sr_vs_pace}</Typography>
          <Typography variant="body2">vs Spin: {player.sr_vs_spin}</Typography>
          <Typography variant="body2" sx={{ color: player.value > 0 ? '#4CAF50' : '#f44336' }}>
            Delta: {player.value > 0 ? '+' : ''}{player.value}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="diverging-card-content">
      {/* Section Labels */}
      <Box className="section-labels">
        <Typography variant="caption" className="label-left" sx={{ color: '#4CAF50' }}>
          🔥 Pace Crushers
        </Typography>
        <Typography variant="caption" className="label-right" sx={{ color: '#f44336' }}>
          🌀 Spin Crushers
        </Typography>
      </Box>

      {/* Diverging Bar Chart */}
      <Box className="diverging-chart">
        <ResponsiveContainer width="100%" height={250}>
          <BarChart 
            data={chartData} 
            layout="vertical"
            margin={{ top: 10, right: 30, left: 60, bottom: 10 }}
          >
            <XAxis 
              type="number" 
              domain={[-50, 50]}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              tickFormatter={(val) => val > 0 ? `+${val}` : val}
            />
            <YAxis 
              type="category" 
              dataKey="name" 
              width={55}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
            />
            <ReferenceLine x={0} stroke="#fff" />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="value" 
              cursor="pointer"
              onClick={(data) => {
                handlePlayerClick(data.name);
              }}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={entry.value > 0 ? '#4CAF50' : '#f44336'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Legend */}
      <Box className="chart-legend">
        <Typography variant="caption">
          Positive = Better vs Pace | Negative = Better vs Spin
        </Typography>
      </Box>
    </Box>
  );
};

export default PaceVsSpinCard;
