/**
 * PlayerPitchMap Component
 *
 * Wrapper for PitchMapContainer that fetches data from the API
 * and provides filtering options for phase, bowling kind, and bowling style.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Chip
} from '@mui/material';
import { PitchMapVisualization } from './PitchMap';
import config from '../config';

const PlayerPitchMap = ({
  playerName,
  startDate,
  endDate,
  venue,
  leagues = [],
  includeInternational = false,
  topTeams = null
}) => {
  const [pitchData, setPitchData] = useState(null);
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

    const fetchPitchData = async () => {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (venue) params.append('venue', venue);

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
          `${config.API_URL}/visualizations/player/${encodeURIComponent(playerName)}/pitch-map?${params}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch pitch map data');
        }

        const data = await response.json();
        setPitchData(data);

        // Get unique bowling styles by fetching wagon wheel data
        // (pitch map aggregates, so we need raw data for styles)
        const wagonResponse = await fetch(
          `${config.API_URL}/visualizations/player/${encodeURIComponent(playerName)}/wagon-wheel?${params}`
        );
        if (wagonResponse.ok) {
          const wagonData = await wagonResponse.json();
          const styles = [...new Set(wagonData.deliveries.map(d => d.bowl_style).filter(Boolean))];
          setAvailableStyles(styles.sort());
        }
      } catch (err) {
        console.error('Error fetching pitch map data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPitchData();
  }, [playerName, startDate, endDate, venue, leagues, includeInternational, topTeams, phase, bowlKind, bowlStyle]);

  if (loading) {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading pitch map data...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ py: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!pitchData || pitchData.total_balls === 0) {
    return (
      <Box sx={{ py: 2 }}>
        <Alert severity="info">No pitch map data available for the selected filters.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h6" gutterBottom sx={{ textAlign: 'center' }}>
        Pitch Map
      </Typography>

      {/* Filters */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2, justifyContent: 'center' }}>
        {/* Phase Filter */}
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Phase</InputLabel>
          <Select value={phase} label="Phase" onChange={(e) => setPhase(e.target.value)}>
            <MenuItem value="overall">Overall</MenuItem>
            <MenuItem value="powerplay">Powerplay</MenuItem>
            <MenuItem value="middle">Middle</MenuItem>
            <MenuItem value="death">Death</MenuItem>
          </Select>
        </FormControl>

        {/* Bowl Kind Filter */}
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Bowl Kind</InputLabel>
          <Select value={bowlKind} label="Bowl Kind" onChange={(e) => setBowlKind(e.target.value)}>
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="pace bowler">Pace</MenuItem>
            <MenuItem value="spin bowler">Spin</MenuItem>
          </Select>
        </FormControl>

        {/* Bowl Style Filter */}
        {availableStyles.length > 0 && (
          <FormControl size="small" sx={{ minWidth: 120 }}>
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
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Chip label={`${pitchData.total_balls} balls`} size="small" color="primary" />
      </Box>

      {/* Pitch Map Visualization */}
      <Box sx={{ maxWidth: 420, mx: 'auto' }}>
        <PitchMapVisualization
          cells={pitchData.cells}
          mode="grid"
          colorMetric="strike_rate"
          displayMetrics={['average', 'strike_rate']}
          secondaryMetrics={['dot_percentage', 'boundary_percentage']}
          minBalls={5}
          title={playerName}
          subtitle={`${phase === 'overall' ? 'All Phases' : phase} ${bowlKind !== 'all' ? `• ${bowlKind}` : ''}`}
          hideStumps={true}
        />
      </Box>
    </Box>
  );
};

export default PlayerPitchMap;
