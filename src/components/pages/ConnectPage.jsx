import React, { useEffect } from 'react';
import { Box } from '@mui/material';
import { colors } from '../../theme/hindsightDark';
import { ConnectorSection } from '../LandingPage';

// The MCP connector's setup (landing plan L4): its own page rather than a home-page section.
// hindsightcricket.com/mcp opened in a browser lands here (vercel.json), and so does the old /#connector.
const ConnectPage = () => {
  useEffect(() => { document.title = 'Use Hindsight in Claude or ChatGPT · Hindsight'; }, []);
  return (
    <Box sx={{ maxWidth: 760, mx: 'auto', px: 2, pt: 2, pb: 3, color: colors.textHi }}>
      <ConnectorSection />
    </Box>
  );
};

export default ConnectPage;
