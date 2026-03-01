import React from 'react';
import { Box, Button, Typography } from '@mui/material';

const VenueNotesDesktopNav = ({ sections, activeSectionId, onSectionSelect }) => (
  <Box
    sx={{
      position: 'sticky',
      top: 16,
      alignSelf: 'flex-start',
      border: '1px solid',
      borderColor: 'divider',
      borderRadius: 3,
      boxShadow: 1,
      bgcolor: 'background.paper',
      p: 2,
    }}
  >
    <Typography
      variant="caption"
      sx={{
        display: 'block',
        mb: 1.5,
        color: 'text.secondary',
        fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}
    >
      Contents
    </Typography>
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {sections.map((section) => {
        const isActive = section.id === activeSectionId;

        return (
          <Button
            key={section.id}
            onClick={() => onSectionSelect(section.id)}
            variant={isActive ? 'contained' : 'text'}
            color={isActive ? 'primary' : 'inherit'}
            sx={{
              justifyContent: 'flex-start',
              textTransform: 'none',
              borderRadius: 2,
              px: 1.5,
              py: 1,
              fontWeight: 600,
              color: isActive ? 'primary.contrastText' : 'text.primary',
              bgcolor: isActive ? 'primary.main' : 'transparent',
            }}
            aria-current={isActive ? 'true' : undefined}
          >
            {section.label}
          </Button>
        );
      })}
    </Box>
  </Box>
);

export default VenueNotesDesktopNav;
