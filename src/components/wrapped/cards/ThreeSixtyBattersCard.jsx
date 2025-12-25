import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import TeamBadge from '../TeamBadge';

// Simple wagon wheel SVG component
const WagonWheel = ({ zoneBreakdown, size = 120 }) => {
  const centerX = size / 2;
  const centerY = size / 2;
  const radius = size * 0.42;
  
  // Zone angles (8 zones, each 45 degrees, starting from fine leg)
  const zones = [
    { zone: 1, label: 'Fine Leg', startAngle: 180, endAngle: 225 },
    { zone: 2, label: 'Sq Leg', startAngle: 225, endAngle: 270 },
    { zone: 3, label: 'Midwicket', startAngle: 270, endAngle: 315 },
    { zone: 4, label: 'Long On', startAngle: 315, endAngle: 360 },
    { zone: 5, label: 'Long Off', startAngle: 0, endAngle: 45 },
    { zone: 6, label: 'Cover', startAngle: 45, endAngle: 90 },
    { zone: 7, label: 'Point', startAngle: 90, endAngle: 135 },
    { zone: 8, label: 'Third Man', startAngle: 135, endAngle: 180 },
  ];

  const getColor = (runPct) => {
    if (runPct >= 15) return '#1DB954';  // High
    if (runPct >= 10) return '#4CAF50';  // Good
    if (runPct >= 5) return '#8BC34A';   // Medium
    if (runPct > 0) return '#CDDC39';    // Low
    return 'rgba(255,255,255,0.1)';      // None
  };

  const polarToCartesian = (angle, r) => {
    const rad = (angle - 90) * Math.PI / 180;
    return {
      x: centerX + r * Math.cos(rad),
      y: centerY + r * Math.sin(rad)
    };
  };

  const createArcPath = (startAngle, endAngle, innerR, outerR) => {
    const start1 = polarToCartesian(startAngle, outerR);
    const end1 = polarToCartesian(endAngle, outerR);
    const start2 = polarToCartesian(endAngle, innerR);
    const end2 = polarToCartesian(startAngle, innerR);
    
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    
    return `M ${start1.x} ${start1.y} 
            A ${outerR} ${outerR} 0 ${largeArc} 1 ${end1.x} ${end1.y} 
            L ${start2.x} ${start2.y} 
            A ${innerR} ${innerR} 0 ${largeArc} 0 ${end2.x} ${end2.y} Z`;
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Field background */}
      <circle cx={centerX} cy={centerY} r={radius + 5} fill="rgba(0,100,0,0.2)" />
      
      {/* Zone segments */}
      {zones.map(({ zone, startAngle, endAngle }) => {
        const zoneData = zoneBreakdown?.find(z => z.zone === zone);
        const runPct = zoneData?.run_pct || 0;
        
        return (
          <path
            key={zone}
            d={createArcPath(startAngle, endAngle, 8, radius)}
            fill={getColor(runPct)}
            stroke="rgba(255,255,255,0.3)"
            strokeWidth="0.5"
          />
        );
      })}
      
      {/* Center pitch */}
      <rect 
        x={centerX - 4} 
        y={centerY - 10} 
        width={8} 
        height={20} 
        fill="rgba(200,180,150,0.6)"
        rx={1}
      />
    </svg>
  );
};

const ThreeSixtyBattersCard = ({ data }) => {
  const [selectedPlayer, setSelectedPlayer] = useState(0);

  if (!data.players || data.players.length === 0) {
    return <Typography sx={{ color: '#fff' }}>No 360° batters data available</Typography>;
  }

  const handlePlayerClick = (player) => {
    const url = `/player?name=${encodeURIComponent(player.name)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const topPlayers = data.players.slice(0, 5);
  const currentPlayer = topPlayers[selectedPlayer];

  return (
    <Box className="table-card-content">
      {/* Hero - Selected Player with Wagon Wheel */}
      {currentPlayer && (
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <Box 
            onClick={(e) => {
              e.stopPropagation();
              handlePlayerClick(currentPlayer);
            }}
            sx={{ cursor: 'pointer' }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="h6" sx={{ color: '#fff' }}>{currentPlayer.name}</Typography>
              <TeamBadge team={currentPlayer.team} />
            </Box>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
              <WagonWheel zoneBreakdown={currentPlayer.zone_breakdown} size={140} />
            </Box>
            
            <Typography variant="h3" sx={{ color: '#1DB954', fontWeight: 'bold' }}>
              {currentPlayer.score_360}
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
              360° Score
            </Typography>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 1 }}>
              <Typography variant="caption" sx={{ color: '#fff' }}>
                SR: <strong>{currentPlayer.strike_rate}</strong>
              </Typography>
              <Typography variant="caption" sx={{ color: '#fff' }}>
                Zones: <strong>{currentPlayer.zones_used}/8</strong>
              </Typography>
            </Box>
          </Box>
        </Box>
      )}

      {/* Player selector tabs */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        gap: 0.5, 
        flexWrap: 'wrap',
        mb: 2 
      }}>
        {topPlayers.map((player, index) => (
          <Box
            key={player.name}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedPlayer(index);
            }}
            sx={{
              px: 1.5,
              py: 0.5,
              borderRadius: 2,
              bgcolor: selectedPlayer === index ? '#1DB954' : 'rgba(255,255,255,0.1)',
              color: selectedPlayer === index ? '#000' : '#fff',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: selectedPlayer === index ? 'bold' : 'normal',
              transition: 'all 0.2s ease'
            }}
          >
            #{index + 1}
          </Box>
        ))}
      </Box>

      {/* Zone Legend */}
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: 0.5,
        fontSize: '0.65rem',
        color: 'rgba(255,255,255,0.6)'
      }}>
        {currentPlayer?.zone_breakdown?.map(zone => (
          <Box key={zone.zone} sx={{ textAlign: 'center' }}>
            <Typography variant="caption" sx={{ display: 'block', fontWeight: 'bold', color: '#fff' }}>
              {zone.run_pct.toFixed(1)}%
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.6)' }}>
              {data.zone_labels?.[zone.zone] || `Zone ${zone.zone}`}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default ThreeSixtyBattersCard;
