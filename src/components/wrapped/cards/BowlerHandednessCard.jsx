import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const BowlerHandednessCard = ({ data }) => {
  const hasLHB = data.lhb_specialists && data.lhb_specialists.length > 0;
  const hasRHB = data.rhb_specialists && data.rhb_specialists.length > 0;
  
  if (!hasLHB && !hasRHB) {
    return <Typography>No handedness specialist data available</Typography>;
  }

  const handleBowlerClick = (name) => {
    const url = `/search?q=${encodeURIComponent(name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Find max delta for scaling bars
  const allDeltas = [
    ...(data.lhb_specialists || []).map(p => Math.abs(p.econ_delta)),
    ...(data.rhb_specialists || []).map(p => Math.abs(p.econ_delta))
  ];
  const maxDelta = Math.max(...allDeltas, 1);

  const renderBowlerRow = (bowler, isLHBSpecialist) => {
    const barWidth = Math.min(100, (Math.abs(bowler.econ_delta) / maxDelta) * 100);
    const betterEcon = isLHBSpecialist ? bowler.econ_vs_lhb : bowler.econ_vs_rhb;
    const worseEcon = isLHBSpecialist ? bowler.econ_vs_rhb : bowler.econ_vs_lhb;
    
    return (
      <Box 
        key={bowler.name}
        onClick={(e) => { e.stopPropagation(); handleBowlerClick(bowler.name); }}
        sx={{ 
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          py: 0.75,
          px: 1,
          cursor: 'pointer',
          borderRadius: 1,
          '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' },
          transition: 'background-color 0.2s'
        }}
      >
        {/* Name & Team */}
        <Box sx={{ minWidth: 100, flex: '0 0 auto' }}>
          <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500, fontSize: '0.8rem' }}>
            {bowler.name}
          </Typography>
          <TeamBadge team={bowler.team} size="small" />
        </Box>
        
        {/* Bar visualization */}
        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ 
            height: 8, 
            width: `${barWidth}%`,
            bgcolor: isLHBSpecialist ? '#4ECDC4' : '#FF6B6B',
            borderRadius: 1,
            transition: 'width 0.3s ease'
          }} />
          <Typography variant="caption" sx={{ 
            color: isLHBSpecialist ? '#4ECDC4' : '#FF6B6B',
            fontWeight: 'bold',
            minWidth: 40
          }}>
            {Math.abs(bowler.econ_delta).toFixed(1)}
          </Typography>
        </Box>
        
        {/* Stats */}
        <Box sx={{ textAlign: 'right', minWidth: 70 }}>
          <Typography variant="caption" sx={{ color: '#1DB954', display: 'block' }}>
            {betterEcon} econ
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
            vs {worseEcon}
          </Typography>
        </Box>
      </Box>
    );
  };

  return (
    <Box className="table-card-content">
      {/* LHB Specialists Section */}
      {hasLHB && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1, 
            mb: 1,
            pb: 0.5,
            borderBottom: '1px solid rgba(255,255,255,0.1)'
          }}>
            <Typography sx={{ fontSize: '1.2rem' }}>🎯</Typography>
            <Typography variant="subtitle2" sx={{ color: '#4ECDC4', fontWeight: 'bold' }}>
              LHB Specialists
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', ml: 'auto' }}>
              Better economy vs lefties
            </Typography>
          </Box>
          
          {data.lhb_specialists.map(bowler => renderBowlerRow(bowler, true))}
        </Box>
      )}

      {/* RHB Specialists Section */}
      {hasRHB && (
        <Box>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1, 
            mb: 1,
            pb: 0.5,
            borderBottom: '1px solid rgba(255,255,255,0.1)'
          }}>
            <Typography sx={{ fontSize: '1.2rem' }}>🎯</Typography>
            <Typography variant="subtitle2" sx={{ color: '#FF6B6B', fontWeight: 'bold' }}>
              RHB Specialists
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', ml: 'auto' }}>
              Better economy vs righties
            </Typography>
          </Box>
          
          {data.rhb_specialists.map(bowler => renderBowlerRow(bowler, false))}
        </Box>
      )}

      {/* Footer note */}
      <Box sx={{ 
        mt: 2, 
        pt: 1, 
        borderTop: '1px solid rgba(255,255,255,0.08)',
        textAlign: 'center'
      }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>
          Bar length = economy difference between hands
        </Typography>
      </Box>
    </Box>
  );
};

export default BowlerHandednessCard;
