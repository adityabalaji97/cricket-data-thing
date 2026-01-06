import React from 'react';
import { Box, Skeleton as MuiSkeleton } from '@mui/material';
import { Card, Section, Skeleton, VisualizationCard } from '../ui';
import { borderRadius, spacing } from '../../theme/designSystem';

const BowlerProfileLoadingState = ({ isMobile = false }) => {
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
      {/* Overview Section */}
      <Section title="Overview" isMobile={isMobile} columns="1fr" disableTopSpacing>
        {/* Skeleton for BowlingCareerStatsCards - 6 stat cards */}
        <Skeleton.Grid cols={isMobile ? 2 : 3} rows={2} isMobile={isMobile} />

        {/* Skeleton for PlayerDNASummary */}
        <Card isMobile={isMobile}>
          <MuiSkeleton width="40%" height={24} sx={{ mb: `${spacing.sm}px` }} />
          <MuiSkeleton width="90%" height={16} sx={{ mb: `${spacing.xs}px` }} />
          <MuiSkeleton width="85%" height={16} sx={{ mb: `${spacing.xs}px` }} />
          <MuiSkeleton width="70%" height={16} />
        </Card>
      </Section>

      {/* Bowling Performance Section */}
      <Section
        title="Bowling Performance"
        subtitle="Phase-wise wickets, economy rates, and over-by-over analysis"
        isMobile={isMobile}
        columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
      >
        {renderVisualizationSkeleton('Wicket Distribution')}
        {renderVisualizationSkeleton('Over Economy')}
        {renderVisualizationSkeleton('Frequent Overs')}
        {renderVisualizationSkeleton('Over Combinations')}
      </Section>

      {/* Innings Details Section */}
      <Section
        title="Innings Details"
        subtitle="Complete breakdown of individual bowling performances"
        isMobile={isMobile}
        columns="1fr"
      >
        <VisualizationCard title="Bowling Innings" isMobile={isMobile}>
          <Box sx={{ pt: `${spacing.base}px` }}>
            <MuiSkeleton variant="rectangular" height={400} sx={{ borderRadius: `${borderRadius.base}px` }} />
          </Box>
        </VisualizationCard>
      </Section>
    </Box>
  );
};

export default BowlerProfileLoadingState;
