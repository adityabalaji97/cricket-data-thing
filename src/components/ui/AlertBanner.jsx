import React from 'react';
import { Alert } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { borderRadius, colors, spacing, typography } from '../../theme/designSystem';

const severityTokens = {
  error: {
    base: colors.error[600],
    background: colors.error[50],
  },
  warning: {
    base: colors.warning[600],
    background: colors.warning[50],
  },
  info: {
    base: colors.primary[600],
    background: colors.primary[50],
  },
  success: {
    base: colors.success[600],
    background: colors.success[50],
  },
};

const AlertBanner = ({ severity = 'info', sx = {}, children, ...props }) => {
  const tokens = severityTokens[severity] ?? severityTokens.info;

  return (
    <Alert
      severity={severity}
      variant="outlined"
      sx={{
        borderRadius: `${borderRadius.base}px`,
        borderColor: alpha(tokens.base, 0.35),
        backgroundColor: tokens.background,
        color: colors.neutral[900],
        px: `${spacing.base}px`,
        py: `${spacing.sm}px`,
        alignItems: 'center',
        '.MuiAlert-icon': {
          color: tokens.base,
        },
        '.MuiAlert-message': {
          fontSize: typography.fontSize.sm,
          color: colors.neutral[800],
        },
        ...sx,
      }}
      {...props}
    >
      {children}
    </Alert>
  );
};

export default AlertBanner;
