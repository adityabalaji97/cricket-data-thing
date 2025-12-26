import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import TeamBadge from '../TeamBadge';

const UncontrolledChaosCard = ({ data }) => {
  if (!data.players || data.players.length === 0) {
    return <Typography>No uncontrolled chaos data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/search?q=${encodeURIComponent(player.name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Reference lines at criteria thresholds
  const controlThreshold = data.criteria?.max_control_pct || 70;
  const srThreshold = data.criteria?.min_sr || 130;

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">
            {player.name} {player.team && <TeamBadge team={player.team} />}
          </Typography>
          <Typography variant="body2">SR: {player.strike_rate}</Typography>
          <Typography variant="body2">Control%: {player.control_pct}%</Typography>
          <Typography variant="body2">Boundary%: {player.boundary_pct}%</Typography>
          <Typography variant="body2">Sixes: {player.sixes} | Balls: {player.balls}</Typography>
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
                SR: {player.strike_rate} | Ctrl: {player.control_pct}% | {player.sixes} 6s
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Scatter Plot - Low control% but high SR */}
      <Box className="scatter-chart">
        <ResponsiveContainer width="100%" height={180}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="control_pct" 
              name="Control %" 
              domain={['dataMin - 5', controlThreshold + 5]}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Control % (← chaos)', position: 'bottom', fontSize: 10, fill: '#b3b3b3' }}
              reversed={true}
            />
            <YAxis 
              type="number" 
              dataKey="strike_rate" 
              name="SR" 
              domain={[srThreshold - 10, 'dataMax + 10']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'SR', angle: -90, position: 'left', fontSize: 10, fill: '#b3b3b3' }}
            />
            <ReferenceLine x={controlThreshold} stroke="#FF6B6B" strokeDasharray="3 3" />
            <ReferenceLine y={srThreshold} stroke="#1DB954" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.players} 
              fill="#FF9F1C"
              cursor="pointer"
            >
              {data.players.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={index < 3 ? '#FF9F1C' : '#666'}
                  opacity={index < 3 ? 1 : 0.6}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </Box>

      {/* Criteria note */}
      <Box sx={{ mt: 1, textAlign: 'center' }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          SR &gt; {srThreshold} | Control &lt; {controlThreshold}% | Boundary &gt; 15%
        </Typography>
      </Box>
    </Box>
  );
};

export default UncontrolledChaosCard;
