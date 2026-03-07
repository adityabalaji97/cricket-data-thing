import React from 'react';
import { Box } from '@mui/material';
import InningsScatter from '../../InningsScatter';
import StrikeRateProgression from '../../StrikeRateProgression';
import BallRunDistribution from '../../BallRunDistribution';
import StrikeRateIntervals from '../../StrikeRateIntervals';
import ContributionGraph from '../../ContributionGraph';
import FrequentOversChart from '../../FrequentOversChart';
import OverCombinationsChart from '../../OverCombinationsChart';
import BowlingInningsTable from '../../BowlingInningsTable';

const BattingVisualizations = ({ stats, selectedPlayer, dateRange, selectedVenue, competitionFilters }) => {
  if (!stats) return null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <ContributionGraph
        innings={stats.innings || []}
        mode="batter"
        dateRange={dateRange}
      />
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
        <InningsScatter innings={stats.innings || []} />
        <StrikeRateProgression
          selectedPlayer={selectedPlayer}
          dateRange={dateRange}
          selectedVenue={selectedVenue}
          competitionFilters={competitionFilters}
        />
        <BallRunDistribution innings={stats.innings || []} />
        <StrikeRateIntervals ballStats={stats.ball_by_ball_stats || []} />
      </Box>
    </Box>
  );
};

const BowlingVisualizations = ({ stats }) => {
  if (!stats) return null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
        <FrequentOversChart stats={stats} />
        <OverCombinationsChart stats={stats} />
      </Box>
      <BowlingInningsTable stats={stats} />
    </Box>
  );
};

const VisualizationsSection = ({ stats, mode, selectedPlayer, dateRange, selectedVenue, competitionFilters }) => {
  if (mode === 'bowling') {
    return <BowlingVisualizations stats={stats} />;
  }
  return (
    <BattingVisualizations
      stats={stats}
      selectedPlayer={selectedPlayer}
      dateRange={dateRange}
      selectedVenue={selectedVenue}
      competitionFilters={competitionFilters}
    />
  );
};

export default VisualizationsSection;
