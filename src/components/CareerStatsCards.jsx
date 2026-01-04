import React from 'react';
import { Box } from '@mui/material';
import {
  EmojiEvents as TrophyIcon,
  PercentOutlined as PercentIcon,
  Timer as TimerIcon,
  TrendingUp as TrendingUpIcon,
  GpsFixed as TargetIcon,
  Bolt as FlashIcon
} from '@mui/icons-material';
import StatCard from './ui/StatCard';

const CareerStatsCards = ({ stats, isMobile = false }) => {
  const { overall } = stats;

  if (isMobile) {
    return (
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: 2,
        mb: 3
      }}>
        <StatCard
          label="MATCHES"
          value={overall.matches}
          icon={TrophyIcon}
          variant="primary"
          isMobile={isMobile}
        />
        <StatCard
          label="RUNS"
          value={overall.runs}
          subtitle={`Avg: ${overall.average.toFixed(2)}`}
          icon={TrendingUpIcon}
          variant="primary"
          isMobile={isMobile}
        />
        <StatCard
          label="STRIKE RATE"
          value={overall.strike_rate.toFixed(1)}
          icon={TimerIcon}
          isMobile={isMobile}
        />
        <StatCard
          label="50s/100s"
          value={`${overall.fifties}/${overall.hundreds}`}
          icon={TargetIcon}
          isMobile={isMobile}
        />
        <StatCard
          label="DOT %"
          value={`${overall.dot_percentage.toFixed(1)}%`}
          icon={PercentIcon}
          isMobile={isMobile}
        />
        <StatCard
          label="BOUNDARY %"
          value={`${overall.boundary_percentage.toFixed(1)}%`}
          icon={FlashIcon}
          isMobile={isMobile}
        />
      </Box>
    );
  }

  return (
    <Box sx={{
      display: 'grid',
      gap: 2,
      gridTemplateColumns: {
        xs: '1fr',
        sm: '1fr 1fr',
        md: '1fr 1fr 1fr',
        lg: 'repeat(3, 1fr)'
      },
      mb: 3
    }}>
      <StatCard
        label="MATCHES"
        value={overall.matches}
        subtitle="Total Innings"
        icon={TrophyIcon}
        variant="primary"
        isMobile={isMobile}
      />
      <StatCard
        label="RUNS"
        value={overall.runs}
        subtitle={`Avg: ${overall.average.toFixed(2)}`}
        icon={TrendingUpIcon}
        variant="primary"
        isMobile={isMobile}
      />
      <StatCard
        label="STRIKE RATE"
        value={overall.strike_rate.toFixed(1)}
        icon={TimerIcon}
        isMobile={isMobile}
      />
      <StatCard
        label="50s/100s"
        value={`${overall.fifties}/${overall.hundreds}`}
        subtitle={`${overall.fifties + overall.hundreds} milestone innings`}
        icon={TargetIcon}
        isMobile={isMobile}
      />
      <StatCard
        label="DOT %"
        value={`${overall.dot_percentage.toFixed(1)}%`}
        subtitle="Dot ball percentage"
        icon={PercentIcon}
        isMobile={isMobile}
      />
      <StatCard
        label="BOUNDARY %"
        value={`${overall.boundary_percentage.toFixed(1)}%`}
        subtitle="Boundary percentage"
        icon={FlashIcon}
        isMobile={isMobile}
      />
    </Box>
  );
};

export default CareerStatsCards;
