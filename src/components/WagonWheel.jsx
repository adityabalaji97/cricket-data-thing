/**
 * WagonWheel Component
 *
 * Displays wagon wheel visualization showing where a batter's shots ended up.
 * Uses wagon_x and wagon_y coordinates from delivery_details table.
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  ToggleButtonGroup,
  ToggleButton,
  Chip
} from '@mui/material';
import config from '../config';

// Wagon wheel zones (0-8, clockwise from fine leg)
const ZONE_LABELS = {
  0: 'Fine Leg',
  1: 'Square Leg',
  2: 'Mid Wicket',
  3: 'Long On',
  4: 'Long Off',
  5: 'Extra Cover',
  6: 'Point',
  7: 'Third Man',
  8: 'Straight'
};

const WagonWheel = ({
  playerName,
  startDate,
  endDate,
  venue,
  leagues = [],
  includeInternational = false,
  topTeams = null
}) => {
  const [wagonData, setWagonData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [phase, setPhase] = useState('overall');
  const [bowlKind, setBowlKind] = useState('all');
  const [bowlStyle, setBowlStyle] = useState('all');

  // Available bowling styles from data
  const [availableStyles, setAvailableStyles] = useState([]);

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
      if (bowlKind !== 'all') params.append('bowl_kind', bowlKind);
      if (bowlStyle !== 'all') params.append('bowl_style', bowlStyle);

      try {
        const response = await fetch(
          `${config.API_URL}/visualizations/player/${encodeURIComponent(playerName)}/wagon-wheel?${params}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch wagon wheel data');
        }

        const data = await response.json();
        setWagonData(data);

        // Extract unique bowling styles for filter
        const styles = [...new Set(data.deliveries.map(d => d.bowl_style).filter(Boolean))];
        setAvailableStyles(styles.sort());
      } catch (err) {
        console.error('Error fetching wagon wheel data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchWagonData();
  }, [playerName, startDate, endDate, venue, leagues, includeInternational, topTeams, phase, bowlKind, bowlStyle]);

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
      strikeRate: deliveries.length > 0 ? ((totalRuns / deliveries.length) * 100).toFixed(1) : 0,
      boundaryPercentage: deliveries.length > 0 ? ((boundaries / deliveries.length) * 100).toFixed(1) : 0,
      byZone
    };
  }, [wagonData]);

  // SVG rendering - cricket field with wagon wheel
  const renderWagonWheel = () => {
    if (!wagonData || !stats) return null;

    const width = 400;
    const height = 400;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = 180;

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
          stroke="#e0e0e0"
          strokeWidth="1"
          strokeDasharray="4,4"
        />
      );
    }

    // Plot deliveries
    const deliveryDots = wagonData.deliveries
      .filter(d => d.wagon_x !== null && d.wagon_y !== null)
      .map((delivery, idx) => {
        // Scale coordinates to fit in our SVG (assuming wagon_x/y are in range 0-300)
        const scale = maxRadius / 300;
        const x = centerX + (delivery.wagon_x - 150) * scale;
        const y = centerY + (delivery.wagon_y - 150) * scale;

        // Color by runs
        let color = '#9e9e9e'; // dots
        let radius = 2;
        if (delivery.runs === 6) {
          color = '#e91e63'; // sixes - pink
          radius = 4;
        } else if (delivery.runs === 4) {
          color = '#2196f3'; // fours - blue
          radius = 3;
        } else if (delivery.runs > 0) {
          color = '#4caf50'; // runs - green
          radius = 2.5;
        }

        return (
          <circle
            key={`delivery-${idx}`}
            cx={x}
            cy={y}
            r={radius}
            fill={color}
            fillOpacity={0.6}
            stroke={color}
            strokeWidth="0.5"
          />
        );
      });

    return (
      <svg width={width} height={height} style={{ maxWidth: '100%', height: 'auto' }}>
        {/* Field boundary */}
        <circle
          cx={centerX}
          cy={centerY}
          r={maxRadius}
          fill="#f5f5f5"
          stroke="#bdbdbd"
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
          stroke="#e0e0e0"
          strokeWidth="1"
          strokeDasharray="4,4"
        />

        {/* Pitch */}
        <rect
          x={centerX - 5}
          y={centerY - 30}
          width={10}
          height={60}
          fill="#d4a574"
          stroke="#8d6e63"
          strokeWidth="1"
        />

        {/* Stumps */}
        <circle cx={centerX} cy={centerY} r={3} fill="#8d6e63" />

        {/* Deliveries */}
        {deliveryDots}

        {/* Zone labels */}
        <text x={centerX} y={centerY - maxRadius - 10} textAnchor="middle" fontSize="11" fill="#666">Straight</text>
        <text x={centerX + maxRadius + 10} y={centerY + 5} textAnchor="start" fontSize="11" fill="#666">Off</text>
        <text x={centerX - maxRadius - 10} y={centerY + 5} textAnchor="end" fontSize="11" fill="#666">Leg</text>
        <text x={centerX} y={centerY + maxRadius + 20} textAnchor="middle" fontSize="11" fill="#666">Behind</text>
      </svg>
    );
  };

  if (loading) {
    return (
      <Paper elevation={2} sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading wagon wheel data...</Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper elevation={2} sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (!wagonData || wagonData.total_deliveries === 0) {
    return (
      <Paper elevation={2} sx={{ p: 3 }}>
        <Alert severity="info">No wagon wheel data available for the selected filters.</Alert>
      </Paper>
    );
  }

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Wagon Wheel
      </Typography>

      {/* Filters */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
        {/* Phase Filter */}
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Phase</InputLabel>
          <Select value={phase} label="Phase" onChange={(e) => setPhase(e.target.value)}>
            <MenuItem value="overall">Overall</MenuItem>
            <MenuItem value="powerplay">Powerplay (0-5)</MenuItem>
            <MenuItem value="middle">Middle (6-14)</MenuItem>
            <MenuItem value="death">Death (15+)</MenuItem>
          </Select>
        </FormControl>

        {/* Bowl Kind Filter */}
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Bowl Kind</InputLabel>
          <Select value={bowlKind} label="Bowl Kind" onChange={(e) => setBowlKind(e.target.value)}>
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="pace bowler">Pace</MenuItem>
            <MenuItem value="spin bowler">Spin</MenuItem>
          </Select>
        </FormControl>

        {/* Bowl Style Filter */}
        {availableStyles.length > 0 && (
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Bowl Style</InputLabel>
            <Select value={bowlStyle} label="Bowl Style" onChange={(e) => setBowlStyle(e.target.value)}>
              <MenuItem value="all">All</MenuItem>
              {availableStyles.map(style => (
                <MenuItem key={style} value={style}>{style}</MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Box>

      {/* Stats Summary */}
      <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
        <Chip label={`${stats.totalBalls} balls`} size="small" />
        <Chip label={`${stats.totalRuns} runs`} size="small" color="primary" />
        <Chip label={`SR: ${stats.strikeRate}`} size="small" />
        <Chip label={`${stats.fours} x 4s`} size="small" sx={{ bgcolor: '#2196f3', color: 'white' }} />
        <Chip label={`${stats.sixes} x 6s`} size="small" sx={{ bgcolor: '#e91e63', color: 'white' }} />
        <Chip label={`${stats.boundaryPercentage}% boundaries`} size="small" />
      </Box>

      {/* Legend */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', fontSize: '0.875rem' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#e91e63' }} />
          <Typography variant="caption">Sixes</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#2196f3' }} />
          <Typography variant="caption">Fours</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#4caf50' }} />
          <Typography variant="caption">Runs</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#9e9e9e' }} />
          <Typography variant="caption">Dots</Typography>
        </Box>
      </Box>

      {/* Wagon Wheel Visualization */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
        {renderWagonWheel()}
      </Box>

      {/* Zone Statistics */}
      {Object.keys(stats.byZone).length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Scoring by Zone
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 1 }}>
            {Object.entries(stats.byZone)
              .sort(([a], [b]) => parseInt(a) - parseInt(b))
              .map(([zone, data]) => (
                <Box key={zone} sx={{ p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                  <Typography variant="caption" display="block" fontWeight="bold">
                    {ZONE_LABELS[zone] || `Zone ${zone}`}
                  </Typography>
                  <Typography variant="caption" display="block">
                    {data.runs} runs ({data.count} balls)
                  </Typography>
                  {data.boundaries > 0 && (
                    <Typography variant="caption" display="block" color="primary">
                      {data.boundaries} boundaries
                    </Typography>
                  )}
                </Box>
              ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default WagonWheel;
