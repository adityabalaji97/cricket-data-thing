import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const LengthMastersCard = ({ data }) => {
  const [selectedPlayer, setSelectedPlayer] = useState(0);

  if (!data.players || data.players.length === 0) {
    return <Typography>No length masters data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const topPlayers = data.players.slice(0, 5);
  const currentPlayer = topPlayers[selectedPlayer];

  // Color based on SR
  const getSRColor = (sr) => {
    if (sr >= 150) return '#1DB954';
    if (sr >= 120) return '#4CAF50';
    if (sr >= 100) return '#8BC34A';
    if (sr >= 80) return '#FFC107';
    if (sr > 0) return '#FF5722';
    return 'rgba(255,255,255,0.1)';
  };

  return (
    <Box className="table-card-content">
      {/* Hero - Selected Player */}
      {currentPlayer && (
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <Box 
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(currentPlayer);
            }}
            sx={{ cursor: 'pointer' }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="h6">{currentPlayer.name}</Typography>
              <TeamBadge team={currentPlayer.team} />
            </Box>
            
            <Typography variant="h3" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
              {currentPlayer.length_master_score}
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
              Length Master Score
            </Typography>
          </Box>

          {/* Length Heatmap */}
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 0.5 }}>
            {currentPlayer.length_breakdown?.map((len) => (
              <Box
                key={len.length}
                sx={{
                  width: 50,
                  textAlign: 'center',
                  p: 0.5,
                  borderRadius: 1,
                  bgcolor: getSRColor(len.strike_rate),
                  color: len.strike_rate >= 100 ? '#000' : '#fff'
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 'bold', fontSize: '0.85rem' }}>
                  {len.strike_rate > 0 ? len.strike_rate.toFixed(0) : '-'}
                </Typography>
                <Typography variant="caption" sx={{ fontSize: '0.55rem', display: 'block', lineHeight: 1.1 }}>
                  {data.length_labels?.[len.length] || len.length}
                </Typography>
                <Typography variant="caption" sx={{ fontSize: '0.5rem', opacity: 0.7 }}>
                  {len.balls}b
                </Typography>
              </Box>
            ))}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 1.5 }}>
            <Typography variant="caption">
              Overall SR: <strong>{currentPlayer.overall_sr}</strong>
            </Typography>
            <Typography variant="caption">
              {currentPlayer.total_balls} balls
            </Typography>
          </Box>
        </Box>
      )}

      {/* Player selector tabs */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5, mb: 2 }}>
        {topPlayers.map((player, index) => (
          <Box
            key={player.name}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedPlayer(index);
            }}
            sx={{
              px: 1.5,
              py: 0.5,
              borderRadius: 2,
              bgcolor: selectedPlayer === index ? '#1DB954' : 'rgba(255,255,255,0.1)',
              color: selectedPlayer === index ? '#000' : '#fff',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: selectedPlayer === index ? 'bold' : 'normal'
            }}
          >
            #{index + 1}
          </Box>
        ))}
      </Box>

      {/* Legend */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: 1, 
        flexWrap: 'wrap',
        pt: 1,
        borderTop: '1px solid rgba(255,255,255,0.1)'
      }}>
        {[
          { color: '#1DB954', label: '150+' },
          { color: '#4CAF50', label: '120-150' },
          { color: '#8BC34A', label: '100-120' },
          { color: '#FFC107', label: '80-100' },
          { color: '#FF5722', label: '<80' }
        ].map(({ color, label }) => (
          <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.3 }}>
            <Box sx={{ width: 10, height: 10, bgcolor: color, borderRadius: 0.5 }} />
            <Typography variant="caption" sx={{ fontSize: '0.6rem' }}>{label}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default LengthMastersCard;
