import React, { useState, useEffect, useRef } from 'react';
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
  useTheme,
  Collapse,
  Card,
  CardContent
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import VenueNotes from './components/VenueNotes';
import MatchupsTab from './components/MatchupsTab';
import CompetitionFilter from './components/CompetitionFilter';
import LandingPage from './components/LandingPage';
import UnifiedPlayerProfile from './components/UnifiedPlayerProfile';
import BatterComparison from './components/BatterComparison';
import QueryBuilder from './components/QueryBuilder'; // Import the new QueryBuilder component
import TeamProfile from './components/TeamProfile';
import TeamComparison from './components/TeamComparison';
import DoppelgangerLeaderboard from './components/DoppelgangerLeaderboard';
import IPLPredictions from './components/IPLPredictions';
import GlobalT20Rankings from './components/GlobalT20Rankings';
import WrappedPage from './components/wrapped/WrappedPage';
import { GoogleSearchLanding, SearchBar } from './components/search';
import GuessInningsGame from './components/games/GuessInningsGame';
import PlayerJourneysGame from './components/games/PlayerJourneysGame';
import CreditsPage from './components/CreditsPage';
import axios from 'axios';

import config from './config';
import { DEFAULT_START_DATE, TODAY } from './utils/dateDefaults';

const TEAM_NAME_TO_ABBREVIATION = {
  'chennai super kings': 'CSK',
  'mumbai indians': 'MI',
  'kolkata knight riders': 'KKR',
  'gujarat titans': 'GT',
  'lucknow super giants': 'LSG',
  'punjab kings': 'PBKS',
  'kings xi punjab': 'PBKS',
  'royal challengers bangalore': 'RCB',
  'royal challengers bengaluru': 'RCB',
  'delhi capitals': 'DC',
  'delhi daredevils': 'DC',
  'sunrisers hyderabad': 'SRH',
  'rajasthan royals': 'RR',
  'rising pune supergiants': 'RPSG',
  'rising pune supergiant': 'RPSG',
  'gujarat lions': 'GL',
  'deccan chargers': 'DCh',
  'kochi tuskers kerala': 'KTK'
};

const normalizeTeamValue = (value) => (value || '').trim().toLowerCase().replace(/\s+/g, ' ');

const resolveTeamFromParam = (teamParam, sortedTeams) => {
  if (!teamParam) return null;

  const normalizedParam = normalizeTeamValue(teamParam);
  const exactMatch = sortedTeams.find((team) =>
    normalizeTeamValue(team.abbreviated_name) === normalizedParam ||
    normalizeTeamValue(team.full_name) === normalizedParam
  );
  if (exactMatch) return exactMatch;

  const mappedAbbreviation = TEAM_NAME_TO_ABBREVIATION[normalizedParam];
  if (mappedAbbreviation) {
    const mappedMatch = sortedTeams.find(
      (team) => normalizeTeamValue(team.abbreviated_name) === normalizeTeamValue(mappedAbbreviation)
    );
    if (mappedMatch) return mappedMatch;
  }

  return null;
};

// Redirect /bowler?name=X&autoload=true to /player?name=X&tab=bowling&autoload=true
const BowlerRedirect = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  searchParams.set('tab', 'bowling');
  return <Navigate to={`/player?${searchParams.toString()}`} replace />;
};

const AppContent = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const getCurrentTabForPath = (path) => (
    path === '/' ? 0 :
    path === '/search' ? 1 :
    path === '/venue' ? 2 :
    path === '/player' ? 3 :
    path === '/comparison' ? 4 :
    path === '/matchups' ? 5 :
    path === '/query' ? 6 :
    path === '/team' ? 7 :
    path === '/team-comparison' ? 8 :
    path === '/doppelgangers' ? 9 :
    path === '/ipl-predictions' ? 10 :
    path === '/rankings' ? 11 :
    path === '/games/guess-innings' ? 12 :
    path === '/games/player-journeys' ? 13 :
    path === '/credits' ? false :
    path.startsWith('/wrapped') ? false : 0
  );

  const getPageTitleForPath = (path) => (
    path === '/' ? 'Home' :
    path === '/search' ? 'Search' :
    path === '/venue' ? 'Match Preview' :
    path === '/player' ? 'Player Profile' :
    path === '/comparison' ? 'Batter Comparison' :
    path === '/matchups' ? 'Matchups' :
    path === '/query' ? 'Query Builder' :
    path === '/team' ? 'Team Profile' :
    path === '/team-comparison' ? 'Team Comparison' :
    path === '/doppelgangers' ? 'Doppelgangers' :
    path === '/ipl-predictions' ? 'IPL Predictions' :
    path === '/rankings' ? 'Global Rankings' :
    path === '/games/guess-innings' ? 'Guess the Innings' :
    path === '/games/player-journeys' ? 'Player Journeys' :
    path === '/credits' ? 'Credits & Acknowledgements' :
    path.startsWith('/wrapped') ? '2025 Wrapped' : 'Home'
  );
  
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
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(true);

  const [venueFantasyStats, setVenueFantasyStats] = useState({ team1_players: [], team2_players: [] });
  const [venuePlayerHistory, setVenuePlayerHistory] = useState({ players: [] });
  const hasFetchedRef = useRef(false);

  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  // Handle header search selection
  const handleHeaderSearchSelect = (item) => {
    setSearchExpanded(false);
    if (item.type === 'player') {
      navigate(`/search?q=${encodeURIComponent(item.name)}`);
    } else if (item.type === 'team') {
      navigate(`/team?team=${encodeURIComponent(item.name)}&autoload=true`);
    } else if (item.type === 'venue') {
      navigate(`/venue?venue=${encodeURIComponent(item.name)}&autoload=true`);
    }
  };

  const handleNavigate = (path) => {
    handleMenuClose();
    navigate(path);
    setCurrentTab(getCurrentTabForPath(path));
  };

  useEffect(() => {
    setCurrentTab(getCurrentTabForPath(location.pathname));
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
          const includeInternationalParam = getQueryParam('includeInternational');
          const topTeamsParam = getQueryParam('topTeams');

          if (includeInternationalParam !== null || topTeamsParam !== null) {
            const parsedTopTeams = Number.parseInt(topTeamsParam, 10);
            setCompetitions(prev => ({
              ...prev,
              international: includeInternationalParam !== null
                ? includeInternationalParam === 'true'
                : prev.international,
              topTeams: Number.isFinite(parsedTopTeams) && parsedTopTeams > 0
                ? parsedTopTeams
                : prev.topTeams
            }));
          }
          
          // Set venue if it's in the URL parameters
          if (venueParam) {
            setSelectedVenue(venueParam);
          }
          
          // Set team1 if found
          if (team1Param) {
            const team1 = resolveTeamFromParam(team1Param, sortedTeams);
            if (team1) {
              setSelectedTeam1(team1);
            }
          }
          
          // Set team2 if found
          if (team2Param) {
            const team2 = resolveTeamFromParam(team2Param, sortedTeams);
            if (team2) {
              setSelectedTeam2(team2);
            }
          }
          
          // If venue is present with autoload, or all params present, trigger the analysis
          const autoloadParam = getQueryParam('autoload') === 'true';
          if ((venueParam && autoloadParam) || (venueParam && team1Param && team2Param)) {
            hasFetchedRef.current = false;
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
    const abortController = new AbortController();

    const fetchMatchHistory = async () => {
      if (!showVisualizations) {
        return;
      }

      // Prevent duplicate fetches
      if (hasFetchedRef.current) {
        return;
      }
      hasFetchedRef.current = true;

      // Clear stale data before fetching
      setMatchHistory(null);
      setStatsData(null);
      setVenueFantasyStats({ team1_players: [], team2_players: [] });
      setVenuePlayerHistory({ players: [] });

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
            axios.get(`${config.API_URL}/venue_notes/${encodeURIComponent(selectedVenue)}?${params.toString()}`, { signal: abortController.signal }),
            axios.get(`${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/stats?${params.toString()}`, { signal: abortController.signal })
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
          if (error.name === 'AbortError' || error.name === 'CanceledError') return;
          console.error('Error in main API calls:', error);
          setError('Failed to load venue data. Please try again.');
        }

        // Only fetch team-specific data if both teams are selected
        if (selectedTeam1 && selectedTeam2) {
          try {
            const [historyResponseResult, fantasyResponseResult, playerHistoryResponseResult] = await Promise.allSettled([
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/teams/${encodeURIComponent(selectedTeam1.full_name)}/${encodeURIComponent(selectedTeam2.full_name)}/history?${params.toString()}`,
                { signal: abortController.signal }
              ),
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/teams/${encodeURIComponent(selectedTeam1.full_name)}/${encodeURIComponent(selectedTeam2.full_name)}/fantasy_stats?${params.toString()}`,
                { signal: abortController.signal }
              ),
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/players/fantasy_history?team1=${encodeURIComponent(selectedTeam1.full_name)}&team2=${encodeURIComponent(selectedTeam2.full_name)}&${params.toString()}`,
                { signal: abortController.signal }
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
            if (error.name === 'AbortError' || error.name === 'CanceledError') return;
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
        if (error.name === 'AbortError' || error.name === 'CanceledError') return;
        console.error('Global error fetching data:', error);
        setError(error.response?.data?.detail || 'Failed to load data. Please check the console for details.');
      } finally {
        setLoading(false);
      }
    };

    fetchMatchHistory();
    return () => abortController.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVenue, selectedTeam1, selectedTeam2, startDate, endDate, showVisualizations]);

  // Collapse filters after data has loaded
  useEffect(() => {
    // Only collapse if we're showing visualizations AND loading is done
    // This prevents collapsing when GO is clicked but before loading starts
    if (showVisualizations && !loading) {
      // Use a small delay to ensure all rendering is complete
      const timer = setTimeout(() => {
        setFiltersExpanded(false);
      }, 100);
      return () => clearTimeout(timer);
    } else if (showVisualizations && loading) {
      // Keep filters expanded while loading
      setFiltersExpanded(true);
    }
  }, [showVisualizations, loading]);

  const handleFilterChange = (filters) => {
    setCompetitions(filters);
  };

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  // Create page title based on current tab
  const getPageTitle = () => {
    return getPageTitleForPath(location.pathname);
  };

  return (
    <Container maxWidth="xl" sx={{ px: { xs: 1, sm: 2, md: 3 } }}>
      <Box sx={{ 
        borderBottom: 1, 
        borderColor: 'divider', 
        mb: 3, 
        display: 'flex',
        alignItems: 'center',
        flexDirection: 'row',
        flexWrap: 'nowrap',
        position: 'relative'
      }}>
        {/* Expandable Search Bar Overlay */}
        {searchExpanded && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              bgcolor: 'background.paper',
              zIndex: 1200,
              display: 'flex',
              alignItems: 'center',
              px: 1,
              gap: 1
            }}
          >
            <Box sx={{ flexGrow: 1 }}>
              <SearchBar 
                onSelect={handleHeaderSearchSelect}
                placeholder="Search players, teams, venues..."
              />
            </Box>
            <IconButton 
              onClick={() => setSearchExpanded(false)}
              size="small"
            >
              <CloseIcon />
            </IconButton>
          </Box>
        )}
        
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
              <MenuItem onClick={() => handleNavigate('/search')}>
                Search
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/venue')}>
                Match Preview
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/player')}>
                Player Profile
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
              <MenuItem onClick={() => handleNavigate('/team-comparison')}>                Team Comparison
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/doppelgangers')}>
                Doppelgangers
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/ipl-predictions')}>
                IPL Predictions
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/rankings')}>
                Global Rankings
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/games/guess-innings')}>
                🎯 Guess the Innings
              </MenuItem>
              <MenuItem onClick={() => handleNavigate('/games/player-journeys')}>
                🛤️ Player Journeys
              </MenuItem>
            </Menu>
            <Typography variant="h6" sx={{ ml: 1, flexGrow: 1, whiteSpace: 'nowrap' }}>
              {getPageTitle()}
            </Typography>
            <IconButton
              onClick={() => setSearchExpanded(true)}
              size="small"
              sx={{ ml: 'auto' }}
              aria-label="search"
            >
              <SearchIcon />
            </IconButton>
          </>
        ) : (
          <>
            <Tabs 
              value={currentTab} 
              onChange={handleTabChange}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              sx={{ flexGrow: 1 }}
            >
              <Tab label="Home" component={Link} to="/" />
              <Tab label="Search" component={Link} to="/search" />
              <Tab label="Match Preview" component={Link} to="/venue" />
              <Tab label="Player Profile" component={Link} to="/player" />
              <Tab label="Batter Comparison" component={Link} to="/comparison" />
              <Tab label="Matchups" component={Link} to="/matchups" />
              <Tab label="Query Builder" component={Link} to="/query" />
              <Tab label="Team Profile" component={Link} to="/team" />
              <Tab label="Team Comparison" component={Link} to="/team-comparison" />
              <Tab label="Doppelgangers" component={Link} to="/doppelgangers" />
              <Tab label="IPL Predictions" component={Link} to="/ipl-predictions" />
              <Tab label="Global Rankings" component={Link} to="/rankings" />
              <Tab label="🎯 Guess the Innings" component={Link} to="/games/guess-innings" />
              <Tab label="🛤️ Player Journeys" component={Link} to="/games/player-journeys" />
            </Tabs>
            <IconButton
              onClick={() => setSearchExpanded(true)}
              size="small"
              sx={{ ml: 1 }}
              aria-label="search"
            >
              <SearchIcon />
            </IconButton>
          </>
        )}
      </Box>

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/player" element={<UnifiedPlayerProfile isMobile={isMobile} />} />
        <Route path="/bowler" element={<BowlerRedirect />} />
        <Route path="/comparison" element={<BatterComparison />} />
        <Route path="/matchups" element={<MatchupsTab isMobile={isMobile} />} />
        <Route path="/query" element={<QueryBuilder isMobile={isMobile} />} />
        <Route path="/team" element={<TeamProfile isMobile={isMobile} />} />
        <Route path="/team-comparison" element={<TeamComparison />} />
        <Route path="/doppelgangers" element={<DoppelgangerLeaderboard />} />
        <Route path="/ipl-predictions" element={<IPLPredictions />} />
        <Route path="/rankings" element={<GlobalT20Rankings />} />
        <Route path="/games/guess-innings" element={<GuessInningsGame isMobile={isMobile} />} />
        <Route path="/games/player-journeys" element={<PlayerJourneysGame isMobile={isMobile} />} />
        <Route path="/wrapped/2025" element={<WrappedPage />} />
        <Route path="/search" element={<GoogleSearchLanding />} />
        <Route path="/credits" element={<CreditsPage />} />
        <Route path="/venue" element={
          <Box sx={{ my: { xs: 1.5, md: 3 } }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Collapse in={filtersExpanded || !showVisualizations}>
              <Card sx={{ mb: 2, boxShadow: showVisualizations ? 2 : 0, backgroundColor: showVisualizations ? undefined : 'transparent' }}>
                <CardContent sx={{ p: showVisualizations ? 2 : 0 }}>
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

                  <CompetitionFilter onFilterChange={handleFilterChange} isMobile={isMobile} value={competitions} />

                  {startDate && endDate && !error && (
                    <Box sx={{
                      display: 'flex',
                      flexDirection: { xs: 'column', md: 'row' },
                      gap: 2,
                      mb: 0
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
                        onClick={() => {
                          hasFetchedRef.current = false;
                          setShowVisualizations(true);
                        }}
                        disabled={loading || error}
                        sx={{
                          mt: { xs: 1, md: 0 },
                          width: { xs: '100%', md: 'auto' },
                          height: { xs: 'auto', md: '56px' }
                        }}
                      >
                        Go
                      </Button>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Collapse>

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
                  filtersExpanded={filtersExpanded}
                  onToggleFilters={() => setFiltersExpanded((currentValue) => !currentValue)}
                  isMobile={isMobile}
                  leagues={competitions.leagues}
                  includeInternational={competitions.international}
                  topTeams={competitions.topTeams}
                />
              </>
            )}
          </Box>
        } />
      </Routes>
      {!location.pathname.startsWith('/wrapped') && (
        <Box
          sx={{
            mt: 4,
            mb: 3,
            pt: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
            textAlign: 'center',
          }}
        >
          <Typography
            component={Link}
            to="/credits"
            variant="body2"
            sx={{
              color: 'text.secondary',
              textDecoration: 'none',
              '&:hover': {
                color: 'primary.main',
              },
            }}
          >
            Credits & Acknowledgements
          </Typography>
        </Box>
      )}
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
