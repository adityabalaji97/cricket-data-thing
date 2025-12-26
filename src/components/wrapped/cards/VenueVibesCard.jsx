import React from 'react';
import { Box, Typography } from '@mui/material';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
const VenueVibesCard = ({ data }) => {

  if (!data.venues || data.venues.length === 0) {
    return <Typography>No venue data available</Typography>;
  }

  const handleVenueClick = (venue) => {
    const url = `/venue?venue=${encodeURIComponent(venue.name)}&start_date=2025-01-01&end_date=2025-12-31`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Calculate average for reference lines
  const avgPar = data.venues.reduce((sum, v) => sum + v.par_score, 0) / data.venues.length;

  // Categorize venues
  const highScoring = data.venues.filter(v => v.par_score > avgPar);
  const chaseFriendly = data.venues.filter(v => v.chase_win_pct > 55);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const venue = payload[0].payload;
      return (
        <Box className="wrapped-tooltip">
          <Typography variant="subtitle2">{venue.name.split(',')[0]}</Typography>
          <Typography variant="body2">Par Score: {venue.par_score}</Typography>
          <Typography variant="body2">Chase Win%: {venue.chase_win_pct}%</Typography>
          <Typography variant="body2">Matches: {venue.matches}</Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Box className="venue-card-content">
      {/* Quick Stats */}
      <Box className="venue-quick-stats">
        <Box className="venue-stat">
          <Typography variant="h5">{highScoring.length}</Typography>
          <Typography variant="caption">High-Scoring</Typography>
        </Box>
        <Box className="venue-stat">
          <Typography variant="h5">{chaseFriendly.length}</Typography>
          <Typography variant="caption">Chase-Friendly</Typography>
        </Box>
      </Box>

      {/* Scatter Plot */}
      <Box className="venue-scatter">
        <ResponsiveContainer width="100%" height={160}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis 
              type="number" 
              dataKey="par_score" 
              name="Par Score"
              domain={['dataMin - 10', 'dataMax + 10']}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Par Score', position: 'bottom', fontSize: 10, fill: '#b3b3b3' }}
            />
            <YAxis 
              type="number" 
              dataKey="chase_win_pct" 
              name="Chase Win %"
              domain={[30, 70]}
              tick={{ fontSize: 10, fill: '#b3b3b3' }}
              label={{ value: 'Chase %', angle: -90, position: 'left', fontSize: 10, fill: '#b3b3b3' }}
            />
            <ReferenceLine y={50} stroke="#666" strokeDasharray="3 3" />
            <ReferenceLine x={avgPar} stroke="#666" strokeDasharray="3 3" />
            <Tooltip content={<CustomTooltip />} />
            <Scatter 
              data={data.venues} 
              cursor="pointer"
            >
              {data.venues.map((entry, index) => (
                <Cell 
                  key={index} 
                  fill={entry.chase_win_pct > 55 ? '#4CAF50' : entry.chase_win_pct < 45 ? '#f44336' : '#2196F3'}
                  opacity={0.8}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </Box>

      {/* Top Venues List */}
      <Box className="top-venues">
        {data.venues.slice(0, 3).map((venue) => (
          <Box 
            key={venue.name} 
            className="venue-item"
            onClick={(e) => {
              e.stopPropagation();
              handleVenueClick(venue);
            }}
          >
            <Typography variant="body2" className="venue-name">
              {venue.name.split(',')[0]}
            </Typography>
            <Typography variant="caption">
              Par: {venue.par_score} | Chase: {venue.chase_win_pct}%
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default VenueVibesCard;
