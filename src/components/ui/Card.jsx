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
  sx = {},
  ...props
}) => {
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
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

export default Card;
