/**
 * BowlerWagonWheel Component
 *
 * Displays wagon wheel visualization showing where a bowler was hit.
 * Uses wagon_x and wagon_y coordinates from delivery_details table.
 * Adapted from WagonWheel.jsx for bowlers.
 */

import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Chip
} from '@mui/material';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { AlertBanner, EmptyState } from './ui';
import config from '../config';
import { colors as designColors } from '../theme/designSystem';


const BowlerWagonWheel = ({
  playerName,
  startDate,
  endDate,
  venue,
  leagues = [],
  includeInternational = false,
  topTeams = null,
  isMobile = false,
  wrapInCard = true,
  shareView = false
}) => {
  const [wagonData, setWagonData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const isCompact = shareView || isMobile;
  const Wrapper = wrapInCard ? Card : Box;
  const frameSx = isMobile
    ? { minHeight: 420 }
    : {};
  const wrapperProps = wrapInCard
    ? { isMobile, shareFrame: shareView, sx: frameSx }
    : { sx: { width: '100%', ...frameSx } };

  // Filters
  const [phase, setPhase] = useState('overall');
  const [line, setLine] = useState('all');
  const [length, setLength] = useState('all');
  const [shot, setShot] = useState('all');

  // Available options from data
  const [availableLines, setAvailableLines] = useState([]);
  const [availableLengths, setAvailableLengths] = useState([]);
  const [availableShots, setAvailableShots] = useState([]);

  const chartContainerRef = useRef(null);
  const [containerSize, setContainerSize] = useState(360);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const resizeObserver = new ResizeObserver(entries => {
      entries.forEach(entry => {
        const nextWidth = Math.max(240, Math.floor(entry.contentRect.width));
        setContainerSize(nextWidth);
      });
    });
    resizeObserver.observe(chartContainerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!playerName) return;

    const fetchWagonData = async () => {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (venue && venue !== 'All Venues') params.append('venue', venue);

      leagues.forEach(league => params.append('leagues', league));
      params.append('include_international', includeInternational);
      if (includeInternational && topTeams) {
        params.append('top_teams', topTeams);
      }

      params.append('phase', phase);
      if (line !== 'all') params.append('line', line);
      if (length !== 'all') params.append('length', length);
      if (shot !== 'all') params.append('shot', shot);

      try {
        const response = await fetch(
          `${config.API_URL}/visualizations/bowler/${encodeURIComponent(playerName)}/wagon-wheel?${params}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch wagon wheel data');
        }

        const data = await response.json();
        setWagonData(data);

        // Extract unique values for filters
        const lines = [...new Set(data.deliveries.map(d => d.line).filter(Boolean))];
        setAvailableLines(lines.sort());

        const lengths = [...new Set(data.deliveries.map(d => d.length).filter(Boolean))];
        setAvailableLengths(lengths.sort());

        const shots = [...new Set(data.deliveries.map(d => d.shot).filter(Boolean))];
        setAvailableShots(shots.sort());
      } catch (err) {
        console.error('Error fetching bowler wagon wheel data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchWagonData();
  }, [playerName, startDate, endDate, venue, leagues, includeInternational, topTeams, phase, line, length, shot]);

  // Calculate statistics from wagon data
  const stats = useMemo(() => {
    if (!wagonData) return null;

    const deliveries = wagonData.deliveries;
    const totalRuns = deliveries.reduce((sum, d) => sum + (d.runs || 0), 0);
    const boundaries = deliveries.filter(d => d.runs === 4 || d.runs === 6).length;
    const fours = deliveries.filter(d => d.runs === 4).length;
    const sixes = deliveries.filter(d => d.runs === 6).length;

    // Group by zone
    const byZone = deliveries.reduce((acc, d) => {
      const zone = d.wagon_zone;
      if (zone === null || zone === undefined) return acc;

      if (!acc[zone]) {
        acc[zone] = { count: 0, runs: 0, boundaries: 0 };
      }
      acc[zone].count++;
      acc[zone].runs += d.runs || 0;
      if (d.runs === 4 || d.runs === 6) acc[zone].boundaries++;

      return acc;
    }, {});

    return {
      totalBalls: deliveries.length,
      totalRuns,
      boundaries,
      fours,
      sixes,
      economy: deliveries.length > 0 ? ((totalRuns / deliveries.length) * 6).toFixed(2) : 0,
      boundaryPercentage: deliveries.length > 0 ? ((boundaries / deliveries.length) * 100).toFixed(1) : 0,
      byZone
    };
  }, [wagonData]);

  // SVG rendering - cricket field with wagon wheel
  const renderWagonWheel = () => {
    if (!wagonData || !stats) return null;

    // Responsive dimensions - circular field
    const width = Math.min(containerSize, isCompact ? 360 : 420);
    const height = width; // Circular - same width and height
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = width * 0.4; // Single radius for circle
    const batterRadius = width * 0.02; // 2% of width (8/400)

    // Field zones (8 zones + center)
    const zoneLines = [];
    for (let i = 0; i < 8; i++) {
      const angle = (i * Math.PI / 4) - (Math.PI / 2); // Start from top
      const x2 = centerX + maxRadius * Math.cos(angle);
      const y2 = centerY + maxRadius * Math.sin(angle);
      zoneLines.push(
        <line
          key={`zone-${i}`}
          x1={centerX}
          y1={centerY}
          x2={x2}
          y2={y2}
          stroke={designColors.neutral[200]}
          strokeWidth="1"
          strokeDasharray="4,4"
        />
      );
    }

    // Plot deliveries as lines from batter to shot endpoint
    const deliveryLines = wagonData.deliveries
      .filter(d => d.wagon_x !== null && d.wagon_y !== null)
      .map((delivery, idx) => {
        // Scale coordinates to fit in our SVG (assuming wagon_x/y are in range 0-300)
        const scale = maxRadius / 300;
        let x = centerX + (delivery.wagon_x - 150) * scale;
        let y = centerY + (delivery.wagon_y - 150) * scale;

        // For boundaries (4s and 6s), extend to the circle edge
        if (delivery.runs === 4 || delivery.runs === 6) {
          const dx = x - centerX;
          const dy = y - centerY;
          const distance = Math.sqrt(dx * dx + dy * dy);
          if (distance > 0) {
            // Extend to circle boundary
            const angle = Math.atan2(dy, dx);
            x = centerX + maxRadius * Math.cos(angle);
            y = centerY + maxRadius * Math.sin(angle);
          }
        }

        // Color by runs
        let color = designColors.neutral[400]; // dots
        let strokeWidth = 1;
        let opacity = 0.4;
        if (delivery.runs === 6) {
          color = designColors.chart.pink; // sixes - pink
          strokeWidth = 2.5;
          opacity = 0.7;
        } else if (delivery.runs === 4) {
          color = designColors.chart.blue; // fours - blue
          strokeWidth = 2;
          opacity = 0.6;
        } else if (delivery.runs > 0) {
          color = designColors.chart.green; // runs - green
          strokeWidth = 1.5;
          opacity = 0.5;
        }

        return (
          <line
            key={`delivery-${idx}`}
            x1={centerX}
            y1={centerY}
            x2={x}
            y2={y}
            stroke={color}
            strokeWidth={strokeWidth}
            opacity={opacity}
            strokeLinecap="round"
          />
        );
      });

    return (
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ maxWidth: '100%', height: 'auto', display: 'block' }}
      >
        {/* Field boundary - circle for cricket field */}
        <circle
          cx={centerX}
          cy={centerY}
          r={maxRadius}
          fill={designColors.neutral[50]}
          stroke={designColors.neutral[300]}
          strokeWidth="2"
        />

        {/* Zone lines */}
        {zoneLines}

        {/* Inner circle (30 yard circle) */}
        <circle
          cx={centerX}
          cy={centerY}
          r={maxRadius * 0.5}
          fill="none"
          stroke={designColors.neutral[200]}
          strokeWidth="1"
          strokeDasharray="4,4"
        />

        {/* Pitch */}
        <rect
          x={centerX - (width * 0.0125)}
          y={centerY - (width * 0.075)}
          width={width * 0.025}
          height={width * 0.15}
          fill={designColors.warning[50]}
          stroke={designColors.warning[600]}
          strokeWidth="1"
        />

        {/* Delivery lines */}
        {deliveryLines}

        {/* Batter position (circle at center) */}
        <circle cx={centerX} cy={centerY} r={batterRadius} fill="#333" stroke="#000" strokeWidth="1" />
      </svg>
    );
  };

  if (loading) {
    return (
      <Wrapper {...wrapperProps}>
        <Box sx={{ textAlign: 'center', py: 3 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Loading wagon wheel data...</Typography>
        </Box>
      </Wrapper>
    );
  }

  if (error) {
    return (
      <Wrapper {...wrapperProps}>
        <AlertBanner severity="error">{error}</AlertBanner>
      </Wrapper>
    );
  }

  if (!wagonData || wagonData.total_deliveries === 0) {
    return (
      <Wrapper {...wrapperProps}>
        <EmptyState
          title="No innings match these filters"
          description="No wagon wheel data is available for the selected filters."
          isMobile={isCompact}
          minHeight={isCompact ? 280 : 320}
        />
      </Wrapper>
    );
  }

  const filterConfig = [
    {
      key: 'phase',
      label: 'Phase',
      options: [
        { value: 'overall', label: 'Overall' },
        { value: 'powerplay', label: isMobile ? 'PP' : 'Powerplay' },
        { value: 'middle', label: 'Middle' },
        { value: 'death', label: 'Death' },
      ],
    },
    ...(availableLines.length > 0 ? [{
      key: 'line',
      label: 'Line',
      options: [
        { value: 'all', label: 'All' },
        ...availableLines.map(l => ({ value: l, label: l })),
      ],
    }] : []),
    ...(availableLengths.length > 0 ? [{
      key: 'length',
      label: 'Length',
      options: [
        { value: 'all', label: 'All' },
        ...availableLengths.map(l => ({ value: l, label: l })),
      ],
    }] : []),
    ...(availableShots.length > 0 ? [{
      key: 'shot',
      label: 'Shot',
      options: [
        { value: 'all', label: 'All' },
        ...availableShots.map(s => ({ value: s, label: s })),
      ],
    }] : []),
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'phase') setPhase(value);
    else if (key === 'line') setLine(value);
    else if (key === 'length') setLength(value);
    else if (key === 'shot') setShot(value);
  };

  return (
    <Wrapper {...wrapperProps}>
      {/* Title and Filters in one row */}
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: 2,
        gap: 1,
        flexWrap: isMobile ? 'wrap' : 'nowrap'
      }}>
        <Typography variant={isCompact ? "h6" : "h5"} sx={{ fontWeight: 600, flexShrink: 0 }}>
          Where Hit
        </Typography>
        <Box sx={{ flexShrink: 1, minWidth: 0 }}>
          <FilterBar
            filters={filterConfig}
            activeFilters={{ phase, line, length, shot }}
            onFilterChange={handleFilterChange}
            isMobile={isCompact}
            showActiveCount={false}
          />
        </Box>
      </Box>

      {/* Stats Summary */}
      <Box sx={{ display: 'flex', gap: isCompact ? 0.5 : 1, mb: isCompact ? 1.5 : 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Chip label={`${stats.totalBalls} balls`} size="small" sx={{ fontSize: isCompact ? '0.7rem' : undefined, height: isCompact ? 24 : undefined }} />
        <Chip label={`${stats.totalRuns} runs`} size="small" sx={{ bgcolor: designColors.chart.blue, color: 'white', fontSize: isCompact ? '0.7rem' : undefined, height: isCompact ? 24 : undefined }} />
        <Chip label={`Econ: ${stats.economy}`} size="small" sx={{ fontSize: isCompact ? '0.7rem' : undefined, height: isCompact ? 24 : undefined }} />
        <Chip label={`${stats.fours} x 4s`} size="small" sx={{ bgcolor: designColors.chart.blue, color: 'white', fontSize: isCompact ? '0.7rem' : undefined, height: isCompact ? 24 : undefined }} />
        <Chip label={`${stats.sixes} x 6s`} size="small" sx={{ bgcolor: designColors.chart.pink, color: 'white', fontSize: isCompact ? '0.7rem' : undefined, height: isCompact ? 24 : undefined }} />
      </Box>

      {/* Legend */}
      <Box sx={{ display: 'flex', gap: isCompact ? 1.5 : 2, mb: isCompact ? 1.5 : 2, flexWrap: 'wrap', justifyContent: 'center', fontSize: isCompact ? '0.65rem' : '0.875rem' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: isCompact ? 10 : 12, height: isCompact ? 10 : 12, borderRadius: '50%', bgcolor: designColors.chart.pink }} />
          <Typography variant="caption" sx={{ fontSize: isCompact ? '0.65rem' : undefined }}>Sixes</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: isCompact ? 8 : 10, height: isCompact ? 8 : 10, borderRadius: '50%', bgcolor: designColors.chart.blue }} />
          <Typography variant="caption" sx={{ fontSize: isCompact ? '0.65rem' : undefined }}>Fours</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: isCompact ? 7 : 8, height: isCompact ? 7 : 8, borderRadius: '50%', bgcolor: designColors.chart.green }} />
          <Typography variant="caption" sx={{ fontSize: isCompact ? '0.65rem' : undefined }}>Runs</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: isCompact ? 5 : 6, height: isCompact ? 5 : 6, borderRadius: '50%', bgcolor: designColors.neutral[400] }} />
          <Typography variant="caption" sx={{ fontSize: isCompact ? '0.65rem' : undefined }}>Dots</Typography>
        </Box>
      </Box>

      {/* Wagon Wheel Visualization */}
      <Box
        ref={chartContainerRef}
        sx={{
          display: 'flex',
          justifyContent: 'center',
          width: '100%',
          maxWidth: isCompact ? 360 : 420,
          mx: 'auto'
        }}
      >
        {renderWagonWheel()}
      </Box>
    </Wrapper>
  );
};

export default BowlerWagonWheel;
