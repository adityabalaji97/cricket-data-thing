import React from 'react';
import { Box, Chip, Typography } from '@mui/material';

const VenueNotesCardShell = ({ groupLabel, cardLabel, metaText, isMobile = false, children }) => (
  <Box
    sx={{
      display: 'flex',
      flexDirection: 'column',
      height: isMobile ? 'calc(100dvh - 250px)' : '100%',
      minHeight: isMobile ? 420 : 'auto',
      borderRadius: 3,
      border: '1px solid',
      borderColor: 'divider',
      boxShadow: 1,
      bgcolor: 'background.paper',
      backgroundImage: 'linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(250,250,250,1) 100%)',
      overflow: 'hidden',
    }}
  >
    <Box
      sx={{
        px: { xs: 2, sm: 2.5 },
        py: { xs: 1.75, sm: 2 },
        borderBottom: '1px solid',
        borderColor: 'divider',
        display: 'flex',
        flexDirection: 'column',
        gap: 0.75,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: 'primary.main',
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
        }}
      >
        {groupLabel}
      </Typography>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 1,
          flexWrap: 'wrap',
        }}
      >
        <Typography variant={isMobile ? 'h6' : 'h5'} sx={{ fontWeight: 600 }}>
          {cardLabel}
        </Typography>
        {metaText ? (
          <Chip
            size="small"
            label={metaText}
            sx={{
              bgcolor: 'rgba(2, 132, 199, 0.08)',
              color: 'primary.main',
              borderRadius: 1.5,
              fontWeight: 600,
            }}
          />
        ) : null}
      </Box>
    </Box>
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        overflowY: 'auto',
        px: { xs: 2, sm: 2.5 },
        py: { xs: 1.75, sm: 2 },
      }}
    >
      {children}
    </Box>
  </Box>
);

export default VenueNotesCardShell;
