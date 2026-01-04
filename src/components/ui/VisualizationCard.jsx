/**
 * VisualizationCard Component - consistent visualization container with slots
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import Card from './Card';
import { colors, spacing, typography } from '../../theme/designSystem';

const VisualizationCard = ({
  title,
  subtitle,
  actions,
  children,
  isMobile = false,
  sx = {},
  headerSx = {},
  contentSx = {},
  ...props
}) => {
  return (
    <Card
      isMobile={isMobile}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        gap: `${spacing.base}px`,
        ...sx,
      }}
      {...props}
    >
      {(title || subtitle || actions) && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: `${spacing.base}px`,
            flexWrap: 'wrap',
            ...headerSx,
          }}
        >
          <Box>
            {title && (
              <Typography
                variant={isMobile ? 'h6' : 'h5'}
                sx={{
                  fontWeight: typography.fontWeight.semibold,
                  color: colors.neutral[900],
                }}
              >
                {title}
              </Typography>
            )}
            {subtitle && (
              <Typography
                variant="body2"
                sx={{
                  mt: `${spacing.xs}px`,
                  color: colors.neutral[600],
                }}
              >
                {subtitle}
              </Typography>
            )}
          </Box>
          {actions && <Box sx={{ marginLeft: 'auto' }}>{actions}</Box>}
        </Box>
      )}

      <Box sx={{ width: '100%', ...contentSx }}>{children}</Box>
    </Card>
  );
};

export default VisualizationCard;
