import React from 'react';
import { Box, Typography } from '@mui/material';
import { borderRadius, colors, spacing, typography } from '../../theme/designSystem';

const EmptyState = ({
  title = 'No data available',
  description,
  isMobile = false,
  minHeight = 220,
  sx = {},
}) => (
  <Box
    sx={{
      minHeight,
      borderRadius: `${borderRadius.base}px`,
      border: `1px dashed ${colors.neutral[200]}`,
      backgroundColor: colors.neutral[50],
      px: `${spacing.lg}px`,
      py: `${spacing.lg}px`,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      gap: `${spacing.xs}px`,
      ...sx,
    }}
  >
    <Typography
      variant={isMobile ? 'subtitle1' : 'h6'}
      sx={{ fontWeight: typography.fontWeight.semibold, color: colors.neutral[800] }}
    >
      {title}
    </Typography>
    {description && (
      <Typography variant="body2" sx={{ color: colors.neutral[600] }}>
        {description}
      </Typography>
    )}
  </Box>
);

export default EmptyState;
