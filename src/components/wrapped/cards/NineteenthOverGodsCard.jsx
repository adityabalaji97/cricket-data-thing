import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const NineteenthOverGodsCard = ({ data }) => {
  if (!data.bowlers || data.bowlers.length === 0) {
    return <Typography>No death bowling data available</Typography>;
  }

  const handleBowlerClick = (bowler) => {
    const url = `/bowler?name=${encodeURIComponent(bowler.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const topBowlers = data.bowlers.slice(0, 5);

  return (
    <Box className="table-card-content">
      {/* Podium-style top 3 - by economy */}
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
            <Typography variant="caption">Economy</Typography>
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
            <Typography variant="h5" className="podium-rank">👑</Typography>
            <Typography variant="subtitle1" className="podium-name">{topBowlers[0]?.name}</Typography>
            <TeamBadge team={topBowlers[0]?.team} size="medium" />
            <Typography variant="h4" className="podium-stat">{topBowlers[0]?.economy}</Typography>
            <Typography variant="caption">Economy</Typography>
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
            <Typography variant="caption">Economy</Typography>
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
              Econ: {bowler.economy} | {bowler.wickets} wkts
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default NineteenthOverGodsCard;
