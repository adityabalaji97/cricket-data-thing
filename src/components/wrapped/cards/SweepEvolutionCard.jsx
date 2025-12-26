import React from 'react';
import { Box, Typography } from '@mui/material';

const SweepEvolutionCard = ({ data }) => {
  if (!data || data.error) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography sx={{ color: '#fff' }}>No data available</Typography>
      </Box>
    );
  }

  const { sweep_stats = [], top_sweepers = [], shot_labels = {} } = data;

  const handlePlayerClick = (player) => {
    const url = `/search?q=${encodeURIComponent(player.name)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Get total balls for percentage calculations
  const totalBalls = sweep_stats.reduce((sum, s) => sum + (s.total_balls || 0), 0);

  return (
    <Box sx={{ p: 2 }}>
      {/* Sweep Type Breakdown */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 1.5, textTransform: 'uppercase', letterSpacing: 1 }}>
          Sweep Type Usage
        </Typography>
        
        {sweep_stats.map((sweep, idx) => {
          const pct = totalBalls > 0 ? ((sweep.total_balls / totalBalls) * 100).toFixed(0) : 0;
          const vsSpinSR = sweep.vs_spin?.strike_rate || 0;
          const vsPaceSR = sweep.vs_pace?.strike_rate || 0;
          
          return (
            <Box key={idx} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2" sx={{ color: '#fff', fontWeight: 600 }}>
                  {shot_labels[sweep.shot] || sweep.shot}
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                  {sweep.total_balls?.toLocaleString()} balls ({pct}%)
                </Typography>
              </Box>
              
              {/* Usage bar */}
              <Box sx={{ 
                height: 8, 
                bgcolor: 'rgba(255,255,255,0.1)', 
                borderRadius: 1, 
                overflow: 'hidden',
                mb: 0.5 
              }}>
                <Box sx={{ 
                  height: '100%', 
                  width: `${pct}%`, 
                  bgcolor: idx === 0 ? '#4ECDC4' : idx === 1 ? '#45B7AA' : idx === 2 ? '#FF6B6B' : '#FFE66D',
                  transition: 'width 0.5s ease'
                }} />
              </Box>
              
              {/* vs Spin / vs Pace SR */}
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Typography variant="caption" sx={{ color: '#4ECDC4' }}>
                  vs Spin: {vsSpinSR} SR
                </Typography>
                <Typography variant="caption" sx={{ color: '#FF6B6B' }}>
                  vs Pace: {vsPaceSR} SR
                </Typography>
              </Box>
            </Box>
          );
        })}
      </Box>

      {/* Top Sweepers */}
      <Box>
        <Typography variant="subtitle2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 1.5, textTransform: 'uppercase', letterSpacing: 1 }}>
          Top Sweep Merchants
        </Typography>
        
        {top_sweepers.slice(0, 5).map((player, idx) => (
          <Box 
            key={idx}
            onClick={() => handlePlayerClick(player)}
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              py: 1,
              borderBottom: idx < 4 ? '1px solid rgba(255,255,255,0.1)' : 'none',
              cursor: 'pointer',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography sx={{ 
                color: 'rgba(255,255,255,0.5)', 
                fontSize: '0.75rem',
                width: 16 
              }}>
                {idx + 1}
              </Typography>
              <Box>
                <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500 }}>
                  {player.name}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                  {player.team}
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="body2" sx={{ color: '#4ECDC4', fontWeight: 600 }}>
                {player.total_runs} runs
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                SR {player.strike_rate} • {player.sweep_types_used} types
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default SweepEvolutionCard;
