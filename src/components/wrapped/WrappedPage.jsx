import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Alert, Skeleton } from '@mui/material';
import WrappedStoryContainer from './WrappedStoryContainer';
import config from '../../config';
import './wrapped.css';

// Default filter settings
const DEFAULT_FILTERS = {
  startDate: '2025-01-01',
  endDate: '2025-12-31',
  leagues: ['IPL', 'BBL', 'PSL', 'SA20', 'BLAST', 'SMASH'],
  leagueValues: [
    'Indian Premier League', 'IPL',
    'Big Bash League', 'BBL',
    'Pakistan Super League', 'PSL',
    'SA20',
    'Vitality Blast', 'T20 Blast',
    'Super Smash'
  ],
  includeInternational: true
};

// Build query string from filters
const buildFilterParams = (filters) => {
  const params = new URLSearchParams();
  
  if (filters.startDate) {
    params.append('start_date', filters.startDate);
  }
  if (filters.endDate) {
    params.append('end_date', filters.endDate);
  }
  
  // Use leagueValues (full names) for API, not league IDs
  const leagueValues = filters.leagueValues || [];
  if (leagueValues.length > 0) {
    leagueValues.forEach(league => {
      params.append('leagues', league);
    });
  } else {
    // Explicitly tell backend no leagues selected (T20I only mode)
    params.append('no_leagues', 'true');
  }
  
  if (filters.includeInternational !== undefined) {
    params.append('include_international', filters.includeInternational);
  }
  
  return params.toString();
};

const WrappedPage = () => {
  const [searchParams] = useSearchParams();
  const [cardsData, setCardsData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Track which cards have been loaded
  const [loadedCardIds, setLoadedCardIds] = useState(new Set());
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  
  // Filter state
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  
  // Ref to track current filters for use in callbacks
  const filtersRef = useRef(filters);
  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);
  
  // Ref to track if lazy cards are being fetched
  const lazyFetchInProgress = useRef(false);
  
  // Get initial card from URL if present
  const initialCardId = searchParams.get('card');

  // Set document title for better social sharing
  useEffect(() => {
    document.title = '2025 In Hindsight - T20 Cricket Wrapped';
    
    // Update OG meta tags dynamically (helps with some mobile share scenarios)
    const updateMetaTag = (property, content) => {
      let meta = document.querySelector(`meta[property="${property}"]`);
      if (meta) {
        meta.setAttribute('content', content);
      }
    };
    
    updateMetaTag('og:title', '2025 In Hindsight - T20 Cricket Wrapped');
    updateMetaTag('og:description', 'Your year in T20 cricket data. Explore the stats, stories, and standout performances of 2025.');
    updateMetaTag('og:url', 'https://hindsight2020.vercel.app/wrapped/2025');
    updateMetaTag('twitter:title', '2025 In Hindsight - T20 Cricket Wrapped');
    updateMetaTag('twitter:description', 'Your year in T20 cricket data. Explore the stats, stories, and standout performances of 2025.');
    
    // Cleanup on unmount
    return () => {
      document.title = 'Hindsight - T20 Cricket Analytics';
    };
  }, []);

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
        
        const filterParams = buildFilterParams(filters);
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards/initial?${filterParams}`);
        
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
  }, []); // Only run once on mount - filter changes handled separately

  // Function to fetch remaining cards in background
  const fetchRemainingCards = useCallback(async () => {
    if (!cardsData?.remaining_card_ids?.length || lazyFetchInProgress.current) {
      return;
    }
    
    lazyFetchInProgress.current = true;
    setIsLoadingMore(true);
    
    try {
      const remainingIds = cardsData.remaining_card_ids;
      const currentFilters = filtersRef.current;
      
      // Fetch in batches of 8 for faster loading
      const batchSize = 8;
      for (let i = 0; i < remainingIds.length; i += batchSize) {
        const batch = remainingIds.slice(i, i + batchSize);
        const cardParams = batch.map(id => `card_ids=${encodeURIComponent(id)}`).join('&');
        const filterParams = buildFilterParams(currentFilters);
        
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards/batch?${cardParams}&${filterParams}`);
        
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

  // Start fetching remaining cards immediately after initial load
  useEffect(() => {
    if (cardsData && !loading && cardsData.remaining_card_ids?.length > 0) {
      // Fetch immediately - no delay
      fetchRemainingCards();
    }
  }, [cardsData, loading, fetchRemainingCards]);

  // Handle filter changes - reset and refetch
  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
    // Reset state for refetch
    setCardsData(null);
    setLoadedCardIds(new Set());
    setLoading(true);
    lazyFetchInProgress.current = false;
    
    const fetchWithFilters = async () => {
      try {
        const filterParams = buildFilterParams(newFilters);
        const response = await fetch(`${config.API_URL}/wrapped/2025/cards/initial?${filterParams}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setCardsData(data);
        setLoadedCardIds(new Set(data.cards.map(c => c.card_id)));
      } catch (err) {
        console.error('Error refetching:', err);
        setError('Failed to load data with new filters.');
      } finally {
        setLoading(false);
      }
    };
    fetchWithFilters();
  }, []);

  // Sort cards based on metadata order and add outro at end
  const getSortedCards = useCallback(() => {
    if (!cardsData?.cards || !metadata?.cards) {
      return cardsData?.cards || [];
    }
    
    const orderMap = new Map(
      metadata.cards.map((card, idx) => [card.id, idx])
    );
    
    const sorted = [...cardsData.cards].sort((a, b) => {
      const orderA = orderMap.get(a.card_id) ?? 999;
      const orderB = orderMap.get(b.card_id) ?? 999;
      return orderA - orderB;
    });
    
    // Add outro card at the end
    const outroCard = {
      card_id: 'outro',
      card_title: "That's a Wrap!",
      card_subtitle: '2025 In Hindsight',
      data: {}
    };
    
    return [...sorted, outroCard];
  }, [cardsData, metadata]);

  if (loading) {
    return (
      <Box className="wrapped-loading">
        <CircularProgress size={60} sx={{ color: '#1DB954' }} />
        <p>Loading 2025 In Hindsight...</p>
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
      onFilterChange={handleFilterChange}
      currentFilters={filters}
    />
  );
};

export default WrappedPage;
