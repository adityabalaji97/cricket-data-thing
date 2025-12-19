/**
 * PitchMapVisualization
 * 
 * Pure SVG rendering component for pitch map.
 * Mobile-first design with stumps at top.
 */

import React from 'react';
import { Box, Typography, Tooltip } from '@mui/material';
import {
  PITCH_DIMENSIONS,
  LINE_ORDER,
  LENGTH_ORDER,
  LINE_SHORT_LABELS,
  LENGTH_SHORT_LABELS,
  METRICS,
  HEAT_COLORS
} from './pitchMapConstants';
import {
  getCellPosition,
  getHeatColor,
  calculateDataRange
} from './pitchMapUtils';

const PitchMapVisualization = ({
  cells,
  mode,
  colorMetric = 'strike_rate',
  displayMetrics = ['average', 'strike_rate'],
  secondaryMetrics = ['dot_percentage', 'boundary_percentage'],
  minBalls = 10,
  title,
  subtitle,
  width: propWidth,
  svgRef
}) => {
  // Use ref to measure container if no width prop
  const [containerWidth, setContainerWidth] = React.useState(propWidth || PITCH_DIMENSIONS.width);
  const containerRef = React.useRef(null);
  
  React.useEffect(() => {
    if (!propWidth && containerRef.current) {
      const resizeObserver = new ResizeObserver(entries => {
        for (const entry of entries) {
          setContainerWidth(entry.contentRect.width - 16); // Account for padding
        }
      });
      resizeObserver.observe(containerRef.current);
      return () => resizeObserver.disconnect();
    }
  }, [propWidth]);
  
  // Calculate dimensions based on container width
  const width = propWidth || containerWidth;
  const scale = width / PITCH_DIMENSIONS.width;
  
  const scaledDimensions = {
    width,
    height: Math.max(500, PITCH_DIMENSIONS.height * scale),
    pitchWidth: (width - (PITCH_DIMENSIONS.padding.left + PITCH_DIMENSIONS.padding.right) * scale),
    pitchHeight: PITCH_DIMENSIONS.pitchHeight * scale,
    padding: {
      top: PITCH_DIMENSIONS.padding.top * scale,
      right: PITCH_DIMENSIONS.padding.right * scale,
      bottom: PITCH_DIMENSIONS.padding.bottom * scale,
      left: PITCH_DIMENSIONS.padding.left * scale
    },
    stumpHeight: Math.max(30, PITCH_DIMENSIONS.stumpHeight * scale),
    stumpWidth: Math.max(4, PITCH_DIMENSIONS.stumpWidth * scale),
    stumpGap: Math.max(6, PITCH_DIMENSIONS.stumpGap * scale)
  };
  
  // Calculate color range from data
  const dataRange = calculateDataRange(cells, colorMetric, minBalls);
  
  return (
    <Box 
      ref={containerRef}
      sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}
    >
      {title && (
        <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 600, textAlign: 'center', px: 1 }}>
          {title}
        </Typography>
      )}
      {subtitle && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1, textAlign: 'center' }}>
          {subtitle}
        </Typography>
      )}
      
      <svg 
        ref={svgRef}
        width={scaledDimensions.width} 
        height={scaledDimensions.height}
        style={{ overflow: 'visible', maxWidth: '100%' }}
      >
        {/* Background */}
        <rect
          x={scaledDimensions.padding.left}
          y={scaledDimensions.padding.top}
          width={scaledDimensions.pitchWidth}
          height={scaledDimensions.pitchHeight}
          fill="#f0fdf4"
          stroke="#86efac"
          strokeWidth={2}
          rx={4}
        />
        
        {/* Pitch markings - crease lines */}
        <PitchMarkings dimensions={scaledDimensions} mode={mode} />
        
        {/* Stumps at top */}
        <StumpsIndicator dimensions={scaledDimensions} scale={scale} />
        
        {/* Cells */}
        {cells.map((cell, index) => (
          <PitchCell
            key={`${cell.line}-${cell.length}-${index}`}
            cell={cell}
            mode={mode}
            dimensions={scaledDimensions}
            colorMetric={colorMetric}
            displayMetrics={displayMetrics}
            secondaryMetrics={secondaryMetrics}
            dataRange={dataRange}
            minBalls={minBalls}
            scale={scale}
          />
        ))}
        
        {/* Axis labels */}
        <AxisLabels dimensions={scaledDimensions} mode={mode} scale={scale} />
      </svg>
      
      {/* Legend */}
      <ColorLegend 
        metric={colorMetric} 
        dataRange={dataRange}
        width={scaledDimensions.pitchWidth}
      />
    </Box>
  );
};

/**
 * Individual cell in the pitch map
 */
const PitchCell = ({ 
  cell, 
  mode, 
  dimensions, 
  colorMetric, 
  displayMetrics,
  secondaryMetrics,
  dataRange,
  minBalls,
  scale
}) => {
  const { x, y, width, height } = getCellPosition(
    cell.line, 
    cell.length, 
    mode, 
    dimensions
  );
  
  const hasData = cell.balls >= minBalls;
  const color = hasData 
    ? getHeatColor(cell[colorMetric], colorMetric, dataRange)
    : HEAT_COLORS.noData;
  
  // Tooltip content
  const tooltipContent = hasData ? (
    <Box sx={{ p: 1 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
        {cell.line && LINE_SHORT_LABELS[cell.line]}
        {cell.line && cell.length && ' / '}
        {cell.length && LENGTH_SHORT_LABELS[cell.length]}
      </Typography>
      <Typography variant="body2">Balls: {cell.balls}</Typography>
      {Object.keys(METRICS).map(key => {
        const value = cell[key];
        if (value === null || value === undefined) return null;
        return (
          <Typography key={key} variant="body2">
            {METRICS[key].label}: {METRICS[key].format(value)}
          </Typography>
        );
      })}
    </Box>
  ) : (
    <Typography variant="body2">
      {cell.balls > 0 ? `${cell.balls} balls (below threshold)` : 'No data'}
    </Typography>
  );
  
  return (
    <Tooltip title={tooltipContent} arrow placement="top">
      <g style={{ cursor: 'pointer' }}>
        <rect
          x={x + 1}
          y={y + 1}
          width={width - 2}
          height={height - 2}
          fill={color}
          stroke="#fff"
          strokeWidth={1}
          rx={3}
          opacity={hasData ? 0.9 : 0.3}
        />
        
        {hasData && (
          <CellContent
            x={x}
            y={y}
            width={width}
            height={height}
            cell={cell}
            displayMetrics={displayMetrics}
            secondaryMetrics={secondaryMetrics}
            mode={mode}
            scale={scale}
          />
        )}
      </g>
    </Tooltip>
  );
};

/**
 * Cell content rendering (metrics text)
 */
const CellContent = ({ x, y, width, height, cell, displayMetrics, secondaryMetrics, mode, scale }) => {
  const baseFontSize = mode === 'grid' ? 11 : 13;
  const fontSize = baseFontSize * Math.max(0.8, scale);
  const smallFontSize = fontSize * 0.85;
  const centerX = x + width / 2;
  const centerY = y + height / 2;
  
  // Format primary metrics (e.g., "36.5 @ 155")
  const formatPrimaryLine = () => {
    const parts = [];
    displayMetrics.forEach(key => {
      const metric = METRICS[key];
      if (metric && cell[key] !== null && cell[key] !== undefined) {
        parts.push(metric.format(cell[key]));
      }
    });
    return parts.join(' @ ');
  };
  
  // Format secondary metrics (e.g., "25.5% | 10.7%")
  const formatSecondaryLine = () => {
    const parts = [];
    secondaryMetrics.forEach(key => {
      const metric = METRICS[key];
      if (metric && cell[key] !== null && cell[key] !== undefined) {
        parts.push(metric.format(cell[key]));
      }
    });
    return parts.join(' | ');
  };
  
  const primaryLine = formatPrimaryLine();
  const secondaryLine = formatSecondaryLine();
  const hasSecondary = secondaryLine && secondaryMetrics.length > 0;
  
  // Adjust vertical positioning based on content
  const lineSpacing = fontSize + 4;
  const totalHeight = hasSecondary ? lineSpacing * 2 : lineSpacing;
  const startY = centerY - totalHeight / 2 + fontSize / 2;
  
  return (
    <>
      {/* Primary metrics line */}
      <text
        x={centerX}
        y={hasSecondary ? startY : centerY}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={fontSize}
        fontWeight="600"
        fill="#1f2937"
      >
        {primaryLine || '-'}
      </text>
      
      {/* Secondary metrics line */}
      {hasSecondary && (
        <text
          x={centerX}
          y={startY + lineSpacing}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={smallFontSize}
          fill="#4b5563"
        >
          {secondaryLine}
        </text>
      )}
    </>
  );
};

/**
 * Pitch markings (crease lines, etc.)
 */
const PitchMarkings = ({ dimensions, mode }) => {
  const { padding, pitchWidth } = dimensions;
  
  // Popping crease (where batter stands) - near top
  const creaseY = padding.top + 25;
  
  return (
    <g stroke="#86efac" strokeWidth={1.5} strokeDasharray="6,4">
      {/* Popping crease */}
      <line
        x1={padding.left + 15}
        y1={creaseY}
        x2={padding.left + pitchWidth - 15}
        y2={creaseY}
      />
    </g>
  );
};

/**
 * Axis labels for line and length
 */
const AxisLabels = ({ dimensions, mode, scale }) => {
  const { padding, pitchWidth, pitchHeight } = dimensions;
  const fontSize = 11 * scale;
  
  // Reverse length order to match cell positions (yorker at top, short at bottom)
  const reversedLengthOrder = [...LENGTH_ORDER].reverse();
  
  return (
    <>
      {/* Line labels (bottom, below pitch) */}
      {(mode === 'grid' || mode === 'line-only') && (
        LINE_ORDER.map((line, index) => {
          const cellWidth = pitchWidth / LINE_ORDER.length;
          const x = padding.left + index * cellWidth + cellWidth / 2;
          return (
            <text
              key={line}
              x={x}
              y={padding.top + pitchHeight + 18}
              textAnchor="middle"
              fontSize={fontSize}
              fill="#6b7280"
            >
              {LINE_SHORT_LABELS[line]}
            </text>
          );
        })
      )}
      
      {/* Length labels (right, in reversed order) */}
      {(mode === 'grid' || mode === 'length-only') && (
        reversedLengthOrder.map((length, index) => {
          const cellHeight = pitchHeight / LENGTH_ORDER.length;
          const y = padding.top + index * cellHeight + cellHeight / 2;
          return (
            <text
              key={length}
              x={padding.left + pitchWidth + 8}
              y={y}
              textAnchor="start"
              dominantBaseline="middle"
              fontSize={fontSize}
              fill="#6b7280"
            >
              {LENGTH_SHORT_LABELS[length]}
            </text>
          );
        })
      )}
    </>
  );
};

/**
 * Stumps indicator at batter's end (TOP of pitch) - taller and more prominent
 */
const StumpsIndicator = ({ dimensions, scale }) => {
  const { padding, pitchWidth, pitchHeight, stumpHeight, stumpWidth, stumpGap } = dimensions;
  const stumpX = padding.left + pitchWidth / 2;
  const stumpY = padding.top - stumpHeight - 8;
  
  return (
    <g>
      {/* Three stumps - taller */}
      {[-1, 0, 1].map(offset => (
        <rect
          key={offset}
          x={stumpX + offset * stumpGap - stumpWidth / 2}
          y={stumpY}
          width={stumpWidth}
          height={stumpHeight}
          fill="#92400e"
          rx={1}
        />
      ))}
      {/* Bails - on top of stumps */}
      <rect
        x={stumpX - stumpGap - stumpWidth}
        y={stumpY - 4}
        width={stumpGap * 2 + stumpWidth * 2}
        height={5}
        fill="#b45309"
        rx={2}
      />
      {/* Batter label */}
      <text
        x={stumpX}
        y={stumpY - 14}
        textAnchor="middle"
        fontSize={12 * scale}
        fontWeight="500"
        fill="#78350f"
      >
        🏏 Batter
      </text>
      
      {/* Bowler label at bottom */}
      <text
        x={stumpX}
        y={padding.top + pitchHeight + 45}
        textAnchor="middle"
        fontSize={12 * scale}
        fontWeight="500"
        fill="#6b7280"
      >
        ↑ Bowler
      </text>
    </g>
  );
};

/**
 * Color scale legend (red=bad for batter, green=good for batter)
 */
const ColorLegend = ({ metric, dataRange, width }) => {
  const metricConfig = METRICS[metric];
  if (!metricConfig || !dataRange) return null;
  
  const gradientId = `legend-gradient-${metric}`;
  const legendWidth = Math.min(width * 0.8, 250);
  
  // For descending metrics (like dot%), lower is better, so flip the gradient
  const isDescending = metricConfig.colorScale === 'descending';
  
  return (
    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
        Color: {metricConfig.label} {isDescending ? '(lower = better)' : '(higher = better)'}
      </Typography>
      <svg width={legendWidth} height={28}>
        <defs>
          <linearGradient id={gradientId}>
            <stop offset="0%" stopColor={isDescending ? HEAT_COLORS.good : HEAT_COLORS.bad} />
            <stop offset="50%" stopColor={HEAT_COLORS.neutral} />
            <stop offset="100%" stopColor={isDescending ? HEAT_COLORS.bad : HEAT_COLORS.good} />
          </linearGradient>
        </defs>
        <rect
          x={0}
          y={0}
          width={legendWidth}
          height={14}
          fill={`url(#${gradientId})`}
          rx={3}
        />
        <text x={0} y={26} fontSize={10} fill="#6b7280">
          {metricConfig.format(dataRange.min)}
        </text>
        <text x={legendWidth} y={26} fontSize={10} fill="#6b7280" textAnchor="end">
          {metricConfig.format(dataRange.max)}
        </text>
      </svg>
    </Box>
  );
};

export default PitchMapVisualization;
