import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import TeamBadge from '../TeamBadge';

const MiddleMerchantsCard = ({ data }) => {
  if (!data.players || data.players.length === 0) {
    return <Typography>No middle overs data available</Typography>;
  }

  // Calculate averages for reference lines
  const avgSR = data.players.reduce((sum, p) => sum + p.strike_rate, 0) / data.players.length;
  const avgAvg = data.players.reduce((sum, p) => sum + (p.average || 0), 0) / data.players.length;

  const handlePlayerClick = (player) => {
    const url = `/search?q=${encodeURIComponent(player.name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">
            {player.name} {player.team && <TeamBadge team={player.team} />}
          </Typography>
          <Typography variant="body2">SR: {player.strike_rate}</Typography>
          <Typography variant="body2">Avg: {player.average}</Typography>
          <Typography variant="body2">Balls: {player.balls}</Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="scatter-card-content">
      {/* Top 3 highlight */}
      <Box className="top-players-list">
        {data.players.slice(0, 3).map((player, index) => (
          <Box 
            key={player.name} 
            className="top-player-item"
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(player);
            }}
          >
            <Typography variant="h5" className="rank">#{index + 1}</Typography>
            <Box className="player-info">
              <Typography variant="subtitle1" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                {player.name}
                <TeamBadge team={player.team} />
              </Typography>
              <Typography variant="body2">
                SR: {player.strike_rate} | Avg: {player.average}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Scatter Plot - Average vs Strike Rate */}
      <Box className="scatter-chart">
        <ResponsiveContainer width="100%" height={180}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="average" 
              name="Average" 
              domain={['dataMin - 5', 'dataMax + 5']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Average', position: 'bottom', fontSize: 10, fill: '#b3b3b3' }}
            />
            <YAxis 
              type="number" 
              dataKey="strike_rate" 
              name="SR" 
              domain={['dataMin - 10', 'dataMax + 10']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'SR', angle: -90, position: 'left', fontSize: 10, fill: '#b3b3b3' }}
            />
            <ReferenceLine y={avgSR} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgAvg} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.players} 
              fill="#2196F3"
              cursor="pointer"
            >
              {data.players.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={index < 3 ? '#2196F3' : '#666'}
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

export default MiddleMerchantsCard;
