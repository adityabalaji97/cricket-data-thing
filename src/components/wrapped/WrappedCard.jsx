import React from 'react';
import { Box, Typography } from '@mui/material';
import WrappedCardActions from './WrappedCardActions';

// Import card-specific components
import IntroCard from './cards/IntroCard';
import PowerplayBulliesCard from './cards/PowerplayBulliesCard';
import MiddleMerchantsCard from './cards/MiddleMerchantsCard';
import DeathHittersCard from './cards/DeathHittersCard';
import PaceVsSpinCard from './cards/PaceVsSpinCard';
import PowerplayThievesCard from './cards/PowerplayThievesCard';
import NineteenthOverGodsCard from './cards/NineteenthOverGodsCard';
import EloMoversCard from './cards/EloMoversCard';
import VenueVibesCard from './cards/VenueVibesCard';
import './wrapped.css';

// Map card IDs to their specific visualization components
const cardComponents = {
  'intro': IntroCard,
  'powerplay_bullies': PowerplayBulliesCard,
  'middle_merchants': MiddleMerchantsCard,
  'death_hitters': DeathHittersCard,
  'pace_vs_spin': PaceVsSpinCard,
  'powerplay_thieves': PowerplayThievesCard,
  'nineteenth_over_gods': NineteenthOverGodsCard,
  'elo_movers': EloMoversCard,
  'venue_vibes': VenueVibesCard,
};

const WrappedCard = ({ cardData, cardIndex, totalCards }) => {
  if (!cardData) {
    return (
      <Box className="wrapped-card wrapped-card-error">
        <Typography>Card data unavailable</Typography>
      </Box>
    );
  }

  // Check for error in card data
  if (cardData.error) {
    return (
      <Box className="wrapped-card wrapped-card-error">
        <Typography variant="h5">{cardData.card_title || 'Error'}</Typography>
        <Typography>{cardData.error}</Typography>
      </Box>
    );
  }

  // Get the specific card component
  const CardComponent = cardComponents[cardData.card_id];

  return (
    <Box className="wrapped-card">
      {/* Card Header */}
      <Box className="wrapped-card-header">
        <Typography variant="overline" className="wrapped-card-index">
          {cardIndex + 1} / {totalCards}
        </Typography>
        <Typography variant="h4" className="wrapped-card-title">
          {cardData.card_title}
        </Typography>
        <Typography variant="subtitle1" className="wrapped-card-subtitle">
          {cardData.card_subtitle}
        </Typography>
      </Box>

      {/* Card Content - Specific visualization */}
      <Box className="wrapped-card-content">
        {CardComponent ? (
          <CardComponent data={cardData} />
        ) : (
          <Typography>Visualization not available for this card type</Typography>
        )}
      </Box>

      {/* Card Actions */}
      <WrappedCardActions deepLinks={cardData.deep_links} />
    </Box>
  );
};

export default WrappedCard;
