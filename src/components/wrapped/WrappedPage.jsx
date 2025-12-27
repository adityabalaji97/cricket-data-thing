import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Alert, Skeleton } from '@mui/material';
import WrappedStoryContainer from './WrappedStoryContainer';
import config from '../../config';
import './wrapped.css';

const WrappedPage = () => {
  const [searchParams] = useSearchParams();
  const [cardsData, setCardsData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Track which cards have been loaded
  const [loadedCardIds, setLoadedCardIds] = useState(new Set());
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  
  // Ref to track if lazy cards are being fetched
  const lazyFetchInProgress = useRef(false);
  
  // Get initial card from URL if present
  const initialCardId = searchParams.get('card');

  // Fetch metadata first (instant)
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const response = await fetch(`${config.API_URL}/wrapped/2025/metadata`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setMetadata(data);
      } catch (err) {
        console.error('Error fetching metadata:', err);
      }
    };
    fetchMetadata();
  }, []);

  // Fetch initial cards
  useEffect(() => {
    const fetchInitialCards = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards/initial`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setCardsData(data);
        
        // Track loaded card IDs
        const loadedIds = new Set(data.cards.map(c => c.card_id));
        setLoadedCardIds(loadedIds);
        
      } catch (err) {
        console.error('Error fetching initial wrapped data:', err);
        setError('Failed to load Wrapped 2025 data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchInitialCards();
  }, []);

  // Function to fetch remaining cards in background
  const fetchRemainingCards = useCallback(async () => {
    if (!cardsData?.remaining_card_ids?.length || lazyFetchInProgress.current) {
      return;
    }
    
    lazyFetchInProgress.current = true;
    setIsLoadingMore(true);
    
    try {
      const remainingIds = cardsData.remaining_card_ids;
      
      // Fetch in batches of 8 for faster loading
      const batchSize = 8;
      for (let i = 0; i < remainingIds.length; i += batchSize) {
        const batch = remainingIds.slice(i, i + batchSize);
        const queryParams = batch.map(id => `card_ids=${encodeURIComponent(id)}`).join('&');
        
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards/batch?${queryParams}`);
        
        if (!response.ok) {
          console.error(`Error fetching batch: ${response.status}`);
          continue;
        }
        
        const batchData = await response.json();
        
        // Merge new cards with existing
        setCardsData(prev => {
          if (!prev) return prev;
          
          const existingIds = new Set(prev.cards.map(c => c.card_id));
          const newCards = batchData.cards.filter(c => !existingIds.has(c.card_id));
          
          // Maintain order based on metadata
          const allCards = [...prev.cards, ...newCards];
          
          return {
            ...prev,
            cards: allCards,
            total_cards: allCards.length
          };
        });
        
        // Update loaded IDs
        setLoadedCardIds(prev => {
          const updated = new Set(prev);
          batch.forEach(id => updated.add(id));
          return updated;
        });
      }
      
      // Clear remaining_card_ids to prevent re-fetching
      setCardsData(prev => ({
        ...prev,
        remaining_card_ids: []
      }));
    } catch (err) {
      console.error('Error fetching remaining cards:', err);
    } finally {
      setIsLoadingMore(false);
      // Don't reset lazyFetchInProgress - keep it true to prevent re-triggering
    }
  }, [cardsData]);

  // Start fetching remaining cards after initial load
  useEffect(() => {
    if (cardsData && !loading && cardsData.remaining_card_ids?.length > 0) {
      // Use requestIdleCallback to fetch when browser is idle (no arbitrary delay)
      if ('requestIdleCallback' in window) {
        const idleId = requestIdleCallback(() => {
          fetchRemainingCards();
        }, { timeout: 100 }); // Max 100ms wait
        return () => cancelIdleCallback(idleId);
      } else {
        // Fallback for Safari - minimal delay
        const timer = setTimeout(fetchRemainingCards, 50);
        return () => clearTimeout(timer);
      }
    }
  }, [cardsData, loading, fetchRemainingCards]);

  // Sort cards based on metadata order
  const getSortedCards = useCallback(() => {
    if (!cardsData?.cards || !metadata?.cards) {
      return cardsData?.cards || [];
    }
    
    const orderMap = new Map(
      metadata.cards.map((card, idx) => [card.id, idx])
    );
    
    return [...cardsData.cards].sort((a, b) => {
      const orderA = orderMap.get(a.card_id) ?? 999;
      const orderB = orderMap.get(b.card_id) ?? 999;
      return orderA - orderB;
    });
  }, [cardsData, metadata]);

  if (loading) {
    return (
      <Box className="wrapped-loading">
        <CircularProgress size={60} sx={{ color: '#1DB954' }} />
        <p>Loading 2025 In Hindsight...</p>
        {metadata && (
          <p style={{ fontSize: '0.9rem', opacity: 0.7, marginTop: '0.5rem' }}>
            {metadata.total_cards} cards to explore
          </p>
        )}
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

  const sortedCards = getSortedCards();

  return (
    <WrappedStoryContainer 
      cards={sortedCards} 
      initialCardId={initialCardId}
      year={cardsData.year}
      totalCardsAvailable={metadata?.total_cards || sortedCards.length}
      isLoadingMore={isLoadingMore}
      loadedCardIds={loadedCardIds}
    />
  );
};

export default WrappedPage;
