import React from 'react';
import { Box, Typography } from '@mui/material';
import Card from './ui/Card';

const CareerStatsCards = ({ stats, isMobile = false }) => {
  const { overall } = stats;

  return (
    <Box sx={{
      display: 'grid',
      gap: 2,
      gridTemplateColumns: '1fr',
      mb: 3
    }}>
      {/* Primary Stats Card */}
      <Card isMobile={isMobile}>
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          gap: { xs: 2, md: 3 }
        }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem', fontWeight: 600 }}>
              MATCHES
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: 0.5 }}>
              {overall.matches}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem', fontWeight: 600 }}>
              RUNS
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: 0.5 }}>
              {overall.runs}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.65rem' : '0.7rem' }}>
              Avg: {overall.average.toFixed(2)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem', fontWeight: 600 }}>
              STRIKE RATE
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: 0.5 }}>
              {overall.strike_rate.toFixed(1)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem', fontWeight: 600 }}>
              50s/100s
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: 0.5 }}>
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
          gap: { xs: 2, md: 3 }
        }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem', fontWeight: 600 }}>
              DOT %
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: 0.5 }}>
              {overall.dot_percentage.toFixed(1)}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem', fontWeight: 600 }}>
              BOUNDARY %
            </Typography>
            <Typography variant={isMobile ? "h5" : "h4"} sx={{ fontWeight: 700, mt: 0.5 }}>
              {overall.boundary_percentage.toFixed(1)}%
            </Typography>
          </Box>
        </Box>
      </Card>
    </Box>
  );
};

export default CareerStatsCards;
