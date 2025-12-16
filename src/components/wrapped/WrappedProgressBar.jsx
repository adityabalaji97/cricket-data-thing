import React from 'react';
import { Box } from '@mui/material';
import './wrapped.css';

const WrappedProgressBar = ({ totalCards, currentIndex, onProgressClick }) => {
  return (
    <Box className="wrapped-progress-bar">
      {Array.from({ length: totalCards }, (_, index) => (
        <Box
          key={index}
          className={`progress-segment ${index === currentIndex ? 'active' : ''} ${index < currentIndex ? 'completed' : ''}`}
          onClick={(e) => {
            e.stopPropagation();
            onProgressClick(index);
          }}
        />
      ))}
    </Box>
  );
};

export default WrappedProgressBar;
