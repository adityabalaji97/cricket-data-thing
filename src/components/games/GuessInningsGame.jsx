/**
 * Guess the Innings Game
 *
 * Mobile-first wagon wheel game - guess the batter from their shot pattern.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  IconButton,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import ReplayIcon from '@mui/icons-material/Replay';
import config from '../../config';
import { colors as designColors } from '../../theme/designSystem';

const DEFAULT_FILTERS = {
  leagues: 'IPL',
  competitions: '',
  startDate: '2015-01-01',
  endDate: '',
  poolLimit: 1000,
  minRuns: 0,
  minBalls: 30,
  minStrikeRate: 150,
};

const runColor = (runs) => {
  if (runs === 6) return designColors.chart.orange;
  if (runs === 4) return designColors.chart.green;
  if (runs === 3) return designColors.primary[500];
  if (runs === 2) return designColors.primary[400];
  if (runs === 1) return designColors.primary[300];
  return designColors.neutral[400];
};

const LEGEND_ITEMS = [
  { label: '6', runs: 6 },
  { label: '4', runs: 4 },
  { label: '3', runs: 3 },
  { label: '2', runs: 2 },
  { label: '1', runs: 1 },
  { label: '0', runs: 0 },
];

const GuessInningsGame = ({ isMobile = false }) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [showFilters, setShowFilters] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [guess, setGuess] = useState('');
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [containerSize, setContainerSize] = useState(320);
  const chartContainerRef = useRef(null);
  const playTimerRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const resizeObserver = new ResizeObserver(entries => {
      entries.forEach(entry => {
        const nextWidth = Math.max(280, Math.floor(entry.contentRect.width));
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
    }, 300);
    return () => clearInterval(playTimerRef.current);
  }, [isPlaying, data]);

  const deliveries = useMemo(() => data?.deliveries || [], [data]);
  const validDeliveries = useMemo(() =>
    deliveries.filter(d => d.wagon_x !== null && d.wagon_y !== null && d.wagon_x !== 0 && d.wagon_y !== 0),
    [deliveries]
  );
  const visibleDeliveries = useMemo(() =>
    validDeliveries.slice(0, visibleCount),
    [validDeliveries, visibleCount]
  );
  const answer = data?.answer?.batter || '';
  const normalizedGuess = guess.trim().toLowerCase();
  const isCorrect = answer && normalizedGuess && answer.trim().toLowerCase() === normalizedGuess;

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
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch innings');
      }
      const payload = await response.json();
      setData(payload);
      // Auto-start playback
      setIsPlaying(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderWagonWheel = () => {
    if (!data) return null;
    const size = Math.min(containerSize, 360);
    const width = size;
    const height = size;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = width * 0.42;
    const batterRadius = width * 0.025;

    // Zone divider lines
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
          strokeDasharray="3,3"
        />
      );
    }

    // Delivery lines - normalized to circle radius
    const deliveryLines = visibleDeliveries.map((delivery, index) => {
      // Calculate direction from center
      const dx = delivery.wagon_x - 150;
      const dy = delivery.wagon_y - 150;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance === 0) return null;

      // Normalize to maxRadius (all lines extend to the edge)
      const normalizedX = centerX + (dx / distance) * maxRadius;
      const normalizedY = centerY + (dy / distance) * maxRadius;

      const isLatest = index === visibleDeliveries.length - 1;

      return (
        <g key={`delivery-${index}`}>
          <line
            x1={centerX}
            y1={centerY}
            x2={normalizedX}
            y2={normalizedY}
            stroke={runColor(delivery.runs)}
            strokeWidth={isLatest ? 3 : 2}
            opacity={isLatest ? 1 : 0.55}
            strokeLinecap="round"
          />
          <circle
            cx={normalizedX}
            cy={normalizedY}
            r={isLatest ? 6 : 4}
            fill={runColor(delivery.runs)}
            stroke={isLatest ? designColors.neutral[900] : 'none'}
            strokeWidth={isLatest ? 2 : 0}
          />
        </g>
      );
    });

    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <circle cx={centerX} cy={centerY} r={maxRadius} fill={designColors.neutral[100]} stroke={designColors.neutral[300]} strokeWidth="2" />
        {zoneLines}
        {deliveryLines}
        <circle cx={centerX} cy={centerY} r={batterRadius} fill={designColors.neutral[800]} />
      </svg>
    );
  };

  const renderLegend = () => (
    <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" sx={{ gap: 0.5 }}>
      {LEGEND_ITEMS.map(item => (
        <Box key={item.label} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            bgcolor: runColor(item.runs),
          }} />
          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: designColors.neutral[600] }}>
            {item.label}
          </Typography>
        </Box>
      ))}
    </Stack>
  );

  // Mobile-optimized compact layout
  return (
    <Box sx={{ py: 1, px: isMobile ? 1 : 2 }}>
      {/* Header with New Game button */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600 }}>
          Guess the Innings
        </Typography>
        <Stack direction="row" spacing={1}>
          <IconButton size="small" onClick={() => setShowFilters(!showFilters)}>
            <SettingsIcon fontSize="small" />
          </IconButton>
          <Button
            variant="contained"
            size="small"
            onClick={fetchGame}
            disabled={loading}
            sx={{ minWidth: 100 }}
          >
            {loading ? 'Loading...' : data ? 'New Game' : 'Start'}
          </Button>
        </Stack>
      </Stack>

      {/* Collapsible Filters */}
      <Collapse in={showFilters}>
        <Box sx={{ mb: 2, p: 1.5, bgcolor: designColors.neutral[50], borderRadius: 1 }}>
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={1}>
              <TextField
                label="Leagues"
                value={filters.leagues}
                onChange={(e) => setFilters(prev => ({ ...prev, leagues: e.target.value }))}
                size="small"
                fullWidth
              />
              <TextField
                label="Min SR"
                type="number"
                value={filters.minStrikeRate}
                onChange={(e) => setFilters(prev => ({ ...prev, minStrikeRate: Number(e.target.value) }))}
                size="small"
                sx={{ width: 100 }}
              />
            </Stack>
            <Stack direction="row" spacing={1}>
              <TextField
                label="Min Balls"
                type="number"
                value={filters.minBalls}
                onChange={(e) => setFilters(prev => ({ ...prev, minBalls: Number(e.target.value) }))}
                size="small"
                sx={{ width: 100 }}
              />
              <TextField
                label="Start Date"
                type="date"
                value={filters.startDate}
                onChange={(e) => setFilters(prev => ({ ...prev, startDate: e.target.value }))}
                InputLabelProps={{ shrink: true }}
                size="small"
                fullWidth
              />
            </Stack>
          </Stack>
        </Box>
      </Collapse>

      {error && (
        <Typography variant="body2" color="error" sx={{ mb: 1, textAlign: 'center' }}>
          {error}
        </Typography>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={32} />
        </Box>
      )}

      {data && !loading && (
        <Stack spacing={1.5}>
          {/* Info Pills */}
          <Stack direction="row" spacing={0.5} flexWrap="wrap" justifyContent="center" sx={{ gap: 0.5 }}>
            <Chip
              label={`${visibleCount}/${validDeliveries.length} balls`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`${data.innings?.runs} runs`}
              size="small"
              sx={{ bgcolor: designColors.primary[50] }}
            />
            <Chip
              label={`SR ${data.innings?.strike_rate?.toFixed?.(0) ?? data.innings?.strike_rate}`}
              size="small"
              sx={{ bgcolor: designColors.chart.green + '20' }}
            />
            <Chip
              label={data.innings?.competition}
              size="small"
              variant="outlined"
            />
          </Stack>

          {/* Wagon Wheel */}
          <Box
            ref={chartContainerRef}
            sx={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              py: 1
            }}
          >
            {renderWagonWheel()}
          </Box>

          {/* Legend */}
          {renderLegend()}

          {/* Playback Controls */}
          <Stack direction="row" spacing={1} justifyContent="center">
            <IconButton
              onClick={() => setIsPlaying(!isPlaying)}
              disabled={visibleCount >= validDeliveries.length}
              sx={{ bgcolor: designColors.primary[50] }}
            >
              {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>
            <IconButton
              onClick={() => setVisibleCount(prev => Math.min(prev + 1, validDeliveries.length))}
              disabled={visibleCount >= validDeliveries.length}
            >
              <SkipNextIcon />
            </IconButton>
            <IconButton onClick={() => { setVisibleCount(0); setIsPlaying(false); }}>
              <ReplayIcon />
            </IconButton>
          </Stack>

          {/* Guess Input */}
          <Stack direction="row" spacing={1} alignItems="center">
            <TextField
              placeholder="Who is this batter?"
              value={guess}
              onChange={(e) => setGuess(e.target.value)}
              size="small"
              fullWidth
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: isCorrect ? designColors.success[50] : 'white'
                }
              }}
            />
            <Button
              variant="outlined"
              size="small"
              onClick={() => setRevealAnswer(true)}
              sx={{ minWidth: 80 }}
            >
              Reveal
            </Button>
          </Stack>

          {isCorrect && (
            <Typography variant="body2" sx={{ color: designColors.success[600], textAlign: 'center', fontWeight: 600 }}>
              Correct!
            </Typography>
          )}

          {revealAnswer && (
            <Typography variant="body1" sx={{ textAlign: 'center' }}>
              Answer: <strong>{answer}</strong>
            </Typography>
          )}

          {/* Match Info (smaller) */}
          <Typography variant="caption" sx={{ textAlign: 'center', color: designColors.neutral[500] }}>
            {data.innings?.venue} • {data.innings?.match_date}
          </Typography>
        </Stack>
      )}

      {/* Initial state prompt */}
      {!data && !loading && !error && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" color="text.secondary">
            Click Start to begin!
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default GuessInningsGame;
