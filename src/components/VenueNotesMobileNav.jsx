import React, { useEffect, useRef } from 'react';
import { Box, Chip, IconButton, Typography } from '@mui/material';
import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';

const VenueNotesMobileNav = ({
  sections,
  activeGroupId,
  activeGroupLabel,
  activeCardMeta,
  onGroupClick,
  onPrevious,
  onNext,
  disablePrevious,
  disableNext,
}) => {
  const chipRefs = useRef([]);

  useEffect(() => {
    const activeIndex = sections.findIndex((section) => section.id === activeGroupId);
    if (activeIndex >= 0 && chipRefs.current[activeIndex]) {
      chipRefs.current[activeIndex].scrollIntoView({
        behavior: 'smooth',
        inline: 'center',
        block: 'nearest',
      });
    }
  }, [sections, activeGroupId]);

  return (
    <Box
      sx={{
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 1100,
        px: 1.5,
        pt: 1,
        pb: 'calc(10px + env(safe-area-inset-bottom))',
        borderTop: '1px solid',
        borderColor: 'divider',
        bgcolor: 'rgba(255,255,255,0.96)',
        backdropFilter: 'blur(10px)',
        boxShadow: '0 -10px 24px rgba(15, 23, 42, 0.08)',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 1,
          gap: 1,
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {activeGroupLabel}
        </Typography>
        {activeCardMeta ? (
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            {activeCardMeta}
          </Typography>
        ) : null}
      </Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: '40px minmax(0, 1fr) 40px', gap: 1, alignItems: 'center' }}>
        <IconButton
          size="small"
          onClick={onPrevious}
          disabled={disablePrevious}
          aria-label="Go to previous venue notes card"
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <ChevronLeftRoundedIcon fontSize="small" />
        </IconButton>
        <Box
          sx={{
            display: 'flex',
            gap: 0.75,
            overflowX: 'auto',
            px: 0.5,
            '&::-webkit-scrollbar': { display: 'none' },
            scrollbarWidth: 'none',
          }}
        >
          {sections.map((section, index) => (
            <Chip
              key={section.id}
              ref={(element) => {
                chipRefs.current[index] = element;
              }}
              label={section.label}
              onClick={() => onGroupClick(section.id)}
              color={section.id === activeGroupId ? 'primary' : 'default'}
              variant={section.id === activeGroupId ? 'filled' : 'outlined'}
              size="small"
              sx={{ flexShrink: 0, borderRadius: 1.5, fontWeight: 600 }}
            />
          ))}
        </Box>
        <IconButton
          size="small"
          onClick={onNext}
          disabled={disableNext}
          aria-label="Go to next venue notes card"
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <ChevronRightRoundedIcon fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
};

export default VenueNotesMobileNav;
