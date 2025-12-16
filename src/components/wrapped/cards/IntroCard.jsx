import React from 'react';
import { Box, Typography } from '@mui/material';

const PHASE_COLORS = {
  powerplay: '#4CAF50',
  middle: '#2196F3', 
  death: '#f44336'
};

const IntroCard = ({ data }) => {
  if (!data.phases || data.phases.length === 0) {
    return <Typography>No phase data available</Typography>;
  }

  const { total_matches, phases, toss_stats } = data;
  const batFirstPct = toss_stats?.bat_first_pct || 50;
  const chasePct = (100 - batFirstPct).toFixed(1);

  return (
    <Box className="intro-card-content">
      {/* Hero Number */}
      <Box className="intro-stat-hero">
        <Typography variant="h2" className="hero-number">
          {total_matches}
        </Typography>
        <Typography variant="subtitle1" className="hero-label">
          T20 matches analyzed
        </Typography>
      </Box>

      {/* Toss/Win Stats - Compact Bar */}
      {toss_stats && (
        <Box sx={{ width: '100%', maxWidth: 300, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#4CAF50', fontWeight: 500 }}>
              Bat First Wins
            </Typography>
            <Typography variant="caption" sx={{ color: '#2196F3', fontWeight: 500 }}>
              Chase Wins
            </Typography>
          </Box>
          <Box sx={{ 
            height: 12, 
            bgcolor: '#333', 
            borderRadius: 2, 
            overflow: 'hidden', 
            display: 'flex' 
          }}>
            <Box 
              sx={{ 
                width: `${batFirstPct}%`, 
                bgcolor: '#4CAF50',
                transition: 'width 0.5s ease'
              }} 
            />
            <Box 
              sx={{ 
                width: `${chasePct}%`, 
                bgcolor: '#2196F3',
                transition: 'width 0.5s ease'
              }} 
            />
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#4CAF50', fontWeight: 600 }}>
              {batFirstPct}%
            </Typography>
            <Typography variant="caption" sx={{ color: '#2196F3', fontWeight: 600 }}>
              {chasePct}%
            </Typography>
          </Box>
        </Box>
      )}

      {/* Phase Run Rates - Compact horizontal display */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: 4,
        mt: 2
      }}>
        {phases.map((phase) => (
          <Box key={phase.phase} sx={{ textAlign: 'center' }}>
            <Typography 
              variant="h4" 
              sx={{ 
                color: PHASE_COLORS[phase.phase],
                fontWeight: 700,
                lineHeight: 1
              }}
            >
              {phase.run_rate}
            </Typography>
            <Typography 
              variant="caption" 
              sx={{ 
                color: '#b3b3b3',
                textTransform: 'uppercase',
                fontSize: '0.65rem',
                letterSpacing: 1
              }}
            >
              {phase.phase === 'powerplay' ? 'PP' : 
               phase.phase === 'middle' ? 'MID' : 'DEATH'} RR
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default IntroCard;
