/**
 * Player Journeys Game
 *
 * Guess the IPL player from their team journey through the years.
 * Features: Timeline display, staggered hints, scoring.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  Typography,
  Snackbar
} from '@mui/material';
import ShareIcon from '@mui/icons-material/Share';
import config from '../../config';
import { colors as designColors } from '../../theme/designSystem';

// IPL Team Colors
const TEAM_COLORS = {
  'Chennai Super Kings': '#FFCB05',
  'Mumbai Indians': '#004BA0',
  'Royal Challengers Bangalore': '#EC1C24',
  'Royal Challengers Bengaluru': '#EC1C24',
  'Kolkata Knight Riders': '#3A225D',
  'Delhi Capitals': '#0078BC',
  'Delhi Daredevils': '#0078BC',
  'Rajasthan Royals': '#EA1A85',
  'Sunrisers Hyderabad': '#F7A721',
  'Punjab Kings': '#ED1B24',
  'Kings XI Punjab': '#ED1B24',
  'Gujarat Titans': '#1C1C1C',
  'Lucknow Super Giants': '#A72056',
  'Pune Warriors India': '#2F9BE3',
  'Rising Pune Supergiant': '#6F61AC',
  'Rising Pune Supergiants': '#6F61AC',
  'Deccan Chargers': '#D69C2A',
  'Kochi Tuskers Kerala': '#E8462F',
  'Gujarat Lions': '#E04F16',
};

// Helper to get first letters of name
const getFirstLetters = (name) => {
  if (!name) return '';
  return name.split(' ').map(word => word[0]).join('. ') + '.';
};

// Game URL for sharing
const GAME_URL = 'https://hindsight2020.vercel.app/games/player-journeys';

// Hint definitions in reveal order
const HINT_CONFIG = [
  { key: 'years', label: 'Years', icon: '📅', getValue: (d) => 'Year ranges revealed' },
  { key: 'stats', label: 'Stats', icon: '📊', getValue: (d) => {
    const runs = d.stats?.total_runs || 0;
    const wickets = d.stats?.total_wickets || 0;
    const sr = d.stats?.strike_rate?.toFixed(1) || 0;
    if (wickets > 0 && runs > 0) {
      return `${runs} runs, ${wickets} wkts`;
    } else if (wickets > 0) {
      return `${wickets} wickets`;
    }
    return `${runs} runs @ SR ${sr}`;
  }},
  { key: 'first_letters', label: 'Initials', icon: '🔤', getValue: (d) => getFirstLetters(d.answer?.player) },
];

const GAME_INSTRUCTIONS = [
  "Guess the IPL player from their team history",
  "Use hints if stuck (each costs 1 point)",
  "Score: 3 points - hints used",
];

// localStorage key
const STATS_KEY = 'player_journeys_stats';

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

const PlayerJourneysGame = ({ isMobile = false }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [guess, setGuess] = useState('');
  const [guessResult, setGuessResult] = useState(null);
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [revealedHints, setRevealedHints] = useState([]);
  const [gameEnded, setGameEnded] = useState(false);
  const [stats, setStats] = useState(loadStats);
  const [showCopied, setShowCopied] = useState(false);
  const [shakeInput, setShakeInput] = useState(false);
  const inputRef = useRef(null);

  const hintsUsed = revealedHints.length;
  const score = gameEnded ? (guessResult === 'correct' ? 3 - hintsUsed : 0) : null;
  const answer = data?.answer?.player || '';

  // Check if years hint is revealed (1st hint, index 0)
  const yearsRevealed = revealedHints.includes(0);
  // Check if first_letters hint is revealed (3rd hint, index 2)
  const firstLettersRevealed = revealedHints.includes(2);

  // Build slots from answer (excluding spaces) for slot-based typing
  const slots = useMemo(() => {
    if (!answer) return [];
    const result = [];
    answer.split(' ').forEach((word, wordIdx) => {
      word.split('').forEach((char, charIdx) => {
        result.push({
          char: char.toUpperCase(),
          wordIdx,
          charIdx,
          isFirstLetter: charIdx === 0,
        });
      });
    });
    return result;
  }, [answer]);

  // Map user input to slots (auto-skip first letters when hint revealed)
  const filledSlots = useMemo(() => {
    const userChars = guess.toUpperCase().split('');
    let userIdx = 0;
    return slots.map(slot => {
      if (firstLettersRevealed && slot.isFirstLetter) {
        return slot.char;
      }
      if (userIdx < userChars.length) {
        return userChars[userIdx++];
      }
      return '';
    });
  }, [guess, slots, firstLettersRevealed]);

  // When first letters hint is revealed, clear guess
  useEffect(() => {
    if (firstLettersRevealed && answer && guess) {
      setGuess('');
      setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 100);
    }
  }, [firstLettersRevealed]);

  // Auto-evaluate when all slots are filled
  useEffect(() => {
    if (!gameEnded && slots.length > 0 && filledSlots.every(char => char)) {
      const timer = setTimeout(() => {
        const answerChars = slots.map(s => s.char);
        const isCorrect = filledSlots.every((char, idx) => char === answerChars[idx]);

        if (isCorrect) {
          setGuessResult('correct');
          endGame('correct');
        } else {
          setGuessResult('incorrect');
          setShakeInput(true);
          setTimeout(() => {
            setShakeInput(false);
            setGuess('');
            setGuessResult(null);
          }, 500);
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [filledSlots, slots, gameEnded]);

  const endGame = (result) => {
    if (gameEnded) return;
    setGameEnded(true);

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

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      // Check if all slots filled
      if (filledSlots.every(char => char)) {
        const answerChars = slots.map(s => s.char);
        const isCorrect = filledSlots.every((char, idx) => char === answerChars[idx]);
        if (isCorrect) {
          setGuessResult('correct');
          endGame('correct');
        } else {
          setGuessResult('incorrect');
          setShakeInput(true);
          setTimeout(() => {
            setShakeInput(false);
            setGuess('');
            setGuessResult(null);
          }, 500);
        }
      }
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

    const resultEmoji = guessResult === 'correct' ? '✅' : '❌';
    const streakText = stats.currentStreak > 1 ? ` | Streak: ${stats.currentStreak} 🔥` : '';

    const hintLines = HINT_CONFIG.map((hint, idx) => {
      const revealed = revealedHints.includes(idx);
      const checkmark = revealed ? '✓' : '✗';
      return `${hint.icon}${checkmark}`;
    }).join(' ');

    return `Player Journeys 🏏

${data.journey?.length || 0} teams over ${data.stats?.total_seasons || 0} seasons

${hintLines}

${resultEmoji} Score: ${score}/3${streakText}

Play: ${GAME_URL}`;
  };

  const handleShare = async () => {
    try {
      const text = generateShareText();
      if (navigator.share) {
        await navigator.share({
          title: 'Player Journeys',
          text: text,
        });
      } else {
        await navigator.clipboard.writeText(text);
        setShowCopied(true);
      }
    } catch (e) {
      console.error('Share failed:', e);
      try {
        await navigator.clipboard.writeText(generateShareText());
        setShowCopied(true);
      } catch (clipErr) {
        console.error('Clipboard failed:', clipErr);
      }
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

    try {
      const response = await fetch(`${config.API_URL}/games/player-journey?include_answer=true&min_seasons=3`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch player journey');
      }
      const payload = await response.json();
      setData(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Render Hangman-style underscore display
  const renderHangmanDisplay = () => {
    if (!answer) return null;

    const words = answer.split(' ');
    const showAnswer = revealAnswer || guessResult === 'correct';

    let slotIdx = 0;
    const nextEmptySlot = filledSlots.findIndex(char => !char);

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
          },
          '@keyframes blink': {
            '0%, 100%': { opacity: 1 },
            '50%': { opacity: 0 },
          }
        }}
        onClick={() => !gameEnded && inputRef.current?.focus({ preventScroll: true })}
      >
        <Stack direction="row" spacing={2} justifyContent="center" flexWrap="wrap" sx={{ rowGap: 1 }}>
          {words.map((word, wordIdx) => (
            <Stack key={wordIdx} direction="row" spacing={0.5}>
              {word.split('').map((char, charIdx) => {
                const currentSlotIdx = slotIdx++;
                const slot = slots[currentSlotIdx];
                const filledChar = filledSlots[currentSlotIdx] || '';
                const isFirstLetter = slot?.isFirstLetter && firstLettersRevealed;
                const displayChar = showAnswer ? char.toUpperCase() : filledChar;
                const isNextEmpty = !showAnswer && !gameEnded && currentSlotIdx === nextEmptySlot;

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
                        isNextEmpty ? designColors.primary[500] :
                        filledChar ? designColors.primary[400] :
                        designColors.neutral[400]
                      }`,
                      mx: 0.2,
                      position: 'relative',
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
                    {isNextEmpty && (
                      <Box
                        sx={{
                          position: 'absolute',
                          bottom: 4,
                          width: 12,
                          height: 2,
                          bgcolor: designColors.primary[500],
                          animation: 'blink 1s ease-in-out infinite',
                        }}
                      />
                    )}
                  </Box>
                );
              })}
            </Stack>
          ))}
        </Stack>

        {!gameEnded && (
          <input
            ref={inputRef}
            type="text"
            value={guess}
            onChange={(e) => {
              const filtered = e.target.value.replace(/[^a-zA-Z]/g, '');
              setGuess(filtered);
              if (guessResult === 'incorrect') setGuessResult(null);
            }}
            onKeyDown={handleKeyDown}
            onFocus={(e) => {
              e.target.scrollIntoView = () => {};
            }}
            style={{
              position: 'absolute',
              width: '1px',
              height: '1px',
              padding: 0,
              margin: '-1px',
              overflow: 'hidden',
              clip: 'rect(0, 0, 0, 0)',
              whiteSpace: 'nowrap',
              border: 0,
            }}
            autoComplete="off"
            autoCapitalize="off"
            spellCheck="false"
          />
        )}
      </Box>
    );
  };

  // Render team timeline
  const renderTimeline = () => {
    if (!data?.journey) return null;

    return (
      <Stack spacing={1} sx={{ my: 2 }}>
        {data.journey.map((step, idx) => {
          const teamColor = TEAM_COLORS[step.team] || designColors.neutral[400];
          const isLast = idx === data.journey.length - 1;

          return (
            <Box key={idx}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: teamColor + '20',
                  border: `2px solid ${teamColor}`,
                }}
              >
                {/* Team color indicator */}
                <Box
                  sx={{
                    width: 8,
                    height: 40,
                    bgcolor: teamColor,
                    borderRadius: 1,
                    mr: 2,
                    flexShrink: 0,
                  }}
                />
                <Box sx={{ flex: 1 }}>
                  <Typography
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.95rem',
                      color: designColors.neutral[800],
                    }}
                  >
                    {step.team}
                  </Typography>
                  <Typography
                    sx={{
                      fontSize: '0.85rem',
                      color: yearsRevealed ? designColors.neutral[600] : designColors.neutral[400],
                      fontFamily: 'monospace',
                    }}
                  >
                    {yearsRevealed ? step.years : '????'}
                  </Typography>
                </Box>
              </Box>
              {/* Connector arrow */}
              {!isLast && (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 0.5 }}>
                  <Typography sx={{ color: designColors.neutral[400], fontSize: '1.2rem' }}>↓</Typography>
                </Box>
              )}
            </Box>
          );
        })}
      </Stack>
    );
  };

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
      <Stack direction="row" spacing={1} alignItems="center" justifyContent="center" sx={{ mb: 0.5 }}>
        <Typography
          variant="caption"
          sx={{
            color: designColors.neutral[400],
            fontSize: '0.7rem',
            fontWeight: 500,
          }}
        >
          Hints
        </Typography>
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
          {revealedHints.filter(idx => idx === 1).map((hintIdx) => {
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
                {value}
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
      {/* Stats bar */}
      {stats.played > 0 && renderStatsBar()}

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
            Player Journeys
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
          {/* Journey summary */}
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" sx={{ gap: 0.5 }}>
            <Chip
              label={`${data.journey?.length || 0} teams`}
              size="small"
              sx={{ fontWeight: 600 }}
            />
            <Chip
              label={`${data.stats?.total_seasons || 0} seasons`}
              size="small"
              variant="outlined"
            />
          </Stack>

          {/* Team Timeline */}
          {renderTimeline()}

          {/* Hint buttons */}
          {renderHints()}

          {/* Hangman display with integrated input */}
          {renderHangmanDisplay()}

          {/* Wrong guess message */}
          {guessResult === 'incorrect' && !gameEnded && (
            <Typography variant="body2" sx={{ color: designColors.error[600], textAlign: 'center', fontWeight: 500 }}>
              Try again!
            </Typography>
          )}

          {/* Give Up button (during game) or Score + actions (after game) */}
          {!gameEnded ? (
            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="outlined"
                size="small"
                color="error"
                onClick={handleRevealAnswer}
              >
                Give Up
              </Button>
            </Box>
          ) : (
            <>
              <Box sx={{ textAlign: 'center' }}>
                <Chip
                  label={`Score: ${score}/3`}
                  sx={{
                    fontWeight: 700,
                    fontSize: '1rem',
                    py: 2,
                    bgcolor: score === 3 ? designColors.chart.orange + '40' :
                             score >= 2 ? designColors.chart.green + '40' :
                             score > 0 ? designColors.primary[100] :
                             designColors.neutral[100],
                  }}
                />
              </Box>
              <Stack direction="row" spacing={1} justifyContent="center">
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
              </Stack>
            </>
          )}
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

export default PlayerJourneysGame;
