/**
 * Section Component - Visual sections with headers and descriptions
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import { components, colors, spacing, typography } from '../../theme/designSystem';

const Section = ({
  title,
  description,
  action,
  children,
  isMobile = false,
  sx = {},
}) => {
  const sectionSpacing = isMobile
    ? components.section.spacing.mobile
    : components.section.spacing.desktop;

  return (
    <Box sx={{ mb: `${sectionSpacing}px`, ...sx }}>
      {/* Section Header */}
      {(title || description || action) && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'flex-start' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            mb: `${spacing.base}px`,
            gap: isMobile ? `${spacing.sm}px` : 0,
          }}
        >
          <Box sx={{ flex: 1 }}>
            {title && (
              <Typography
                variant={isMobile ? 'h5' : 'h4'}
                sx={{
                  fontWeight: typography.fontWeight.semibold,
                  color: colors.neutral[900],
                  mb: description ? `${spacing.xs}px` : 0,
                }}
              >
                {title}
              </Typography>
            )}
            {description && (
              <Typography
                variant="body2"
                sx={{
                  color: colors.neutral[600],
                  maxWidth: isMobile ? '100%' : '600px',
                }}
              >
                {description}
              </Typography>
            )}
          </Box>
          {action && <Box>{action}</Box>}
        </Box>
      )}

      {/* Section Content */}
      {children}
    </Box>
  );
};

export default Section;
