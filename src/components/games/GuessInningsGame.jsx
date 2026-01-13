/**
 * Guess the Innings Game
 *
 * Mobile-first wagon wheel game - guess the batter from their shot pattern.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Collapse,
  ClickAwayListener,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
  InputAdornment
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import ReplayIcon from '@mui/icons-material/Replay';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';
import LightbulbOutlinedIcon from '@mui/icons-material/LightbulbOutlined';
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

const GAME_INSTRUCTIONS = [
  "Watch the wagon wheel animate ball-by-ball",
  "Lines show where shots were hit - longer = further",
  "4s and 6s always reach the edge of the circle",
  "Use the search to guess the batter's name",
  "Reveal the answer anytime if you're stuck!"
];

const GuessInningsGame = ({ isMobile = false }) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [showFilters, setShowFilters] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [guess, setGuess] = useState('');
  const [guessResult, setGuessResult] = useState(null); // 'correct', 'incorrect', null
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [containerSize, setContainerSize] = useState(320);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const chartContainerRef = useRef(null);
  const playTimerRef = useRef(null);
  const debounceRef = useRef(null);

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
    const totalDeliveries = data?.deliveries?.length || 0;
    playTimerRef.current = setInterval(() => {
      setVisibleCount((prev) => {
        if (prev >= totalDeliveries) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 300);
    return () => clearInterval(playTimerRef.current);
  }, [isPlaying, data]);

  // Search suggestions effect
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (guess.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const response = await fetch(`${config.API_URL}/search/suggestions?q=${encodeURIComponent(guess)}&limit=8`);
        if (response.ok) {
          const data = await response.json();
          // Filter to only show players
          const playerSuggestions = (data.suggestions || []).filter(s => s.type === 'player');
          setSuggestions(playerSuggestions);
          setShowSuggestions(playerSuggestions.length > 0);
        }
      } catch (error) {
        console.error('Search error:', error);
        setSuggestions([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [guess]);

  const deliveries = useMemo(() => data?.deliveries || [], [data]);
  // All deliveries up to visibleCount
  const visibleDeliveries = useMemo(() =>
    deliveries.slice(0, visibleCount),
    [deliveries, visibleCount]
  );
  // Only those with valid wagon coordinates for drawing
  const drawableDeliveries = useMemo(() =>
    visibleDeliveries.filter(d => d.wagon_x !== null && d.wagon_y !== null && d.wagon_x !== 0 && d.wagon_y !== 0),
    [visibleDeliveries]
  );
  const answer = data?.answer?.batter || '';

  const checkGuess = (selectedName) => {
    if (!answer) return;
    const normalizedAnswer = answer.trim().toLowerCase();
    const normalizedGuess = selectedName.trim().toLowerCase();

    // Check if it's a match (exact or contains the key part)
    if (normalizedAnswer === normalizedGuess ||
        normalizedAnswer.includes(normalizedGuess) ||
        normalizedGuess.includes(normalizedAnswer)) {
      setGuessResult('correct');
    } else {
      setGuessResult('incorrect');
    }
  };

  const handleSelectSuggestion = (item) => {
    const name = item.display_name || item.name;
    setGuess(name);
    setShowSuggestions(false);
    checkGuess(name);
  };

  const fetchGame = async () => {
    setLoading(true);
    setError(null);
    setRevealAnswer(false);
    setShowHint(false);
    setGuess('');
    setGuessResult(null);
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
    const size = Math.min(containerSize, 340);
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

    // Find max distance among non-boundary shots for normalization
    const nonBoundaryDeliveries = drawableDeliveries.filter(d => d.runs < 4);
    const maxNonBoundaryDistance = Math.max(
      ...nonBoundaryDeliveries.map(d => {
        const dx = d.wagon_x - 150;
        const dy = d.wagon_y - 150;
        return Math.sqrt(dx * dx + dy * dy);
      }),
      1
    );

    // Delivery lines
    const deliveryLines = drawableDeliveries.map((delivery, index) => {
      const dx = delivery.wagon_x - 150;
      const dy = delivery.wagon_y - 150;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance === 0) return null;

      // 4s and 6s always reach the edge, others proportionally scaled
      let scaledRadius;
      if (delivery.runs >= 4) {
        scaledRadius = maxRadius;
      } else {
        // Scale non-boundaries: longest non-boundary = 70% of radius, others proportional
        scaledRadius = (distance / maxNonBoundaryDistance) * maxRadius * 0.7;
      }

      const normalizedX = centerX + (dx / distance) * scaledRadius;
      const normalizedY = centerY + (dy / distance) * scaledRadius;

      const isLatest = index === drawableDeliveries.length - 1;

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

  const renderInstructions = () => (
    <Box sx={{ mb: 2, p: 2, bgcolor: designColors.neutral[50], borderRadius: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        How to Play
      </Typography>
      <Stack spacing={0.5}>
        {GAME_INSTRUCTIONS.map((instruction, i) => (
          <Typography key={i} variant="body2" sx={{ color: designColors.neutral[600], fontSize: '0.85rem' }}>
            • {instruction}
          </Typography>
        ))}
      </Stack>
    </Box>
  );

  // Mobile-optimized compact layout
  return (
    <Box sx={{
      py: 1,
      px: isMobile ? 1 : 2,
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100%'
    }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600 }}>
          Guess the Innings
        </Typography>
        <Stack direction="row" spacing={0.5}>
          {data && (
            <IconButton size="small" onClick={() => setShowInfo(!showInfo)}>
              <InfoOutlinedIcon fontSize="small" />
            </IconButton>
          )}
          <IconButton size="small" onClick={() => setShowFilters(!showFilters)}>
            <SettingsIcon fontSize="small" />
          </IconButton>
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

      {/* Info panel (when game is active) */}
      <Collapse in={showInfo && data}>
        {renderInstructions()}
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

      {/* Initial state - instructions and start button */}
      {!data && !loading && !error && (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {renderInstructions()}
          <Box sx={{ flex: 1 }} />
          <Box sx={{ textAlign: 'center', pb: 3 }}>
            <Button
              variant="contained"
              size="large"
              onClick={fetchGame}
              sx={{
                minWidth: 200,
                py: 1.5,
                fontSize: '1.1rem',
                fontWeight: 600
              }}
            >
              Start Game
            </Button>
          </Box>
        </Box>
      )}

      {data && !loading && (
        <Stack spacing={1.5} sx={{ flex: 1 }}>
          {/* Compact Metrics: runs (balls) SR | Hand | Competition */}
          <Typography
            variant="body2"
            sx={{
              textAlign: 'center',
              color: designColors.neutral[700],
              fontWeight: 500
            }}
          >
            {data.innings?.runs} ({data.innings?.balls}) SR {data.innings?.strike_rate?.toFixed?.(0) ?? data.innings?.strike_rate}
            {data.innings?.bat_hand && ` • ${data.innings.bat_hand === 'LHB' ? 'Left-hand' : 'Right-hand'}`}
            {' • '}{data.innings?.competition}
          </Typography>

          {/* Date and Venue */}
          <Typography variant="caption" sx={{ textAlign: 'center', color: designColors.neutral[500] }}>
            {data.innings?.match_date} • {data.innings?.venue}
          </Typography>

          {/* Wagon Wheel */}
          <Box
            ref={chartContainerRef}
            sx={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              py: 0.5
            }}
          >
            {renderWagonWheel()}
          </Box>

          {/* Legend */}
          {renderLegend()}

          {/* Ball counter and Playback Controls */}
          <Stack direction="row" spacing={1} justifyContent="center" alignItems="center">
            <Typography variant="caption" sx={{ color: designColors.neutral[500], minWidth: 60 }}>
              {visibleCount}/{deliveries.length}
            </Typography>
            <IconButton
              onClick={() => setIsPlaying(!isPlaying)}
              disabled={visibleCount >= deliveries.length}
              size="small"
              sx={{ bgcolor: designColors.primary[50] }}
            >
              {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>
            <IconButton
              onClick={() => setVisibleCount(prev => Math.min(prev + 1, deliveries.length))}
              disabled={visibleCount >= deliveries.length}
              size="small"
            >
              <SkipNextIcon />
            </IconButton>
            <IconButton onClick={() => { setVisibleCount(0); setIsPlaying(false); }} size="small">
              <ReplayIcon />
            </IconButton>
          </Stack>

          {/* Guess Input with Autocomplete */}
          <ClickAwayListener onClickAway={() => setShowSuggestions(false)}>
            <Box sx={{ position: 'relative' }}>
              <TextField
                placeholder="Search for the batter..."
                value={guess}
                onChange={(e) => {
                  setGuess(e.target.value);
                  setGuessResult(null);
                }}
                onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                size="small"
                fullWidth
                disabled={guessResult === 'correct' || revealAnswer}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" color="action" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      {searchLoading && <CircularProgress size={16} />}
                      {guessResult === 'correct' && <CheckCircleIcon color="success" />}
                      {guessResult === 'incorrect' && <CancelIcon color="error" />}
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: guessResult === 'correct' ? designColors.success[50] :
                             guessResult === 'incorrect' ? designColors.error[50] : 'white'
                  }
                }}
              />

              {/* Suggestions dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <Paper
                  elevation={3}
                  sx={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    mt: 0.5,
                    maxHeight: 200,
                    overflow: 'auto',
                    zIndex: 1000,
                    borderRadius: 1
                  }}
                >
                  <List dense disablePadding>
                    {suggestions.map((item, index) => (
                      <ListItem
                        key={`${item.name}-${index}`}
                        button
                        onClick={() => handleSelectSuggestion(item)}
                        sx={{
                          '&:hover': { bgcolor: 'action.hover' },
                          py: 0.75
                        }}
                      >
                        <ListItemText
                          primary={item.display_name || item.name}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              )}
            </Box>
          </ClickAwayListener>

          {/* Hint */}
          {showHint && data.innings?.batting_team && data.innings?.bowling_team && (
            <Typography variant="body2" sx={{ textAlign: 'center', color: designColors.neutral[600] }}>
              <strong>{data.innings.batting_team}</strong> vs {data.innings.bowling_team}
            </Typography>
          )}

          {/* Result messages */}
          {guessResult === 'correct' && (
            <Typography variant="body2" sx={{ color: designColors.success[600], textAlign: 'center', fontWeight: 600 }}>
              Correct! It's {answer}
            </Typography>
          )}

          {guessResult === 'incorrect' && !revealAnswer && (
            <Typography variant="body2" sx={{ color: designColors.error[600], textAlign: 'center' }}>
              Not quite - try again or reveal the answer
            </Typography>
          )}

          {revealAnswer && (
            <Typography variant="body1" sx={{ textAlign: 'center' }}>
              Answer: <strong>{answer}</strong>
            </Typography>
          )}

          {/* Bottom buttons */}
          <Stack direction="row" spacing={1} justifyContent="center" sx={{ pt: 1 }}>
            {!showHint && !revealAnswer && guessResult !== 'correct' && (
              <Button
                variant="outlined"
                size="small"
                onClick={() => setShowHint(true)}
                startIcon={<LightbulbOutlinedIcon />}
              >
                Hint
              </Button>
            )}
            {!revealAnswer && guessResult !== 'correct' && (
              <Button
                variant="outlined"
                size="small"
                onClick={() => setRevealAnswer(true)}
              >
                Reveal
              </Button>
            )}
            <Button
              variant="contained"
              size="small"
              onClick={fetchGame}
            >
              New Game
            </Button>
          </Stack>
        </Stack>
      )}
    </Box>
  );
};

export default GuessInningsGame;
