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
  CircularProgress,
  Alert,
  Chip
} from '@mui/material';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
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

  // Filter configuration
  const filterConfig = [
    {
      key: 'phase',
      label: 'Phase',
      options: [
        { value: 'overall', label: 'Overall' },
        { value: 'powerplay', label: isMobile ? 'PP' : 'Powerplay' },
        { value: 'middle', label: 'Middle' },
        { value: 'death', label: 'Death' }
      ]
    },
    {
      key: 'bowlKind',
      label: 'Bowl',
      options: [
        { value: 'all', label: 'All' },
        { value: 'pace bowler', label: 'Pace' },
        { value: 'spin bowler', label: 'Spin' }
      ]
    }
  ];

  // Add line filter if data available
  if (availableLines.length > 0) {
    filterConfig.push({
      key: 'line',
      label: 'Line',
      options: [
        { value: 'all', label: 'All' },
        ...availableLines.map(l => ({ value: l, label: l }))
      ]
    });
  }

  // Add length filter if data available
  if (availableLengths.length > 0) {
    filterConfig.push({
      key: 'length',
      label: 'Length',
      options: [
        { value: 'all', label: 'All' },
        ...availableLengths.map(len => ({ value: len, label: len }))
      ]
    });
  }

  // Add shot filter if data available
  if (availableShots.length > 0) {
    filterConfig.push({
      key: 'shot',
      label: 'Shot',
      options: [
        { value: 'all', label: 'All' },
        ...availableShots.map(s => ({ value: s, label: s }))
      ]
    });
  }

  const handleFilterChange = (key, value) => {
    if (key === 'phase') setPhase(value);
    else if (key === 'bowlKind') setBowlKind(value);
    else if (key === 'line') setLine(value);
    else if (key === 'length') setLength(value);
    else if (key === 'shot') setShot(value);
  };

  return (
    <Card isMobile={isMobile}>
      <Typography variant={isMobile ? "h6" : "h5"} sx={{ mb: isMobile ? 1.5 : 2, fontWeight: 600 }}>
        Pitch Map
      </Typography>

      {/* Filters */}
      <Box sx={{ mb: 2 }}>
        <FilterBar
          filters={filterConfig}
          activeFilters={{ phase, bowlKind, line, length, shot }}
          onFilterChange={handleFilterChange}
          isMobile={isMobile}
        />
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
    </Card>
  );
};

export default PlayerPitchMap;
