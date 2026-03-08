import React from 'react';
import { Box } from '@mui/material';
import PhasePerformanceRadar from '../../PhasePerformanceRadar';
import PaceSpinBreakdown from '../../PaceSpinBreakdown';
import WicketDistribution from '../../WicketDistribution';
import OverEconomyChart from '../../OverEconomyChart';
import LineLengthProfile from '../LineLengthProfile';

const PerformanceSection = ({ stats, mode, isMobile, playerName, dateRange, selectedVenue, competitionFilters }) => {
  if (!stats) return null;

  if (mode === 'bowling') {
    return (
      <>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
          <WicketDistribution stats={stats} />
          <OverEconomyChart stats={stats} />
        </Box>
        {playerName && (
          <Box sx={{ mt: 3 }}>
            <LineLengthProfile
              playerName={playerName}
              mode="bowling"
              dateRange={dateRange}
              selectedVenue={selectedVenue}
              competitionFilters={competitionFilters}
              isMobile={isMobile}
            />
          </Box>
        )}
      </>
    );
  }

  return (
    <>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
        <PhasePerformanceRadar stats={stats} />
        <PaceSpinBreakdown stats={stats} />
      </Box>
      {playerName && (
        <Box sx={{ mt: 3 }}>
          <LineLengthProfile
            playerName={playerName}
            mode="batting"
            dateRange={dateRange}
            selectedVenue={selectedVenue}
            competitionFilters={competitionFilters}
            isMobile={isMobile}
          />
        </Box>
      )}
    </>
  );
};

export default PerformanceSection;
