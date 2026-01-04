import React from 'react';
import { Box, Skeleton as MuiSkeleton } from '@mui/material';
import { Card, Section, Skeleton, VisualizationCard } from '../ui';
import { borderRadius, spacing } from '../../theme/designSystem';

const PlayerProfileLoadingState = ({ isMobile = false }) => {
  const chartHeight = isMobile ? 220 : 280;

  const renderChartSkeleton = () => (
    <MuiSkeleton
      variant="rectangular"
      height={chartHeight}
      sx={{ borderRadius: `${borderRadius.base}px` }}
    />
  );

  const renderVisualizationSkeleton = (title) => (
    <VisualizationCard title={title} isMobile={isMobile}>
      {renderChartSkeleton()}
    </VisualizationCard>
  );

  return (
    <Box sx={{ mt: isMobile ? 2 : 0 }}>
      <Section title="Career Overview" isMobile={isMobile} columns="1fr" disableTopSpacing>
        <Skeleton.Grid cols={4} rows={1} isMobile={isMobile} />

        <Card isMobile={isMobile}>
          <MuiSkeleton width="40%" height={24} sx={{ mb: `${spacing.sm}px` }} />
          <MuiSkeleton width="90%" height={16} sx={{ mb: `${spacing.xs}px` }} />
          <MuiSkeleton width="85%" height={16} sx={{ mb: `${spacing.xs}px` }} />
          <MuiSkeleton width="70%" height={16} />
        </Card>

        {renderVisualizationSkeleton('Contribution Timeline')}
      </Section>

      <Section
        title="Shot Analysis"
        isMobile={isMobile}
        columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
      >
        {renderVisualizationSkeleton('Wagon Wheel')}
        {renderVisualizationSkeleton('Pitch Map')}
      </Section>

      <Section
        title="Performance Breakdown"
        isMobile={isMobile}
        columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
      >
        {renderVisualizationSkeleton('Phase Radar')}
        {renderVisualizationSkeleton('Pace vs Spin')}
        {renderVisualizationSkeleton('Innings Scatter')}
        {renderVisualizationSkeleton('Strike Rate Progression')}
        {renderVisualizationSkeleton('Ball Run Distribution')}
        {renderVisualizationSkeleton('SR Progression')}
      </Section>

      <Section
        title="Performance Highlights"
        isMobile={isMobile}
        columns={{ xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' }}
      >
        {renderVisualizationSkeleton('Top Innings')}
        {renderVisualizationSkeleton('Bowling Type Matchups')}
      </Section>
    </Box>
  );
};

export default PlayerProfileLoadingState;
