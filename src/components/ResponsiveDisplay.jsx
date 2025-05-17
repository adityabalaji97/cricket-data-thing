import React from 'react';
import { Box, useMediaQuery, useTheme } from '@mui/material';

// Component to conditionally render content based on screen size
const ResponsiveDisplay = ({ 
  desktopContent, 
  mobileContent, 
  breakpoint = 'md' 
}) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up(breakpoint));
  
  return (
    <Box>
      {isDesktop ? desktopContent : mobileContent}
    </Box>
  );
};

export default ResponsiveDisplay;