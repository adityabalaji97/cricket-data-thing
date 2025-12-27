import React from 'react';
import { Box } from '@mui/material';
import './wrapped.css';

const WrappedProgressBar = ({ totalCards, currentIndex, onProgressClick, loadedCount, isLoadingMore }) => {
  return (
    <Box className="wrapped-progress-bar">
      {Array.from({ length: totalCards }, (_, index) => {
        const isLoaded = index < loadedCount;
        const isActive = index === currentIndex;
        const isCompleted = index < currentIndex;
        
        return (
          <Box
            key={index}
            className={`progress-segment ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${!isLoaded ? 'unloaded' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              // Only allow clicking on loaded cards
              if (isLoaded) {
                onProgressClick(index);
              }
            }}
            style={{
              cursor: isLoaded ? 'pointer' : 'default',
              opacity: isLoaded ? 1 : 0.3
            }}
          />
        );
      })}

    </Box>
  );
};

export default WrappedProgressBar;
