import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const ControlledAggressionCard = ({ data }) => {
  if (!data.players || data.players.length === 0) {
    return <Typography>No controlled aggression data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Top 5 for display
  const topPlayers = data.players.slice(0, 5);

  // Helper to render metric bar
  const MetricBar = ({ label, value, maxValue, color }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
      <Typography variant="caption" sx={{ width: 55, color: 'rgba(255,255,255,0.7)' }}>
        {label}
      </Typography>
      <Box sx={{ flex: 1, height: 6, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 1 }}>
        <Box sx={{ 
          width: `${Math.min(100, (value / maxValue) * 100)}%`, 
          height: '100%', 
          bgcolor: color,
          borderRadius: 1,
          transition: 'width 0.5s ease'
        }} />
      </Box>
      <Typography variant="caption" sx={{ width: 40, textAlign: 'right' }}>
        {value.toFixed(1)}
      </Typography>
    </Box>
  );

  return (
    <Box className="table-card-content">
      {/* Hero - Top Player */}
      {topPlayers[0] && (
        <Box 
          className="hero-player"
          onClick={(e) => {
            e.stopPropagation();
            handlePlayerClick(topPlayers[0]);
          }}
          sx={{ mb: 2, p: 2, bgcolor: 'rgba(255,255,255,0.05)', borderRadius: 2 }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6">👑</Typography>
              <Typography variant="h6">{topPlayers[0].name}</Typography>
              <TeamBadge team={topPlayers[0].team} />
            </Box>
            <Typography variant="h4" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
              {topPlayers[0].ca_score}
            </Typography>
          </Box>
          
          <MetricBar label="Control" value={topPlayers[0].control_pct} maxValue={100} color="#4CAF50" />
          <MetricBar label="SR" value={topPlayers[0].strike_rate} maxValue={200} color="#2196F3" />
          <MetricBar label="Boundary" value={topPlayers[0].boundary_pct} maxValue={30} color="#FF9800" />
          <MetricBar label="Anti-Dot" value={50 - topPlayers[0].dot_pct} maxValue={35} color="#9C27B0" />
        </Box>
      )}

      {/* Remaining players */}
      <Box className="remaining-list">
        {topPlayers.slice(1).map((player, index) => (
          <Box 
            key={player.name} 
            className="list-item"
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(player);
            }}
            sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              p: 1,
              borderRadius: 1,
              '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', width: 20 }}>
                #{index + 2}
              </Typography>
              <Typography variant="body2">{player.name}</Typography>
              <TeamBadge team={player.team} />
            </Box>
            <Typography variant="body1" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
              {player.ca_score}
            </Typography>
          </Box>
        ))}
      </Box>

      {/* Legend */}
      <Box sx={{ mt: 2, pt: 1, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          CA Score = Control (25%) + SR (35%) + Boundary% (25%) + Anti-Dot (15%)
        </Typography>
      </Box>
    </Box>
  );
};

export default ControlledAggressionCard;
