/**
 * PitchMapVisualization
 * 
 * Pure SVG rendering component for pitch map.
 * Mobile-first design with stumps at top, full toss at stump level.
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
          setContainerWidth(entry.contentRect.width - 16);
        }
      });
      resizeObserver.observe(containerRef.current);
      return () => resizeObserver.disconnect();
    }
  }, [propWidth]);
  
  // Calculate dimensions based on container width
  const width = propWidth || containerWidth;
  const scale = width / PITCH_DIMENSIONS.width;
  
  // Calculate cell height first (for stump overlap calculation)
  const cellHeight = (PITCH_DIMENSIONS.pitchHeight * scale) / LENGTH_ORDER.length;
  
  // Pitch starts higher up - full toss row should be at stump level
  // stumpOverlap is the full height of one cell so full toss aligns with stumps
  const stumpOverlap = cellHeight;
  
  const scaledDimensions = {
    width,
    height: Math.max(550, PITCH_DIMENSIONS.height * scale + stumpOverlap),
    pitchWidth: (width - (PITCH_DIMENSIONS.padding.left + PITCH_DIMENSIONS.padding.right) * scale),
    pitchHeight: PITCH_DIMENSIONS.pitchHeight * scale,
    padding: {
      top: PITCH_DIMENSIONS.padding.top * scale + stumpOverlap, // Add overlap to top padding
      right: PITCH_DIMENSIONS.padding.right * scale,
      bottom: PITCH_DIMENSIONS.padding.bottom * scale,
      left: PITCH_DIMENSIONS.padding.left * scale
    },
    stumpHeight: Math.max(40, PITCH_DIMENSIONS.stumpHeight * scale),
    stumpWidth: Math.max(6, PITCH_DIMENSIONS.stumpWidth * scale),
    stumpGap: Math.max(8, PITCH_DIMENSIONS.stumpGap * scale),
    stumpOverlap
  };
  
  // Calculate color range from data
  const dataRange = calculateDataRange(cells, colorMetric, minBalls);
  
  // Calculate responsive font sizes based on cell dimensions
  const getCellFontSizes = () => {
    let cellWidth, cellHeight;
    
    if (mode === 'grid') {
      cellWidth = scaledDimensions.pitchWidth / LINE_ORDER.length;
      cellHeight = scaledDimensions.pitchHeight / LENGTH_ORDER.length;
    } else if (mode === 'line-only') {
      cellWidth = scaledDimensions.pitchWidth / LINE_ORDER.length;
      cellHeight = scaledDimensions.pitchHeight;
    } else {
      cellWidth = scaledDimensions.pitchWidth;
      cellHeight = scaledDimensions.pitchHeight / LENGTH_ORDER.length;
    }
    
    const hasSecondary = secondaryMetrics.length > 0;
    
    // Calculate available space more conservatively
    const availableHeight = cellHeight * 0.7;
    const availableWidth = cellWidth * 0.92;
    
    // Estimate character widths more accurately
    // Each metric value is roughly 4-6 chars, separator is 3 chars (" @ " or " | ")
    const primaryMetricCount = displayMetrics.length;
    const secondaryMetricCount = secondaryMetrics.length;
    
    // Estimate primary line width: each value ~5 chars, each separator ~3 chars
    const primaryCharWidth = primaryMetricCount * 5 + Math.max(0, primaryMetricCount - 1) * 3;
    const secondaryCharWidth = secondaryMetricCount * 5 + Math.max(0, secondaryMetricCount - 1) * 3;
    
    // Character width is roughly 0.55-0.6 of font size
    const charWidthRatio = 0.58;
    
    // Calculate max font size based on width constraint
    const maxPrimaryByWidth = availableWidth / (primaryCharWidth * charWidthRatio);
    const maxSecondaryByWidth = availableWidth / (secondaryCharWidth * charWidthRatio);
    
    // Calculate max font size based on height constraint
    let maxPrimaryByHeight, maxSecondaryByHeight;
    if (hasSecondary) {
      // Two lines need to fit with some spacing
      const lineHeight = availableHeight / 2.5;
      maxPrimaryByHeight = lineHeight;
      maxSecondaryByHeight = lineHeight * 0.9;
    } else {
      maxPrimaryByHeight = availableHeight * 0.8;
      maxSecondaryByHeight = 0;
    }
    
    // Take the minimum of width and height constraints, cap at reasonable max
    const primaryFontSize = Math.min(maxPrimaryByWidth, maxPrimaryByHeight, 13);
    const secondaryFontSize = Math.min(maxSecondaryByWidth, maxSecondaryByHeight, 11);
    
    return {
      primary: Math.max(7, primaryFontSize),
      secondary: Math.max(6, secondaryFontSize)
    };
  };
  
  const fontSizes = getCellFontSizes();
  
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
        {/* Stumps at top - positioned so full toss row is at stump level */}
        <StumpsIndicator dimensions={scaledDimensions} scale={scale} />
        
        {/* Background pitch - starts slightly behind stumps */}
        <rect
          x={scaledDimensions.padding.left}
          y={scaledDimensions.padding.top - stumpOverlap}
          width={scaledDimensions.pitchWidth}
          height={scaledDimensions.pitchHeight + stumpOverlap}
          fill="#f0fdf4"
          stroke="#86efac"
          strokeWidth={2}
          rx={4}
        />
        
        {/* Pitch markings - crease line at full toss level */}
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
            secondaryMetrics={secondaryMetrics}
            dataRange={dataRange}
            minBalls={minBalls}
            scale={scale}
            fontSizes={fontSizes}
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
  scale,
  fontSizes
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
            fontSizes={fontSizes}
          />
        )}
      </g>
    </Tooltip>
  );
};

/**
 * Cell content rendering (metrics text) - responsive sizing
 */
const CellContent = ({ x, y, width, height, cell, displayMetrics, secondaryMetrics, mode, fontSizes }) => {
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
  
  // Calculate vertical positions
  const lineSpacing = fontSizes.primary + 4;
  const primaryY = hasSecondary ? centerY - lineSpacing / 2 : centerY;
  const secondaryY = centerY + lineSpacing / 2;
  
  return (
    <>
      {/* Primary metrics line */}
      {primaryLine && (
        <text
          x={centerX}
          y={primaryY}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={fontSizes.primary}
          fontWeight="600"
          fill="#1f2937"
        >
          {primaryLine}
        </text>
      )}
      
      {/* Secondary metrics line */}
      {hasSecondary && (
        <text
          x={centerX}
          y={secondaryY}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={fontSizes.secondary}
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
  const { padding, pitchWidth, stumpOverlap } = dimensions;
  
  // Popping crease at full toss level (just below where stumps sit)
  const creaseY = padding.top - stumpOverlap + 10;
  
  return (
    <g stroke="#86efac" strokeWidth={2} strokeDasharray="8,4">
      {/* Popping crease */}
      <line
        x1={padding.left + 10}
        y1={creaseY}
        x2={padding.left + pitchWidth - 10}
        y2={creaseY}
      />
    </g>
  );
};

/**
 * Axis labels for line and length
 */
const AxisLabels = ({ dimensions, mode, scale }) => {
  const { padding, pitchWidth, pitchHeight, stumpOverlap } = dimensions;
  const fontSize = 11 * scale;
  
  // Reverse length order to match cell positions (full toss at top near stumps, short at bottom)
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
      
      {/* Length labels (right, in reversed order - full toss at top) */}
      {(mode === 'grid' || mode === 'length-only') && (
        reversedLengthOrder.map((length, index) => {
          const cellHeight = pitchHeight / LENGTH_ORDER.length;
          // Offset by stumpOverlap since pitch starts higher
          const y = (padding.top - stumpOverlap) + index * cellHeight + cellHeight / 2;
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
 * Positioned so stumps sit at the top of the full toss row
 */
const StumpsIndicator = ({ dimensions, scale }) => {
  const { padding, pitchWidth, pitchHeight, stumpHeight, stumpWidth, stumpGap, stumpOverlap } = dimensions;
  const stumpX = padding.left + pitchWidth / 2;
  
  // Stumps sit at the very top of the pitch, base at top of full toss row
  const stumpBaseY = padding.top - stumpOverlap + 5; // Just inside the top of full toss cell
  const stumpY = stumpBaseY - stumpHeight;
  
  return (
    <g>
      {/* Three stumps - taller and more prominent */}
      {[-1, 0, 1].map(offset => (
        <rect
          key={offset}
          x={stumpX + offset * stumpGap - stumpWidth / 2}
          y={stumpY}
          width={stumpWidth}
          height={stumpHeight}
          fill="#78350f"
          rx={1}
        />
      ))}
      {/* Bails - on top of stumps */}
      <rect
        x={stumpX - stumpGap - stumpWidth}
        y={stumpY - 6}
        width={stumpGap * 2 + stumpWidth * 2}
        height={7}
        fill="#92400e"
        rx={2}
      />
      {/* Batter label */}
      <text
        x={stumpX}
        y={stumpY - 16}
        textAnchor="middle"
        fontSize={12 * scale}
        fontWeight="600"
        fill="#78350f"
      >
        🏏 Batter
      </text>
      
      {/* Bowler label at bottom */}
      <text
        x={stumpX}
        y={padding.top + pitchHeight + 42}
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
