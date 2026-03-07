import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import {
  getScoringZoneLabel,
  normalizeScoringZone,
  SCORING_ZONE_CLOCKWISE_FROM_TOP,
} from '../../utils/wagonZones';

// RHB baseline label anchors tuned to match annotated field-map positions.
const RHB_LABEL_LAYOUT_BY_ZONE = Object.freeze({
  8: { clock_deg: 0, radius_ratio: 1.08 },   // Behind (top edge)
  1: { clock_deg: 45, radius_ratio: 1.08 },  // Fine Leg (upper-right edge)
  2: { clock_deg: 88, radius_ratio: 1.08 },  // Square Leg (right edge)
  3: { clock_deg: 138, radius_ratio: 1.08 }, // Midwicket (lower-right edge)
  4: { clock_deg: 168, radius_ratio: 1.03 }, // Long On (near lower arc edge)
  5: { clock_deg: 222, radius_ratio: 1.03 }, // Long Off (near lower arc edge)
  6: { clock_deg: 266, radius_ratio: 1.08 }, // Cover (left edge)
  7: { clock_deg: 318, radius_ratio: 1.08 }, // Point (upper-left edge)
});

const clockToCartesian = (clockDeg, radius, cx, cy) => {
  // Clock convention: 0 deg at 12 o'clock, clockwise positive.
  const radians = ((clockDeg - 90) * Math.PI) / 180;
  return {
    x: cx + (radius * Math.cos(radians)),
    y: cy + (radius * Math.sin(radians)),
  };
};

const CaughtDismissalScatterMap = ({
  deliveries = [],
  isMobile = false,
  dotMode = 'caught',
  batHand = 'RHB',
  selectedZone = 'all',
  onZoneSelect,
}) => {
  const width = isMobile ? 320 : 420;
  const height = width;
  const centerX = width / 2;
  const centerY = height / 2;
  const maxRadius = width * 0.42;
  const scale = maxRadius / 300;

  const withZone = useMemo(() => (
    deliveries
      .map((delivery) => ({
        ...delivery,
        __zone: normalizeScoringZone(delivery),
      }))
      .filter((delivery) => delivery.__zone)
  ), [deliveries]);

  const points = useMemo(() => (
    withZone.map((delivery, index) => {
      const xRaw = Number(delivery.wagon_x);
      const yRaw = Number(delivery.wagon_y);
      if (!Number.isFinite(xRaw) || !Number.isFinite(yRaw)) return null;

      const x = centerX + (xRaw - 150) * scale;
      const y = centerY + (yRaw - 150) * scale;
      const inSelectedZone = selectedZone === 'all' || selectedZone === delivery.__zone;
      const pointColor = dotMode === 'caught' ? '#c62828' : '#1e88e5';

      return (
        <circle
          key={`caught-point-${index}-${delivery.match_id || 'm'}-${delivery.over || 0}`}
          cx={x}
          cy={y}
          r={inSelectedZone ? (isMobile ? 3 : 3.5) : 2}
          fill={pointColor}
          opacity={inSelectedZone ? 0.78 : 0.18}
        >
          <title>
            {`Zone ${delivery.__zone} (${getScoringZoneLabel(delivery.__zone, batHand)}) • ${delivery.phase || 'overall'} • ${delivery.bowl_kind || 'unknown'} • ${delivery.bowl_style || 'unknown'}`}
          </title>
        </circle>
      );
    })
  ), [withZone, centerX, centerY, scale, selectedZone, dotMode, isMobile, batHand]);

  const labelForMap = (zoneNum) => {
    const label = getScoringZoneLabel(zoneNum, batHand);
    return label === 'Square Leg' ? 'Sq Leg' : label;
  };

  const zoneWedges = SCORING_ZONE_CLOCKWISE_FROM_TOP.map((zoneValue, index) => {
    const zoneNum = Number(zoneValue);
    const startAngle = -Math.PI / 2 + index * (Math.PI / 4);
    const endAngle = startAngle + (Math.PI / 4);
    const x1 = centerX + maxRadius * Math.cos(startAngle);
    const y1 = centerY + maxRadius * Math.sin(startAngle);
    const x2 = centerX + maxRadius * Math.cos(endAngle);
    const y2 = centerY + maxRadius * Math.sin(endAngle);
    const isActive = String(zoneNum) === String(selectedZone);

    return (
      <path
        key={`zone-wedge-${zoneNum}`}
        d={`M ${centerX} ${centerY} L ${x1} ${y1} A ${maxRadius} ${maxRadius} 0 0 1 ${x2} ${y2} Z`}
        fill={isActive ? 'rgba(198, 40, 40, 0.12)' : 'rgba(0, 0, 0, 0.01)'}
        stroke={isActive ? '#c62828' : '#d5d5d5'}
        strokeWidth={isActive ? 2 : 1}
        style={{ cursor: 'pointer' }}
        onClick={() => {
          if (onZoneSelect) {
            onZoneSelect(String(zoneNum));
          }
        }}
      >
        <title>{`Zone ${zoneNum}: ${getScoringZoneLabel(zoneNum, batHand)}`}</title>
      </path>
    );
  });

  const zoneLabels = SCORING_ZONE_CLOCKWISE_FROM_TOP.map((zoneValue, index) => {
    const zoneNum = Number(zoneValue);
    const fallbackClockDeg = index * 45;
    const layout = RHB_LABEL_LAYOUT_BY_ZONE[zoneNum] || {
      clock_deg: fallbackClockDeg,
      radius_ratio: 1.04,
    };
    const labelPoint = clockToCartesian(
      Number(layout.clock_deg),
      maxRadius * Number(layout.radius_ratio),
      centerX,
      centerY,
    );
    const x = labelPoint.x;
    const y = labelPoint.y;

    const anchor = x > (centerX + 10)
      ? 'start'
      : x < (centerX - 10)
        ? 'end'
        : 'middle';

    return (
      <text
        key={`zone-label-${zoneNum}`}
        x={x}
        y={y}
        textAnchor={anchor}
        dominantBaseline="middle"
        fontSize={isMobile ? 10 : 11}
        fontWeight={600}
        fill="#4b5563"
        style={{ pointerEvents: 'none' }}
      >
        {labelForMap(zoneNum)}
      </text>
    );
  });

  const resetHint = selectedZone !== 'all';

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="subtitle2">Caught dismissal points</Typography>
        {resetHint && (
          <Typography
            variant="caption"
            sx={{ cursor: 'pointer', color: 'primary.main', fontWeight: 600 }}
            onClick={() => onZoneSelect && onZoneSelect('all')}
          >
            Reset zone
          </Typography>
        )}
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: '100%', height: 'auto' }}>
          <circle cx={centerX} cy={centerY} r={maxRadius} fill="#fafafa" stroke="#d9d9d9" strokeWidth="2" />
          {zoneWedges}
          <circle cx={centerX} cy={centerY} r={maxRadius * 0.5} fill="none" stroke="#e6e6e6" strokeWidth="1" strokeDasharray="4,4" />
          {points}
          {zoneLabels}
          <circle cx={centerX} cy={centerY} r={6} fill="#1f1f1f" />
        </svg>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1 }}>
        Behind is aligned to 12 o'clock. LHB labels are mirrored across the 12-6 axis.
      </Typography>
    </Box>
  );
};

export default CaughtDismissalScatterMap;
