import React, { useRef, useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';

/**
 * OTP-style name entry for the name-guessing games (Player Journeys, Guess the Innings).
 *
 * One box per letter, grouped by word, visible from the start, so the answer's shape is the first
 * clue. Typing fills the boxes in order. With the initials hint taken, each word's first box is
 * pre-filled and skipped. A single transparent input sits over the boxes: a tap anywhere focuses
 * it and brings up the phone keyboard, and backspace/paste behave natively.
 */
const NameGuessInput = ({ shape, initials, disabled, onGuess, onGiveUp, guessesLeft }) => {
  const [value, setValue] = useState('');
  const [focused, setFocused] = useState(false);
  const [shake, setShake] = useState(false);
  const inputRef = useRef(null);

  const initialLetters = initials
    ? initials.split(/\s+/).filter(Boolean).map((w) => w[0].toUpperCase())
    : [];
  const fixed = (word, i) => (i === 0 && initialLetters[word]) || null;
  const freeSlots = shape.reduce((n, len, word) => n + len - (fixed(word, 0) ? 1 : 0), 0);
  const typed = value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, freeSlots).split('');

  let cursor = 0;
  let activeSet = false;
  const words = shape.map((length, word) => Array.from({ length }, (_, i) => {
    const pinned = fixed(word, i);
    if (pinned) return { letter: pinned, pinned: true };
    const letter = typed[cursor];
    cursor += 1;
    const active = !letter && !activeSet;
    if (active) activeSet = true;
    return { letter, active };
  }));

  const complete = typed.length === freeSlots;
  const guessText = words.map((slots) => slots.map((s) => s.letter || '').join('')).join(' ');

  const submit = async () => {
    if (!complete || disabled) return;
    const correct = await onGuess(guessText);
    if (!correct) {
      setShake(true);
      setTimeout(() => { setShake(false); setValue(''); }, 450);
    }
  };

  return (
    <Box>
      <Box
        onClick={() => inputRef.current?.focus()}
        sx={{
          position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center',
          gap: '4px', py: 0.5, cursor: 'text',
          animation: shake ? 'nameShake 0.4s' : 'none',
          '@keyframes nameShake': {
            '0%, 100%': { transform: 'translateX(0)' },
            '25%': { transform: 'translateX(-6px)' },
            '75%': { transform: 'translateX(6px)' },
          },
        }}
      >
        {words.map((slots, w) => (
          <React.Fragment key={w}>
            {w > 0 && <Box sx={{ flex: '0 0 14px' }} />}
            {slots.map((slot, i) => (
              <Box
                key={i}
                sx={{
                  flex: '0 1 38px', minWidth: 14, height: 46, borderRadius: 1.25,
                  display: 'grid', placeItems: 'center',
                  fontFamily: fonts.mono, fontWeight: 700, fontSize: { xs: 17, sm: 20 },
                  bgcolor: slot.pinned ? colors.accentSoft : colors.surface1,
                  color: slot.pinned ? colors.accent : colors.textHi,
                  border: `2px solid ${
                    focused && slot.active ? colors.accent
                      : slot.letter ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.22)'
                  }`,
                  transition: 'border-color 100ms',
                }}
              >
                {slot.letter || ''}
              </Box>
            ))}
          </React.Fragment>
        ))}
        <input
          ref={inputRef}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value.replace(/[^A-Za-z]/g, '').slice(0, freeSlots))}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          autoCapitalize="characters"
          autoCorrect="off"
          autoComplete="off"
          spellCheck={false}
          aria-label={`Player's name: ${shape.length} word${shape.length === 1 ? '' : 's'} of ${shape.join(' and ')} letters`}
          style={{
            position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0,
            border: 0, padding: 0, fontSize: 16, color: 'transparent', background: 'transparent', caretColor: 'transparent',
          }}
        />
      </Box>
      <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
        <Button fullWidth variant="contained" disabled={disabled || !complete} onClick={submit} sx={{ minHeight: 44 }}>Guess</Button>
        <Button variant="outlined" disabled={disabled} onClick={onGiveUp} sx={{ minHeight: 44, flexShrink: 0 }}>Give up</Button>
      </Box>
      {guessesLeft !== undefined && (
        <Typography sx={{ color: colors.textLo, fontSize: 13, mt: 1 }}>
          {guessesLeft} guess{guessesLeft === 1 ? '' : 'es'} left · tap the boxes to type
        </Typography>
      )}
    </Box>
  );
};

export default NameGuessInput;
