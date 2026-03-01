import React from 'react';
import { Box, IconButton, Typography } from '@mui/material';
import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';

const VenueNotesMobileNav = ({
  label,
  meta,
  onPrevious,
  onNext,
  disablePrevious,
  disableNext,
}) => (
  <Box
    sx={{
      position: 'fixed',
      left: 16,
      right: 16,
      bottom: 'calc(8px + env(safe-area-inset-bottom))',
      zIndex: 1100,
      pointerEvents: 'none',
    }}
  >
    <Box
      sx={{
        position: 'relative',
        minHeight: 50,
        px: 6,
        py: 1,
        borderRadius: 999,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'rgba(255,255,255,0.94)',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 10px 24px rgba(15, 23, 42, 0.12)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
        overflow: 'hidden',
        pointerEvents: 'auto',
      }}
    >
      <IconButton
        size="small"
        onClick={onPrevious}
        disabled={disablePrevious}
        aria-label="Go to previous venue notes card"
        sx={{
          position: 'absolute',
          left: -8,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 40,
          height: 40,
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          opacity: disablePrevious ? 0.35 : 1,
        }}
      >
        <ChevronLeftRoundedIcon fontSize="small" />
      </IconButton>
      <Typography
        variant="body2"
        sx={{
          fontWeight: 700,
          lineHeight: 1.2,
          maxWidth: '100%',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {label}
      </Typography>
      {meta ? (
        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, flexShrink: 0 }}>
          {meta}
        </Typography>
      ) : null}
      <IconButton
        size="small"
        onClick={onNext}
        disabled={disableNext}
        aria-label="Go to next venue notes card"
        sx={{
          position: 'absolute',
          right: -8,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 40,
          height: 40,
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          opacity: disableNext ? 0.35 : 1,
        }}
      >
        <ChevronRightRoundedIcon fontSize="small" />
      </IconButton>
    </Box>
  </Box>
);

export default VenueNotesMobileNav;
