/**
 * Guess the Innings Game
 *
 * Mobile-first wagon wheel game - guess the batter from their shot pattern.
 * Features: Staggered hints, scoring, shareable results.
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
  Typography,
  Snackbar
} from '@mui/material';
// Note: TextField still used in filters section
import SettingsIcon from '@mui/icons-material/Settings';
import ShareIcon from '@mui/icons-material/Share';
import config from '../../config';
import { colors as designColors } from '../../theme/designSystem';

const DEFAULT_FILTERS = {
  leagues: 'IPL,BBL,PSL,CPL,SA20,T20 Blast,T20I',
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
  "Guess the batter from their wagon wheel pattern",
  "Use hints if stuck (each costs 1 point)",
  "Score: 5 points - hints used",
];

// Helper to get first letters of name
const getFirstLetters = (name) => {
  if (!name) return '';
  return name.split(' ').map(word => word[0]).join('. ') + '.';
};

// Format date as "Jan 15, 2023"
const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

// Game URL for sharing
const GAME_URL = 'hindsight2020.vercel.app/games/guess-innings';

// Hint definitions in reveal order
const HINT_CONFIG = [
  { key: 'venue', label: 'Venue', icon: '📍', getValue: (d) => d.innings?.venue },
  { key: 'competition', label: 'League', icon: '🏆', getValue: (d) => d.innings?.competition },
  { key: 'bowling_team', label: 'vs', icon: '🎯', getValue: (d) => d.innings?.bowling_team },
  { key: 'batting_team', label: 'For', icon: '🏏', getValue: (d) => d.innings?.batting_team },
  { key: 'first_letters', label: 'Initials', icon: '🔤', getValue: (d) => getFirstLetters(d.answer?.batter) },
];

// localStorage key
const STATS_KEY = 'guess_innings_stats';

// Load stats from localStorage
const loadStats = () => {
  try {
    const saved = localStorage.getItem(STATS_KEY);
    if (saved) return JSON.parse(saved);
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
  return {
    played: 0,
    solved: 0,
    revealed: 0,
    perfectGames: 0,
    totalHints: 0,
    currentStreak: 0,
    maxStreak: 0,
  };
};

// Save stats to localStorage
const saveStats = (stats) => {
  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(stats));
  } catch (e) {
    console.error('Failed to save stats:', e);
  }
};

const GuessInningsGame = ({ isMobile = false }) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [showFilters, setShowFilters] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [guess, setGuess] = useState('');
  const [guessResult, setGuessResult] = useState(null); // 'correct', 'incorrect', null
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [revealedHints, setRevealedHints] = useState([]); // indices of revealed hints
  const [gameEnded, setGameEnded] = useState(false);
  const [stats, setStats] = useState(loadStats);
  const [showCopied, setShowCopied] = useState(false);
  const [containerSize, setContainerSize] = useState(320);
  const [shakeInput, setShakeInput] = useState(false);
  const chartContainerRef = useRef(null);
  const inputRef = useRef(null);

  const hintsUsed = revealedHints.length;
  const score = gameEnded ? (guessResult === 'correct' ? 5 - hintsUsed : 0) : null;

  // Check if first_letters hint is revealed (5th hint, index 4)
  const firstLettersRevealed = revealedHints.includes(4);

  // When first letters hint is revealed, pre-fill guess with skeleton
  useEffect(() => {
    if (firstLettersRevealed && answer && !guess) {
      // Pre-fill with first letters and spaces: "Mayank Agarwal" -> "M A"
      const skeleton = answer.split(' ').map(word => word[0]).join(' ');
      setGuess(skeleton);
      // Focus the input
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [firstLettersRevealed, answer]);

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

  // Auto-play all deliveries when game loads
  useEffect(() => {
    if (!data) return;
    const totalDeliveries = data?.deliveries?.length || 0;
    // Instantly show all deliveries (no animation)
    setVisibleCount(totalDeliveries);
  }, [data]);

  const deliveries = useMemo(() => data?.deliveries || [], [data]);
  const visibleDeliveries = useMemo(() =>
    deliveries.slice(0, visibleCount),
    [deliveries, visibleCount]
  );
  const drawableDeliveries = useMemo(() =>
    visibleDeliveries.filter(d => d.wagon_x !== null && d.wagon_y !== null),
    [visibleDeliveries]
  );
  const answer = data?.answer?.batter || '';

  const endGame = (result) => {
    if (gameEnded) return;
    setGameEnded(true);

    // Update stats
    const newStats = { ...stats };
    newStats.played += 1;

    if (result === 'correct') {
      newStats.solved += 1;
      newStats.currentStreak += 1;
      newStats.maxStreak = Math.max(newStats.maxStreak, newStats.currentStreak);
      if (hintsUsed === 0) {
        newStats.perfectGames += 1;
      }
    } else {
      newStats.revealed += 1;
      newStats.currentStreak = 0;
    }

    newStats.totalHints += hintsUsed;
    setStats(newStats);
    saveStats(newStats);
  };

  const checkGuess = () => {
    if (!answer || gameEnded || !guess.trim()) return;
    const normalizedAnswer = answer.trim().toLowerCase();
    const normalizedGuess = guess.trim().toLowerCase();

    if (normalizedAnswer === normalizedGuess) {
      setGuessResult('correct');
      endGame('correct');
    } else {
      setGuessResult('incorrect');
      // Shake animation
      setShakeInput(true);
      setTimeout(() => setShakeInput(false), 500);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      checkGuess();
    }
  };

  const handleRevealAnswer = () => {
    setRevealAnswer(true);
    endGame('revealed');
  };

  const revealNextHint = () => {
    if (revealedHints.length < HINT_CONFIG.length && !gameEnded) {
      setRevealedHints([...revealedHints, revealedHints.length]);
    }
  };

  const generateShareText = () => {
    if (!data || !gameEnded) return '';

    const innings = data.innings;
    const resultEmoji = guessResult === 'correct' ? '✅' : '❌';
    const streakText = stats.currentStreak > 1 ? ` | Streak: ${stats.currentStreak} 🔥` : '';

    // Build hint status
    const hintLines = HINT_CONFIG.map((hint, idx) => {
      const revealed = revealedHints.includes(idx);
      const checkmark = revealed ? '✓' : '✗';
      return `${hint.icon}${checkmark}`;
    }).join(' ');

    return `Guess the Innings 🏏

${innings.runs} (${innings.balls}) • SR ${innings.strike_rate?.toFixed?.(0) ?? innings.strike_rate}

${hintLines}

${resultEmoji} Score: ${score}/5${streakText}

Play: ${GAME_URL}`;
  };

  const handleShare = async () => {
    const text = generateShareText();

    if (navigator.share) {
      try {
        await navigator.share({ text });
        return;
      } catch (e) {
        // Fall through to clipboard
      }
    }

    try {
      await navigator.clipboard.writeText(text);
      setShowCopied(true);
    } catch (e) {
      console.error('Failed to copy:', e);
    }
  };

  const fetchGame = async () => {
    setLoading(true);
    setError(null);
    setRevealAnswer(false);
    setRevealedHints([]);
    setGameEnded(false);
    setGuess('');
    setGuessResult(null);
    setVisibleCount(0);

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
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Render Hangman-style underscore display with integrated input
  const renderHangmanDisplay = () => {
    if (!answer) return null;

    const words = answer.split(' ');
    const guessWords = guess.split(' ');
    const showAnswer = revealAnswer || guessResult === 'correct';
    const displayAnswer = showAnswer ? answer : guess;

    // Build flat index mapping for guess characters
    let charIndex = 0;
    const getGuessChar = (wordIdx, charIdx) => {
      // Calculate position in guess string (accounting for spaces)
      let pos = 0;
      for (let w = 0; w < wordIdx; w++) {
        pos += words[w].length + 1; // +1 for space
      }
      pos += charIdx;
      return guess[pos]?.toUpperCase() || '';
    };

    return (
      <Box
        sx={{
          textAlign: 'center',
          py: 1,
          cursor: gameEnded ? 'default' : 'text',
          animation: shakeInput ? 'shake 0.5s ease-in-out' : 'none',
          '@keyframes shake': {
            '0%, 100%': { transform: 'translateX(0)' },
            '20%, 60%': { transform: 'translateX(-5px)' },
            '40%, 80%': { transform: 'translateX(5px)' },
          }
        }}
        onClick={() => !gameEnded && inputRef.current?.focus()}
      >
        <Stack direction="row" spacing={2} justifyContent="center" flexWrap="wrap" sx={{ rowGap: 1 }}>
          {words.map((word, wordIdx) => (
            <Stack key={wordIdx} direction="row" spacing={0.5}>
              {word.split('').map((char, charIdx) => {
                const isFirstLetter = charIdx === 0 && firstLettersRevealed;
                const guessChar = getGuessChar(wordIdx, charIdx);
                const displayChar = showAnswer ? char.toUpperCase() : (isFirstLetter ? char.toUpperCase() : guessChar);

                return (
                  <Box
                    key={charIdx}
                    sx={{
                      width: 22,
                      height: 30,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderBottom: `2px solid ${
                        showAnswer ? designColors.success[500] :
                        guessChar ? designColors.primary[400] :
                        designColors.neutral[400]
                      }`,
                      mx: 0.2,
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: '1.1rem',
                        fontWeight: 700,
                        color: showAnswer ? designColors.success[600] :
                               isFirstLetter ? designColors.primary[600] :
                               designColors.neutral[800],
                        fontFamily: 'monospace',
                      }}
                    >
                      {displayChar}
                    </Typography>
                  </Box>
                );
              })}
            </Stack>
          ))}
        </Stack>

        {/* Hidden input for typing */}
        {!gameEnded && (
          <input
            ref={inputRef}
            type="text"
            value={guess}
            onChange={(e) => {
              setGuess(e.target.value);
              if (guessResult === 'incorrect') setGuessResult(null);
            }}
            onKeyDown={handleKeyDown}
            style={{
              position: 'absolute',
              opacity: 0,
              pointerEvents: 'none',
            }}
            autoComplete="off"
          />
        )}
      </Box>
    );
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

    const nonBoundaryDeliveries = drawableDeliveries.filter(d => d.runs < 4);
    const maxNonBoundaryDistance = Math.max(
      ...nonBoundaryDeliveries.map(d => {
        const dx = d.wagon_x - 150;
        const dy = d.wagon_y - 150;
        return Math.sqrt(dx * dx + dy * dy);
      }),
      1
    );

    const deliveryLines = drawableDeliveries.map((delivery, index) => {
      const dx = delivery.wagon_x - 150;
      const dy = delivery.wagon_y - 150;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance === 0) return null;

      let scaledRadius;
      if (delivery.runs >= 4) {
        scaledRadius = maxRadius;
      } else {
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
    <Box sx={{ mb: 2, p: 1.5, bgcolor: designColors.neutral[50], borderRadius: 2 }}>
      <Stack spacing={0.5}>
        {GAME_INSTRUCTIONS.map((instruction, i) => (
          <Typography key={i} variant="body2" sx={{ color: designColors.neutral[600], fontSize: '0.8rem' }}>
            • {instruction}
          </Typography>
        ))}
      </Stack>
    </Box>
  );

  const renderStatsBar = () => (
    <Stack
      direction="row"
      spacing={1}
      justifyContent="center"
      sx={{ mb: 1, flexWrap: 'wrap', gap: 0.5 }}
    >
      <Chip
        label={`${stats.solved}/${stats.played}`}
        size="small"
        sx={{ fontSize: '0.7rem', height: 22 }}
      />
      {stats.perfectGames > 0 && (
        <Chip
          label={`${stats.perfectGames} perfect`}
          size="small"
          sx={{ fontSize: '0.7rem', height: 22, bgcolor: designColors.chart.orange + '30' }}
        />
      )}
      {stats.currentStreak > 0 && (
        <Chip
          label={`🔥 ${stats.currentStreak}`}
          size="small"
          sx={{ fontSize: '0.7rem', height: 22 }}
        />
      )}
    </Stack>
  );

  const renderHints = () => (
    <Box sx={{ mb: 1 }}>
      {/* Hint buttons row */}
      <Stack direction="row" spacing={0.5} justifyContent="center" sx={{ mb: 0.5 }}>
        {HINT_CONFIG.map((hint, idx) => {
          const isRevealed = revealedHints.includes(idx);
          const isNextHint = idx === revealedHints.length;
          return (
            <Button
              key={hint.key}
              size="small"
              variant={isRevealed ? "contained" : "outlined"}
              disabled={!isNextHint || gameEnded}
              onClick={revealNextHint}
              sx={{
                minWidth: 40,
                px: 1,
                py: 0.25,
                fontSize: '0.9rem',
                bgcolor: isRevealed ? designColors.primary[100] : undefined,
                borderColor: isRevealed ? designColors.primary[300] : designColors.neutral[300],
                color: isRevealed ? designColors.primary[700] : designColors.neutral[600],
                '&.Mui-disabled': {
                  bgcolor: isRevealed ? designColors.primary[100] : undefined,
                  color: isRevealed ? designColors.primary[700] : undefined,
                }
              }}
            >
              {hint.icon}
            </Button>
          );
        })}
      </Stack>

      {/* Revealed hint values */}
      {revealedHints.length > 0 && (
        <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" sx={{ gap: 0.5 }}>
          {revealedHints.filter(idx => idx < 4).map((hintIdx) => {
            const hint = HINT_CONFIG[hintIdx];
            const value = hint.getValue(data);
            return (
              <Typography
                key={hint.key}
                variant="caption"
                sx={{
                  color: designColors.neutral[600],
                  bgcolor: designColors.neutral[100],
                  px: 1,
                  py: 0.25,
                  borderRadius: 1,
                  fontSize: '0.75rem',
                }}
              >
                {hint.label === 'vs' ? 'vs ' : hint.label === 'For' ? '' : ''}{value}
              </Typography>
            );
          })}
        </Stack>
      )}
    </Box>
  );

  return (
    <Box sx={{
      py: 1,
      px: isMobile ? 1 : 2,
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100%'
    }}>
      {/* Compact header with stats and settings */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        {stats.played > 0 ? renderStatsBar() : <Box />}
        <IconButton size="small" onClick={() => setShowFilters(!showFilters)}>
          <SettingsIcon fontSize="small" />
        </IconButton>
      </Stack>

      {/* Collapsible Filters */}
      <Collapse in={showFilters}>
        <Box sx={{ mb: 2, p: 1.5, bgcolor: designColors.neutral[50], borderRadius: 1 }}>
          <Stack spacing={1.5}>
            <TextField
              label="Leagues"
              value={filters.leagues}
              onChange={(e) => setFilters(prev => ({ ...prev, leagues: e.target.value }))}
              size="small"
              fullWidth
              helperText="IPL, BBL, PSL, CPL, SA20, T20 Blast, T20I"
            />
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
                label="Min SR"
                type="number"
                value={filters.minStrikeRate}
                onChange={(e) => setFilters(prev => ({ ...prev, minStrikeRate: Number(e.target.value) }))}
                size="small"
                sx={{ width: 100 }}
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

      {/* Initial state */}
      {!data && !loading && !error && (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 2, textAlign: 'center' }}>
            Guess the Innings
          </Typography>
          {renderInstructions()}
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
      )}

      {data && !loading && (
        <Stack spacing={1} sx={{ flex: 1 }}>
          {/* Stats pills: runs (balls), SR, date, hand */}
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" sx={{ gap: 0.5 }}>
            <Chip
              label={`${data.innings?.runs} (${data.innings?.balls})`}
              size="small"
              sx={{ fontWeight: 600 }}
            />
            <Chip
              label={`SR ${data.innings?.strike_rate?.toFixed?.(0) ?? data.innings?.strike_rate}`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={formatDate(data.innings?.match_date)}
              size="small"
              variant="outlined"
            />
            {data.innings?.bat_hand && (
              <Chip
                label={data.innings.bat_hand}
                size="small"
                variant="outlined"
              />
            )}
          </Stack>

          {/* Wagon Wheel */}
          <Box
            ref={chartContainerRef}
            sx={{
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            {renderWagonWheel()}
          </Box>

          {/* Legend */}
          {renderLegend()}

          {/* Hint buttons */}
          {renderHints()}

          {/* Hangman display with integrated input */}
          {renderHangmanDisplay()}

          {/* Guess button */}
          {!gameEnded && (
            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="contained"
                size="small"
                onClick={checkGuess}
                disabled={!guess.trim()}
              >
                Guess
              </Button>
            </Box>
          )}

          {/* Wrong guess message */}
          {guessResult === 'incorrect' && !gameEnded && (
            <Typography variant="body2" sx={{ color: designColors.error[600], textAlign: 'center', fontWeight: 500 }}>
              Try again!
            </Typography>
          )}

          {/* Score display when game ended */}
          {gameEnded && (
            <Box sx={{ textAlign: 'center' }}>
              <Chip
                label={`Score: ${score}/5`}
                sx={{
                  fontWeight: 700,
                  fontSize: '1rem',
                  py: 2,
                  bgcolor: score === 5 ? designColors.chart.orange + '40' :
                           score >= 3 ? designColors.chart.green + '40' :
                           score > 0 ? designColors.primary[100] :
                           designColors.neutral[100],
                }}
              />
            </Box>
          )}

          {/* Action buttons */}
          <Stack direction="row" spacing={1} justifyContent="center">
            {!gameEnded && (
              <Button
                variant="outlined"
                size="small"
                color="error"
                onClick={handleRevealAnswer}
              >
                Give Up
              </Button>
            )}
            {gameEnded && (
              <>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleShare}
                  startIcon={<ShareIcon />}
                >
                  Share
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  onClick={fetchGame}
                >
                  Next
                </Button>
              </>
            )}
          </Stack>
        </Stack>
      )}

      <Snackbar
        open={showCopied}
        autoHideDuration={2000}
        onClose={() => setShowCopied(false)}
        message="Copied to clipboard!"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default GuessInningsGame;
