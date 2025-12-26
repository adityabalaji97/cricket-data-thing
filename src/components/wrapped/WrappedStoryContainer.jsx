import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box } from '@mui/material';
import WrappedProgressBar from './WrappedProgressBar';
import WrappedHeader from './WrappedHeader';
import WrappedCard from './WrappedCard';
import { captureAndShare } from '../../utils/shareUtils';
import './wrapped.css';

const WrappedStoryContainer = ({ cards, initialCardId, year, totalCardsAvailable, isLoadingMore, loadedCardIds }) => {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const cardRef = useRef(null);
  
  // Find initial card index
  const getInitialIndex = () => {
    if (initialCardId) {
      const index = cards.findIndex(card => card.card_id === initialCardId);
      return index >= 0 ? index : 0;
    }
    return 0;
  };
  
  const [currentIndex, setCurrentIndex] = useState(getInitialIndex());
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  // Minimum swipe distance (in px)
  const minSwipeDistance = 50;

  const goToNext = useCallback(() => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(prev => prev + 1);
    }
  }, [currentIndex, cards.length]);

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
    }
  }, [currentIndex]);

  const goToCard = useCallback((index) => {
    if (index >= 0 && index < cards.length) {
      setCurrentIndex(index);
    }
  }, [cards.length]);

  const handleClose = () => {
    navigate('/');
  };

  // Share card as image
  const handleShareImage = useCallback(async () => {
    if (!cardRef.current || isSharing) return;
    
    setIsSharing(true);
    try {
      const cardTitle = cards[currentIndex]?.card_title || 'Wrapped';
      await captureAndShare(cardRef.current, cardTitle);
    } catch (error) {
      console.error('Share failed:', error);
    } finally {
      setIsSharing(false);
    }
  }, [cards, currentIndex, isSharing]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        goToNext();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goToPrevious();
      } else if (e.key === 'Escape') {
        handleClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToNext, goToPrevious]);

  // Update URL when card changes
  useEffect(() => {
    const currentCard = cards[currentIndex];
    if (currentCard) {
      const newUrl = `/wrapped/2025?card=${currentCard.card_id}`;
      window.history.replaceState(null, '', newUrl);
    }
  }, [currentIndex, cards]);

  // Touch handlers for swipe
  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;
    
    if (isLeftSwipe) {
      goToNext();
    } else if (isRightSwipe) {
      goToPrevious();
    }
  };

  // Tap navigation (Instagram-style)
  const handleTap = (e) => {
    // Don't trigger tap navigation if clicking on interactive elements
    if (e.target.closest('button') || e.target.closest('a') || e.target.closest('.MuiSlider-root')) {
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const containerWidth = rect.width;

    // Left third = previous, right two-thirds = next
    if (x < containerWidth / 3) {
      goToPrevious();
    } else {
      goToNext();
    }
  };

  const currentCard = cards[currentIndex];

  return (
    <Box 
      ref={containerRef}
      className="wrapped-container"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onClick={handleTap}
    >
      {/* Top Section: Progress + Header */}
      <div className="wrapped-top-section">
        {/* Progress Bar */}
        <WrappedProgressBar 
          totalCards={totalCardsAvailable || cards.length} 
          currentIndex={currentIndex}
          onProgressClick={goToCard}
          loadedCount={cards.length}
          isLoadingMore={isLoadingMore}
        />

        {/* Header Row */}
        <WrappedHeader 
          onMenuClick={() => setShowFilterMenu(true)}
          onClose={handleClose}
        />
      </div>

      {/* Current Card */}
      <WrappedCard 
        ref={cardRef}
        cardData={currentCard}
        cardIndex={currentIndex}
        totalCards={cards.length}
        onShareImage={handleShareImage}
        isSharing={isSharing}
      />

      {/* Navigation hints */}
      <Box className="wrapped-nav-hints">
        {currentIndex > 0 && <span className="nav-hint nav-hint-left">‹</span>}
        {currentIndex < cards.length - 1 && <span className="nav-hint nav-hint-right">›</span>}
      </Box>
    </Box>
  );
};

export default WrappedStoryContainer;
