import React from 'react';
import { Box, Typography } from '@mui/material';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';

const ChaseMastersCard = ({ data }) => {
  if (!data || data.error) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography sx={{ color: '#fff' }}>No data available</Typography>
      </Box>
    );
  }

  const { clutch_performers = [], pressure_folders = [], coverage_pct = 0, data_note = '' } = data;

  const handlePlayerClick = (player) => {
    const url = `/search?q=${encodeURIComponent(player.name)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <Box sx={{ p: 2 }}>
      {/* Coverage Note */}
      {coverage_pct > 0 && (
        <Box sx={{ 
          bgcolor: 'rgba(255,255,255,0.05)', 
          borderRadius: 1, 
          p: 1.5, 
          mb: 2,
          textAlign: 'center'
        }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
            📈 {data_note}
          </Typography>
        </Box>
      )}

      {/* Clutch Performers */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <EmojiEventsIcon sx={{ color: '#FFE66D', fontSize: 18 }} />
          <Typography variant="subtitle2" sx={{ color: '#FFE66D', textTransform: 'uppercase', letterSpacing: 1 }}>
            Clutch Performers
          </Typography>
        </Box>

        {clutch_performers.slice(0, 5).map((player, idx) => (
          <Box 
            key={idx}
            onClick={() => handlePlayerClick(player)}
            sx={{ 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              py: 1.5,
              px: 1.5,
              mb: 1,
              bgcolor: idx === 0 ? 'rgba(255,230,109,0.15)' : 'rgba(255,255,255,0.03)',
              borderRadius: 1,
              border: idx === 0 ? '1px solid rgba(255,230,109,0.3)' : '1px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.2s',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.08)' }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography sx={{ 
                color: idx === 0 ? '#FFE66D' : 'rgba(255,255,255,0.5)',
                fontWeight: idx === 0 ? 700 : 400,
                fontSize: idx === 0 ? '1.1rem' : '0.9rem',
                width: 20
              }}>
                {idx + 1}
              </Typography>
              <Box>
                <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500 }}>
                  {player.name}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                  {player.team} • {player.balls} balls
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="body1" sx={{ 
                color: '#4ECDC4', 
                fontWeight: 700,
                fontSize: idx === 0 ? '1.1rem' : '1rem'
              }}>
                +{player.wp_change_pct?.toFixed(1)}%
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                WP added
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>

      {/* Pressure Folders (if any) */}
      {pressure_folders.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ 
            color: 'rgba(255,255,255,0.5)', 
            mb: 1.5, 
            textTransform: 'uppercase', 
            letterSpacing: 1,
            fontSize: '0.7rem'
          }}>
            Struggled Under Pressure
          </Typography>

          {pressure_folders.slice(0, 3).map((player, idx) => (
            <Box 
              key={idx}
              onClick={() => handlePlayerClick(player)}
              sx={{ 
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                py: 1,
                borderBottom: idx < 2 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                cursor: 'pointer',
                '&:hover': { opacity: 0.7 }
              }}
            >
              <Box>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                  {player.name}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>
                  {player.balls} balls • SR {player.strike_rate}
                </Typography>
              </Box>
              
              <Typography variant="body2" sx={{ color: '#FF6B6B', fontWeight: 600 }}>
                {player.wp_change_pct?.toFixed(1)}%
              </Typography>
            </Box>
          ))}
        </Box>
      )}

      {/* Legend */}
      <Box sx={{ 
        mt: 2, 
        pt: 2, 
        borderTop: '1px solid rgba(255,255,255,0.1)',
        textAlign: 'center'
      }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          Win probability change while batting in 2nd innings chases
        </Typography>
      </Box>
    </Box>
  );
};

export default ChaseMastersCard;
