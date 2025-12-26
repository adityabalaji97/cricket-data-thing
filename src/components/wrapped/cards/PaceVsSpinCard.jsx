import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { getTeamAbbr } from '../../../utils/teamAbbreviations';
import TeamBadge from '../TeamBadge';

const PaceVsSpinCard = ({ data }) => {
  if ((!data.pace_crushers || data.pace_crushers.length === 0) && 
      (!data.spin_crushers || data.spin_crushers.length === 0)) {
    return <Typography>No pace vs spin data available</Typography>;
  }

  // Combine and prepare data for diverging bar chart
  const chartData = [
    ...(data.pace_crushers || []).map(p => ({
      name: p.name,
      displayName: `${p.name} (${getTeamAbbr(p.team)})`,
      team: p.team,
      value: p.sr_delta,
      category: 'Pace Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    })),
    ...(data.spin_crushers || []).map(p => ({
      name: p.name,
      displayName: `${p.name} (${getTeamAbbr(p.team)})`,
      team: p.team,
      value: p.sr_delta,
      category: 'Spin Crusher',
      sr_vs_pace: p.sr_vs_pace,
      sr_vs_spin: p.sr_vs_spin
    }))
  ].sort((a, b) => b.value - a.value);

  const handlePlayerClick = (playerName) => {
    const url = `/search?q=${encodeURIComponent(playerName)}&start_date=2025-01-01`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const player = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">
            {player.name}
            {player.team && (
              <span style={{ 
                marginLeft: 6, 
                fontSize: 11, 
                color: '#888',
                backgroundColor: 'rgba(255,255,255,0.1)',
                padding: '2px 5px',
                borderRadius: 3
              }}>
                {getTeamAbbr(player.team)}
              </span>
            )}
          </Typography>
          <Typography variant="body2">vs Pace: {player.sr_vs_pace}</Typography>
          <Typography variant="body2">vs Spin: {player.sr_vs_spin}</Typography>
          <Typography variant="body2" sx={{ color: player.value > 0 ? '#4CAF50' : '#f44336' }}>
            Delta: {player.value > 0 ? '+' : ''}{player.value}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="diverging-card-content">
      {/* Section Labels - FIXED: Spin on left (negative), Pace on right (positive) */}
      <Box className="section-labels">
        <Typography variant="caption" sx={{ color: '#f44336', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <span>🌀</span> Spin Crushers
        </Typography>
        <Typography variant="caption" sx={{ color: '#4CAF50', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          Pace Crushers <span>🔥</span>
        </Typography>
      </Box>

      {/* Diverging Bar Chart - Maximized width */}
      <Box className="diverging-chart" sx={{ mx: -1 }}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart 
            data={chartData} 
            layout="vertical"
            margin={{ top: 5, right: 15, left: 5, bottom: 5 }}
          >
            <XAxis 
              type="number" 
              domain={[-50, 50]}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              tickFormatter={(val) => val > 0 ? `+${val}` : val}
            />
            <YAxis 
              type="category" 
              dataKey="displayName" 
              width={95}
              tick={{ fontSize: 9, fill: '#b3b3b3' }}
              tickLine={false}
              axisLine={false}
            />
            <ReferenceLine x={0} stroke="#666" strokeWidth={1} />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="value" 
              cursor="pointer"
              radius={[2, 2, 2, 2]}
              onClick={(data) => {
                handlePlayerClick(data.name);
              }}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={entry.value > 0 ? '#4CAF50' : '#f44336'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Complete Batters Section */}
      {data.complete_batters && data.complete_batters.length > 0 && (
        <Box sx={{ 
          mt: 1.5, 
          pt: 1.5, 
          borderTop: '1px solid rgba(255,255,255,0.1)'
        }}>
          <Typography variant="caption" sx={{ 
            color: '#1DB954', 
            display: 'flex', 
            alignItems: 'center',
            justifyContent: 'center',
            gap: 0.5,
            mb: 1
          }}>
            ⚡ Complete Batters
          </Typography>
          <Typography variant="caption" sx={{ 
            color: 'rgba(255,255,255,0.5)', 
            display: 'block',
            textAlign: 'center',
            fontSize: '0.6rem',
            mb: 1
          }}>
            SR&gt;120 + Dot%&lt;35 + Boundary%&gt;10 vs BOTH
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {data.complete_batters.slice(0, 3).map((player, idx) => (
              <Box 
                key={player.name}
                onClick={(e) => { e.stopPropagation(); handlePlayerClick(player.name); }}
                sx={{ 
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  p: 0.75,
                  bgcolor: idx === 0 ? 'rgba(29, 185, 84, 0.15)' : 'rgba(255,255,255,0.05)',
                  borderRadius: 1,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' },
                  transition: 'background-color 0.2s ease'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <Typography variant="caption" sx={{ 
                    color: idx === 0 ? '#1DB954' : 'rgba(255,255,255,0.5)',
                    fontWeight: idx === 0 ? 'bold' : 'normal',
                    width: 16
                  }}>
                    {idx === 0 ? '👑' : `#${idx + 1}`}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#fff', fontWeight: idx === 0 ? 'bold' : 'normal' }}>
                    {player.name}
                  </Typography>
                  <TeamBadge team={player.team} size="small" />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#4CAF50', fontWeight: 'bold', fontSize: '0.7rem' }}>
                      {player.sr_vs_pace}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.55rem', display: 'block' }}>
                      pace
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#f44336', fontWeight: 'bold', fontSize: '0.7rem' }}>
                      {player.sr_vs_spin}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.55rem', display: 'block' }}>
                      spin
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ color: '#1DB954', fontWeight: 'bold', fontSize: '0.7rem' }}>
                      {player.combined_sr}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.55rem', display: 'block' }}>
                      avg
                    </Typography>
                  </Box>
                </Box>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {/* Legend */}
      <Box className="chart-legend" sx={{ mt: 1 }}>
        <Typography variant="caption" sx={{ color: '#888' }}>
          SR vs Pace − SR vs Spin
        </Typography>
      </Box>
    </Box>
  );
};

export default PaceVsSpinCard;
