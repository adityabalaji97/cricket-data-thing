import React, { useRef, useEffect } from 'react';
import { Box, Chip } from '@mui/material';

const SlideChipBar = ({ slides, activeIndex, onChipClick }) => {
  const chipRefs = useRef([]);

  useEffect(() => {
    if (chipRefs.current[activeIndex]) {
      chipRefs.current[activeIndex].scrollIntoView({
        behavior: 'smooth',
        inline: 'center',
        block: 'nearest',
      });
    }
  }, [activeIndex]);

  return (
    <Box sx={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      bgcolor: 'background.paper',
      borderTop: 1,
      borderColor: 'divider',
      px: 1,
      py: 1,
      zIndex: 1100,
      display: 'flex',
      overflowX: 'auto',
      gap: 1,
      WebkitOverflowScrolling: 'touch',
      '&::-webkit-scrollbar': { display: 'none' },
      scrollbarWidth: 'none',
    }}>
      {slides.map((slide, i) => (
        <Chip
          key={slide.id}
          ref={(el) => { chipRefs.current[i] = el; }}
          label={slide.chipLabel}
          variant={i === activeIndex ? 'filled' : 'outlined'}
          color={i === activeIndex ? 'primary' : 'default'}
          onClick={() => onChipClick(i)}
          size="small"
          sx={{ flexShrink: 0 }}
        />
      ))}
    </Box>
  );
};

export default SlideChipBar;
