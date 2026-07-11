import React from 'react';
import { colors as designColors } from '../theme/designSystem';

const darkRunColors = {
  6: '#f0b429',
  4: '#b6f24a',
  3: '#5b8def',
  2: '#7aa5f0',
  1: '#9fbff5',
  0: '#5b6270',
};

const runColor = (runs, variant = 'light') => {
  if (variant === 'dark') return darkRunColors[runs] || darkRunColors[0];
  if (runs === 6) return designColors.chart.orange;
  if (runs === 4) return designColors.chart.green;
  if (runs === 3) return designColors.primary[500];
  if (runs === 2) return designColors.primary[400];
  if (runs === 1) return designColors.primary[300];
  return designColors.neutral[400];
};

const MiniWagonWheel = ({ deliveries = [], size = 120, variant = 'light' }) => {
  const centerX = size / 2;
  const centerY = size / 2;
  const maxRadius = size * 0.42;
  const batterRadius = Math.max(size * 0.025, 2);
  const isDark = variant === 'dark';

  const zoneLines = [];
  for (let i = 0; i < 8; i++) {
    const angle = (i * Math.PI / 4) - (Math.PI / 2);
    const x2 = centerX + maxRadius * Math.cos(angle);
    const y2 = centerY + maxRadius * Math.sin(angle);
    zoneLines.push(
      <line
        key={`zone-${i}`}
        x1={centerX} y1={centerY} x2={x2} y2={y2}
        stroke={isDark ? 'rgba(255,255,255,0.06)' : designColors.neutral[200]}
        strokeWidth="1"
        strokeDasharray="3,3"
      />
    );
  }

  const nonBoundaryDeliveries = deliveries.filter(d => d.runs < 4);
  const maxNonBoundaryDistance = Math.max(
    ...nonBoundaryDeliveries.map(d => {
      const dx = d.wagon_x - 150;
      const dy = d.wagon_y - 150;
      return Math.sqrt(dx * dx + dy * dy);
    }),
    1
  );

  const deliveryLines = deliveries.map((delivery, index) => {
    const dx = delivery.wagon_x - 150;
    const dy = delivery.wagon_y - 150;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance === 0) return null;

    let scaledRadius;
    if (delivery.runs >= 4) {
      scaledRadius = maxRadius;
    } else {
      scaledRadius = (distance / maxNonBoundaryDistance) * maxRadius * 0.7;
    }

    const normalizedX = centerX + (dx / distance) * scaledRadius;
    const normalizedY = centerY + (dy / distance) * scaledRadius;

    return (
      <g key={`d-${index}`}>
        <line
          x1={centerX} y1={centerY} x2={normalizedX} y2={normalizedY}
          stroke={runColor(delivery.runs, variant)}
          strokeWidth={1.5}
          opacity={0.6}
          strokeLinecap="round"
        />
        <circle
          cx={normalizedX} cy={normalizedY} r={3}
          fill={runColor(delivery.runs, variant)}
        />
      </g>
    );
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle
        cx={centerX} cy={centerY} r={maxRadius}
        fill={isDark ? '#070a0e' : designColors.neutral[100]}
        stroke={isDark ? 'rgba(255,255,255,0.08)' : designColors.neutral[300]}
        strokeWidth="1.5"
      />
      {zoneLines}
      {deliveryLines}
      <circle cx={centerX} cy={centerY} r={batterRadius} fill={isDark ? '#f3f4f6' : designColors.neutral[800]} />
    </svg>
  );
};

export default MiniWagonWheel;
