import React, { useEffect } from 'react';
import { Box } from '@mui/material';
import { colors } from '../../theme/hindsightDark';
import { TodaysGamesSection } from '../LandingPage';

// Daily games (the menu overhaul, 5 Nov 2026): the four daily games in one place, as on the home page, instead of four
// menu entries.
const GamesPage = () => {
  useEffect(() => { document.title = 'Daily games · Hindsight'; }, []);
  return (
    <Box sx={{ maxWidth: 960, mx: 'auto', px: 2, pt: 2, pb: 3, color: colors.textHi }}>
      <TodaysGamesSection />
    </Box>
  );
};

export default GamesPage;
