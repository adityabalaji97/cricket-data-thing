import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const RareShotSpecialistsCard = ({ data }) => {
  if (!data.players || data.players.length === 0) {
    return <Typography>No rare shot data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const topPlayers = data.players.slice(0, 5);

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
      {/* Top 3 Podium */}
      <Box className="podium" sx={{ mb: 2 }}>
        {/* Second */}
        {topPlayers[1] && (
          <Box 
            className="podium-item second"
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(topPlayers[1]); }}
          >
            <Typography variant="h6" className="podium-rank">2</Typography>
            <Typography variant="body2" className="podium-name">{topPlayers[1].name}</Typography>
            <TeamBadge team={topPlayers[1].team} />
            <Typography variant="h5" className="podium-stat">{topPlayers[1].total_rare_runs}</Typography>
            <Typography variant="caption">runs</Typography>
            <Box sx={{ mt: 0.5 }}>
              <Typography variant="caption" sx={{ color: '#1DB954' }}>
                {shotEmoji[topPlayers[1].best_shot]} {data.shot_labels?.[topPlayers[1].best_shot]}
              </Typography>
            </Box>
          </Box>
        )}
        
        {/* First */}
        {topPlayers[0] && (
          <Box 
            className="podium-item first"
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(topPlayers[0]); }}
          >
            <Typography variant="h5" className="podium-rank">👑</Typography>
            <Typography variant="subtitle1" className="podium-name">{topPlayers[0].name}</Typography>
            <TeamBadge team={topPlayers[0].team} />
            <Typography variant="h4" className="podium-stat">{topPlayers[0].total_rare_runs}</Typography>
            <Typography variant="caption">runs from {topPlayers[0].total_rare_balls} balls</Typography>
            <Box sx={{ mt: 0.5 }}>
              <Typography variant="caption" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
                {shotEmoji[topPlayers[0].best_shot]} {data.shot_labels?.[topPlayers[0].best_shot]} @ {topPlayers[0].best_shot_sr} SR
              </Typography>
            </Box>
          </Box>
        )}
        
        {/* Third */}
        {topPlayers[2] && (
          <Box 
            className="podium-item third"
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(topPlayers[2]); }}
          >
            <Typography variant="h6" className="podium-rank">3</Typography>
            <Typography variant="body2" className="podium-name">{topPlayers[2].name}</Typography>
            <TeamBadge team={topPlayers[2].team} />
            <Typography variant="h5" className="podium-stat">{topPlayers[2].total_rare_runs}</Typography>
            <Typography variant="caption">runs</Typography>
            <Box sx={{ mt: 0.5 }}>
              <Typography variant="caption" sx={{ color: '#1DB954' }}>
                {shotEmoji[topPlayers[2].best_shot]} {data.shot_labels?.[topPlayers[2].best_shot]}
              </Typography>
            </Box>
          </Box>
        )}
      </Box>

      {/* Remaining */}
      <Box className="remaining-list">
        {topPlayers.slice(3).map((player, idx) => (
          <Box 
            key={player.name}
            className="list-item"
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(player); }}
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="body2" className="list-rank">#{idx + 4}</Typography>
              <Typography variant="body2">{player.name}</Typography>
              <TeamBadge team={player.team} />
            </Box>
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{player.total_rare_runs} runs</Typography>
              <Typography variant="caption" sx={{ color: '#1DB954' }}>
                {shotEmoji[player.best_shot]} {data.shot_labels?.[player.best_shot]}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Shot Legend */}
      <Box sx={{ 
        mt: 2, 
        pt: 1, 
        borderTop: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        gap: 1
      }}>
        {data.rare_shots?.map(shot => (
          <Typography key={shot} variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.6rem' }}>
            {shotEmoji[shot]} {data.shot_labels?.[shot]}
          </Typography>
        ))}
      </Box>
    </Box>
  );
};

export default RareShotSpecialistsCard;
