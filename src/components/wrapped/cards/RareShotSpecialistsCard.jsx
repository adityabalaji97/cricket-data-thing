import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const RareShotSpecialistsCard = ({ data }) => {
  if (!data.players || data.players.length === 0) {
    return <Typography sx={{ color: '#fff' }}>No rare shot data available</Typography>;
  }

  const handlePlayerClick = (playerName) => {
    const url = `/player?name=${encodeURIComponent(playerName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
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
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(topPlayers[1].name); }}
          >
            <Typography variant="h6" className="podium-rank" sx={{ color: '#1DB954' }}>2</Typography>
            <Typography variant="body2" className="podium-name" sx={{ color: '#fff' }}>{topPlayers[1].name}</Typography>
            <TeamBadge team={topPlayers[1].team} />
            <Typography variant="h5" className="podium-stat" sx={{ color: '#fff' }}>{topPlayers[1].total_rare_runs}</Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>runs</Typography>
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
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(topPlayers[0].name); }}
          >
            <Typography variant="h5" className="podium-rank" sx={{ color: '#fff' }}>👑</Typography>
            <Typography variant="subtitle1" className="podium-name" sx={{ color: '#fff' }}>{topPlayers[0].name}</Typography>
            <TeamBadge team={topPlayers[0].team} />
            <Typography variant="h4" className="podium-stat" sx={{ color: '#fff' }}>{topPlayers[0].total_rare_runs}</Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>runs from {topPlayers[0].total_rare_balls} balls</Typography>
            <Box sx={{ mt: 0.5 }}>
              <Typography variant="caption" sx={{ color: '#fff', fontWeight: 'bold' }}>
                {shotEmoji[topPlayers[0].best_shot]} {data.shot_labels?.[topPlayers[0].best_shot]} @ {topPlayers[0].best_shot_sr} SR
              </Typography>
            </Box>
          </Box>
        )}
        
        {/* Third */}
        {topPlayers[2] && (
          <Box 
            className="podium-item third"
            onClick={(e) => { e.stopPropagation(); handlePlayerClick(topPlayers[2].name); }}
          >
            <Typography variant="h6" className="podium-rank" sx={{ color: '#1DB954' }}>3</Typography>
            <Typography variant="body2" className="podium-name" sx={{ color: '#fff' }}>{topPlayers[2].name}</Typography>
            <TeamBadge team={topPlayers[2].team} />
            <Typography variant="h5" className="podium-stat" sx={{ color: '#fff' }}>{topPlayers[2].total_rare_runs}</Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>runs</Typography>
            <Box sx={{ mt: 0.5 }}>
              <Typography variant="caption" sx={{ color: '#1DB954' }}>
                {shotEmoji[topPlayers[2].best_shot]} {data.shot_labels?.[topPlayers[2].best_shot]}
              </Typography>
            </Box>
          </Box>
        )}
      </Box>

      {/* Best Per Shot Section */}
      {data.best_per_shot && Object.keys(data.best_per_shot).length > 0 && (
        <Box sx={{ 
          mt: 2, 
          pt: 1.5, 
          borderTop: '1px solid rgba(255,255,255,0.1)'
        }}>
          <Typography variant="caption" sx={{ 
            color: 'rgba(255,255,255,0.6)', 
            display: 'block', 
            mb: 1,
            textAlign: 'center'
          }}>
            Best by Strike Rate (min 5 balls)
          </Typography>
          
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: 0.75
          }}>
            {data.rare_shots?.map(shot => {
              const player = data.best_per_shot[shot];
              if (!player) return null;
              
              return (
                <Box 
                  key={shot}
                  onClick={(e) => { e.stopPropagation(); handlePlayerClick(player.name); }}
                  sx={{ 
                    p: 0.75,
                    bgcolor: 'rgba(255,255,255,0.05)',
                    borderRadius: 1,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' },
                    transition: 'background-color 0.2s ease'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.25 }}>
                    <Typography sx={{ fontSize: '0.85rem' }}>
                      {shotEmoji[shot]}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
                      {data.shot_labels?.[shot]}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.7rem' }}>
                      {player.name}
                    </Typography>
                    <TeamBadge team={player.team} size="small" />
                  </Box>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.65rem' }}>
                    SR: <span style={{ color: '#fff', fontWeight: 'bold' }}>{player.strike_rate}</span>
                    {' '}({player.balls}b)
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Box>
      )}

      {/* Remaining players #4-5 */}
      {topPlayers.length > 3 && (
        <Box className="remaining-list" sx={{ mt: 1.5 }}>
          {topPlayers.slice(3).map((player, idx) => (
            <Box 
              key={player.name}
              className="list-item"
              onClick={(e) => { e.stopPropagation(); handlePlayerClick(player.name); }}
              sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="body2" className="list-rank" sx={{ color: 'rgba(255,255,255,0.5)' }}>#{idx + 4}</Typography>
                <Typography variant="body2" sx={{ color: '#fff' }}>{player.name}</Typography>
                <TeamBadge team={player.team} />
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#fff' }}>{player.total_rare_runs} runs</Typography>
                <Typography variant="caption" sx={{ color: '#1DB954' }}>
                  {shotEmoji[player.best_shot]} {data.shot_labels?.[player.best_shot]}
                </Typography>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default RareShotSpecialistsCard;
