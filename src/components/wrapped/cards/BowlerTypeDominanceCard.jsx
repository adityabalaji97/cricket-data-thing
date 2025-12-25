import React from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

const BowlerTypeDominanceCard = ({ data }) => {
  if (!data.kind_stats || Object.keys(data.kind_stats).length === 0) {
    return <Typography sx={{ color: '#fff' }}>No bowler type data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const pace = data.kind_stats['pace'];
  const spin = data.kind_stats['spin'];

  // Format large numbers
  const formatBalls = (num) => {
    if (num >= 1000) return (num / 1000).toFixed(0) + 'k';
    return num;
  };

  // Calculate total balls for percentage bar widths
  const totalBalls = (pace?.balls || 0) + (spin?.balls || 0);
  const pacePct = totalBalls > 0 ? ((pace?.balls || 0) * 100 / totalBalls) : 50;

  return (
    <Box className="table-card-content">
      {/* Pace vs Spin Split Bar */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ 
          display: 'flex', 
          height: 40, 
          borderRadius: 2,
          overflow: 'hidden',
          mb: 1
        }}>
          {/* Pace */}
          <Box sx={{ 
            width: `${pacePct}%`,
            bgcolor: '#FF6B6B',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'width 0.5s ease'
          }}>
            <Typography variant="body2" sx={{ color: '#fff', fontWeight: 'bold' }}>
              ⚡ PACE {pacePct.toFixed(0)}%
            </Typography>
          </Box>
          {/* Spin */}
          <Box sx={{ 
            width: `${100 - pacePct}%`,
            bgcolor: '#4ECDC4',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'width 0.5s ease'
          }}>
            <Typography variant="body2" sx={{ color: '#fff', fontWeight: 'bold' }}>
              🌀 SPIN {(100 - pacePct).toFixed(0)}%
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Stats Comparison */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        gap: 2, 
        mb: 3 
      }}>
        {/* Pace Stats */}
        <Box sx={{ 
          flex: 1, 
          textAlign: 'center',
          p: 1.5,
          bgcolor: 'rgba(255, 107, 107, 0.1)',
          borderRadius: 2,
          border: '1px solid rgba(255, 107, 107, 0.3)'
        }}>
          <Typography variant="subtitle2" sx={{ color: '#FF6B6B', fontWeight: 'bold', mb: 1 }}>
            ⚡ Pace
          </Typography>
          {pace && (
            <>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#fff' }}>
                    {pace.economy}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                    Econ
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#fff' }}>
                    {pace.strike_rate}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                    SR
                  </Typography>
                </Box>
              </Box>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mt: 1 }}>
                {formatBalls(pace.balls)} balls • {pace.wickets} wkts
              </Typography>
            </>
          )}
        </Box>

        {/* Spin Stats */}
        <Box sx={{ 
          flex: 1, 
          textAlign: 'center',
          p: 1.5,
          bgcolor: 'rgba(78, 205, 196, 0.1)',
          borderRadius: 2,
          border: '1px solid rgba(78, 205, 196, 0.3)'
        }}>
          <Typography variant="subtitle2" sx={{ color: '#4ECDC4', fontWeight: 'bold', mb: 1 }}>
            🌀 Spin
          </Typography>
          {spin && (
            <>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#fff' }}>
                    {spin.economy}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                    Econ
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#fff' }}>
                    {spin.strike_rate}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                    SR
                  </Typography>
                </Box>
              </Box>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mt: 1 }}>
                {formatBalls(spin.balls)} balls • {spin.wickets} wkts
              </Typography>
            </>
          )}
        </Box>
      </Box>

      {/* Top Performers */}
      <Box sx={{ display: 'flex', gap: 2 }}>
        {/* Top Pace */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: '#FF6B6B', display: 'block', mb: 0.5, fontWeight: 'bold' }}>
            TOP PACERS
          </Typography>
          {data.top_pace?.slice(0, 3).map((player, idx) => (
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
                  maxWidth: 70, 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: '#fff'
                }}>
                  {player.name}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#FF6B6B' }}>
                {player.wickets}w
              </Typography>
            </Box>
          ))}
        </Box>

        {/* Top Spin */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: '#4ECDC4', display: 'block', mb: 0.5, fontWeight: 'bold' }}>
            TOP SPINNERS
          </Typography>
          {data.top_spin?.slice(0, 3).map((player, idx) => (
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
                  maxWidth: 70, 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: '#fff'
                }}>
                  {player.name}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#4ECDC4' }}>
                {player.wickets}w
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Style Breakdown (compact) */}
      {data.style_stats && data.style_stats.length > 0 && (
        <Box sx={{ mt: 2, pt: 1, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mb: 0.5 }}>
            TOP STYLES BY ECONOMY
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', justifyContent: 'center' }}>
            {data.style_stats
              .slice(0, 6)
              .sort((a, b) => a.economy - b.economy)
              .map(style => (
                <Box 
                  key={style.style}
                  sx={{ 
                    px: 1, 
                    py: 0.3, 
                    borderRadius: 1,
                    bgcolor: style.kind === 'pace' ? 'rgba(255, 107, 107, 0.2)' : 'rgba(78, 205, 196, 0.2)',
                    border: `1px solid ${style.kind === 'pace' ? 'rgba(255, 107, 107, 0.4)' : 'rgba(78, 205, 196, 0.4)'}`
                  }}
                >
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: 'bold' }}>
                    {style.style}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', ml: 0.5 }}>
                    {style.economy}
                  </Typography>
                </Box>
              ))}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default BowlerTypeDominanceCard;
