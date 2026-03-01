import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Skeleton,
  useTheme,
  useMediaQuery
} from '@mui/material';
import { Link } from 'react-router-dom';
import MiniWagonWheel from './MiniWagonWheel';
import config from '../config';

const FeaturedInningsCards = () => {
  const [innings, setInnings] = useState([]);
  const [loading, setLoading] = useState(true);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const res = await fetch(`${config.API_URL}/landing/featured-innings`);
        if (res.ok) {
          const data = await res.json();
          setInnings(data);
        }
      } catch (err) {
        console.error('Failed to fetch featured innings:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchFeatured();
  }, []);

  if (!loading && innings.length === 0) return null;

  if (loading) {
    return (
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ mb: 1, fontSize: { xs: '0.95rem', md: '1.1rem' } }}>
          Recent Standout Innings
        </Typography>
        <Grid container spacing={2}>
          {[...Array(isMobile ? 2 : 6)].map((_, i) => (
            <Grid item xs={12} sm={6} md={4} key={i}>
              <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  const renderCard = (item, index) => (
    <Card
      key={index}
      component={Link}
      to={`/player?name=${encodeURIComponent(item.batter)}&autoload=true`}
      sx={{
        display: 'flex',
        alignItems: 'center',
        textDecoration: 'none',
        color: 'inherit',
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': { transform: 'translateY(-2px)', boxShadow: 4 },
        minWidth: isMobile ? 280 : 'auto',
        height: '100%'
      }}
    >
      <CardContent sx={{
        display: 'flex',
        gap: 1.5,
        p: { xs: 1.5, md: 2 },
        width: '100%',
        '&:last-child': { pb: { xs: 1.5, md: 2 } }
      }}>
        <MiniWagonWheel deliveries={item.deliveries} size={isMobile ? 100 : 120} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="subtitle2"
            fontWeight="bold"
            noWrap
            sx={{ fontSize: { xs: '0.8rem', md: '0.875rem' } }}
          >
            {item.batter}
          </Typography>
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{ fontSize: { xs: '1rem', md: '1.1rem' }, lineHeight: 1.2 }}
          >
            {item.runs}{' '}
            <Typography component="span" variant="body2" color="text.secondary">
              ({item.balls})
            </Typography>
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            SR {item.strike_rate} &middot; {item.fours}x4 {item.sixes}x6
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            noWrap
            sx={{ display: 'block', mt: 0.5 }}
          >
            {item.team} vs {item.opponent}
          </Typography>
          <Typography variant="caption" color="text.disabled" noWrap sx={{ display: 'block' }}>
            {item.venue} &middot; {item.date}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );

  if (isMobile) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 0.5, fontSize: '0.95rem' }}>
          Recent Standout Innings
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
          Top performances from recent matches
        </Typography>
        <Box sx={{
          display: 'flex',
          gap: 2,
          overflowX: 'auto',
          pb: 1,
          '&::-webkit-scrollbar': { height: 4 },
          '&::-webkit-scrollbar-thumb': { borderRadius: 2, bgcolor: 'grey.300' }
        }}>
          {innings.map((item, i) => (
            <Box key={i} sx={{ flexShrink: 0, width: 280 }}>
              {renderCard(item, i)}
            </Box>
          ))}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        Recent Standout Innings
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Top performances from recent matches
      </Typography>
      <Grid container spacing={2}>
        {innings.map((item, i) => (
          <Grid item xs={12} sm={6} md={4} key={i}>
            {renderCard(item, i)}
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default FeaturedInningsCards;
