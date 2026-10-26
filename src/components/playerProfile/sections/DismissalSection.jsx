import React from 'react';
import { Box, Typography } from '@mui/material';
import DismissalFieldDesigner from '../../DismissalFieldDesigner';

const DismissalSection = ({
  dismissalData,
  mode,
  playerName,
  dateRange,
  selectedVenue,
  competitionFilters,
  isMobile,
  loading = false,
}) => {
  if (!dismissalData && loading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">Loading dismissals…</Typography>
      </Box>
    );
  }

  if (!dismissalData) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">No dismissal data available</Typography>
      </Box>
    );
  }

  return (
    <DismissalFieldDesigner
      context={mode === 'bowling' ? 'player_bowling' : 'player_batting'}
      playerName={playerName}
      selectedVenue={selectedVenue}
      startDate={dateRange?.start}
      endDate={dateRange?.end}
      leagues={competitionFilters?.leagues || []}
      includeInternational={!!competitionFilters?.international}
      topTeams={competitionFilters?.topTeams || null}
      isMobile={isMobile}
      summaryData={dismissalData}
    />
  );
};

export default DismissalSection;
