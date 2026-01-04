import React from 'react';
import { Box, Typography } from '@mui/material';
import { spacing } from '../theme/designSystem';
import Card from './ui/Card';

const CareerStatsCards = ({ stats, isMobile = false }) => {
  const { overall } = stats;

  return (
    <Box sx={{
      display: 'grid',
      gap: `${spacing.lg}px`,
      gridTemplateColumns: '1fr',
      mb: `${spacing.xl}px`
    }}>
      {/* Primary Stats Card */}
      <Card isMobile={isMobile}>
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
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
              RUNS
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.runs}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Avg: {overall.average.toFixed(2)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              STRIKE RATE
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.strike_rate.toFixed(1)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              50s/100s
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.fifties}/{overall.hundreds}
            </Typography>
          </Box>
        </Box>
      </Card>

      {/* Secondary Stats Card */}
      <Card isMobile={isMobile}>
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(2, 1fr)' },
          gap: { xs: `${spacing.base}px`, md: `${spacing.lg}px` }
        }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              DOT %
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.dot_percentage.toFixed(1)}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              BOUNDARY %
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: `${spacing.xs}px` }}>
              {overall.boundary_percentage.toFixed(1)}%
            </Typography>
          </Box>
        </Box>
      </Card>
    </Box>
  );
};

export default CareerStatsCards;
