import React from 'react';
import { Box, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const DeathHittersCard = ({ data }) => {
  const navigate = useNavigate();

  if (!data.players || data.players.length === 0) {
    return <Typography>No death overs data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    navigate(`/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`);
  };

  // Top 5 for display
  const topPlayers = data.players.slice(0, 5);

  return (
    <Box className="table-card-content">
      {/* Podium-style top 3 */}
      <Box className="podium">
        {/* Second place */}
        {topPlayers[1] && (
          <Box 
            className="podium-item second" 
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(topPlayers[1]);
            }}
          >
            <Typography variant="h6" className="podium-rank">2</Typography>
            <Typography variant="body2" className="podium-name">{topPlayers[1]?.name}</Typography>
            <Typography variant="h5" className="podium-stat">{topPlayers[1]?.strike_rate}</Typography>
            <Typography variant="caption">SR</Typography>
          </Box>
        )}
        
        {/* First place */}
        {topPlayers[0] && (
          <Box 
            className="podium-item first" 
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(topPlayers[0]);
            }}
          >
            <Typography variant="h5" className="podium-rank">👑</Typography>
            <Typography variant="subtitle1" className="podium-name">{topPlayers[0]?.name}</Typography>
            <Typography variant="h4" className="podium-stat">{topPlayers[0]?.strike_rate}</Typography>
            <Typography variant="caption">SR</Typography>
          </Box>
        )}
        
        {/* Third place */}
        {topPlayers[2] && (
          <Box 
            className="podium-item third" 
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(topPlayers[2]);
            }}
          >
            <Typography variant="h6" className="podium-rank">3</Typography>
            <Typography variant="body2" className="podium-name">{topPlayers[2]?.name}</Typography>
            <Typography variant="h5" className="podium-stat">{topPlayers[2]?.strike_rate}</Typography>
            <Typography variant="caption">SR</Typography>
          </Box>
        )}
      </Box>

      {/* Remaining players in compact list */}
      <Box className="remaining-list">
        {topPlayers.slice(3).map((player, index) => (
          <Box 
            key={player.name} 
            className="list-item"
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(player);
            }}
          >
            <Typography variant="body2" className="list-rank">#{index + 4}</Typography>
            <Typography variant="body2" className="list-name">{player.name}</Typography>
            <Typography variant="body2" className="list-stat">SR: {player.strike_rate}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default DeathHittersCard;
