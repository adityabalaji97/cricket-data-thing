import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box } from '@mui/material';
import WrappedProgressBar from './WrappedProgressBar';
import WrappedHeader from './WrappedHeader';
import WrappedCard from './WrappedCard';
import WrappedFilterModal from './WrappedFilterModal';
import { captureAndShare } from '../../utils/shareUtils';
import './wrapped.css';

const WrappedStoryContainer = ({ cards, initialCardId, year, totalCardsAvailable, isLoadingMore, loadedCardIds, onFilterChange, currentFilters }) => {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const cardRef = useRef(null);
  
  // Track if we've navigated to the initial card (to handle lazy-loaded cards)
  const hasNavigatedToInitial = useRef(false);
  
  // Track scroll position to prevent tap navigation during scroll
  const scrollStartY = useRef(null);
  const didScroll = useRef(false);
  
  // Find initial card index
  const getInitialIndex = () => {
    if (initialCardId) {
      const index = cards.findIndex(card => card.card_id === initialCardId);
      if (index >= 0) {
        hasNavigatedToInitial.current = true;
        return index;
      }
      return 0; // Card not loaded yet, will be handled by effect
    }
    hasNavigatedToInitial.current = true; // No target card, so we're "done"
    return 0;
  };
  
  const [currentIndex, setCurrentIndex] = useState(getInitialIndex());
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  // Minimum swipe distance (in px)
  const minSwipeDistance = 50;
  // Minimum scroll distance to consider it a scroll (not a tap)
  const minScrollDistance = 10;

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

  // Navigate to initial card once it's loaded (handles lazy-loaded cards on refresh)
  useEffect(() => {
    if (hasNavigatedToInitial.current || !initialCardId) return;
    
    const targetIndex = cards.findIndex(card => card.card_id === initialCardId);
    if (targetIndex >= 0) {
      hasNavigatedToInitial.current = true;
      setCurrentIndex(targetIndex);
    }
  }, [cards, initialCardId]);

  // Touch handlers for swipe (horizontal navigation)
  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
    scrollStartY.current = e.targetTouches[0].clientY;
    didScroll.current = false;
  };

  const onTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX);
    
    // Check if user is scrolling vertically
    if (scrollStartY.current !== null) {
      const deltaY = Math.abs(e.targetTouches[0].clientY - scrollStartY.current);
      if (deltaY > minScrollDistance) {
        didScroll.current = true;
      }
    }
  };

  const onTouchEnd = () => {
    // Don't navigate if user was scrolling
    if (didScroll.current) {
      setTouchStart(null);
      setTouchEnd(null);
      // Reset after a short delay so next interaction works
      setTimeout(() => {
        didScroll.current = false;
      }, 100);
      return;
    }
    
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;
    
    if (isLeftSwipe) {
      goToNext();
    } else if (isRightSwipe) {
      goToPrevious();
    }
    
    // Reset scroll tracking
    didScroll.current = false;
  };

  // Tap navigation for areas outside nav targets (middle of screen)
  const handleContainerClick = (e) => {
    // Don't trigger if clicking on interactive elements or nav targets
    if (
      e.target.closest('button') || 
      e.target.closest('a') || 
      e.target.closest('.MuiSlider-root') ||
      e.target.closest('.wrapped-nav-target') ||
      e.target.closest('.wrapped-card-actions')
    ) {
      return;
    }
    
    // Don't trigger if user was scrolling
    if (didScroll.current) {
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const containerWidth = rect.width;

    // Left 20% = previous, right 80% = next
    if (x < containerWidth * 0.2) {
      goToPrevious();
    } else {
      goToNext();
    }
  };

  // Navigation button handlers (for dedicated touch targets)
  const handlePrevClick = (e) => {
    e.stopPropagation();
    e.preventDefault();
    goToPrevious();
  };

  const handleNextClick = (e) => {
    e.stopPropagation();
    e.preventDefault();
    goToNext();
  };

  const currentCard = cards[currentIndex];

  return (
    <Box 
      ref={containerRef}
      className="wrapped-container"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onClick={handleContainerClick}
    >
      {/* Top Section: Progress + Header - Fixed position */}
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
          onMenuClick={() => setShowFilterModal(true)}
          onClose={handleClose}
        />
      </div>

      {/* Filter Modal */}
      <WrappedFilterModal
        open={showFilterModal}
        onClose={() => setShowFilterModal(false)}
        onApply={onFilterChange}
        currentFilters={currentFilters}
      />

      {/* Navigation Touch Targets - Separate elements that don't propagate */}
      <div 
        className="wrapped-nav-target wrapped-nav-target-left"
        onClick={handlePrevClick}
        onTouchEnd={(e) => {
          e.stopPropagation();
          if (!didScroll.current) {
            goToPrevious();
          }
        }}
        aria-label="Previous card"
      >
        {currentIndex > 0 && <span className="nav-hint">‹</span>}
      </div>
      <div 
        className="wrapped-nav-target wrapped-nav-target-right"
        onClick={handleNextClick}
        onTouchEnd={(e) => {
          e.stopPropagation();
          if (!didScroll.current) {
            goToNext();
          }
        }}
        aria-label="Next card"
      >
        {currentIndex < cards.length - 1 && <span className="nav-hint">›</span>}
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
    </Box>
  );
};

export default WrappedStoryContainer;
