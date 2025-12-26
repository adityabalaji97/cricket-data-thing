import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import TeamBadge from '../TeamBadge';

const NineteenthOverGodsCard = ({ data }) => {
  if (!data.bowlers || data.bowlers.length === 0) {
    return <Typography>No death bowling data available</Typography>;
  }

  const handleBowlerClick = (bowler) => {
    const url = `/search?q=${encodeURIComponent(bowler.name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Calculate averages for reference lines
  const avgDot = data.bowlers.reduce((sum, b) => sum + (b.dot_percentage || 0), 0) / data.bowlers.length;
  const avgBoundary = data.bowlers.reduce((sum, b) => sum + (b.boundary_percentage || 0), 0) / data.bowlers.length;

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const bowler = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">
            {bowler.name} {bowler.team && <TeamBadge team={bowler.team} />}
          </Typography>
          <Typography variant="body2">Wickets: {bowler.wickets}</Typography>
          <Typography variant="body2">Economy: {bowler.economy}</Typography>
          <Typography variant="body2">Dot%: {bowler.dot_percentage}%</Typography>
          <Typography variant="body2">Boundary%: {bowler.boundary_percentage}%</Typography>
          <Typography variant="body2">Overs: {bowler.overs}</Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="scatter-card-content">
      {/* Top 3 highlight */}
      <Box className="top-players-list">
        {data.bowlers.slice(0, 3).map((bowler, index) => (
          <Box 
            key={bowler.name} 
            className="top-player-item"
            onClick={(e) => {
              e.stopPropagation();
              handleBowlerClick(bowler);
            }}
          >
            <Typography variant="h5" className="rank">#{index + 1}</Typography>
            <Box className="player-info">
              <Typography variant="subtitle1" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                {bowler.name}
                <TeamBadge team={bowler.team} />
              </Typography>
              <Typography variant="body2">
                Econ: {bowler.economy} | {bowler.dot_percentage}% dots | {bowler.wickets} wkts
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Scatter Plot - High dot% and low boundary% is better */}
      <Box className="scatter-chart">
        <ResponsiveContainer width="100%" height={180}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="dot_percentage" 
              name="Dot %" 
              domain={['dataMin - 3', 'dataMax + 3']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Dot % (→ better)', position: 'bottom', fontSize: 10, fill: '#b3b3b3' }}
            />
            <YAxis 
              type="number" 
              dataKey="boundary_percentage" 
              name="Boundary %" 
              domain={['dataMin - 3', 'dataMax + 3']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Boundary % (↓ better)', angle: -90, position: 'left', fontSize: 10, fill: '#b3b3b3' }}
              reversed={true}
            />
            <ReferenceLine y={avgBoundary} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgDot} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.bowlers} 
              fill="#FF6B6B"
              cursor="pointer"
            >
              {data.bowlers.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={index < 3 ? '#FF6B6B' : '#666'}
                  opacity={index < 3 ? 1 : 0.6}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};

export default NineteenthOverGodsCard;
