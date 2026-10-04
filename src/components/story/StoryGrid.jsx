import React from 'react';
import { Box, Typography } from '@mui/material';
import StoryCard from './StoryCard';
import { GRID_CARD_WIDTH } from './storyLayout';
import { colors, fonts } from '../../theme/hindsightDark';

/**
 * Desktop: the same cards in a grid, chapter by chapter. A click opens the story viewer at that
 * card (onOpen), so the reading and sharing experience matches the phone.
 */
const StoryGrid = ({ chapters, onOpen }) => (
  <Box sx={{ display: 'grid', gap: 4, py: 2 }}>
    {chapters.map((chapter) => (
      <Box key={chapter.id} component="section" aria-label={chapter.title}>
        <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, letterSpacing: '0.08em', color: colors.accent, textTransform: 'uppercase', mb: 1.5 }}>
          {chapter.title}
        </Typography>
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: `repeat(auto-fill, minmax(${GRID_CARD_WIDTH}px, 1fr))`, justifyItems: 'center' }}>
          {chapter.cards.map((card) => (
            // A div with button semantics, not a <button>: the card holds its own info button.
            <Box
              key={card.id}
              role="button"
              tabIndex={0}
              aria-label={`Open ${card.title}`}
              onClick={() => onOpen(card.id)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(card.id); } }}
              sx={{ borderRadius: '20px', cursor: 'pointer', '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}
            >
              <StoryCard card={card} width={GRID_CARD_WIDTH} height={Math.round(GRID_CARD_WIDTH * 1.25)} />
            </Box>
          ))}
        </Box>
      </Box>
    ))}
  </Box>
);

export default StoryGrid;
