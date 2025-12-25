import React, { forwardRef } from 'react';
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
import MiddleOversSqueezeCard from './cards/MiddleOversSqueezeCard';
import EloMoversCard from './cards/EloMoversCard';
import VenueVibesCard from './cards/VenueVibesCard';
import ControlledAggressionCard from './cards/ControlledAggressionCard';
import ThreeSixtyBattersCard from './cards/ThreeSixtyBattersCard';
import BatterHandBreakdownCard from './cards/BatterHandBreakdownCard';
import LengthMastersCard from './cards/LengthMastersCard';
import RareShotSpecialistsCard from './cards/RareShotSpecialistsCard';
import BowlerTypeDominanceCard from './cards/BowlerTypeDominanceCard';
import SweepEvolutionCard from './cards/SweepEvolutionCard';
import NeedleMoversCard from './cards/NeedleMoversCard';
import ChaseMastersCard from './cards/ChaseMastersCard';
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
  'middle_overs_squeeze': MiddleOversSqueezeCard,
  'elo_movers': EloMoversCard,
  'venue_vibes': VenueVibesCard,
  'controlled_aggression': ControlledAggressionCard,
  '360_batters': ThreeSixtyBattersCard,
  'batter_hand_breakdown': BatterHandBreakdownCard,
  'length_masters': LengthMastersCard,
  'rare_shot_specialists': RareShotSpecialistsCard,
  'bowler_type_dominance': BowlerTypeDominanceCard,
  'sweep_evolution': SweepEvolutionCard,
  'needle_movers': NeedleMoversCard,
  'chase_masters': ChaseMastersCard,
};

const WrappedCard = forwardRef(({ cardData, cardIndex, totalCards, onShareImage, isSharing }, ref) => {
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
    <Box className="wrapped-card" ref={ref}>
      {/* Card Body - Vertically centered */}
      <Box className="wrapped-card-body">
        {/* Card Header */}
        <Box className="wrapped-card-header">
          <Typography variant="h4" className="wrapped-card-title">
            {cardData.card_title}
          </Typography>
          {cardData.card_subtitle && (
            <Typography variant="subtitle1" className="wrapped-card-subtitle">
              {cardData.card_subtitle}
            </Typography>
          )}
        </Box>

        {/* Card Content - Specific visualization */}
        <Box className="wrapped-card-content">
          {CardComponent ? (
            <CardComponent data={cardData} />
          ) : (
            <Typography>Visualization not available for this card type</Typography>
          )}
        </Box>
      </Box>

      {/* Card Actions - Stays at bottom */}
      <WrappedCardActions 
        deepLinks={cardData.deep_links} 
        onShareImage={onShareImage}
        isSharing={isSharing}
      />
    </Box>
  );
});

WrappedCard.displayName = 'WrappedCard';

export default WrappedCard;
