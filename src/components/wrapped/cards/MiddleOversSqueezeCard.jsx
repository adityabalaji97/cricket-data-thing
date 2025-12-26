import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const MiddleOversSqueezeCard = ({ data }) => {
  if (!data.bowlers || data.bowlers.length === 0) {
    return <Typography>No middle overs bowling data available</Typography>;
  }

  const handleBowlerClick = (bowler) => {
    const url = `/search?q=${encodeURIComponent(bowler.name)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const topBowlers = data.bowlers.slice(0, 5);

  return (
    <Box className="table-card-content">
      {/* Podium-style top 3 - by squeeze score (economy + dot%) */}
      <Box className="podium">
        {/* Second place */}
        {topBowlers[1] && (
          <Box 
            className="podium-item second" 
            onClick={(e) => {
              e.stopPropagation();
              handleBowlerClick(topBowlers[1]);
            }}
          >
            <Typography variant="h6" className="podium-rank">2</Typography>
            <Typography variant="body2" className="podium-name">{topBowlers[1]?.name}</Typography>
            <TeamBadge team={topBowlers[1]?.team} />
            <Typography variant="h5" className="podium-stat">{topBowlers[1]?.economy}</Typography>
            <Typography variant="caption">Econ</Typography>
            <Typography variant="caption" sx={{ color: 'var(--wrapped-primary)', fontSize: '10px', mt: 0.5 }}>
              {topBowlers[1]?.dot_percentage}% dots
            </Typography>
          </Box>
        )}
        
        {/* First place */}
        {topBowlers[0] && (
          <Box 
            className="podium-item first" 
            onClick={(e) => {
              e.stopPropagation();
              handleBowlerClick(topBowlers[0]);
            }}
          >
            <Typography variant="h5" className="podium-rank">🔒</Typography>
            <Typography variant="subtitle1" className="podium-name">{topBowlers[0]?.name}</Typography>
            <TeamBadge team={topBowlers[0]?.team} size="medium" />
            <Typography variant="h4" className="podium-stat">{topBowlers[0]?.economy}</Typography>
            <Typography variant="caption">Econ</Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)', fontSize: '11px', mt: 0.5 }}>
              {topBowlers[0]?.dot_percentage}% dots
            </Typography>
          </Box>
        )}
        
        {/* Third place */}
        {topBowlers[2] && (
          <Box 
            className="podium-item third" 
            onClick={(e) => {
              e.stopPropagation();
              handleBowlerClick(topBowlers[2]);
            }}
          >
            <Typography variant="h6" className="podium-rank">3</Typography>
            <Typography variant="body2" className="podium-name">{topBowlers[2]?.name}</Typography>
            <TeamBadge team={topBowlers[2]?.team} />
            <Typography variant="h5" className="podium-stat">{topBowlers[2]?.economy}</Typography>
            <Typography variant="caption">Econ</Typography>
            <Typography variant="caption" sx={{ color: 'var(--wrapped-primary)', fontSize: '10px', mt: 0.5 }}>
              {topBowlers[2]?.dot_percentage}% dots
            </Typography>
          </Box>
        )}
      </Box>

      {/* Remaining bowlers in compact list */}
      <Box className="remaining-list">
        {topBowlers.slice(3).map((bowler, index) => (
          <Box 
            key={bowler.name} 
            className="list-item"
            onClick={(e) => {
              e.stopPropagation();
              handleBowlerClick(bowler);
            }}
          >
            <Typography variant="body2" className="list-rank">#{index + 4}</Typography>
            <Typography variant="body2" className="list-name" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {bowler.name}
              <TeamBadge team={bowler.team} />
            </Typography>
            <Typography variant="body2" className="list-stat">
              {bowler.economy} econ | {bowler.dot_percentage}% dots
            </Typography>
          </Box>
        ))}
      </Box>

      {/* Summary stats */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: 3, 
        mt: 2,
        pt: 2,
        borderTop: '1px solid var(--wrapped-border)'
      }}>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" sx={{ color: 'var(--wrapped-secondary)' }}>
            Avg Economy
          </Typography>
          <Typography variant="body2" sx={{ color: 'var(--wrapped-text)', fontWeight: 600 }}>
            {(topBowlers.reduce((sum, b) => sum + b.economy, 0) / topBowlers.length).toFixed(2)}
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" sx={{ color: 'var(--wrapped-secondary)' }}>
            Avg Dot %
          </Typography>
          <Typography variant="body2" sx={{ color: 'var(--wrapped-text)', fontWeight: 600 }}>
            {(topBowlers.reduce((sum, b) => sum + b.dot_percentage, 0) / topBowlers.length).toFixed(1)}%
          </Typography>
        </Box>
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="caption" sx={{ color: 'var(--wrapped-secondary)' }}>
            Total Wkts
          </Typography>
          <Typography variant="body2" sx={{ color: 'var(--wrapped-text)', fontWeight: 600 }}>
            {topBowlers.reduce((sum, b) => sum + b.wickets, 0)}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default MiddleOversSqueezeCard;
