import React, { useState, useEffect } from 'react';
import { 
  Container, 
  TextField, 
  Box, 
  Autocomplete, 
  CircularProgress, 
  Alert,
  Typography,
  Button,
  Tabs,
  Tab,
  IconButton,
  Menu,
  MenuItem,
  useMediaQuery,
  useTheme
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import VenueNotes from './components/VenueNotes';
import MatchHistory from './components/MatchHistory';
import Matchups from './components/Matchups';
import MatchupsTab from './components/MatchupsTab';
import CompetitionFilter from './components/CompetitionFilter';
import LandingPage from './components/LandingPage';
import PlayerProfile from './components/PlayerProfile';
import BowlerProfile from './components/BowlerProfile'; // Import the new BowlerProfile component
import BatterComparison from './components/BatterComparison';
import QueryBuilder from './components/QueryBuilder'; // Import the new QueryBuilder component
import TeamProfile from './components/TeamProfile';
import axios from 'axios';

import config from './config';
const DEFAULT_START_DATE = "2024-01-01";
const TODAY = new Date().toISOString().split('T')[0];

const AppContent = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  // Helper function to get query parameters from URL
  const getQueryParam = (param) => {
    const searchParams = new URLSearchParams(location.search);
    return searchParams.get(param);
  };
  
  const [venues, setVenues] = useState([]);
  const [teams, setTeams] = useState([]);
  const [selectedVenue, setSelectedVenue] = useState("All Venues");
  const [selectedTeam1, setSelectedTeam1] = useState(null);
  const [selectedTeam2, setSelectedTeam2] = useState(null);
  const [startDate, setStartDate] = useState(DEFAULT_START_DATE);
  const [endDate, setEndDate] = useState(TODAY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [matchHistory, setMatchHistory] = useState(null);
  const [venueStats, setVenueStats] = useState(null);
  const [showVisualizations, setShowVisualizations] = useState(false);
  const [competitions, setCompetitions] = useState({
    leagues: [],
    international: false,
    topTeams: 10
  });
  const [statsData, setStatsData] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const [venueFantasyStats, setVenueFantasyStats] = useState({ team1_players: [], team2_players: [] });
  const [venuePlayerHistory, setVenuePlayerHistory] = useState({ players: [] });

  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNavigate = (path) => {
    handleMenuClose();
    navigate(path);
    if (path === '/') {
    setCurrentTab(0); // 0 for home/landing page
    } else {
    setCurrentTab(
    path === '/venue' ? 1 : 
    path === '/player' ? 2 : 
    path === '/bowler' ? 3 : 
    path === '/comparison' ? 4 : 
    path === '/matchups' ? 5 : 
    path === '/query' ? 6 : 
      path === '/team' ? 7 : 0 // Added team profile tab
      );
            }
  };

  useEffect(() => {
    // Set current tab based on location
    const path = location.pathname;
    if (path === '/') {
      setCurrentTab(0); // Home tab
    } else {
      setCurrentTab(
        path === '/venue' ? 1 : 
        path === '/player' ? 2 : 
        path === '/bowler' ? 3 : 
        path === '/comparison' ? 4 : 
        path === '/matchups' ? 5 : 
        path === '/query' ? 6 : 
        path === '/team' ? 7 : 0 // Added team profile tab
      );
    }
  }, [location]);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [venuesResponse, teamsResponse] = await Promise.all([
          axios.get(`${config.API_URL}/venues/`),
          axios.get(`${config.API_URL}/teams/`)
        ]);
        
        // Process venues response
        if (Array.isArray(venuesResponse.data)) {
          const venuesList = ["All Venues", ...venuesResponse.data.filter(v => v).sort()];
          setVenues(venuesList);
        }
        
        // Process teams response
        if (Array.isArray(teamsResponse.data)) {
          const sortedTeams = teamsResponse.data.sort((a, b) => a.full_name.localeCompare(b.full_name));
          setTeams(sortedTeams);
          
          // Get all URL parameters we'll need
          const venueParam = getQueryParam('venue');
          const team1Param = getQueryParam('team1');
          const team2Param = getQueryParam('team2');
          
          // Set venue if it's in the URL parameters
          if (venueParam) {
            setSelectedVenue(venueParam);
          }
          
          // Set team1 if found
          if (team1Param) {
            const team1 = sortedTeams.find(team => team.abbreviated_name === team1Param);
            if (team1) {
              setSelectedTeam1(team1);
            }
          }
          
          // Set team2 if found
          if (team2Param) {
            const team2 = sortedTeams.find(team => team.abbreviated_name === team2Param);
            if (team2) {
              setSelectedTeam2(team2);
            }
          }
          
          // If all required params are present, trigger the analysis
          if (venueParam && team1Param && team2Param) {
            setShowVisualizations(true);
          }
        }
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setError('Failed to load initial data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, [location.search]); // Re-run this effect when location.search changes

  const handleDateChange = (value, isStartDate) => {
    const newDate = value;
    if (isStartDate) {
      if (newDate > endDate) {
        setError("Start date cannot be after end date");
        return;
      }
      setStartDate(newDate);
    } else {
      if (newDate < startDate) {
        setError("End date cannot be before start date");
        return;
      }
      if (newDate > TODAY) {
        setError("End date cannot be in the future");
        return;
      }
      setEndDate(newDate);
    }
    setError(null);
    setShowVisualizations(false);
  };

  useEffect(() => {
    const fetchMatchHistory = async () => {
      if (!showVisualizations) {
        return;
      }
    
      try {
        setLoading(true);
        setError(null);
    
        const params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        
        if (competitions.leagues?.length > 0) {
          competitions.leagues.forEach(league => {
            params.append('leagues', league);
          });
        }
        
        params.append('include_international', competitions.international);
        if (competitions.international && competitions.topTeams) {
          params.append('top_teams', competitions.topTeams);
        }
    
        try {
          // Use allSettled to avoid failing the entire Promise.all if one request fails
          const [venueResponseResult, statsResponseResult] = await Promise.allSettled([
            axios.get(`${config.API_URL}/venue_notes/${encodeURIComponent(selectedVenue)}?${params.toString()}`),
            axios.get(`${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/stats?${params.toString()}`)
          ]);
      
          // Handle results individually
          if (venueResponseResult.status === 'fulfilled') {
            setVenueStats(venueResponseResult.value.data);
          } else {
            console.error('Error fetching venue notes:', venueResponseResult.reason);
            // Set default venue stats if request failed
            setVenueStats({
              venue: selectedVenue,
              total_matches: 0,
              batting_first_wins: 0,
              batting_second_wins: 0,
              highest_total: 0,
              lowest_total: 0,
              average_first_innings: 0,
              average_second_innings: 0,
              highest_total_chased: 0,
              lowest_total_defended: 0,
              average_winning_score: 0,
              average_chasing_score: 0,
              phase_wise_stats: {
                batting_first_wins: {},
                chasing_wins: {}
              }
            });
          }
          
          if (statsResponseResult.status === 'fulfilled') {
            setStatsData(statsResponseResult.value.data);
          } else {
            console.error('Error fetching stats data:', statsResponseResult.reason);
            // Set default stats data if request failed
            setStatsData({
              batting_leaders: [],
              bowling_leaders: [],
              batting_scatter: []
            });
          }
        } catch (error) {
          console.error('Error in main API calls:', error);
          setError('Failed to load venue data. Please try again.');
        }
    
        // Only fetch team-specific data if both teams are selected
        if (selectedTeam1 && selectedTeam2) {
          try {
            const [historyResponseResult, fantasyResponseResult, playerHistoryResponseResult] = await Promise.allSettled([
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/teams/${encodeURIComponent(selectedTeam1.full_name)}/${encodeURIComponent(selectedTeam2.full_name)}/history?${params.toString()}`
              ),
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/teams/${encodeURIComponent(selectedTeam1.full_name)}/${encodeURIComponent(selectedTeam2.full_name)}/fantasy_stats?${params.toString()}`
              ),
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/players/fantasy_history?team1=${encodeURIComponent(selectedTeam1.full_name)}&team2=${encodeURIComponent(selectedTeam2.full_name)}&${params.toString()}`
              )
            ]);
            
            // Handle team-specific results individually
            if (historyResponseResult.status === 'fulfilled') {
              setMatchHistory(historyResponseResult.value.data);
            } else {
              console.error('Error fetching match history:', historyResponseResult.reason);
              setMatchHistory({
                venue_results: [],
                team1_results: [],
                team2_results: [],
                h2h_stats: {
                  team1_wins: 0,
                  team2_wins: 0,
                  draws: 0,
                  recent_matches: []
                }
              });
            }
            
            if (fantasyResponseResult.status === 'fulfilled') {
              setVenueFantasyStats(fantasyResponseResult.value.data);
            } else {
              console.error('Error fetching fantasy stats:', fantasyResponseResult.reason);
              setVenueFantasyStats({ team1_players: [], team2_players: [] });
            }
            
            if (playerHistoryResponseResult.status === 'fulfilled') {
              setVenuePlayerHistory(playerHistoryResponseResult.value.data);
            } else {
              console.error('Error fetching player history:', playerHistoryResponseResult.reason);
              setVenuePlayerHistory({ players: [] });
            }
          } catch (error) {
            console.error('Error in team-specific API calls:', error);
            setError('Failed to load team data. Please try again.');
            setMatchHistory(null);
            setVenueFantasyStats({ team1_players: [], team2_players: [] });
            setVenuePlayerHistory({ players: [] });
          }
        } else {
          // Reset team-specific state if teams not selected
          setMatchHistory(null);
          setVenueFantasyStats({ team1_players: [], team2_players: [] });
          setVenuePlayerHistory({ players: [] });
        }
    
      } catch (error) {
        console.error('Global error fetching data:', error);
        setError(error.response?.data?.detail || 'Failed to load data. Please check the console for details.');
      } finally {
        setLoading(false);
      }
    };

    fetchMatchHistory();
  }, [selectedVenue, selectedTeam1, selectedTeam2, startDate, endDate, showVisualizations, competitions]);

  const handleFilterChange = (filters) => {
    setCompetitions(filters);
    if (showVisualizations) {
      setShowVisualizations(false);
      setTimeout(() => setShowVisualizations(true), 0);
    }
  };

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  // Create page title based on current tab
  const getPageTitle = () => {
    return currentTab === 0 ? 'Home' :
           currentTab === 1 ? 'Venue Analysis' : 
           currentTab === 2 ? 'Batter Profile' : 
           currentTab === 3 ? 'Bowler Profile' :  
           currentTab === 4 ? 'Batter Comparison' : 
           currentTab === 5 ? 'Matchups' : 
           currentTab === 6 ? 'Query Builder' : 
           currentTab === 7 ? 'Team Profile' : 'Home';
  };

  return (
    <Container maxWidth="xl" sx={{ px: { xs: 1, sm: 2, md: 3 } }}>
      <Box sx={{ 
        borderBottom: 1, 
        borderColor: 'divider', 
        mb: 3, 
        display: 'flex', // Always show the tabs
        alignItems: 'center',
        flexDirection: 'row',
        flexWrap: 'nowrap'
      }}>
        {isMobile ? (
          <>
            <IconButton
              aria-label="menu"
              aria-controls="navigation-menu"
              aria-haspopup="true"
              onClick={handleMenuClick}
              size="large"
            >
              <MenuIcon />
            </IconButton>
            <Menu
              id="navigation-menu"
              anchorEl={anchorEl}
              open={open}
              onClose={handleMenuClose}
            >
              <MenuItem onClick={() => handleNavigate('/')}>
                Home
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/venue')}>
                Venue Analysis
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/player')}>
                Batter Profile
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/bowler')}>
                Bowler Profile
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/comparison')}>
                Batter Comparison
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/matchups')}>
                Matchups
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/query')}>
                Query Builder
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/team')}>
                Team Profile
              </MenuItem>
            </Menu>
            <Typography variant="h6" sx={{ ml: 1, flexGrow: 1, whiteSpace: 'nowrap' }}>
              {getPageTitle()}
            </Typography>
          </>
        ) : (
          <Tabs 
            value={currentTab} 
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            sx={{ width: '100%' }}
          >
            <Tab label="Home" component={Link} to="/" />
            <Tab label="Venue Analysis" component={Link} to="/venue" />
            <Tab label="Batter Profile" component={Link} to="/player" />
            <Tab label="Bowler Profile" component={Link} to="/bowler" />
            <Tab label="Batter Comparison" component={Link} to="/comparison" />
            <Tab label="Matchups" component={Link} to="/matchups" />
            <Tab label="Query Builder" component={Link} to="/query" />
            <Tab label="Team Profile" component={Link} to="/team" />
          </Tabs>
        )}
      </Box>

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/player" element={<PlayerProfile isMobile={isMobile} />} />
        <Route path="/bowler" element={<BowlerProfile isMobile={isMobile} />} />
        <Route path="/comparison" element={<BatterComparison />} />
        <Route path="/matchups" element={<MatchupsTab isMobile={isMobile} />} />
        <Route path="/query" element={<QueryBuilder isMobile={isMobile} />} />
        <Route path="/team" element={<TeamProfile isMobile={isMobile} />} />
        <Route path="/venue" element={
          <Box sx={{ my: 3 }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            
            <Box sx={{ 
              display: 'flex', 
              flexDirection: { xs: 'column', md: 'row' },
              gap: 2, 
              mb: 2 
            }}>
              <Autocomplete
                value={selectedVenue}
                onChange={(event, newValue) => {
                  setSelectedVenue(newValue || "All Venues");
                  setShowVisualizations(false);
                }}
                options={venues}
                sx={{ width: '100%' }}
                loading={loading}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Venue"
                    required
                    fullWidth
                    InputProps={{
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {loading ? <CircularProgress color="inherit" size={20} /> : null}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
              />
              
              <TextField
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => handleDateChange(e.target.value, true)}
                InputLabelProps={{ shrink: true }}
                inputProps={{ max: endDate }}
                required
                fullWidth
              />
              
              <TextField
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => handleDateChange(e.target.value, false)}
                InputLabelProps={{ shrink: true }}
                inputProps={{ max: TODAY }}
                required
                fullWidth
              />
            </Box>

            <CompetitionFilter onFilterChange={handleFilterChange} isMobile={isMobile} />

            {startDate && endDate && !error && (
              <Box sx={{ 
                display: 'flex', 
                flexDirection: { xs: 'column', md: 'row' },
                gap: 2, 
                mb: 2 
              }}>
                <Autocomplete
                  value={selectedTeam1}
                  onChange={(event, newValue) => {
                    setSelectedTeam1(newValue);
                    setShowVisualizations(false);
                  }}
                  options={teams}
                  sx={{ width: '100%' }}
                  getOptionLabel={(option) => option?.abbreviated_name || ''}
                  renderOption={(props, option) => (
                    <li {...props}>
                      <Typography>
                        {option.abbreviated_name} - {option.full_name}
                      </Typography>
                    </li>
                  )}
                  renderInput={(params) => (
                    <TextField {...params} label="Team 1" fullWidth />
                  )}
                  isOptionEqualToValue={(option, value) => 
                    option?.full_name === value?.full_name
                  }
                />
                
                <Autocomplete
                  value={selectedTeam2}
                  onChange={(event, newValue) => {
                    setSelectedTeam2(newValue);
                    setShowVisualizations(false);
                  }}
                  options={teams.filter(team => team?.full_name !== selectedTeam1?.full_name)}
                  sx={{ width: '100%' }}
                  getOptionLabel={(option) => option?.abbreviated_name || ''}
                  renderOption={(props, option) => (
                    <li {...props}>
                      <Typography>
                        {option.abbreviated_name} - {option.full_name}
                      </Typography>
                    </li>
                  )}
                  renderInput={(params) => (
                    <TextField {...params} label="Team 2" fullWidth />
                  )}
                  isOptionEqualToValue={(option, value) => 
                    option?.full_name === value?.full_name
                  }
                />

                <Button 
                  variant="contained"
                  onClick={() => setShowVisualizations(true)}
                  disabled={loading || error}
                  sx={{ 
                    mt: { xs: 1, md: 0 },
                    width: { xs: '100%', md: 'auto' },
                    height: { xs: 'auto', md: '56px' }  // Match the height of Autocomplete
                  }}
                >
                  Go
                </Button>
              </Box>
            )}

            {showVisualizations && !loading && !error && (
              <>
                <VenueNotes 
                  venue={selectedVenue}
                  startDate={startDate} 
                  endDate={endDate}
                  venueStats={venueStats}
                  statsData={statsData}
                  selectedTeam1={selectedTeam1} 
                  selectedTeam2={selectedTeam2} 
                  venueFantasyStats={venueFantasyStats}
                  venuePlayerHistory={venuePlayerHistory}
                  matchHistory={matchHistory}
                  isMobile={isMobile}
                />
              </>
            )}
          </Box>
        } />
      </Routes>
    </Container>
  );
};

const App = () => {
  return (
    <Router>
      <AppContent />
    </Router>
  );
};

export default App;