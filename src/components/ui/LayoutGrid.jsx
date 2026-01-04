/**
 * LayoutGrid Component - Consistent responsive grid layout
 */
import React from 'react';
import { Box } from '@mui/material';
import { spacing } from '../../theme/designSystem';

const LayoutGrid = ({
  children,
  minColumnWidth = 280,
  gap = spacing.lg,
  sx = {},
  ...props
}) => {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: `repeat(auto-fit, minmax(${minColumnWidth}px, 1fr))`,
        gap: `${gap}px`,
        width: '100%',
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

export default LayoutGrid;
