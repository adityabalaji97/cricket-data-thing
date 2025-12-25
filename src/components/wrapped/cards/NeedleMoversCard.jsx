import React from 'react';
import { Box, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';

const NeedleMoversCard = ({ data }) => {
  if (!data || data.error) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography sx={{ color: '#fff' }}>No data available</Typography>
      </Box>
    );
  }

  const { positive_impact = [], negative_impact = [], coverage_pct = 0, data_note = '' } = data;

  const handlePlayerClick = (player) => {
    const url = `/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const maxImpact = Math.max(
    ...positive_impact.map(p => Math.abs(p.runs_above_expected || 0)),
    ...negative_impact.map(p => Math.abs(p.runs_above_expected || 0)),
    1
  );

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
            📊 {data_note}
          </Typography>
        </Box>
      )}

      {/* Positive Impact - Outperformers */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <TrendingUpIcon sx={{ color: '#4ECDC4', fontSize: 18 }} />
          <Typography variant="subtitle2" sx={{ color: '#4ECDC4', textTransform: 'uppercase', letterSpacing: 1 }}>
            Above Expected
          </Typography>
        </Box>

        {positive_impact.slice(0, 5).map((player, idx) => {
          const barWidth = (Math.abs(player.runs_above_expected) / maxImpact) * 100;
          
          return (
            <Box 
              key={idx}
              onClick={() => handlePlayerClick(player)}
              sx={{ 
                mb: 1.5,
                cursor: 'pointer',
                '&:hover': { opacity: 0.8 }
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Box>
                  <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500 }}>
                    {player.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                    {player.balls} balls • SR {player.strike_rate}
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: '#4ECDC4', fontWeight: 700 }}>
                  +{player.runs_above_expected?.toFixed(0)}
                </Typography>
              </Box>
              
              <Box sx={{ height: 6, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 1, overflow: 'hidden' }}>
                <Box sx={{ 
                  height: '100%', 
                  width: `${barWidth}%`, 
                  bgcolor: '#4ECDC4',
                  borderRadius: 1,
                  transition: 'width 0.5s ease'
                }} />
              </Box>
            </Box>
          );
        })}
      </Box>

      {/* Negative Impact - Underperformers */}
      {negative_impact.length > 0 && (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <TrendingDownIcon sx={{ color: '#FF6B6B', fontSize: 18 }} />
            <Typography variant="subtitle2" sx={{ color: '#FF6B6B', textTransform: 'uppercase', letterSpacing: 1 }}>
              Below Expected
            </Typography>
          </Box>

          {negative_impact.slice(0, 3).map((player, idx) => {
            const barWidth = (Math.abs(player.runs_above_expected) / maxImpact) * 100;
            
            return (
              <Box 
                key={idx}
                onClick={() => handlePlayerClick(player)}
                sx={{ 
                  mb: 1.5,
                  cursor: 'pointer',
                  '&:hover': { opacity: 0.8 }
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Box>
                    <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500 }}>
                      {player.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                      {player.balls} balls • SR {player.strike_rate}
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ color: '#FF6B6B', fontWeight: 700 }}>
                    {player.runs_above_expected?.toFixed(0)}
                  </Typography>
                </Box>
                
                <Box sx={{ height: 6, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 1, overflow: 'hidden' }}>
                  <Box sx={{ 
                    height: '100%', 
                    width: `${barWidth}%`, 
                    bgcolor: '#FF6B6B',
                    borderRadius: 1,
                    transition: 'width 0.5s ease'
                  }} />
                </Box>
              </Box>
            );
          })}
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
          Runs above/below predicted score (xRuns) based on match situation
        </Typography>
      </Box>
    </Box>
  );
};

export default NeedleMoversCard;
