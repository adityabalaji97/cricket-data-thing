/**
 * SVG-based share card for Guess the Innings game.
 * Uses pure SVG to avoid html2canvas artifacts (gray tint).
 */

import React, { forwardRef } from 'react';
import { colors as designColors } from '../../theme/designSystem';

const runColor = (runs) => {
  if (runs === 6) return designColors.chart.orange;
  if (runs === 4) return designColors.chart.green;
  if (runs === 3) return designColors.primary[500];
  if (runs === 2) return designColors.primary[400];
  if (runs === 1) return designColors.primary[300];
  return designColors.neutral[400];
};

const GuessInningsShareCard = forwardRef(({ data, score, hintsUsed, streak }, ref) => {
  const width = 400;
  const height = 520;
  const wheelSize = 280;
  const wheelCenterX = width / 2;
  const wheelCenterY = 180;
  const maxRadius = wheelSize * 0.42;

  const deliveries = data?.deliveries || [];
  const innings = data?.innings || {};
  const answer = data?.answer?.batter || '';

  // Calculate wagon wheel paths
  const nonBoundaryDeliveries = deliveries.filter(d => d.runs < 4 && d.wagon_x !== null && d.wagon_y !== null);
  const maxNonBoundaryDistance = Math.max(
    ...nonBoundaryDeliveries.map(d => {
      const dx = d.wagon_x - 150;
      const dy = d.wagon_y - 150;
      return Math.sqrt(dx * dx + dy * dy);
    }),
    1
  );

  const wagonWheelLines = deliveries
    .filter(d => d.wagon_x !== null && d.wagon_y !== null)
    .map((delivery, index) => {
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

      const x2 = wheelCenterX + (dx / distance) * scaledRadius;
      const y2 = wheelCenterY + (dy / distance) * scaledRadius;

      return (
        <g key={index}>
          <line
            x1={wheelCenterX}
            y1={wheelCenterY}
            x2={x2}
            y2={y2}
            stroke={runColor(delivery.runs)}
            strokeWidth="2"
            opacity="0.7"
            strokeLinecap="round"
          />
          <circle
            cx={x2}
            cy={y2}
            r="3"
            fill={runColor(delivery.runs)}
          />
        </g>
      );
    });

  // Zone lines
  const zoneLines = [];
  for (let i = 0; i < 8; i++) {
    const angle = (i * Math.PI / 4) - (Math.PI / 2);
    const x2 = wheelCenterX + maxRadius * Math.cos(angle);
    const y2 = wheelCenterY + maxRadius * Math.sin(angle);
    zoneLines.push(
      <line
        key={i}
        x1={wheelCenterX}
        y1={wheelCenterY}
        x2={x2}
        y2={y2}
        stroke="#E0E0E0"
        strokeWidth="1"
        strokeDasharray="3,3"
      />
    );
  }

  const hintIcons = ['📍', '🏆', '🎯', '🏏', '🔤'];

  return (
    <svg
      ref={ref}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      xmlns="http://www.w3.org/2000/svg"
      style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}
    >
      {/* Background */}
      <rect width={width} height={height} fill="#FFFFFF" />

      {/* Header */}
      <text x={width / 2} y="35" textAnchor="middle" fontSize="18" fontWeight="700" fill="#1a1a1a">
        Guess the Innings
      </text>

      {/* Wagon wheel background circle */}
      <circle
        cx={wheelCenterX}
        cy={wheelCenterY}
        r={maxRadius}
        fill="#F5F5F5"
        stroke="#E0E0E0"
        strokeWidth="2"
      />

      {/* Zone lines */}
      {zoneLines}

      {/* Wagon wheel shots */}
      {wagonWheelLines}

      {/* Batter dot */}
      <circle cx={wheelCenterX} cy={wheelCenterY} r="4" fill="#1a1a1a" />

      {/* Player name */}
      <text x={width / 2} y="340" textAnchor="middle" fontSize="22" fontWeight="700" fill="#1a1a1a">
        {answer}
      </text>

      {/* Stats */}
      <text x={width / 2} y="365" textAnchor="middle" fontSize="14" fill="#666666">
        {innings.runs} ({innings.balls}) • SR {innings.strike_rate?.toFixed?.(0) ?? innings.strike_rate}
      </text>

      {/* Match info */}
      <text x={width / 2} y="385" textAnchor="middle" fontSize="12" fill="#888888">
        {innings.competition} • {innings.batting_team} vs {innings.bowling_team}
      </text>

      {/* Hints used indicator */}
      <g transform={`translate(${width / 2 - 60}, 405)`}>
        {hintIcons.map((icon, i) => (
          <text
            key={i}
            x={i * 30}
            y="0"
            fontSize="16"
            opacity={i < hintsUsed ? 1 : 0.3}
          >
            {icon}
          </text>
        ))}
      </g>

      {/* Score badge */}
      <rect
        x={width / 2 - 50}
        y="430"
        width="100"
        height="30"
        rx="15"
        fill={score === 5 ? '#FFF3E0' : score >= 3 ? '#E8F5E9' : '#F5F5F5'}
      />
      <text x={width / 2} y="450" textAnchor="middle" fontSize="14" fontWeight="600" fill="#1a1a1a">
        Score: {score}/5
      </text>

      {/* Streak if any */}
      {streak > 1 && (
        <text x={width / 2} y="475" textAnchor="middle" fontSize="12" fill="#666666">
          🔥 {streak} streak
        </text>
      )}

      {/* Footer */}
      <text x={width / 2} y="505" textAnchor="middle" fontSize="11" fill="#AAAAAA">
        hindsight2020.vercel.app/games/guess-innings
      </text>
    </svg>
  );
});

GuessInningsShareCard.displayName = 'GuessInningsShareCard';

/**
 * Convert SVG element to PNG data URL
 */
export const svgToPng = async (svgElement) => {
  const svgData = new XMLSerializer().serializeToString(svgElement);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const img = new Image();

  return new Promise((resolve, reject) => {
    img.onload = () => {
      // 2x scale for retina
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      ctx.scale(2, 2);
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      resolve(canvas.toDataURL('image/png'));
    };
    img.onerror = reject;
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
  });
};

export default GuessInningsShareCard;
