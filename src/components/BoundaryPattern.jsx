import React from 'react';
import { Card, CardContent, Typography, Box, Tooltip } from '@mui/material';
import { Info as InfoIcon } from 'lucide-react';

const PieSegment = ({ startAngle, endAngle, ballsFaced, boundaryPercent, bowlingType, phase }) => {
  const cx = 0, cy = 0, r = 100;
  const startRadian = (startAngle * Math.PI) / 180;
  const endRadian = (endAngle * Math.PI) / 180;
  
  const x1 = cx + r * Math.cos(startRadian);
  const y1 = cy + r * Math.sin(startRadian);
  const x2 = cx + r * Math.cos(endRadian);
  const y2 = cy + r * Math.sin(endRadian);
  
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  
  const d = [
    "M", cx, cy,
    "L", x1, y1,
    "A", r, r, 0, largeArcFlag, 1, x2, y2,
    "Z"
  ].join(" ");

  const getColor = (percent) => {
    if (percent >= 25) return '#2E7D32';  // Above average (1.5x normal)
    if (percent <= 12) return '#D32F2F';  // Below average
    return '#ED6C02';  // Average range
  };

  return (
    <Tooltip title={
      <Box>
        <Typography variant="body2">
          {`${bowlingType} - ${phase}`}
          <br />
          Boundary %: {boundaryPercent.toFixed(1)}%
          <br />
          Balls: {ballsFaced}
        </Typography>
      </Box>
    }>
      <path
        d={d}
        fill={getColor(boundaryPercent)}
        opacity={0.8}
        style={{ transition: 'opacity 0.2s' }}
        onMouseEnter={(e) => { e.target.style.opacity = 1; }}
        onMouseLeave={(e) => { e.target.style.opacity = 0.8; }}
      />
    </Tooltip>
  );
};

const BoundaryPattern = ({ stats }) => {
  if (!stats?.phase_stats?.bowling_types) return null;

  const segments = [];
  let totalBalls = 0;
  let currentAngle = 0;

  Object.entries(stats.phase_stats.bowling_types).forEach(([type, phases]) => {
    Object.entries(phases).forEach(([phase, data]) => {
      if (phase !== 'overall' && data.balls > 0) {
        totalBalls += data.balls;
      }
    });
  });

  Object.entries(stats.phase_stats.bowling_types).forEach(([type, phases]) => {
    Object.entries(phases).forEach(([phase, data]) => {
      if (phase !== 'overall' && data.balls > 0) {
        const angle = (data.balls / totalBalls) * 360;
        segments.push({
          startAngle: currentAngle,
          endAngle: currentAngle + angle,
          ballsFaced: data.balls,
          boundaryPercent: data.boundary_percentage,
          bowlingType: type,
          phase
        });
        currentAngle += angle;
      }
    });
  });

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography variant="h6">Boundary Hitting Pattern</Typography>
          <Tooltip title="Size shows balls faced, color shows boundary percentage (Green: >25%, Red: <12%)">
            <InfoIcon size={16} />
          </Tooltip>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <svg viewBox="-120 -120 240 240" width="400" height="400">
            {segments.map((segment, i) => (
              <PieSegment key={i} {...segment} />
            ))}
          </svg>
        </Box>
      </CardContent>
    </Card>
  );
};

export default BoundaryPattern;