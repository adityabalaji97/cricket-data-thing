import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { getTeamAbbr } from '../../../utils/teamAbbreviations';

const PaceVsSpinCard = ({ data }) => {
  if ((!data.pace_crushers || data.pace_crushers.length === 0) && 
      (!data.spin_crushers || data.spin_crushers.length === 0)) {
    return <Typography>No pace vs spin data available</Typography>;
  }

  // Combine and prepare data for diverging bar chart
  const chartData = [
    ...(data.pace_crushers || []).map(p => ({
      name: p.name,
      displayName: `${p.name} (${getTeamAbbr(p.team)})`,
      team: p.team,
      value: p.sr_delta,
      category: 'Pace Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    })),
    ...(data.spin_crushers || []).map(p => ({
      name: p.name,
      displayName: `${p.name} (${getTeamAbbr(p.team)})`,
      team: p.team,
      value: p.sr_delta,
      category: 'Spin Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    }))
  ].sort((a, b) => b.value - a.value);

  const handlePlayerClick = (playerName) => {
    const url = `/player?name=${encodeURIComponent(playerName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">
            {player.name}
            {player.team && (
              <span style={{ 
                marginLeft: 6, 
                fontSize: 11, 
                color: '#888',
                backgroundColor: 'rgba(255,255,255,0.1)',
                padding: '2px 5px',
                borderRadius: 3
              }}>
                {getTeamAbbr(player.team)}
              </span>
            )}
          </Typography>
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
      {/* Section Labels - FIXED: Spin on left (negative), Pace on right (positive) */}
      <Box className="section-labels">
        <Typography variant="caption" sx={{ color: '#f44336', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <span>🌀</span> Spin Crushers
        </Typography>
        <Typography variant="caption" sx={{ color: '#4CAF50', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          Pace Crushers <span>🔥</span>
        </Typography>
      </Box>

      {/* Diverging Bar Chart - Maximized width */}
      <Box className="diverging-chart" sx={{ mx: -1 }}>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart 
            data={chartData} 
            layout="vertical"
            margin={{ top: 5, right: 15, left: 5, bottom: 5 }}
          >
            <XAxis 
              type="number" 
              domain={[-50, 50]}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              tickFormatter={(val) => val > 0 ? `+${val}` : val}
            />
            <YAxis 
              type="category" 
              dataKey="displayName" 
              width={95}
              tick={{ fontSize: 9, fill: '#b3b3b3' }}
              tickLine={false}
              axisLine={false}
            />
            <ReferenceLine x={0} stroke="#666" strokeWidth={1} />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="value" 
              cursor="pointer"
              radius={[2, 2, 2, 2]}
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
      <Box className="chart-legend" sx={{ mt: 1 }}>
        <Typography variant="caption" sx={{ color: '#888' }}>
          SR vs Pace − SR vs Spin
        </Typography>
      </Box>
    </Box>
  );
};

export default PaceVsSpinCard;
