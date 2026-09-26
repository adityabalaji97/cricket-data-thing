import React, { useState } from 'react';
import { Box, Button, TextField, Typography } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';

/**
 * Hangman-style name entry for the name-guessing games (Player Journeys, Guess the Innings).
 *
 * The dashes show the answer's shape from the start -- one group per word, one dash per letter --
 * and fill as you type. With the initials hint taken, each word's first letter is pre-shown.
 * Guesses are checked by the server, which forgives close spellings and known aliases, so a typed
 * name does not have to fit the dashes exactly.
 */
const NameGuessInput = ({ shape, initials, disabled, onGuess, onGiveUp, guessesLeft }) => {
  const [value, setValue] = useState('');
  const [shake, setShake] = useState(false);
  const typed = value.toUpperCase().replace(/[^A-Z]/g, '').split('');
  const initialLetters = initials ? initials.replace(/[^A-Z ]/gi, '').split(/\s+/).filter(Boolean).map((w) => w[0].toUpperCase()) : [];

  // Keep the whole name on one line on a phone: longer names get narrower slots.
  const total = shape.reduce((a, b) => a + b, 0);
  const slot = total >= 15 ? 15 : total >= 12 ? 18 : 22;

  let cursor = 0;
  const groups = shape.map((length, word) => Array.from({ length }, (_, i) => {
    const letter = typed[cursor];
    cursor += 1;
    return { letter, hint: i === 0 ? initialLetters[word] : null };
  }));

  const submit = async () => {
    if (typed.length < 3 || disabled) return;
    const correct = await onGuess(value);
    if (!correct) {
      setShake(true);
      setTimeout(() => { setShake(false); setValue(''); }, 450);
    }
  };

  return (
    <Box>
      <Box
        sx={{
          display: 'flex', flexWrap: 'wrap', columnGap: 1.5, rowGap: 1, justifyContent: 'center', mb: 1.5,
          animation: shake ? 'nameShake 0.4s' : 'none',
          '@keyframes nameShake': {
            '0%, 100%': { transform: 'translateX(0)' },
            '25%': { transform: 'translateX(-6px)' },
            '75%': { transform: 'translateX(6px)' },
          },
        }}
        aria-label={`Name has ${shape.length} word${shape.length === 1 ? '' : 's'}: ${shape.join(', ')} letters`}
      >
        {groups.map((slots, g) => (
          <Box key={g} sx={{ display: 'flex', gap: slot < 20 ? 0.375 : 0.5 }}>
            {slots.map((slot, i) => (
              <Box
                key={i}
                sx={{
                  width: slot, height: 30, borderBottom: `2px solid ${slot.letter ? colors.accent : colors.borderStrong}`,
                  display: 'grid', placeItems: 'center',
                  fontFamily: fonts.mono, fontWeight: 700, fontSize: slot < 20 ? 14 : 17,
                  color: slot.letter ? colors.textHi : colors.textFaint,
                }}
              >
                {slot.letter || slot.hint || ''}
              </Box>
            ))}
          </Box>
        ))}
      </Box>
      <TextField
        fullWidth
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
        placeholder="Type the player's name"
        inputProps={{ autoCapitalize: 'words', autoCorrect: 'off', spellCheck: false, 'aria-label': "Player's name" }}
      />
      <Box sx={{ display: 'flex', gap: 1, mt: 1.25 }}>
        <Button fullWidth variant="contained" disabled={disabled || typed.length < 3} onClick={submit} sx={{ minHeight: 44 }}>Guess</Button>
        <Button variant="outlined" disabled={disabled} onClick={onGiveUp} sx={{ minHeight: 44, flexShrink: 0 }}>Give up</Button>
      </Box>
      {guessesLeft !== undefined && (
        <Typography sx={{ color: colors.textLo, fontSize: 13, mt: 1 }}>
          {guessesLeft} guess{guessesLeft === 1 ? '' : 'es'} left · close spellings count
        </Typography>
      )}
    </Box>
  );
};

export default NameGuessInput;
