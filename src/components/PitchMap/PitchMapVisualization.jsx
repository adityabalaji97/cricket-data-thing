/**
 * PitchMapVisualization
 * 
 * Pure SVG rendering component for pitch map.
 * Reusable across QueryBuilder, BatterProfile, BowlerProfile, etc.
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
  formatCellContent,
  calculateDataRange
} from './pitchMapUtils';

const PitchMapVisualization = ({
  cells,
  mode,
  colorMetric = 'strike_rate',
  displayMetrics = ['average', 'strike_rate', 'dot_percentage', 'boundary_percentage'],
  minBalls = 10,
  title,
  subtitle,
  width = PITCH_DIMENSIONS.width,
  height = PITCH_DIMENSIONS.height
}) => {
  // Calculate dimensions with aspect ratio preservation
  const scale = width / PITCH_DIMENSIONS.width;
  const scaledDimensions = {
    ...PITCH_DIMENSIONS,
    width,
    height: PITCH_DIMENSIONS.height * scale,
    pitchWidth: PITCH_DIMENSIONS.pitchWidth * scale,
    pitchHeight: PITCH_DIMENSIONS.pitchHeight * scale,
    padding: {
      top: PITCH_DIMENSIONS.padding.top * scale,
      right: PITCH_DIMENSIONS.padding.right * scale,
      bottom: PITCH_DIMENSIONS.padding.bottom * scale,
      left: PITCH_DIMENSIONS.padding.left * scale
    }
  };
  
  // Calculate color range from data
  const dataRange = calculateDataRange(cells, colorMetric, minBalls);
  
  // Filter cells by minimum balls
  const visibleCells = cells.filter(cell => cell.balls >= minBalls);
  
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {title && (
        <Typography variant="h6" sx={{ mb: 0.5 }}>{title}</Typography>
      )}
      {subtitle && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{subtitle}</Typography>
      )}
      
      <svg 
        width={scaledDimensions.width} 
        height={scaledDimensions.height}
        style={{ overflow: 'visible' }}
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
        
        {/* Cells */}
        {cells.map((cell, index) => (
          <PitchCell
            key={`${cell.line}-${cell.length}-${index}`}
            cell={cell}
            mode={mode}
            dimensions={scaledDimensions}
            colorMetric={colorMetric}
            displayMetrics={displayMetrics}
            dataRange={dataRange}
            minBalls={minBalls}
          />
        ))}
        
        {/* Axis labels */}
        <AxisLabels dimensions={scaledDimensions} mode={mode} scale={scale} />
        
        {/* Stumps indicator */}
        <StumpsIndicator dimensions={scaledDimensions} scale={scale} />
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
  dataRange,
  minBalls 
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
  
  const content = hasData ? formatCellContent(cell, displayMetrics) : null;
  
  // Tooltip content
  const tooltipContent = hasData ? (
    <Box sx={{ p: 1 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
        {cell.line && LINE_SHORT_LABELS[cell.line]}
        {cell.line && cell.length && ' / '}
        {cell.length && LENGTH_SHORT_LABELS[cell.length]}
      </Typography>
      <Typography variant="body2">Balls: {cell.balls}</Typography>
      {content?.map(item => (
        <Typography key={item.key} variant="body2">
          {item.label}: {item.value}
        </Typography>
      ))}
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
          rx={2}
          opacity={hasData ? 0.85 : 0.3}
        />
        
        {hasData && content && (
          <CellContent
            x={x}
            y={y}
            width={width}
            height={height}
            content={content}
            mode={mode}
          />
        )}
      </g>
    </Tooltip>
  );
};

/**
 * Cell content rendering (metrics text)
 */
const CellContent = ({ x, y, width, height, content, mode }) => {
  const fontSize = mode === 'grid' ? 9 : 11;
  const lineHeight = fontSize + 2;
  const centerX = x + width / 2;
  const startY = y + height / 2 - ((content.length - 1) * lineHeight) / 2;
  
  // For grid mode, show abbreviated format
  if (mode === 'grid') {
    // Show: "avg @ SR" on first line, "dot% | bnd%" on second line
    const avg = content.find(c => c.key === 'average');
    const sr = content.find(c => c.key === 'strike_rate');
    const dot = content.find(c => c.key === 'dot_percentage');
    const bnd = content.find(c => c.key === 'boundary_percentage');
    
    const line1 = avg && sr ? `${avg.value} @ ${sr.value}` : '';
    const line2 = dot && bnd ? `${dot.value} | ${bnd.value}` : '';
    
    return (
      <>
        <text
          x={centerX}
          y={y + height / 2 - 5}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={fontSize}
          fontWeight="600"
          fill="#1f2937"
        >
          {line1}
        </text>
        <text
          x={centerX}
          y={y + height / 2 + 8}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={fontSize - 1}
          fill="#4b5563"
        >
          {line2}
        </text>
      </>
    );
  }
  
  // For line-only or length-only, show all metrics
  return (
    <>
      {content.map((item, index) => (
        <text
          key={item.key}
          x={centerX}
          y={startY + index * lineHeight}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={fontSize}
          fill="#1f2937"
        >
          {item.label}: {item.value}
        </text>
      ))}
    </>
  );
};

/**
 * Pitch markings (crease lines, etc.)
 */
const PitchMarkings = ({ dimensions, mode }) => {
  const { padding, pitchWidth, pitchHeight } = dimensions;
  
  // Popping crease (where batter stands) - near top
  const creaseY = padding.top + 30;
  
  return (
    <g stroke="#86efac" strokeWidth={1} strokeDasharray="4,4">
      {/* Popping crease */}
      <line
        x1={padding.left + 20}
        y1={creaseY}
        x2={padding.left + pitchWidth - 20}
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
  const fontSize = 10 * scale;
  
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
              y={padding.top + pitchHeight + 16}
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
 * Stumps indicator at batter's end (TOP of pitch)
 */
const StumpsIndicator = ({ dimensions, scale }) => {
  const { padding, pitchWidth, pitchHeight } = dimensions;
  const stumpX = padding.left + pitchWidth / 2;
  const stumpY = padding.top - 20 * scale; // Above the pitch
  
  return (
    <g>
      {/* Three stumps */}
      {[-1, 0, 1].map(offset => (
        <rect
          key={offset}
          x={stumpX + offset * 6 * scale - 2 * scale}
          y={stumpY}
          width={4 * scale}
          height={15 * scale}
          fill="#92400e"
          rx={1}
        />
      ))}
      {/* Bails */}
      <rect
        x={stumpX - 10 * scale}
        y={stumpY + 15 * scale - 2 * scale}
        width={20 * scale}
        height={3 * scale}
        fill="#b45309"
        rx={1}
      />
      <text
        x={stumpX}
        y={stumpY - 8 * scale}
        textAnchor="middle"
        fontSize={9 * scale}
        fill="#6b7280"
      >
        Batter
      </text>
      
      {/* Bowler label at bottom */}
      <text
        x={stumpX}
        y={padding.top + pitchHeight + 32 * scale}
        textAnchor="middle"
        fontSize={9 * scale}
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
  const legendWidth = Math.min(width, 200);
  
  // For descending metrics (like dot%), lower is better, so flip the gradient
  const isDescending = metricConfig.colorScale === 'descending';
  
  return (
    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
        Color: {metricConfig.label} {isDescending ? '(lower = better)' : '(higher = better)'}
      </Typography>
      <svg width={legendWidth} height={24}>
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
          height={12}
          fill={`url(#${gradientId})`}
          rx={2}
        />
        <text x={0} y={22} fontSize={9} fill="#6b7280">
          {metricConfig.format(dataRange.min)}
        </text>
        <text x={legendWidth} y={22} fontSize={9} fill="#6b7280" textAnchor="end">
          {metricConfig.format(dataRange.max)}
        </text>
      </svg>
    </Box>
  );
};

export default PitchMapVisualization;
