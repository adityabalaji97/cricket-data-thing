import React from 'react';
import { Box, Typography } from '@mui/material';
import { spacing } from '../theme/designSystem';
import Card from './ui/Card';

const BowlingCareerStatsCards = ({ stats, isMobile = false }) => {
  if (!stats || !stats.overall) {
    return null;
  }

  const overall = stats.overall;

  return (
    <Box sx={{ mb: `${spacing.xl}px` }}>
      <Card isMobile={isMobile}>
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' },
          gap: { xs: `${spacing.base}px`, md: `${spacing.lg}px` }
        }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              MATCHES
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.matches}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              WICKETS
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.wickets}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              STRIKE RATE
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.bowling_strike_rate?.toFixed(1) || '0.0'}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              ECONOMY
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.economy_rate?.toFixed(2) || '0.00'}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              3WI/5WI
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.three_wicket_hauls}/{overall.five_wicket_hauls}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              DOT %
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.dot_percentage?.toFixed(1) || '0.0'}%
            </Typography>
          </Box>
        </Box>
      </Card>
    </Box>
  );
};

export default BowlingCareerStatsCards;