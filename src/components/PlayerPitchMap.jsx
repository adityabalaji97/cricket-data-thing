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
  Chip
} from '@mui/material';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { AlertBanner, EmptyState } from './ui';
import { PitchMapVisualization } from './PitchMap';
import config from '../config';
import { colors as designColors } from '../theme/designSystem';

const PlayerPitchMap = ({
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
  const [pitchData, setPitchData] = useState(null);
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
      <Wrapper {...wrapperProps}>
        <Box sx={{ textAlign: 'center', py: 3 }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Loading pitch map data...</Typography>
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

  if (!pitchData || pitchData.total_balls === 0) {
    return (
      <Wrapper {...wrapperProps}>
        <EmptyState
          title="No innings match these filters"
          description="No pitch map data is available for the selected filters."
          isMobile={isCompact}
          minHeight={isCompact ? 280 : 320}
        />
      </Wrapper>
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
          Pitch Map
        </Typography>
        <Box sx={{ flexShrink: 1, minWidth: 0 }}>
          <FilterBar
            filters={filterConfig}
            activeFilters={{ phase, bowlKind, line, length, shot }}
            onFilterChange={handleFilterChange}
            isMobile={isCompact}
          />
        </Box>
      </Box>

      {/* Stats Summary */}
      <Box sx={{ display: 'flex', gap: isCompact ? 0.5 : 1, mb: isCompact ? 1.5 : 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Chip label={`${pitchData.total_balls} balls`} size="small" sx={{ bgcolor: designColors.chart.blue, color: 'white', fontSize: isCompact ? '0.7rem' : undefined, height: isCompact ? 24 : undefined }} />
      </Box>

      {/* Pitch Map Visualization */}
      <Box
        sx={{
          maxWidth: isCompact ? 360 : 420,
          mx: 'auto',
          width: '100%',
          overflow: 'hidden'
        }}
      >
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
          hideLegend={true}
          compactMode={isCompact}
        />
      </Box>
    </Wrapper>
  );
};

export default PlayerPitchMap;
