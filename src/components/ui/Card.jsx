/**
 * Card Component - Consistent card wrapper with world-class styling
 */
import React from 'react';
import { Box } from '@mui/material';
import { components, colors, shadows, transitions } from '../../theme/designSystem';

const Card = ({
  children,
  isMobile = false,
  hover = false,
  noPadding = false,
  shareFrame = false,
  shareFrameLabel = 'Cricket Data Thing',
  sx = {},
  ...props
}) => {
  const shareFrameStyles = shareFrame
    ? {
        background: `linear-gradient(135deg, ${colors.neutral[0]} 0%, ${colors.neutral[50]} 100%)`,
        borderColor: colors.neutral[200],
        position: 'relative',
        overflow: 'hidden',
        '&::after': {
          content: `"${shareFrameLabel}"`,
          position: 'absolute',
          bottom: 8,
          right: 12,
          fontSize: '0.65rem',
          color: colors.neutral[400],
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          opacity: 0.6,
          pointerEvents: 'none',
        },
      }
    : {};

  return (
    <Box
      sx={{
        backgroundColor: components.card.background,
        border: components.card.border,
        borderRadius: `${components.card.borderRadius}px`,
        boxShadow: shadows.sm,
        padding: noPadding
          ? 0
          : isMobile
          ? `${components.card.padding.mobile}px`
          : `${components.card.padding.desktop}px`,
        transition: `all ${transitions.base}`,
        ...(hover && {
          '&:hover': {
            boxShadow: shadows.base,
            borderColor: components.card.hover.borderColor,
            transform: 'translateY(-2px)',
          },
        }),
        ...shareFrameStyles,
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

export default Card;
