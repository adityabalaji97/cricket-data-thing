import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import { useNavigate } from 'react-router-dom';

const OutroCard = ({ data, onNavigateToCard, availableCards = [] }) => {
  const navigate = useNavigate();

  const handleCardClick = (cardId) => {
    // Use callback if provided (for in-place navigation)
    if (onNavigateToCard) {
      onNavigateToCard(cardId);
    } else {
      // Fallback to URL navigation
      window.history.replaceState(null, '', `/wrapped/2025?card=${cardId}`);
      window.location.reload();
    }
  };

  const handleHomeClick = () => {
    navigate('/');
  };

  // Filter out the outro card itself from the list
  const cardList = availableCards.filter(card => card.card_id !== 'outro');

  return (
    <Box className="outro-card-content" sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center',
      gap: 2,
      width: '100%',
      maxWidth: 400,
      mx: 'auto'
    }}>
      {/* Thank you message */}
      <Typography 
        variant="h5" 
        sx={{ 
          textAlign: 'center', 
          color: '#1DB954',
          fontWeight: 700,
          mb: 1
        }}
      >
        Thanks for exploring!
      </Typography>
      
      <Typography 
        variant="body2" 
        sx={{ 
          textAlign: 'center', 
          color: '#b3b3b3',
          mb: 2
        }}
      >
        Revisit any insight or head back home
      </Typography>

      {/* Card Links - Scrollable list */}
      <Box sx={{ 
        maxHeight: 280,
        overflowY: 'auto',
        width: '100%',
        px: 1,
        '&::-webkit-scrollbar': {
          width: 4,
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: '#444',
          borderRadius: 2,
        }
      }}>
        {cardList.map((card, index) => (
          <Box
            key={card.card_id}
            onClick={() => handleCardClick(card.card_id)}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              py: 1,
              px: 1.5,
              cursor: 'pointer',
              borderRadius: 1,
              transition: 'background-color 0.2s',
              '&:hover': {
                backgroundColor: 'rgba(29, 185, 84, 0.15)',
              },
              borderBottom: '1px solid rgba(255,255,255,0.05)'
            }}
          >
            <Typography 
              variant="caption" 
              sx={{ 
                color: '#1DB954',
                fontWeight: 600,
                minWidth: 24
              }}
            >
              {String(index + 1).padStart(2, '0')}
            </Typography>
            <Typography 
              variant="body2" 
              sx={{ 
                color: '#fff',
                fontSize: '0.85rem'
              }}
            >
              {card.card_title}
            </Typography>
          </Box>
        ))}
      </Box>

      {/* Home Button */}
      <Button
        variant="contained"
        startIcon={<HomeIcon />}
        onClick={handleHomeClick}
        sx={{
          mt: 2,
          backgroundColor: '#1DB954',
          color: '#000',
          fontWeight: 600,
          px: 4,
          py: 1,
          borderRadius: 50,
          textTransform: 'none',
          '&:hover': {
            backgroundColor: '#1ed760',
          }
        }}
      >
        Back to Hindsight
      </Button>
    </Box>
  );
};

export default OutroCard;
