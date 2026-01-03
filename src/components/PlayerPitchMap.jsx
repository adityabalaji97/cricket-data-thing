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
  topTeams = null,
  isMobile = false
}) => {
  const [pitchData, setPitchData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [phase, setPhase] = useState('overall');
  const [bowlKind, setBowlKind] = useState('all');
  const [bowlStyle, setBowlStyle] = useState('all');
  const [line, setLine] = useState('all');
  const [length, setLength] = useState('all');
  const [shot, setShot] = useState('all');

  // Available options from data
  const [availableStyles, setAvailableStyles] = useState([]);
  const [availableLines, setAvailableLines] = useState([]);
  const [availableLengths, setAvailableLengths] = useState([]);
  const [availableShots, setAvailableShots] = useState([]);

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
      if (line !== 'all') params.append('line', line);
      if (length !== 'all') params.append('length', length);
      if (shot !== 'all') params.append('shot', shot);

      try {
        const response = await fetch(
          `${config.API_URL}/visualizations/player/${encodeURIComponent(playerName)}/pitch-map?${params}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch pitch map data');
        }

        const data = await response.json();
        setPitchData(data);

        // Get unique values by fetching wagon wheel data
        // (pitch map aggregates, so we need raw data for filter options)
        const wagonResponse = await fetch(
          `${config.API_URL}/visualizations/player/${encodeURIComponent(playerName)}/wagon-wheel?${params}`
        );
        if (wagonResponse.ok) {
          const wagonData = await wagonResponse.json();
          const styles = [...new Set(wagonData.deliveries.map(d => d.bowl_style).filter(Boolean))];
          setAvailableStyles(styles.sort());

          const lines = [...new Set(wagonData.deliveries.map(d => d.line).filter(Boolean))];
          setAvailableLines(lines.sort());

          const lengths = [...new Set(wagonData.deliveries.map(d => d.length).filter(Boolean))];
          setAvailableLengths(lengths.sort());

          const shots = [...new Set(wagonData.deliveries.map(d => d.shot).filter(Boolean))];
          setAvailableShots(shots.sort());
        }
      } catch (err) {
        console.error('Error fetching pitch map data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPitchData();
  }, [playerName, startDate, endDate, venue, leagues, includeInternational, topTeams, phase, bowlKind, bowlStyle, line, length, shot]);

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
    <Box sx={{
      width: '100%',
      px: isMobile ? 0 : 1,
      backgroundColor: isMobile ? 'transparent' : undefined,
      boxShadow: isMobile ? 0 : undefined
    }}>
      <Typography variant={isMobile ? "body1" : "h6"} gutterBottom sx={{ textAlign: 'center', fontWeight: 600, fontSize: isMobile ? '0.875rem' : undefined }}>
        Pitch Map
      </Typography>

      {/* Filters */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: isMobile ? 1 : 1.5, mb: 2, justifyContent: 'center' }}>
        {/* Phase Filter */}
        <FormControl size="small" sx={{ minWidth: isMobile ? 90 : 120 }}>
          <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Phase</InputLabel>
          <Select value={phase} label="Phase" onChange={(e) => setPhase(e.target.value)} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>
            <MenuItem value="overall" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Overall</MenuItem>
            <MenuItem value="powerplay" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>{isMobile ? 'PP' : 'Powerplay'}</MenuItem>
            <MenuItem value="middle" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Middle</MenuItem>
            <MenuItem value="death" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Death</MenuItem>
          </Select>
        </FormControl>

        {/* Bowl Kind Filter */}
        <FormControl size="small" sx={{ minWidth: isMobile ? 90 : 120 }}>
          <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Bowl</InputLabel>
          <Select value={bowlKind} label="Bowl" onChange={(e) => setBowlKind(e.target.value)} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>
            <MenuItem value="all" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>All</MenuItem>
            <MenuItem value="pace bowler" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Pace</MenuItem>
            <MenuItem value="spin bowler" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Spin</MenuItem>
          </Select>
        </FormControl>

        {/* Line Filter */}
        {availableLines.length > 0 && (
          <FormControl size="small" sx={{ minWidth: isMobile ? 90 : 120 }}>
            <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Line</InputLabel>
            <Select value={line} label="Line" onChange={(e) => setLine(e.target.value)} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>
              <MenuItem value="all" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>All</MenuItem>
              {availableLines.map(l => (
                <MenuItem key={l} value={l} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>{l}</MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        {/* Length Filter */}
        {availableLengths.length > 0 && (
          <FormControl size="small" sx={{ minWidth: isMobile ? 90 : 120 }}>
            <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Length</InputLabel>
            <Select value={length} label="Length" onChange={(e) => setLength(e.target.value)} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>
              <MenuItem value="all" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>All</MenuItem>
              {availableLengths.map(len => (
                <MenuItem key={len} value={len} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>{len}</MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        {/* Shot Filter */}
        {availableShots.length > 0 && (
          <FormControl size="small" sx={{ minWidth: isMobile ? 90 : 120 }}>
            <InputLabel sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>Shot</InputLabel>
            <Select value={shot} label="Shot" onChange={(e) => setShot(e.target.value)} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>
              <MenuItem value="all" sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>All</MenuItem>
              {availableShots.map(s => (
                <MenuItem key={s} value={s} sx={{ fontSize: isMobile ? '0.75rem' : undefined }}>{s}</MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Box>

      {/* Stats Summary */}
      <Box sx={{ display: 'flex', gap: isMobile ? 0.5 : 1, mb: isMobile ? 1.5 : 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Chip label={`${pitchData.total_balls} balls`} size="small" color="primary" sx={{ fontSize: isMobile ? '0.7rem' : undefined, height: isMobile ? 24 : undefined }} />
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
