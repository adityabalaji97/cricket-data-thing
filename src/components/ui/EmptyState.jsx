import React from 'react';
import { Box, Button, Typography } from '@mui/material';
import { borderRadius, spacing, typography } from '../../theme/designSystem';

/**
 * "There is nothing here" — and, optionally, why and what to do about it.
 *
 * `reasons`, `actionLabel`/`onAction` and `icon` are optional extras for callers that can
 * explain an empty result (e.g. a venue with no matches under the current filters) instead of
 * rendering a wall of zeros or a raw backend error.
 *
 * Colours come from the theme palette (divider / text.*) rather than fixed light neutrals, so the
 * same component reads correctly on light pages and under the dark themes.
 */
const EmptyState = ({
  title = 'No data available',
  description,
  reasons = [],
  actionLabel,
  onAction,
  icon,
  isMobile = false,
  minHeight = 220,
  sx = {},
}) => (
  <Box
    role="status"
    sx={{
      minHeight,
      borderRadius: `${borderRadius.base}px`,
      border: '1px dashed',
      borderColor: 'divider',
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
    {icon && <Box sx={{ color: 'text.secondary', display: 'flex', mb: 0.5 }}>{icon}</Box>}
    <Typography
      variant={isMobile ? 'subtitle1' : 'h6'}
      sx={{ fontWeight: typography.fontWeight.semibold, color: 'text.primary' }}
    >
      {title}
    </Typography>
    {description && (
      <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 560 }}>
        {description}
      </Typography>
    )}
    {reasons.length > 0 && (
      <Box component="ul" sx={{ m: 0, mt: 0.5, pl: 2.5, textAlign: 'left', color: 'text.secondary', maxWidth: 560 }}>
        {reasons.map((reason) => (
          <Typography component="li" variant="body2" key={reason} sx={{ mb: 0.25 }}>
            {reason}
          </Typography>
        ))}
      </Box>
    )}
    {actionLabel && onAction && (
      <Button variant="outlined" onClick={onAction} sx={{ mt: 1, minHeight: 44 }}>
        {actionLabel}
      </Button>
    )}
  </Box>
);

export default EmptyState;
