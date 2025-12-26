import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import TeamBadge from '../TeamBadge';

const MiddleOversSqueezeCard = ({ data }) => {
  if (!data.bowlers || data.bowlers.length === 0) {
    return <Typography>No middle overs bowling data available</Typography>;
  }

  const handleBowlerClick = (bowler) => {
    const url = `/search?q=${encodeURIComponent(bowler.name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Calculate averages for reference lines
  const avgDot = data.bowlers.reduce((sum, b) => sum + (b.dot_percentage || 0), 0) / data.bowlers.length;
  const avgEcon = data.bowlers.reduce((sum, b) => sum + (b.economy || 0), 0) / data.bowlers.length;

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

      {/* Scatter Plot - High dot% and low economy is better */}
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
              dataKey="economy" 
              name="Economy" 
              domain={['dataMin - 0.5', 'dataMax + 0.5']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Econ (↓ better)', angle: -90, position: 'left', fontSize: 10, fill: '#b3b3b3' }}
              reversed={true}
            />
            <ReferenceLine y={avgEcon} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgDot} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.bowlers} 
              fill="#9C27B0"
              cursor="pointer"
            >
              {data.bowlers.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={index < 3 ? '#9C27B0' : '#666'}
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

export default MiddleOversSqueezeCard;
