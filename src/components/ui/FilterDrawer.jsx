import React from 'react';
import { Box, Drawer, IconButton, Typography } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { borderRadius, colors, spacing, typography } from '../../theme/designSystem';

const FilterDrawer = ({ open, onClose, title = 'Filters', children, footer }) => {
  return (
    <Drawer
      anchor="bottom"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          borderTopLeftRadius: `${borderRadius.lg}px`,
          borderTopRightRadius: `${borderRadius.lg}px`,
          maxHeight: '85vh',
          backgroundColor: colors.neutral[0],
        },
      }}
    >
      <Box sx={{ px: `${spacing.lg}px`, pt: `${spacing.sm}px`, pb: `${spacing.lg}px` }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            mb: `${spacing.base}px`,
          }}
        >
          <Box
            sx={{
              width: 48,
              height: 4,
              borderRadius: `${borderRadius.full}px`,
              backgroundColor: colors.neutral[200],
            }}
          />
        </Box>

        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: `${spacing.lg}px`,
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: typography.fontWeight.semibold }}>
            {title}
          </Typography>
          <IconButton onClick={onClose} size="small" sx={{ color: colors.neutral[600] }}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.base}px` }}>
          {children}
        </Box>

        {footer && <Box sx={{ mt: `${spacing.lg}px` }}>{footer}</Box>}
      </Box>
    </Drawer>
  );
};

export default FilterDrawer;
