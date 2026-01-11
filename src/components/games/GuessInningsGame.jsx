/**
 * Guess the Innings Game
 *
 * Fetches a random innings with wagon wheel data and animates shots chronologically.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import Card from '../ui/Card';
import config from '../../config';
import { colors as designColors } from '../../theme/designSystem';

const DEFAULT_FILTERS = {
  leagues: 'IPL',
  competitions: '',
  startDate: '2015-01-01',
  endDate: '',
  poolLimit: 1000,
  minRuns: 0,
  minBalls: 0,
  minStrikeRate: 0,
};

const runColor = (runs) => {
  if (runs === 6) return designColors.orange[500];
  if (runs === 4) return designColors.green[500];
  if (runs === 3) return designColors.blue[400];
  if (runs === 2) return designColors.blue[300];
  if (runs === 1) return designColors.blue[200];
  return designColors.neutral[300];
};

const GuessInningsGame = ({ isMobile = false }) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [guess, setGuess] = useState('');
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [containerSize, setContainerSize] = useState(360);
  const chartContainerRef = useRef(null);
  const playTimerRef = useRef(null);

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
    if (!isPlaying || !data) return;
    playTimerRef.current = setInterval(() => {
      setVisibleCount((prev) => {
        if (!data?.deliveries) return prev;
        if (prev >= data.deliveries.length) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 350);
    return () => clearInterval(playTimerRef.current);
  }, [isPlaying, data]);

  const deliveries = useMemo(() => data?.deliveries || [], [data]);
  const visibleDeliveries = useMemo(() => deliveries.slice(0, visibleCount), [deliveries, visibleCount]);
  const answer = data?.answer?.batter || '';
  const normalizedGuess = guess.trim().toLowerCase();
  const isCorrect = answer && normalizedGuess && answer.trim().toLowerCase() === normalizedGuess;

  const resetPlayback = () => {
    setVisibleCount(0);
    setIsPlaying(false);
  };

  const fetchGame = async () => {
    setLoading(true);
    setError(null);
    setRevealAnswer(false);
    setGuess('');
    setVisibleCount(0);
    setIsPlaying(false);

    const params = new URLSearchParams();
    const leagues = filters.leagues.split(',').map(item => item.trim()).filter(Boolean);
    leagues.forEach(league => params.append('leagues', league));
    const competitions = filters.competitions.split(',').map(item => item.trim()).filter(Boolean);
    competitions.forEach(competition => params.append('competitions', competition));
    if (filters.startDate) params.append('start_date', filters.startDate);
    if (filters.endDate) params.append('end_date', filters.endDate);
    params.append('pool_limit', filters.poolLimit);
    params.append('min_runs', filters.minRuns);
    params.append('min_balls', filters.minBalls);
    params.append('min_strike_rate', filters.minStrikeRate);
    params.append('include_answer', 'true');

    try {
      const response = await fetch(`${config.API_URL}/games/guess-innings?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to fetch innings');
      }
      const payload = await response.json();
      setData(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderWagonWheel = () => {
    if (!data) return null;
    const width = Math.min(containerSize, isMobile ? 320 : 420);
    const height = width;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = width * 0.4;
    const batterRadius = width * 0.02;
    const zoneLines = [];
    for (let i = 0; i < 8; i++) {
      const angle = (i * Math.PI / 4) - (Math.PI / 2);
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

    const deliveryDots = visibleDeliveries
      .filter(d => d.wagon_x !== null && d.wagon_y !== null)
      .map((delivery, index) => {
        const scale = maxRadius / 150;
        const x = centerX + (delivery.wagon_x - 150) * scale;
        const y = centerY + (delivery.wagon_y - 150) * scale;
        const isLatest = index === visibleDeliveries.length - 1;
        return (
          <circle
            key={`delivery-${index}`}
            cx={x}
            cy={y}
            r={isLatest ? 5 : 3.5}
            fill={runColor(delivery.runs)}
            stroke={isLatest ? designColors.neutral[900] : designColors.neutral[50]}
            strokeWidth={isLatest ? 2 : 1}
            opacity={isLatest ? 1 : 0.75}
          />
        );
      });

    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <circle cx={centerX} cy={centerY} r={maxRadius} fill={designColors.neutral[50]} stroke={designColors.neutral[200]} />
        {zoneLines}
        <circle cx={centerX} cy={centerY} r={batterRadius} fill={designColors.neutral[800]} />
        {deliveryDots}
      </svg>
    );
  };

  return (
    <Box sx={{ my: 3 }}>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Guess the Innings (MVP)
      </Typography>
      <Typography variant="body1" sx={{ mb: 3 }}>
        Watch the wagon wheel animation and guess the batter. Filters are configurable for league and innings pool selection.
      </Typography>

      <Card sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Game Filters</Typography>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
          <TextField
            label="Leagues (comma-separated)"
            value={filters.leagues}
            onChange={(event) => setFilters(prev => ({ ...prev, leagues: event.target.value }))}
            fullWidth
          />
          <TextField
            label="Competitions (override leagues)"
            value={filters.competitions}
            onChange={(event) => setFilters(prev => ({ ...prev, competitions: event.target.value }))}
            fullWidth
          />
        </Stack>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
          <TextField
            label="Start Date"
            type="date"
            value={filters.startDate}
            onChange={(event) => setFilters(prev => ({ ...prev, startDate: event.target.value }))}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="End Date"
            type="date"
            value={filters.endDate}
            onChange={(event) => setFilters(prev => ({ ...prev, endDate: event.target.value }))}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
        </Stack>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
          <TextField
            label="Pool Limit (top N by runs/balls/SR)"
            type="number"
            value={filters.poolLimit}
            onChange={(event) => setFilters(prev => ({ ...prev, poolLimit: Number(event.target.value) }))}
            fullWidth
          />
          <TextField
            label="Min Runs"
            type="number"
            value={filters.minRuns}
            onChange={(event) => setFilters(prev => ({ ...prev, minRuns: Number(event.target.value) }))}
            fullWidth
          />
          <TextField
            label="Min Balls"
            type="number"
            value={filters.minBalls}
            onChange={(event) => setFilters(prev => ({ ...prev, minBalls: Number(event.target.value) }))}
            fullWidth
          />
          <TextField
            label="Min Strike Rate"
            type="number"
            value={filters.minStrikeRate}
            onChange={(event) => setFilters(prev => ({ ...prev, minStrikeRate: Number(event.target.value) }))}
            fullWidth
          />
        </Stack>
        <Button variant="contained" onClick={fetchGame} disabled={loading}>
          {loading ? 'Loading...' : 'Start New Game'}
        </Button>
        {error && (
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            {error}
          </Typography>
        )}
      </Card>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {data && !loading && (
        <Card>
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              <Chip label={`Balls shown: ${visibleCount}/${deliveries.length}`} />
              <Chip label={`Runs: ${data.innings?.runs}`} />
              <Chip label={`SR: ${data.innings?.strike_rate?.toFixed?.(1) ?? data.innings?.strike_rate}`} />
              <Chip label={`Competition: ${data.innings?.competition}`} />
              <Chip label={`Date: ${data.innings?.match_date}`} />
              <Chip label={`Venue: ${data.innings?.venue}`} />
            </Box>

            <Divider />

            <Box ref={chartContainerRef} sx={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
              {renderWagonWheel()}
            </Box>

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
              <Button variant="outlined" onClick={() => setIsPlaying((prev) => !prev)} disabled={visibleCount >= deliveries.length}>
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              <Button variant="outlined" onClick={() => setVisibleCount((prev) => Math.min(prev + 1, deliveries.length))}>
                Next Shot
              </Button>
              <Button variant="outlined" onClick={resetPlayback}>
                Reset
              </Button>
            </Stack>

            <Divider />

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
              <TextField
                label="Your Guess (Batter)"
                value={guess}
                onChange={(event) => setGuess(event.target.value)}
                fullWidth
              />
              <Button variant="contained" onClick={() => setRevealAnswer(true)}>
                Reveal Answer
              </Button>
            </Stack>
            {guess && (
              <Typography variant="body2" color={isCorrect ? 'success.main' : 'text.secondary'}>
                {isCorrect ? 'Correct!' : 'Keep guessing...'}
              </Typography>
            )}
            {revealAnswer && (
              <Typography variant="body1">
                Answer: <strong>{answer}</strong>
              </Typography>
            )}
          </Stack>
        </Card>
      )}
    </Box>
  );
};

export default GuessInningsGame;
