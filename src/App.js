import React, { useState, useEffect, useRef } from 'react';
// The preview's filter controls moved to components/preview/PreviewFilters.jsx (A6), which
// took Autocomplete, TextField, Collapse, Card/CardContent, ToggleButton(Group),
// CircularProgress, Alert and Button with them.
import {
  Container,
  Box,
  Typography,
  Tabs,
  Tab,
  IconButton,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CloseIcon from '@mui/icons-material/Close';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import VenueNotes from './components/VenueNotes';
import PreviewFilters from './components/preview/PreviewFilters';
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
import CallItGame from './components/games/CallItGame';
import HigherLowerGame from './components/games/HigherLowerGame';
import CreditsPage from './components/CreditsPage';
import FantasyPlanner from './components/FantasyPlanner';
import MatchScorecardPage from './components/scorecard/MatchScorecardPage';
import MobileBottomNav, { MobileNavSpacer } from './components/nav/MobileBottomNav';
import { colors as hsColors, fonts as hsFonts } from './theme/hindsightDark';
import axios from 'axios';

import config from './config';
import { getPreviewStartDate, TODAY } from './utils/dateDefaults';
import { NAV_ITEMS, getCurrentTabForPath, getPageTitleForPath } from './navItems';
import { MensT20Scope, useFormat } from './context/FormatContext';
import { trackPageView } from './utils/analytics';

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
  'kochi tuskers kerala': 'KTK',
  'afg': 'Afghanistan',
  'aus': 'Australia',
  'ban': 'Bangladesh',
  'eng': 'England',
  'ind': 'India',
  'ire': 'Ireland',
  'nam': 'Namibia',
  'ned': 'Netherlands',
  'nz': 'New Zealand',
  'omn': 'Oman',
  'pak': 'Pakistan',
  'png': 'Papua New Guinea',
  'sa': 'South Africa',
  'sl': 'Sri Lanka',
  'sco': 'Scotland',
  'uae': 'UAE',
  'usa': 'USA',
  'wi': 'West Indies',
  'zim': 'Zimbabwe'
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
      (team) => (
        normalizeTeamValue(team.abbreviated_name) === normalizeTeamValue(mappedAbbreviation)
        || normalizeTeamValue(team.full_name) === normalizeTeamValue(mappedAbbreviation)
      )
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
  // Phone + small tablet: compact header and bottom nav. The 15-tab strip does not fit below md.
  const isCompactNav = useMediaQuery(theme.breakpoints.down('md'));
  // Pinned, not the raw selection: a venue preview is one format's record at a ground,
  // and the venue endpoints reject 'ALL'.
  const { pinnedFormatParams, active: activeFormat, selectFormat } = useFormat();

  // One page_view per route change (query-string changes on the same page count too: a
  // new player or scorecard is a new view).
  useEffect(() => {
    trackPageView();
  }, [location.pathname, location.search]);

  // In-app links carry ?fmt= so the destination opens in the right format (a Home fixture card
  // opens an ODI preview in ODI; a preview's Explore link opens the query builder in the same
  // format). FormatProvider sits outside the router and only reads ?fmt= on first page load, so
  // apply it here whenever navigation brings a different one.
  const urlFormatSlug = new URLSearchParams(location.search).get('fmt');
  useEffect(() => {
    if (urlFormatSlug && activeFormat?.slug && urlFormatSlug !== activeFormat.slug) {
      selectFormat(urlFormatSlug);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlFormatSlug]);


  
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
  // Preview window depends on format (8 years for ODIs, 4 for T20s, from 1 January).
  const [startDate, setStartDate] = useState(() => getPreviewStartDate(pinnedFormatParams.format));
  const [endDate, setEndDate] = useState(TODAY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [matchHistory, setMatchHistory] = useState(null);
  const [venueStats, setVenueStats] = useState(null);
  const [espnEventId, setEspnEventId] = useState(null);
  const [showVisualizations, setShowVisualizations] = useState(false);
  const [competitions, setCompetitions] = useState({
    leagues: [],
    international: false,
    topTeams: 10
  });
  const [statsData, setStatsData] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(true);
  const [dayNightFilter, setDayNightFilter] = useState('all');

  const hasFetchedRef = useRef(false);
  const dateManuallyAdjustedRef = useRef(false);
  const isQueryRoute = location.pathname === '/query';



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


  useEffect(() => {
    setCurrentTab(getCurrentTabForPath(location.pathname));
  }, [location]);

  useEffect(() => {
    const fetchInitialData = async () => {
      if (location.pathname === '/') {
        setLoading(false);
        return;
      }

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
          const dayNightParam = getQueryParam('dayNight') || getQueryParam('day_or_night');
          const matchIdParam = getQueryParam('matchId');

          if (matchIdParam) {
            setEspnEventId(matchIdParam);
          }

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

          if (dayNightParam === 'day' || dayNightParam === 'night' || dayNightParam === 'all') {
            setDayNightFilter(dayNightParam);

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
  }, [location.pathname, location.search]); // Re-run this effect when route or query changes

  const handleDateChange = (value, isStartDate) => {
    dateManuallyAdjustedRef.current = true;
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

  const handleDayNightChange = (event, nextValue) => {
    if (!nextValue) return;
    setDayNightFilter(nextValue);
    hasFetchedRef.current = false;

    // Day games used to widen the window to 4 years; that is now the T20 default for every
    // filter, so the day/night toggle no longer changes the dates.
  };

  // Follow the format's default window (e.g. arriving from a Home ODI fixture via ?fmt=) unless
  // the user has picked dates themselves.
  useEffect(() => {
    if (!dateManuallyAdjustedRef.current) {
      setStartDate(getPreviewStartDate(pinnedFormatParams.format));
    }
  }, [pinnedFormatParams.format]);

  // A format change (e.g. arriving from a Home ODI fixture via ?fmt=) must refetch even if the
  // preview already loaded under the previous format; the duplicate-fetch guard would otherwise
  // keep the old format's numbers. Declared before the fetch effect so it runs first.
  // startDate too: a format change moves the default window one render later, and the fetch
  // started in between is aborted by that change, so the guard must not block the refetch.
  useEffect(() => {
    hasFetchedRef.current = false;
  }, [pinnedFormatParams.format, pinnedFormatParams.gender, startDate]);

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
        params.append('format', pinnedFormatParams.format);
        params.append('gender', pinnedFormatParams.gender);
        if (competitions.international && competitions.topTeams) {
          params.append('top_teams', competitions.topTeams);
        }
        if (dayNightFilter !== 'all') {
          params.append('day_or_night', dayNightFilter);
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
            const [historyResponseResult] = await Promise.allSettled([
              axios.get(
                `${config.API_URL}/venues/${encodeURIComponent(selectedVenue)}/teams/${encodeURIComponent(selectedTeam1.full_name)}/${encodeURIComponent(selectedTeam2.full_name)}/history?${params.toString()}`,
                { signal: abortController.signal }
              ),
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
          } catch (error) {
            if (error.name === 'AbortError' || error.name === 'CanceledError') return;
            console.error('Error in team-specific API calls:', error);
            setError('Failed to load team data. Please try again.');
            setMatchHistory(null);
          }
        } else {
          // Reset team-specific state if teams not selected
          setMatchHistory(null);
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
  // Format is a dependency: switching it has to refetch, or the preview would keep showing
  // the previous format's venue record.
  }, [selectedVenue, selectedTeam1, selectedTeam2, startDate, endDate, showVisualizations, dayNightFilter,
      pinnedFormatParams.format, pinnedFormatParams.gender]);

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

  const showBottomNav = isCompactNav && !location.pathname.startsWith('/wrapped');

  if (location.pathname === '/') {
    return (
      <>
        <LandingPage />
        {showBottomNav && (
          <>
            <MobileNavSpacer />
            <MobileBottomNav />
          </>
        )}
      </>
    );
  }

  return (
    <Container
      maxWidth={isQueryRoute ? false : "xl"}
      sx={{
        px: { xs: isQueryRoute ? 0 : 1, sm: isQueryRoute ? 0 : 2, md: isQueryRoute ? 0 : 3 },
        minHeight: isQueryRoute ? '100vh' : 'auto',
      }}
    >
      {/* Wrapped is a full-screen story with its own chrome. */}
      {!location.pathname.startsWith('/wrapped') && (
      <Box sx={{
        borderBottom: 1,
        borderColor: 'divider',
        mb: isQueryRoute ? 0 : { xs: 1.5, md: 3 },
        px: isQueryRoute ? { xs: 1.5, md: 3 } : 0,
        bgcolor: 'background.default',
        display: 'flex',
        alignItems: 'center',
        flexDirection: 'row',
        flexWrap: 'nowrap',
        // Sticky on phones so search and the page title stay in reach while scrolling.
        position: isCompactNav ? 'sticky' : 'relative',
        top: 0,
        zIndex: (t) => t.zIndex.appBar,
        minHeight: isCompactNav ? 52 : undefined,
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
                onFallback={(term) => {
                  setSearchExpanded(false);
                  navigate(`/query?nl=${encodeURIComponent(term)}`);
                }}
                placeholder="Search players, teams, venues..."
                variant="dark"
              />
            </Box>
            <IconButton
              onClick={() => setSearchExpanded(false)}
              size="small"
              aria-label="close search"
              sx={{ color: 'text.secondary' }}
            >
              <CloseIcon />
            </IconButton>
          </Box>
        )}

        {isCompactNav ? (
          <>
            <Box
              component={Link}
              to="/"
              aria-label="Hindsight home"
              sx={{ display: 'flex', alignItems: 'center', p: 1, ml: 0.5 }}
            >
              <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 26, height: 26 }} />
            </Box>
            <Typography
              component="h1"
              sx={{
                ml: 0.5,
                flexGrow: 1,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                fontFamily: hsFonts.display,
                fontWeight: 700,
                fontSize: 18,
                color: hsColors.textHi,
              }}
            >
              {getPageTitle()}
            </Typography>
            <IconButton
              onClick={() => setSearchExpanded(true)}
              aria-label="search"
              sx={{ color: 'text.secondary', width: 44, height: 44, mr: 0.5 }}
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
              sx={{ flexGrow: 1, minHeight: 60 }}
            >
              {NAV_ITEMS.map((item) => (
                <Tab
                  key={item.path}
                  label={item.label}
                  component={Link}
                  to={item.path}
                />
              ))}
            </Tabs>
            <Box sx={{ ml: 1, display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
              <IconButton
                onClick={() => setSearchExpanded(true)}
                size="small"
                sx={{ color: 'text.secondary' }}
                aria-label="search"
              >
                <SearchIcon />
              </IconButton>
            </Box>
          </>
        )}
      </Box>
      )}

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/player" element={<MensT20Scope><UnifiedPlayerProfile isMobile={isMobile} /></MensT20Scope>} />
        <Route path="/bowler" element={<BowlerRedirect />} />
        <Route path="/comparison" element={<MensT20Scope><BatterComparison /></MensT20Scope>} />
        <Route path="/matchups" element={<MensT20Scope><MatchupsTab isMobile={isMobile} /></MensT20Scope>} />
        <Route path="/query" element={<QueryBuilder isMobile={isMobile} />} />
        <Route path="/team" element={<MensT20Scope><TeamProfile isMobile={isMobile} /></MensT20Scope>} />
        <Route path="/team-comparison" element={<MensT20Scope><TeamComparison /></MensT20Scope>} />
        <Route path="/doppelgangers" element={<MensT20Scope><DoppelgangerLeaderboard /></MensT20Scope>} />
        <Route path="/ipl-predictions" element={<MensT20Scope><IPLPredictions /></MensT20Scope>} />
        <Route path="/rankings" element={<MensT20Scope><GlobalT20Rankings /></MensT20Scope>} />
        <Route path="/games/guess-innings" element={<MensT20Scope><GuessInningsGame isMobile={isMobile} /></MensT20Scope>} />
        <Route path="/games/player-journeys" element={<MensT20Scope><PlayerJourneysGame isMobile={isMobile} /></MensT20Scope>} />
        <Route path="/games/call-it" element={<MensT20Scope><CallItGame /></MensT20Scope>} />
        <Route path="/games/higher-lower" element={<MensT20Scope><HigherLowerGame /></MensT20Scope>} />
        <Route path="/wrapped/2025" element={<WrappedPage />} />
        <Route path="/search" element={<GoogleSearchLanding />} />
        <Route path="/credits" element={<CreditsPage />} />
        <Route path="/fantasy-planner" element={<MensT20Scope><FantasyPlanner isMobile={isMobile} /></MensT20Scope>} />
        <Route path="/scorecard/:matchId" element={<MatchScorecardPage />} />
        <Route path="/venue" element={
          <Box sx={{ my: { xs: 1.5, md: 3 }, bgcolor: 'background.default', color: 'text.primary' }}>
            <PreviewFilters
              error={error}
              loading={loading}
              isMobile={isMobile}
              filtersExpanded={filtersExpanded}
              showVisualizations={showVisualizations}
              setShowVisualizations={setShowVisualizations}
              hasFetchedRef={hasFetchedRef}
              venues={venues}
              selectedVenue={selectedVenue}
              setSelectedVenue={setSelectedVenue}
              startDate={startDate}
              endDate={endDate}
              handleDateChange={handleDateChange}
              today={TODAY}
              dayNightFilter={dayNightFilter}
              handleDayNightChange={handleDayNightChange}
              competitions={competitions}
              handleFilterChange={handleFilterChange}
              teams={teams}
              selectedTeam1={selectedTeam1}
              setSelectedTeam1={setSelectedTeam1}
              selectedTeam2={selectedTeam2}
              setSelectedTeam2={setSelectedTeam2}
            />

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
                  matchHistory={matchHistory}
                  filtersExpanded={filtersExpanded}
                  onToggleFilters={() => setFiltersExpanded((currentValue) => !currentValue)}
                  isMobile={isMobile}
                  leagues={competitions.leagues}
                  includeInternational={competitions.international}
                  topTeams={competitions.topTeams}
                  dayNightFilter={dayNightFilter}
                  onDayNightFilterChange={(nextValue) => handleDayNightChange(null, nextValue)}
                  espnEventId={espnEventId}
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
      {showBottomNav && (
        <>
          <MobileNavSpacer />
          <MobileBottomNav />
        </>
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
