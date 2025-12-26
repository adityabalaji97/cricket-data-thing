import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import TeamBadge from '../TeamBadge';

const PowerplayThievesCard = ({ data }) => {
  if (!data.bowlers || data.bowlers.length === 0) {
    return <Typography>No powerplay bowling data available</Typography>;
  }

  const handleBowlerClick = (bowler) => {
    const url = `/search?q=${encodeURIComponent(bowler.name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Calculate averages for reference lines
  const avgSR = data.bowlers.reduce((sum, b) => sum + (b.strike_rate || 0), 0) / data.bowlers.length;
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
          <Typography variant="body2">SR: {bowler.strike_rate}</Typography>
          <Typography variant="body2">Econ: {bowler.economy}</Typography>
          <Typography variant="body2">Boundary%: {bowler.boundary_percentage}%</Typography>
          <Typography variant="body2">Dot%: {bowler.dot_percentage}%</Typography>
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
                {bowler.wickets} wkts | SR: {bowler.strike_rate} | Econ: {bowler.economy}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Scatter Plot - Lower SR and lower boundary% is better */}
      <Box className="scatter-chart">
        <ResponsiveContainer width="100%" height={180}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="boundary_percentage" 
              name="Boundary %" 
              domain={['dataMin - 2', 'dataMax + 2']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Boundary %', position: 'bottom', fontSize: 10, fill: '#b3b3b3' }}
              reversed={true}
            />
            <YAxis 
              type="number" 
              dataKey="strike_rate" 
              name="SR" 
              domain={['dataMin - 2', 'dataMax + 2']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'SR (↓ better)', angle: -90, position: 'left', fontSize: 10, fill: '#b3b3b3' }}
              reversed={true}
            />
            <ReferenceLine y={avgSR} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgBoundary} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.bowlers} 
              fill="#4ECDC4"
              cursor="pointer"
            >
              {data.bowlers.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={index < 3 ? '#4ECDC4' : '#666'}
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

export default PowerplayThievesCard;
