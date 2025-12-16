import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Alert } from '@mui/material';
import WrappedStoryContainer from './WrappedStoryContainer';
import config from '../../config';
import './wrapped.css';

const WrappedPage = () => {
  const [searchParams] = useSearchParams();
  const [cardsData, setCardsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Get initial card from URL if present
  const initialCardId = searchParams.get('card');

  useEffect(() => {
    const fetchWrappedData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setCardsData(data);
      } catch (err) {
        console.error('Error fetching wrapped data:', err);
        setError('Failed to load Wrapped 2025 data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchWrappedData();
  }, []);

  if (loading) {
    return (
      <Box className="wrapped-loading">
        <CircularProgress size={60} sx={{ color: '#1DB954' }} />
        <p>Loading your 2025 Wrapped...</p>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="wrapped-error">
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!cardsData || !cardsData.cards || cardsData.cards.length === 0) {
    return (
      <Box className="wrapped-error">
        <Alert severity="warning">No data available for 2025 Wrapped.</Alert>
      </Box>
    );
  }

  return (
    <WrappedStoryContainer 
      cards={cardsData.cards} 
      initialCardId={initialCardId}
      year={cardsData.year}
    />
  );
};

export default WrappedPage;
