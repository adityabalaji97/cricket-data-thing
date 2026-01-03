/**
 * StatCard Component - Consistent stat display
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import Card from './Card';
import { colors, spacing, typography, transitions } from '../../theme/designSystem';

const StatCard = ({
  label,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = 'default', // default, primary, success, warning, error
  isMobile = false,
  onClick,
}) => {
  const variantColors = {
    default: {
      bg: colors.neutral[50],
      text: colors.neutral[900],
      iconBg: colors.neutral[100],
      iconColor: colors.neutral[600],
    },
    primary: {
      bg: colors.primary[50],
      text: colors.primary[900],
      iconBg: colors.primary[100],
      iconColor: colors.primary[600],
    },
    success: {
      bg: colors.success[50],
      text: colors.success[900],
      iconBg: colors.success[100],
      iconColor: colors.success[600],
    },
    warning: {
      bg: colors.warning[50],
      text: colors.warning[900],
      iconBg: colors.warning[100],
      iconColor: colors.warning[600],
    },
    error: {
      bg: colors.error[50],
      text: colors.error[900],
      iconBg: colors.error[100],
      iconColor: colors.error[600],
    },
  };

  const colorScheme = variantColors[variant] || variantColors.default;

  return (
    <Card
      isMobile={isMobile}
      hover={!!onClick}
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        backgroundColor: colorScheme.bg,
        borderColor: colors.neutral[200],
      }}
      onClick={onClick}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="body2"
            sx={{
              color: colors.neutral[600],
              fontSize: isMobile ? typography.fontSize.xs : typography.fontSize.sm,
              fontWeight: typography.fontWeight.medium,
              mb: `${spacing.xs}px`,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {label}
          </Typography>

          <Typography
            variant={isMobile ? 'h5' : 'h3'}
            sx={{
              color: colorScheme.text,
              fontWeight: typography.fontWeight.bold,
              lineHeight: typography.lineHeight.tight,
              mb: subtitle || trend ? `${spacing.xs}px` : 0,
            }}
          >
            {value}
          </Typography>

          {subtitle && (
            <Typography
              variant="body2"
              sx={{
                color: colors.neutral[600],
                fontSize: isMobile ? typography.fontSize.xs : typography.fontSize.sm,
              }}
            >
              {subtitle}
            </Typography>
          )}

          {trend && (
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: `${spacing.xs}px`,
                mt: `${spacing.xs}px`,
                px: `${spacing.sm}px`,
                py: `${spacing.xs}px`,
                borderRadius: `${spacing.xs}px`,
                backgroundColor: trend.positive ? colors.success[100] : colors.error[100],
                color: trend.positive ? colors.success[700] : colors.error[700],
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: typography.fontWeight.semibold }}>
                {trend.value}
              </Typography>
              {trend.label && (
                <Typography variant="caption" sx={{ fontSize: typography.fontSize.xs }}>
                  {trend.label}
                </Typography>
              )}
            </Box>
          )}
        </Box>

        {Icon && (
          <Box
            sx={{
              width: isMobile ? 40 : 48,
              height: isMobile ? 40 : 48,
              borderRadius: `${spacing.md}px`,
              backgroundColor: colorScheme.iconBg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              ml: `${spacing.md}px`,
              transition: `all ${transitions.base}`,
            }}
          >
            <Icon sx={{ fontSize: isMobile ? 20 : 24, color: colorScheme.iconColor }} />
          </Box>
        )}
      </Box>
    </Card>
  );
};

export default StatCard;
