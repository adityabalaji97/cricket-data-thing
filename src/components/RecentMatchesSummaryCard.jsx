import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material';
import { Link } from 'react-router-dom';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import StadiumIcon from '@mui/icons-material/Stadium';
import GroupsIcon from '@mui/icons-material/Groups';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import InfoIcon from '@mui/icons-material/Info';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import axios from 'axios';
import config from '../config';

const RecentMatchesSummaryCard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchRecentMatches = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await axios.get(`${config.API_URL}/recent-matches/by-league`);
        setData(response.data);
      } catch (err) {
        console.error('Error fetching recent matches:', err);
        setError('Failed to load recent matches data');
      } finally {
        setLoading(false);
      }
    };

    fetchRecentMatches();
  }, []);

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getWinnerStyle = (match) => {
    if (!match.winner) return { color: 'text.secondary' };
    return { 
      color: 'success.main',
      fontWeight: 'bold'
    };
  };

  if (loading) {
    return (
      <Card sx={{ mt: 4, p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading recent matches...</Typography>
        </Box>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.recent_matches) {
    return null;
  }

  const displayMatches = expanded ? data.recent_matches : data.recent_matches.slice(0, 6);
  const topCompetitions = Object.values(data.competition_stats || {})
    .sort((a, b) => {
      // T20I first (priority 1), then by match count
      if (a.priority !== b.priority) {
        return a.priority - b.priority;
      }
      return b.match_count - a.match_count;
    });

  return (
    <Card sx={{ 
      mt: 4, 
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      borderRadius: 3,
      boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
    }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          mb: 3,
          justifyContent: 'space-between'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrendingUpIcon sx={{ color: 'primary.main', fontSize: '1.5rem' }} />
            <Typography variant="h5" fontWeight="bold" color="primary.main">
              Latest Cricket Activity
            </Typography>
            <Tooltip title="Most recent match from each league and T20 internationals in our database">
              <IconButton size="small">
                <InfoIcon fontSize="small" color="action" />
              </IconButton>
            </Tooltip>
          </Box>
          
          <Chip 
            label={`${data.total_recent_matches} Recent Matches`}
            color="primary"
            size="small"
            icon={<SportsCricketIcon />}
          />
        </Box>

        {/* Recent Matches Grid */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CalendarTodayIcon fontSize="small" color="primary" />
            Latest Matches (T20I + Leagues)
          </Typography>
          
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {displayMatches.map((match, index) => (
              <Grid item xs={12} sm={6} md={4} key={match.match_id || index}>
                <Card sx={{ 
                  height: '100%',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: 4
                  },
                  border: '1px solid',
                  borderColor: 'divider'
                }}>
                  <CardContent sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Chip 
                        label={match.competition_abbr || match.competition}
                        size="small"
                        color={match.is_international ? "primary" : "secondary"}
                        sx={{ 
                          fontSize: '0.7rem',
                          fontWeight: match.is_international ? 'bold' : 'normal'
                        }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {formatDate(match.date)}
                      </Typography>
                    </Box>
                    
                    <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 1, fontSize: '0.9rem' }}>
                      {match.team1} vs {match.team2}
                    </Typography>
                    
                    {match.winner && (
                      <Typography 
                        variant="caption" 
                        sx={getWinnerStyle(match)}
                      >
                        Winner: {match.winner}
                      </Typography>
                    )}
                    
                    {match.venue && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                        📍 {match.venue}
                      </Typography>
                    )}
                    
                    <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<StadiumIcon />}
                        component={Link}
                        to={`/venue?venue=${encodeURIComponent(match.venue || '')}&team1=${match.team1}&team2=${match.team2}`}
                        sx={{ fontSize: '0.7rem', py: 0.3 }}
                      >
                        Venue
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<GroupsIcon />}
                        component={Link}
                        to={`/matchups?team1=${match.team1}&team2=${match.team2}`}
                        sx={{ fontSize: '0.7rem', py: 0.3 }}
                      >
                        H2H
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
          
          {data.recent_matches.length > 6 && (
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Button 
                variant="outlined" 
                onClick={() => setExpanded(!expanded)}
                size="small"
              >
                {expanded ? 'Show Less' : `Show All ${data.recent_matches.length} Matches`}
              </Button>
            </Box>
          )}
        </Box>

        <Divider sx={{ my: 3 }} />

        {/* Competition Statistics */}
        <Box>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SportsCricketIcon fontSize="small" color="primary" />
            League Match Counts
          </Typography>
          
          <Grid container spacing={1.5} sx={{ mt: 1 }}>
            {topCompetitions.map((comp, index) => (
              <Grid item xs={6} sm={4} md={3} key={comp.competition || index}>
                <Box sx={{ 
                  p: 1.5, 
                  bgcolor: 'background.paper', 
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  textAlign: 'center',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'scale(1.02)'
                  }
                }}>
                  <Typography variant="body2" fontWeight="bold" color="primary.main">
                    {comp.competition_display}
                  </Typography>
                  <Typography variant="h6" color="text.primary" sx={{ my: 0.5 }}>
                    {comp.match_count.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    matches
                  </Typography>
                  {comp.latest_date && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                      Latest: {formatDate(comp.latest_date)}
                    </Typography>
                  )}
                </Box>
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* Footer */}
        <Box sx={{ 
          mt: 3, 
          pt: 2, 
          borderTop: '1px solid', 
          borderColor: 'divider',
          textAlign: 'center' 
        }}>
          <Typography variant="caption" color="text.secondary">
            Showing the most recent match from each of {data.total_competitions} competitions in our database
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default RecentMatchesSummaryCard;
