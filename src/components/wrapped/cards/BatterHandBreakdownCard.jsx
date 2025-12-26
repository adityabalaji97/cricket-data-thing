import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const BatterHandBreakdownCard = ({ data }) => {
  if (!data.hand_stats || Object.keys(data.hand_stats).length === 0) {
    return <Typography sx={{ color: '#fff' }}>No batter hand data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/search?q=${encodeURIComponent(player.name)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const lhb = data.hand_stats['LHB'];
  const rhb = data.hand_stats['RHB'];

  // Format large numbers
  const formatBalls = (num) => {
    if (num >= 1000) return (num / 1000).toFixed(0) + 'k';
    return num;
  };

  return (
    <Box className="table-card-content">
      {/* LHB vs RHB Comparison */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        gap: 2, 
        mb: 3 
      }}>
        {/* LHB */}
        <Box sx={{ 
          flex: 1, 
          textAlign: 'center',
          p: 1.5,
          bgcolor: 'rgba(33, 150, 243, 0.1)',
          borderRadius: 2,
          border: '1px solid rgba(33, 150, 243, 0.3)'
        }}>
          <Typography variant="h5" sx={{ mb: 0.5 }}>🫲</Typography>
          <Typography variant="subtitle2" sx={{ color: '#2196F3', fontWeight: 'bold' }}>
            Left-Hand
          </Typography>
          {lhb && (
            <>
              <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: '#fff' }}>
                {lhb.strike_rate}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.7)' }}>
                SR ({formatBalls(lhb.balls)} balls)
              </Typography>
              <Box sx={{ mt: 1, fontSize: '0.7rem', color: 'rgba(255,255,255,0.6)' }}>
                <span>Avg: {lhb.average}</span>
                {' • '}
                <span>Bdy: {lhb.boundary_pct}%</span>
              </Box>
            </>
          )}
        </Box>

        {/* RHB */}
        <Box sx={{ 
          flex: 1, 
          textAlign: 'center',
          p: 1.5,
          bgcolor: 'rgba(255, 152, 0, 0.1)',
          borderRadius: 2,
          border: '1px solid rgba(255, 152, 0, 0.3)'
        }}>
          <Typography variant="h5" sx={{ mb: 0.5 }}>🫱</Typography>
          <Typography variant="subtitle2" sx={{ color: '#FF9800', fontWeight: 'bold' }}>
            Right-Hand
          </Typography>
          {rhb && (
            <>
              <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: '#fff' }}>
                {rhb.strike_rate}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.7)' }}>
                SR ({formatBalls(rhb.balls)} balls)
              </Typography>
              <Box sx={{ mt: 1, fontSize: '0.7rem', color: 'rgba(255,255,255,0.6)' }}>
                <span>Avg: {rhb.average}</span>
                {' • '}
                <span>Bdy: {rhb.boundary_pct}%</span>
              </Box>
            </>
          )}
        </Box>
      </Box>

      {/* Crease Combo Stats */}
      {data.crease_combo_stats && data.crease_combo_stats.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mb: 1 }}>
            CREASE COMBINATIONS
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
            {data.crease_combo_stats.map(combo => (
              <Box 
                key={combo.combo}
                sx={{ 
                  textAlign: 'center', 
                  p: 1,
                  bgcolor: 'rgba(255,255,255,0.05)',
                  borderRadius: 1,
                  flex: 1,
                  maxWidth: 90
                }}
              >
                <Typography variant="caption" sx={{ 
                  display: 'block', 
                  color: combo.combo === 'Mixed' ? '#9C27B0' : 
                         combo.combo === 'LHB_LHB' ? '#2196F3' : '#FF9800',
                  fontWeight: 'bold'
                }}>
                  {combo.combo === 'Mixed' ? '🫲🫱' : 
                   combo.combo === 'LHB_LHB' ? '🫲🫲' : '🫱🫱'}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#fff' }}>
                  {combo.strike_rate}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.6rem' }}>
                  {formatBalls(combo.balls)}b
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {/* Top Performers */}
      <Box sx={{ display: 'flex', gap: 2 }}>
        {/* Top LHB */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: '#2196F3', display: 'block', mb: 0.5 }}>
            TOP LHB
          </Typography>
          {data.top_lhb?.slice(0, 3).map((player, idx) => (
            <Box 
              key={player.name}
              onClick={(e) => {
                e.stopPropagation();
                handlePlayerClick(player);
              }}
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                py: 0.5,
                cursor: 'pointer',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', width: 14 }}>
                  {idx + 1}
                </Typography>
                <Typography variant="caption" sx={{ 
                  maxWidth: 80, 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: '#fff'
                }}>
                  {player.name}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#fff' }}>
                {player.strike_rate}
              </Typography>
            </Box>
          ))}
        </Box>

        {/* Top RHB */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: '#FF9800', display: 'block', mb: 0.5 }}>
            TOP RHB
          </Typography>
          {data.top_rhb?.slice(0, 3).map((player, idx) => (
            <Box 
              key={player.name}
              onClick={(e) => {
                e.stopPropagation();
                handlePlayerClick(player);
              }}
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                py: 0.5,
                cursor: 'pointer',
                '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', width: 14 }}>
                  {idx + 1}
                </Typography>
                <Typography variant="caption" sx={{ 
                  maxWidth: 80, 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: '#fff'
                }}>
                  {player.name}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#fff' }}>
                {player.strike_rate}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default BatterHandBreakdownCard;
