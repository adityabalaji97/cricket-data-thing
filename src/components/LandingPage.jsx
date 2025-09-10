import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Box, 
  Typography, 
  Button, 
  Card, 
  CardContent,
  Grid,
  Paper,
  Divider,
  useTheme,
  useMediaQuery,
  Chip,
  Stack,
  CircularProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import StadiumIcon from '@mui/icons-material/Stadium';
import GroupsIcon from '@mui/icons-material/Groups';
import PersonIcon from '@mui/icons-material/Person';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import EventNoteIcon from '@mui/icons-material/EventNote';
import PeopleIcon from '@mui/icons-material/People';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import SearchIcon from '@mui/icons-material/Search';
import InfoIcon from '@mui/icons-material/Info';
import { getUpcomingMatches, formatDate, formatVenue } from '../data/iplSchedule';
import RecentMatchesSummaryCard from './RecentMatchesSummaryCard';

// This will be a new component that serves as a landing page
const LandingPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isMedium = useMediaQuery(theme.breakpoints.down('md'));
  const [upcomingMatches, setUpcomingMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  // URLs for analysis pages are now created inline with template literals
  // This avoids the need for a separate createAnalysisUrl function

  useEffect(() => {
    const fetchUpcomingMatches = async () => {
      try {
        setLoading(true);
        
        // Get today's date
        const today = new Date();
        const todayString = today.toISOString().split('T')[0];
        
        // Get upcoming matches starting from today
        const nextMatches = getUpcomingMatches(3, todayString);
        setUpcomingMatches(nextMatches);
      } catch (error) {
        console.error('Error fetching upcoming matches:', error);
        // If there's an error, set an empty array
        setUpcomingMatches([]);
      } finally {
        setLoading(false);
      }
    };

    fetchUpcomingMatches();
  }, []);

  // Component to display upcoming match links
  const UpcomingMatchLinks = () => {
    if (loading) {
      return (
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="subtitle1" sx={{ mb: 2 }}>
            Loading match schedule...
          </Typography>
          <CircularProgress size={24} />
        </Box>
      );
    }

    if (upcomingMatches.length === 0 && !loading) {
      return (
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="subtitle1" color="text.secondary">
            No upcoming matches found in the schedule. We're showing you some sample matches instead.
          </Typography>
        </Box>
      );
    }

    return (
      <Box sx={{ mt: 4 }}>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Upcoming Matches Analysis
        </Typography>
        
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {upcomingMatches.map((match) => (
            <Grid item xs={12} md={4} key={match.matchNumber}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5, gap: 1 }}>
                    <CalendarTodayIcon color="primary" fontSize="small" />
                    <Typography variant="subtitle1">
                      {formatDate(match.date)}
                    </Typography>
                  </Box>
                  
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    {match.team1Abbr} vs {match.team2Abbr}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {formatVenue(match.venue)}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', gap: 1, flexDirection: 'column' }}>
                    <Button
                      variant="outlined"
                      size="small"
                      color="primary"
                      component={Link}
                      startIcon={<StadiumIcon />}
                      fullWidth
                      to={`/venue?venue=${encodeURIComponent(match.venue)}&team1=${match.team1Abbr}&team2=${match.team2Abbr}&autoload=true`}
                    >
                      Venue Analysis
                    </Button>
                    
                    <Button
                      variant="outlined"
                      size="small"
                      color="secondary"
                      component={Link}
                      startIcon={<GroupsIcon />}
                      fullWidth
                      to={`/matchups?team1=${match.team1Abbr}&team2=${match.team2Abbr}&autoload=true`}
                    >
                      Team Matchups
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
        
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
          <Button
            variant="outlined"
            size="medium"
            startIcon={<EventNoteIcon />}
            component={Link}
            to="/venue"
            sx={{ px: 2 }}
          >
            Venue Analysis
          </Button>
          
          <Button
            variant="outlined"
            size="medium"
            startIcon={<PeopleIcon />}
            component={Link}
            to="/matchups"
            sx={{ px: 2 }}
          >
            Team Matchups
          </Button>
        </Box>
      </Box>
    );
  };

  return (
    <Container maxWidth="xl" sx={{ py: { xs: 0.5, md: 2 } }}>
      {/* Hero Section */}
      <Paper 
        elevation={0}
        sx={{
          p: { xs: 0.5, md: 3 },
          mb: 1,
          background: 'linear-gradient(to right, #0057b7, #1976d2)',
          borderRadius: 4,
          position: 'relative',
          overflow: 'hidden',
          color: 'white',
          textAlign: 'center'
        }}
      >
        <Box 
          sx={{ 
            position: 'absolute', 
            top: -50, 
            right: -50, 
            fontSize: 300, 
            opacity: 0.1,
            transform: 'rotate(15deg)'
          }}
        >
          <SportsCricketIcon fontSize="inherit" />
        </Box>
        
        <Typography variant="h4" fontWeight="bold" gutterBottom sx={{ fontSize: { xs: '1.25rem', md: '1.75rem' } }}>
          Welcome to Hindsight
        </Typography>
        
        <Typography variant="h5" sx={{ maxWidth: 800, mx: 'auto', fontSize: { xs: '0.85rem', md: '1rem' } }}>
          Because hindsight is 20/20,
        </Typography>
        <Typography variant="h5" sx={{ maxWidth: 800, mx: 'auto', fontSize: { xs: '0.85rem', md: '1rem' } }}>
          and this is all about 20-20 cricket data
        </Typography>
      </Paper>

      {/* Features Section */}
      <Grid container spacing={{ xs: 1, md: 3 }} sx={{ mb: 4 }}>
        {/* Batter Profile Card */}
        <Grid item xs={6} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-3px)',
              boxShadow: 6
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, md: 2.5 } }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                alignItems: 'center',
                mb: 1,
                gap: 0.5
              }}>
                <PersonIcon 
                  sx={{ 
                    fontSize: '1rem', 
                    color: '#c70d3a'
                  }} 
                />
                <Typography 
                  variant="h6" 
                  component={Link}
                  to="/player"
                  fontWeight="bold" 
                  sx={{ 
                    fontSize: { xs: '0.75rem', md: '0.9rem' },
                    textDecoration: 'none',
                    color: 'inherit',
                    '&:hover': {
                      textDecoration: 'underline'
                    },
                    whiteSpace: 'nowrap'
                  }}
                >
                  Batter Profiles
                </Typography>
                <Tooltip title="Deep dive into batting performance with comprehensive stats, scoring patterns, and matchup analysis.">
                  <IconButton size="small" sx={{ p: 0.5 }}>
                    <InfoIcon sx={{ fontSize: '1rem' }} color="action" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 1, 
                borderRadius: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom sx={{ fontSize: '0.7rem' }}>
                  Featured Batters:
                </Typography>
                <Button
                  fullWidth
                  variant="text"
                  color="error"
                  component={Link}
                  to="/player?name=MS%20Dhoni&autoload=true"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  MS Dhoni
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="error"
                  component={Link}
                  to="/player?name=V%20Kohli&autoload=true"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  V Kohli
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="error"
                  component={Link}
                  to="/player?name=RG%20Sharma&autoload=true"
                  sx={{ justifyContent: 'flex-start', textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  RG Sharma
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Bowler Profiles Card */}
        <Grid item xs={6} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-3px)',
              boxShadow: 6
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, md: 2.5 } }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                alignItems: 'center',
                mb: 1,
                gap: 0.5
              }}>
                <SportsCricketIcon 
                  sx={{ 
                    fontSize: '1rem', 
                    color: '#ff6f00'
                  }} 
                />
                <Typography 
                  variant="h6" 
                  component={Link}
                  to="/bowler"
                  fontWeight="bold" 
                  sx={{ 
                    fontSize: { xs: '0.75rem', md: '0.9rem' },
                    textDecoration: 'none',
                    color: 'inherit',
                    '&:hover': {
                      textDecoration: 'underline'
                    },
                    whiteSpace: 'nowrap'
                  }}
                >
                  Bowler Profiles
                </Typography>
                <Tooltip title="Comprehensive bowling analysis with wicket patterns, economy rates, and phase-wise performance metrics.">
                  <IconButton size="small" sx={{ p: 0.5 }}>
                    <InfoIcon sx={{ fontSize: '1rem' }} color="action" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 1, 
                borderRadius: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom sx={{ fontSize: '0.7rem' }}>
                  Featured Bowlers:
                </Typography>
                <Button
                  fullWidth
                  variant="text"
                  color="warning"
                  component={Link}
                  to="/bowler?name=JJ%20Bumrah&autoload=true"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  JJ Bumrah
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="warning"
                  component={Link}
                  to="/bowler?name=DL%20Chahar&autoload=true"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  DL Chahar
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="warning"
                  component={Link}
                  to="/bowler?name=Rashid%20Khan&autoload=true"
                  sx={{ justifyContent: 'flex-start', textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  Rashid Khan
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Batter Comparison Card */}
        <Grid item xs={6} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-3px)',
              boxShadow: 6
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, md: 2.5 } }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                alignItems: 'center',
                mb: 1,
                gap: 0.5
              }}>
                <CompareArrowsIcon 
                  sx={{ 
                    fontSize: '1rem', 
                    color: '#9c27b0'
                  }} 
                />
                <Typography 
                  variant="h6" 
                  component={Link}
                  to="/comparison"
                  fontWeight="bold" 
                  sx={{ 
                    fontSize: { xs: '0.7rem', md: '0.85rem' },
                    textDecoration: 'none',
                    color: 'inherit',
                    '&:hover': {
                      textDecoration: 'underline'
                    },
                    whiteSpace: 'nowrap'
                  }}
                >
                  Batter Comparison
                </Typography>
                <Tooltip title="Compare multiple batters across various metrics, including phase-wise performance, strike rates, and matchups.">
                  <IconButton size="small" sx={{ p: 0.5 }}>
                    <InfoIcon sx={{ fontSize: '1rem' }} color="action" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 1, 
                borderRadius: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom sx={{ fontSize: '0.7rem' }}>
                  Example Comparisons:
                </Typography>
                <Button
                  fullWidth
                  variant="text"
                  color="secondary"
                  component={Link}
                  to="/comparison?batters=V%20Kohli,RG%20Sharma,KL%20Rahul&leagues=Indian%20Premier%20League"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  Rohit vs Kohli vs Rahul
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="secondary"
                  component={Link}
                  to="/comparison?batters=DA%20Warner,JC%20Buttler,Q%20de%20Kock&leagues=Indian%20Premier%20League"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  Warner vs Buttler vs de Kock
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="secondary"
                  component={Link}
                  to="/comparison?batters=Shubman%20Gill,Abhishek%20Sharma,SV%20Samson&leagues=Indian%20Premier%20League"
                  sx={{ justifyContent: 'flex-start', textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  Gill vs Abhishek vs Samson
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Query Builder Card */}
        <Grid item xs={6} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-3px)',
              boxShadow: 6
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, md: 2.5 } }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                alignItems: 'center',
                mb: 1,
                gap: 0.5
              }}>
                <SearchIcon 
                  sx={{ 
                    fontSize: '1rem', 
                    color: '#1976d2'
                  }} 
                />
                <Typography 
                  variant="h6" 
                  component={Link}
                  to="/query"
                  fontWeight="bold" 
                  sx={{ 
                    fontSize: { xs: '0.75rem', md: '0.9rem' },
                    textDecoration: 'none',
                    color: 'inherit',
                    '&:hover': {
                      textDecoration: 'underline'
                    },
                    whiteSpace: 'nowrap'
                  }}
                >
                  Query Builder
                </Typography>
                <Tooltip title="Build custom queries to analyze specific scenarios, player combinations, and match conditions.">
                  <IconButton size="small" sx={{ p: 0.5 }}>
                    <InfoIcon sx={{ fontSize: '1rem' }} color="action" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 1, 
                borderRadius: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom sx={{ fontSize: '0.7rem' }}>
                  Quick Start Queries:
                </Typography>
                <Button
                  fullWidth
                  variant="text"
                  color="primary"
                  component={Link}
                  to="/query?batting_teams=Chennai%20Super%20Kings&start_date=2025-01-01&leagues=IPL&min_balls=30&group_by=batter&group_by=phase"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  CSK batters by phase in 2025
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="primary"
                  component={Link}
                  to="/query?batters=V%20Kohli&bowler_type=LC&bowler_type=LO&bowler_type=RL&bowler_type=RO&leagues=IPL&start_date=2023-01-01&min_balls=10&group_by=phase&group_by=ball_direction"
                  sx={{ justifyContent: 'flex-start', mb: 0.3, textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  Kohli vs spinners by phase & direction
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  color="primary"
                  component={Link}
                  to="/query?start_date=2020-01-01&bowler_type=LO&bowler_type=LC&bowler_type=RO&bowler_type=RL&min_balls=100&group_by=crease_combo"
                  sx={{ justifyContent: 'flex-start', textAlign: 'left', fontSize: '0.75rem', py: 0.3 }}
                >
                  T20 crease combos vs spin
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Venue Analysis Card */}
        <Grid item xs={6} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-3px)',
              boxShadow: 6
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, md: 2.5 } }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                alignItems: 'center',
                mb: 1,
                gap: 0.5
              }}>
                <StadiumIcon 
                  sx={{ 
                    fontSize: '1rem', 
                    color: '#0057b7'
                  }} 
                />
                <Typography 
                  variant="h6" 
                  component={Link}
                  to="/venue"
                  fontWeight="bold" 
                  sx={{ 
                    fontSize: { xs: '0.75rem', md: '0.9rem' },
                    textDecoration: 'none',
                    color: 'inherit',
                    '&:hover': {
                      textDecoration: 'underline'
                    },
                    whiteSpace: 'nowrap'
                  }}
                >
                  Venue Analysis
                </Typography>
                <Tooltip title="Explore match statistics by venue, including win percentages, scoring patterns, and historical performance data.">
                  <IconButton size="small" sx={{ p: 0.5 }}>
                    <InfoIcon sx={{ fontSize: '1rem' }} color="action" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 1, 
                borderRadius: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom sx={{ fontSize: '0.7rem' }}>
                  Upcoming Matches:
                </Typography>
                {loading ? (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ fontSize: '0.7rem' }}>
                    Loading matches...
                  </Typography>
                ) : upcomingMatches.length > 0 ? (
                  upcomingMatches.slice(0, 3).map((match) => (
                    <Button
                      key={match.matchNumber}
                      fullWidth
                      variant="text"
                      color="primary"
                      component={Link}
                      to={`/venue?venue=${encodeURIComponent(match.venue)}&team1=${match.team1Abbr}&team2=${match.team2Abbr}&autoload=true`}
                      sx={{ 
                        justifyContent: 'flex-start', 
                        mb: 0.3, 
                        textAlign: 'left',
                        fontSize: '0.65rem',
                        py: 0.2,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}
                    >
                      {formatDate(match.date)} {match.team1Abbr} vs {match.team2Abbr}
                    </Button>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ fontSize: '0.7rem' }}>
                    No upcoming matches found.
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Team Matchups Card */}
        <Grid item xs={6} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-3px)',
              boxShadow: 6
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: { xs: 1.5, md: 2.5 } }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                alignItems: 'center',
                mb: 1,
                gap: 0.5
              }}>
                <GroupsIcon 
                  sx={{ 
                    fontSize: '1rem', 
                    color: '#007e33'
                  }} 
                />
                <Typography 
                  variant="h6" 
                  component={Link}
                  to="/matchups"
                  fontWeight="bold" 
                  sx={{ 
                    fontSize: { xs: '0.75rem', md: '0.9rem' },
                    textDecoration: 'none',
                    color: 'inherit',
                    '&:hover': {
                      textDecoration: 'underline'
                    },
                    whiteSpace: 'nowrap'
                  }}
                >
                  Team Matchups
                </Typography>
                <Tooltip title="Compare head-to-head team statistics, player matchups, and historical encounters.">
                  <IconButton size="small" sx={{ p: 0.5 }}>
                    <InfoIcon sx={{ fontSize: '1rem' }} color="action" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 1, 
                borderRadius: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom sx={{ fontSize: '0.7rem' }}>
                  Upcoming Matchups:
                </Typography>
                {loading ? (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ fontSize: '0.7rem' }}>
                    Loading matches...
                  </Typography>
                ) : upcomingMatches.length > 0 ? (
                  upcomingMatches.slice(0, 3).map((match) => (
                    <Button
                      key={match.matchNumber}
                      fullWidth
                      variant="text"
                      color="success"
                      component={Link}
                      to={`/matchups?team1=${match.team1Abbr}&team2=${match.team2Abbr}&autoload=true`}
                      sx={{ 
                        justifyContent: 'flex-start', 
                        mb: 0.3, 
                        textAlign: 'left',
                        fontSize: '0.65rem',
                        py: 0.2,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}
                    >
                      {formatDate(match.date)} {match.team1Abbr} vs {match.team2Abbr}
                    </Button>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ fontSize: '0.7rem' }}>
                    No upcoming matches found.
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* How It Works Section */}
      <Box sx={{ 
        mb: 8,
        p: { xs: 3, md: 5 },
        backgroundColor: 'grey.50',
        borderRadius: 4
      }}>
        <Typography variant="h4" align="center" gutterBottom sx={{ mb: 4 }}>
          How It Works
        </Typography>
        
        <Grid container spacing={4} alignItems="center">
          <Grid item xs={12} md={6}>
            {/* Use a direct SVG or component instead of trying to load an image */}
            <Box
              sx={{
                width: '100%',
                maxWidth: '500px',
                height: '300px',
                margin: '0 auto',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#0057b7',
                borderRadius: '8px',
                color: 'white',
                position: 'relative',
                overflow: 'hidden',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
              }}
            >
              <SportsCricketIcon sx={{ fontSize: 100, opacity: 0.2, position: 'absolute', right: 20, bottom: 20 }} />
              <Typography variant="h5" component="div" sx={{ fontWeight: 'bold', textAlign: 'center', p: 2 }}>
                Hindsight
                <Typography component="div" variant="body1" sx={{ mt: 1 }}>
                  Cricket Analytics with Perfect Hindsight
                </Typography>
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Box sx={{ 
                  width: 36, 
                  height: 36, 
                  borderRadius: '50%', 
                  bgcolor: '#0057b7', 
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  flexShrink: 0
                }}>
                  1
                </Box>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Select Data Parameters
                  </Typography>
                  <Typography color="textSecondary">
                    Choose venues, dates, and teams to analyze from our comprehensive database of cricket matches.
                  </Typography>
                </Box>
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Box sx={{ 
                  width: 36, 
                  height: 36, 
                  borderRadius: '50%', 
                  bgcolor: '#c70d3a', 
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  flexShrink: 0
                }}>
                  2
                </Box>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Visualize Insights
                  </Typography>
                  <Typography color="textSecondary">
                    Explore interactive charts, statistical breakdowns, and player performance data through our intuitive visualization tools.
                  </Typography>
                </Box>
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Box sx={{ 
                  width: 36, 
                  height: 36, 
                  borderRadius: '50%', 
                  bgcolor: '#007e33', 
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  flexShrink: 0
                }}>
                  3
                </Box>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Make Informed Decisions
                  </Typography>
                  <Typography color="textSecondary">
                    Use analytics for team selection, fantasy teams, betting or match predictions based on data-driven insights.
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Grid>
        </Grid>
        
        <Typography variant="body2" color="textSecondary" align="center" sx={{ mt: 3, pb: 2 }}>
          Hindsight © {new Date().getFullYear()} - Cricket analytics with perfect hindsight
        </Typography>
      </Box>


      
      {/* Upcoming Matches Section */}
      <UpcomingMatchLinks />
      
      {/* Recent Matches Summary */}
      <RecentMatchesSummaryCard />
      
      {/* Footer with Credits */}
      <Divider sx={{ mb: 3 }} />
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" align="center" gutterBottom>
          Credits & Acknowledgements
        </Typography>
        
        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" gutterBottom color="primary">
              Data Sources
            </Typography>
            <Typography variant="body2" paragraph>
              Ball-by-ball data from <a href="https://cricsheet.org/" target="_blank" rel="noopener noreferrer">Cricsheet.org</a>
            </Typography>
            <Typography variant="body2" paragraph>
              Player information from <a href="https://cricmetric.com/" target="_blank" rel="noopener noreferrer">Cricmetric</a>
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" gutterBottom color="primary">
              Metrics & Visualization Inspiration
            </Typography>
            <Typography variant="body2" component="div">
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/prasannalara" target="_blank" rel="noopener noreferrer">@prasannalara</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/cricketingview" target="_blank" rel="noopener noreferrer">@cricketingview</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/IndianMourinho" target="_blank" rel="noopener noreferrer">@IndianMourinho</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/hganjoo_153" target="_blank" rel="noopener noreferrer">@hganjoo_153</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/randomcricstat" target="_blank" rel="noopener noreferrer">@randomcricstat</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/kaustats" target="_blank" rel="noopener noreferrer">@kaustats</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/cricviz" target="_blank" rel="noopener noreferrer">@cricviz</a>
              </Box>
              <Box component="span" sx={{ display: 'inline-block', mr: 1, mb: 0.5 }}>
                <a href="https://twitter.com/ajarrodkimber" target="_blank" rel="noopener noreferrer">@ajarrodkimber</a>
              </Box>
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" gutterBottom color="primary">
              Development Assistance
            </Typography>
            <Typography variant="body2" paragraph>
              Claude and ChatGPT for Vibe Coding my way through this project
            </Typography>
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, gap: 4 }}>
          <Typography variant="body2" color="text.secondary">
            <a href="https://github.com/adityabalaji97/cricket-data-thing" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0016 8c0-4.42-3.58-8-8-8z" />
              </svg>
              View on GitHub
            </a>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <a href="https://twitter.com/maybe_eybe" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <svg width="16" height="13" viewBox="0 0 16 13" fill="currentColor">
                <path d="M14.2617 3.31344C14.2701 3.45862 14.2701 3.60381 14.2701 3.74899C14.2701 8.19609 11.0026 13.2965 5.05124 13.2965C3.20076 13.2965 1.48646 12.7762 0.0393066 11.8788C0.303819 11.9079 0.559496 11.9162 0.832842 11.9162C2.33451 11.9162 3.71642 11.4125 4.81887 10.5651C3.39903 10.536 2.20063 9.60505 1.79388 8.33242C2.00001 8.36152 2.20615 8.38229 2.42061 8.38229C2.71227 8.38229 3.00394 8.34075 3.27729 8.26599C1.80289 7.96602 0.70044 6.69339 0.70044 5.15979V5.1223C1.12391 5.35677 1.60996 5.50196 2.12195 5.51857C1.25279 4.93753 0.70877 3.94626 0.70877 2.82382C0.70877 2.22611 0.866618 1.67785 1.14829 1.19996C2.73127 3.13901 5.09276 4.38572 7.73617 4.52673C7.68631 4.29226 7.6614 4.04946 7.6614 3.80667C7.6614 2.02146 9.10716 0.576691 10.893 0.576691C11.8154 0.576691 12.6512 0.947396 13.2405 1.5493C13.9714 1.40413 14.6691 1.1306 15.2915 0.756231C15.057 1.51606 14.5534 2.1762 13.8805 2.59126C14.5367 2.52483 15.1759 2.35373 15.7653 2.11261C15.2915 2.78107 14.7127 3.38712 14.2617 3.31344Z" />
              </svg>
              @maybe_eybe
            </a>
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default LandingPage;