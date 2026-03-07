import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';

const ZONE_LABELS = {
  1: 'Long Off Arc',
  2: 'Midwicket Arc',
  3: 'Square Leg Arc',
  4: 'Fine Leg Arc',
  5: 'Behind Point Arc',
  6: 'Point Arc',
  7: 'Cover Arc',
  8: 'Long On Arc',
};

const normalizeZone = (delivery) => {
  const rawZone = Number(delivery?.wagon_zone);
  if (Number.isFinite(rawZone) && rawZone >= 1 && rawZone <= 8) {
    return String(rawZone);
  }

  const x = Number(delivery?.wagon_x);
  const y = Number(delivery?.wagon_y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }

  const dx = x - 150;
  const dy = y - 150;
  if (dx === 0 && dy === 0) {
    return '1';
  }

  let theta = Math.atan2(dy, dx) + Math.PI / 2;
  if (theta < 0) theta += Math.PI * 2;
  const sector = Math.floor(theta / (Math.PI / 4)) + 1;
  return String(sector > 8 ? 1 : sector);
};

const CaughtDismissalScatterMap = ({
  deliveries = [],
  isMobile = false,
  dotMode = 'caught',
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
        __zone: normalizeZone(delivery),
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
            {`Zone ${delivery.__zone} • ${delivery.phase || 'overall'} • ${delivery.bowl_kind || 'unknown'} • ${delivery.bowl_style || 'unknown'}`}
          </title>
        </circle>
      );
    })
  ), [withZone, centerX, centerY, scale, selectedZone, dotMode, isMobile]);

  const zoneWedges = Array.from({ length: 8 }).map((_, index) => {
    const zoneNum = index + 1;
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
        <title>{`Zone ${zoneNum}: ${ZONE_LABELS[zoneNum]}`}</title>
      </path>
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
          <circle cx={centerX} cy={centerY} r={6} fill="#1f1f1f" />
        </svg>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1 }}>
        Tap a zone to focus recommendations for that arc.
      </Typography>
    </Box>
  );
};

export default CaughtDismissalScatterMap;
