import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const RareShotSpecialistsCard = ({ data }) => {
  if (!data.best_per_shot || Object.keys(data.best_per_shot).length === 0) {
    return <Typography sx={{ color: '#fff' }}>No rare shot data available</Typography>;
  }

  const handlePlayerClick = (playerName) => {
    const url = `/search?q=${encodeURIComponent(playerName)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Shot emoji map
  const shotEmoji = {
    'REVERSE_SCOOP': '🔄',
    'REVERSE_PULL': '↩️',
    'LATE_CUT': '✂️',
    'PADDLE_SWEEP': '🏓',
    'RAMP': '📐',
    'HOOK': '🪝',
    'UPPER_CUT': '⬆️'
  };

  return (
    <Box className="table-card-content">
      {/* Header */}
      <Typography variant="caption" sx={{ 
        color: 'rgba(255,255,255,0.6)', 
        display: 'block', 
        mb: 1.5,
        textAlign: 'center'
      }}>
        Top Strike Rate for Each Rare Shot (min 5 balls)
      </Typography>
      
      {/* Best Per Shot Grid */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: 1
      }}>
        {data.rare_shots?.map(shot => {
          const player = data.best_per_shot[shot];
          if (!player) return null;
          
          return (
            <Box 
              key={shot}
              onClick={(e) => { e.stopPropagation(); handlePlayerClick(player.name); }}
              sx={{ 
                p: 1.25,
                bgcolor: 'rgba(255,255,255,0.05)',
                borderRadius: 1.5,
                cursor: 'pointer',
                border: '1px solid rgba(255,255,255,0.08)',
                '&:hover': { 
                  bgcolor: 'rgba(29, 185, 84, 0.15)',
                  borderColor: 'rgba(29, 185, 84, 0.3)'
                },
                transition: 'all 0.2s ease'
              }}
            >
              {/* Shot header */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75 }}>
                <Typography sx={{ fontSize: '1.1rem' }}>
                  {shotEmoji[shot]}
                </Typography>
                <Typography variant="body2" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
                  {data.shot_labels?.[shot]}
                </Typography>
              </Box>
              
              {/* Player info */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500 }}>
                  {player.name}
                </Typography>
                <TeamBadge team={player.team} size="small" />
              </Box>
              
              {/* Stats */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ color: '#fff', fontWeight: 'bold' }}>
                  SR: {player.strike_rate}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                  {player.runs} runs / {player.balls}b
                </Typography>
              </Box>
              
              {/* Boundaries */}
              {player.boundaries > 0 && (
                <Typography variant="caption" sx={{ color: '#FF6B6B', mt: 0.25, display: 'block' }}>
                  {player.boundaries} boundaries
                </Typography>
              )}
            </Box>
          );
        })}
      </Box>

      {/* Footer note */}
      <Box sx={{ 
        mt: 2, 
        pt: 1.5, 
        borderTop: '1px solid rgba(255,255,255,0.08)',
        textAlign: 'center'
      }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>
          Rare shots: reverse scoops, ramps, hooks, upper cuts & more
        </Typography>
      </Box>
    </Box>
  );
};

export default RareShotSpecialistsCard;
