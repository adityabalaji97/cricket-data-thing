import React from 'react';
import { 
  Container, 
  Box, 
  Typography, 
  Button, 
  Card, 
  CardContent, 
  CardActions,
  Grid,
  Paper,
  Divider,
  useTheme,
  useMediaQuery,
  Chip
} from '@mui/material';
import { Link } from 'react-router-dom';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import StadiumIcon from '@mui/icons-material/Stadium';
import GroupsIcon from '@mui/icons-material/Groups';
import PersonIcon from '@mui/icons-material/Person';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

// This will be a new component that serves as a landing page
const LandingPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isMedium = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Hero Section */}
      <Paper 
        elevation={0}
        sx={{
          p: { xs: 4, md: 8 },
          mb: 6,
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
        
        <Typography variant={isMobile ? "h4" : "h2"} fontWeight="bold" gutterBottom>
          Cricket Analytics Made Simple
        </Typography>
        
        <Typography variant={isMobile ? "body1" : "h6"} sx={{ mb: 4, maxWidth: 800, mx: 'auto' }}>
          Visualize match data, analyze player performance, and explore team matchups all in one place
        </Typography>
        
        <Box sx={{ 
          display: 'flex', 
          gap: 2, 
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          <Button 
            variant="contained" 
            component={Link} 
            to="/venue" 
            color="secondary"
            size="large"
            startIcon={<StadiumIcon />}
            sx={{ 
              px: 3, 
              py: 1.5,
              backgroundColor: '#ffffff',
              color: '#0057b7',
              '&:hover': {
                backgroundColor: '#f5f5f5',
              } 
            }}
          >
            Explore Venue Data
          </Button>
          
          <Button 
            variant="outlined" 
            component={Link} 
            to="/player" 
            color="inherit"
            size="large"
            startIcon={<PersonIcon />}
            sx={{ px: 3, py: 1.5 }}
          >
            Analyze Batters
          </Button>
          
          <Button 
            variant="outlined" 
            component={Link} 
            to="/matchups" 
            color="inherit"
            size="large"
            startIcon={<GroupsIcon />}
            sx={{ px: 3, py: 1.5 }}
          >
            Compare Matchups
          </Button>
        </Box>
        
        <Chip 
          label="NEW" 
          color="error" 
          size="small" 
          sx={{ 
            position: 'absolute', 
            top: 20, 
            right: 20,
            fontWeight: 'bold'
          }} 
        />
      </Paper>

      {/* Features Section */}
      <Typography variant="h4" align="center" gutterBottom sx={{ mb: 4 }}>
        What would you like to do?
      </Typography>
      
      <Grid container spacing={4} sx={{ mb: 8 }}>
        {/* Venue Analysis Card */}
        <Grid item xs={12} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-5px)',
              boxShadow: 8
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: 3 }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                mb: 2
              }}>
                <StadiumIcon 
                  sx={{ 
                    fontSize: 60, 
                    color: '#0057b7',
                    p: 1,
                    borderRadius: '50%',
                    backgroundColor: 'rgba(0, 87, 183, 0.1)'
                  }} 
                />
              </Box>
              
              <Typography variant="h5" component="h2" gutterBottom align="center" fontWeight="bold">
                Venue Analysis
              </Typography>
              
              <Typography color="textSecondary" paragraph align="center">
                Explore match statistics by venue, including win percentages, scoring patterns, and historical performance data.
              </Typography>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 2, 
                borderRadius: 2,
                mb: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary">
                  Perfect for pre-match preparation and understanding venue characteristics
                </Typography>
              </Box>
            </CardContent>
            
            <CardActions sx={{ p: 2, pt: 0 }}>
              <Button 
                component={Link}
                to="/venue"
                fullWidth 
                variant="outlined" 
                endIcon={<ArrowForwardIcon />}
                size="large"
              >
                Analyze Venues
              </Button>
            </CardActions>
          </Card>
        </Grid>
        
        {/* Batter Profile Card */}
        <Grid item xs={12} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-5px)',
              boxShadow: 8
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: 3 }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                mb: 2
              }}>
                <PersonIcon 
                  sx={{ 
                    fontSize: 60, 
                    color: '#c70d3a',
                    p: 1,
                    borderRadius: '50%',
                    backgroundColor: 'rgba(199, 13, 58, 0.1)'
                  }} 
                />
              </Box>
              
              <Typography variant="h5" component="h2" gutterBottom align="center" fontWeight="bold">
                Batter Profiles
              </Typography>
              
              <Typography color="textSecondary" paragraph align="center">
                Deep dive into batting performance with comprehensive stats, scoring patterns, and matchup analysis.
              </Typography>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 2, 
                borderRadius: 2,
                mb: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary">
                  Ideal for player evaluation and identifying strengths and weaknesses
                </Typography>
              </Box>
            </CardContent>
            
            <CardActions sx={{ p: 2, pt: 0 }}>
              <Button 
                component={Link}
                to="/player"
                fullWidth 
                variant="outlined" 
                endIcon={<ArrowForwardIcon />} 
                color="error"
                size="large"
              >
                Explore Batters
              </Button>
            </CardActions>
          </Card>
        </Grid>
        
        {/* Matchups Card */}
        <Grid item xs={12} md={4}>
          <Card sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            transition: 'transform 0.3s, box-shadow 0.3s',
            '&:hover': {
              transform: 'translateY(-5px)',
              boxShadow: 8
            }
          }}>
            <CardContent sx={{ flexGrow: 1, p: 3 }}>
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'center',
                mb: 2
              }}>
                <GroupsIcon 
                  sx={{ 
                    fontSize: 60, 
                    color: '#007e33',
                    p: 1,
                    borderRadius: '50%',
                    backgroundColor: 'rgba(0, 126, 51, 0.1)'
                  }} 
                />
              </Box>
              
              <Typography variant="h5" component="h2" gutterBottom align="center" fontWeight="bold">
                Team Matchups
              </Typography>
              
              <Typography color="textSecondary" paragraph align="center">
                Compare head-to-head team statistics, player matchups, and historical encounters.
              </Typography>
              
              <Box sx={{ 
                bgcolor: 'grey.100', 
                p: 2, 
                borderRadius: 2,
                mb: 2
              }}>
                <Typography variant="subtitle2" color="textSecondary">
                  Essential for pre-match strategy and betting insights
                </Typography>
              </Box>
            </CardContent>
            
            <CardActions sx={{ p: 2, pt: 0 }}>
              <Button 
                component={Link}
                to="/matchups"
                fullWidth 
                variant="outlined" 
                endIcon={<ArrowForwardIcon />}
                color="success"
                size="large"
              >
                View Matchups
              </Button>
            </CardActions>
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
            <img 
              src="/cricket-og-image.svg" 
              alt="Cricket Data Visualization" 
              style={{ 
                width: '100%', 
                maxWidth: '500px', 
                display: 'block',
                margin: '0 auto',
                borderRadius: '8px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
              }} 
            />
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
      </Box>

      {/* Sample Insights Section (Optional) */}
      <Box sx={{ mb: 6 }}>
        <Typography variant="h4" align="center" gutterBottom sx={{ mb: 3 }}>
          Data-Driven Cricket Insights
        </Typography>
        
        <Typography variant="subtitle1" color="textSecondary" align="center" sx={{ mb: 4, maxWidth: 800, mx: 'auto' }}>
          Our advanced analytics help you understand cricket performance in detail through clear visualizations and comprehensive statistics
        </Typography>
        
        <Grid container spacing={3} justifyContent="center">
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom color="primary">
                <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Player Analysis
              </Typography>
              <Typography variant="body2" paragraph>
                Uncover batting strengths and weaknesses with detailed performance breakdowns by bowling type, match phase, and opposition.
              </Typography>
              <Box sx={{ 
                p: 1, 
                bgcolor: 'primary.light', 
                color: 'white', 
                borderRadius: 1,
                fontSize: '0.875rem',
                mt: 'auto'
              }}>
                Popular for fantasy cricket and team selection
              </Box>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom color="error">
                <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Venue Insights
              </Typography>
              <Typography variant="body2" paragraph>
                Analyze pitch behavior, historical scoring patterns, and batting/bowling success rates at different venues.
              </Typography>
              <Box sx={{ 
                p: 1, 
                bgcolor: 'error.light', 
                color: 'white', 
                borderRadius: 1,
                fontSize: '0.875rem',
                mt: 'auto'
              }}>
                Essential for pre-match preparation
              </Box>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom color="success.dark">
                <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Matchup Analytics
              </Typography>
              <Typography variant="body2" paragraph>
                Review head-to-head records, player vs player statistics, and historical encounter data to predict match outcomes.
              </Typography>
              <Box sx={{ 
                p: 1, 
                bgcolor: 'success.light', 
                color: 'white', 
                borderRadius: 1,
                fontSize: '0.875rem',
                mt: 'auto'
              }}>
                Game-changing for strategic planning
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Box>
      
      {/* Final CTA */}
      <Box 
        sx={{ 
          textAlign: 'center', 
          p: 4, 
          borderRadius: 4,
          bgcolor: 'grey.100',
          mb: 4
        }}
      >
        <Typography variant="h5" gutterBottom>
          Ready to dive into cricket analytics?
        </Typography>
        
        <Button 
          variant="contained" 
          color="primary" 
          size="large" 
          component={Link}
          to="/venue"
          sx={{ 
            mt: 2,
            px: 4,
            py: 1.5
          }}
        >
          Get Started Now
        </Button>
      </Box>
      
      {/* Footer */}
      <Divider sx={{ mb: 3 }} />
      <Typography variant="body2" color="textSecondary" align="center" sx={{ pb: 2 }}>
        Cricket Data Thing © {new Date().getFullYear()} - Advanced cricket analytics and visualization
      </Typography>
    </Container>
  );
};

export default LandingPage;