/**
 * Skeleton Component - Loading states
 */
import React from 'react';
import { Box, Skeleton as MuiSkeleton } from '@mui/material';
import Card from './Card';
import { spacing, borderRadius, colors } from '../../theme/designSystem';

export const SkeletonCard = ({ isMobile = false, height = 200 }) => {
  return (
    <Card isMobile={isMobile}>
      <MuiSkeleton
        variant="rectangular"
        width="100%"
        height={height}
        sx={{ borderRadius: `${borderRadius.base}px` }}
      />
    </Card>
  );
};

export const SkeletonStatCard = ({ isMobile = false }) => {
  return (
    <Card isMobile={isMobile}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Box sx={{ flex: 1 }}>
          <MuiSkeleton width="60%" height={16} sx={{ mb: `${spacing.sm}px` }} />
          <MuiSkeleton width="80%" height={32} sx={{ mb: `${spacing.xs}px` }} />
          <MuiSkeleton width="50%" height={14} />
        </Box>
        <MuiSkeleton
          variant="circular"
          width={isMobile ? 40 : 48}
          height={isMobile ? 40 : 48}
        />
      </Box>
    </Card>
  );
};

export const SkeletonTable = ({ rows = 5, isMobile = false }) => {
  return (
    <Card isMobile={isMobile}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.base}px` }}>
        {/* Header */}
        <Box sx={{ display: 'flex', gap: `${spacing.md}px` }}>
          <MuiSkeleton width="20%" height={20} />
          <MuiSkeleton width="15%" height={20} />
          <MuiSkeleton width="15%" height={20} />
          <MuiSkeleton width="20%" height={20} />
        </Box>
        {/* Rows */}
        {Array.from({ length: rows }).map((_, idx) => (
          <Box key={idx} sx={{ display: 'flex', gap: `${spacing.md}px` }}>
            <MuiSkeleton width="20%" height={16} />
            <MuiSkeleton width="15%" height={16} />
            <MuiSkeleton width="15%" height={16} />
            <MuiSkeleton width="20%" height={16} />
          </Box>
        ))}
      </Box>
    </Card>
  );
};

export const SkeletonGrid = ({ cols = 3, rows = 2, isMobile = false }) => {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : `repeat(${cols}, 1fr)`,
        gap: `${spacing.base}px`,
      }}
    >
      {Array.from({ length: cols * rows }).map((_, idx) => (
        <SkeletonStatCard key={idx} isMobile={isMobile} />
      ))}
    </Box>
  );
};

export default {
  Card: SkeletonCard,
  StatCard: SkeletonStatCard,
  Table: SkeletonTable,
  Grid: SkeletonGrid,
};
