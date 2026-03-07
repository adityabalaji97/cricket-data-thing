import React from 'react';
import { Box } from '@mui/material';
import PhasePerformanceRadar from '../../PhasePerformanceRadar';
import PaceSpinBreakdown from '../../PaceSpinBreakdown';
import WicketDistribution from '../../WicketDistribution';
import OverEconomyChart from '../../OverEconomyChart';

const PerformanceSection = ({ stats, mode, isMobile }) => {
  if (!stats) return null;

  if (mode === 'bowling') {
    return (
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
        <WicketDistribution stats={stats} />
        <OverEconomyChart stats={stats} />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
      <PhasePerformanceRadar stats={stats} />
      <PaceSpinBreakdown stats={stats} />
    </Box>
  );
};

export default PerformanceSection;
