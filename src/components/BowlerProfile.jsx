import React, { useState, useEffect } from 'react';
import { Container, Box, Button, Typography, TextField, CircularProgress, Alert, Autocomplete } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import CompetitionFilter from './CompetitionFilter';
import BowlingCareerStatsCards from './BowlingCareerStatsCards';
import WicketDistribution from './WicketDistribution';
import OverEconomyChart from './OverEconomyChart';
import OverCombinationsChart from './OverCombinationsChart';
import FrequentOversChart from './FrequentOversChart';
import BowlingInningsTable from './BowlingInningsTable';
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getBowlerContextualQueries } from '../utils/queryBuilderLinks';
import config from '../config';
import PlayerDNASummary from './PlayerDNASummary';

const DEFAULT_START_DATE = "2020-01-01";
const TODAY = new Date().toISOString().split('T')[0];

const BowlerProfile = ({ isMobile }) => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Helper function to get URL parameters
  const getQueryParam = (param) => {
    const searchParams = new URLSearchParams(location.search);
    return searchParams.get(param);
  };
  
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [dateRange, setDateRange] = useState({ start: DEFAULT_START_DATE, end: TODAY });
  const [selectedVenue, setSelectedVenue] = useState("All Venues");
  const [players, setPlayers] = useState([]);
  const [venues, setVenues] = useState([]);
  const [competitionFilters, setCompetitionFilters] = useState({
    leagues: [],
    international: false,
    topTeams: 10
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [shouldFetch, setShouldFetch] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const [dnaFetchTrigger, setDnaFetchTrigger] = useState(0);

  // Add a direct event listener to trigger analysis on page load if needed
  useEffect(() => {
    // This function will run once when component mounts
    const urlParams = new URLSearchParams(window.location.search);
    const playerName = urlParams.get('name');
    const autoload = urlParams.get('autoload') === 'true';
    
    if (playerName && autoload) {
      console.log('Adding window load event for autoloading');
      
      // Add a one-time event listener for when everything is loaded
      const handleLoad = () => {
        setTimeout(() => {
          // Try to find and click the GO button
          const goButton = document.getElementById('go-button');
          if (goButton && !goButton.disabled) {
            console.log('Auto-clicking GO button from window load event');
            goButton.click();
          }
        }, 1000); // Longer delay to ensure everything is ready
      };
      
      window.addEventListener('load', handleLoad, { once: true });
      
      // Cleanup
      return () => {
        window.removeEventListener('load', handleLoad);
      };
    }
  }, []);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [playersRes, venuesRes] = await Promise.all([
          fetch(`${config.API_URL}/players`),
          fetch(`${config.API_URL}/venues`)
        ]);
        const playersList = await playersRes.json();
        setPlayers(playersList);
        setVenues(['All Venues', ...await venuesRes.json()]);
        
        console.log('Players loaded:', playersList);
        console.log('URL parameters:', { 
          name: getQueryParam('name'), 
          autoload: getQueryParam('autoload'),
          start_date: getQueryParam('start_date')
        });
        
        // Get player name and other parameters from URL if present
        const playerNameFromURL = getQueryParam('name');
        const autoload = getQueryParam('autoload') === 'true';
        const startDateFromURL = getQueryParam('start_date');
        const endDateFromURL = getQueryParam('end_date');
        const venueFromURL = getQueryParam('venue');
        
        // Update date range from URL parameters if present
        if (startDateFromURL || endDateFromURL) {
          console.log('Setting date range from URL:', { start: startDateFromURL || DEFAULT_START_DATE, end: endDateFromURL || TODAY });
          setDateRange({
            start: startDateFromURL || DEFAULT_START_DATE,
            end: endDateFromURL || TODAY
          });
        }
        
        // Set venue from URL if present
        if (venueFromURL) {
          console.log('Setting venue from URL:', venueFromURL);
          setSelectedVenue(venueFromURL);
        }
        
        if (playerNameFromURL && playersList.includes(playerNameFromURL)) {
          console.log('Setting player from URL:', playerNameFromURL);
          setSelectedPlayer(playerNameFromURL);
          
          // Auto-trigger data fetch if autoload parameter is true
          if (autoload) {
            setTimeout(() => {
              setShouldFetch(true);
            }, 500); // Small delay to ensure state is updated
          }
        } else if (playerNameFromURL) {
          console.warn('Player name in URL not found in player list:', playerNameFromURL);
        }
        
        setInitialLoadComplete(true);
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setError('Failed to load initial data');
        setInitialLoadComplete(true);
      }
    };
    fetchInitialData();
  }, []);

  // Function to programmatically click the GO button when needed
  useEffect(() => {
    if (initialLoadComplete && selectedPlayer && getQueryParam('autoload') === 'true' && !stats && !loading && !shouldFetch) {
      // Find and click the GO button after a small delay to ensure DOM is ready
      const timer = setTimeout(() => {
        const goButton = document.getElementById('go-button');
        if (goButton) {
          goButton.click();
          console.log('Auto-clicking GO button');
        }
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [initialLoadComplete, selectedPlayer, stats, loading, shouldFetch]);

  // Update URL when user changes filters
  useEffect(() => {
    if (!initialLoadComplete) return; // Skip on initial load
    
    const searchParams = new URLSearchParams();
    
    if (selectedPlayer) {
      searchParams.set('name', selectedPlayer);
    }
    
    if (selectedVenue !== 'All Venues') {
      searchParams.set('venue', selectedVenue);
    }
    
    if (dateRange.start !== DEFAULT_START_DATE) {
      searchParams.set('start_date', dateRange.start);
    }
    
    if (dateRange.end !== TODAY) {
      searchParams.set('end_date', dateRange.end);
    }
    
    if (stats) {
      searchParams.set('autoload', 'true');
    }
    
    // Update URL without reloading the page
    const newUrl = searchParams.toString() ? `?${searchParams.toString()}` : '';
    navigate(newUrl, { replace: true });
  }, [selectedPlayer, selectedVenue, dateRange, stats, initialLoadComplete, navigate]);

  const handleFetch = () => {
    if (!selectedPlayer) return;
    console.log('Manually triggered fetch for player:', selectedPlayer);
    setShouldFetch(true);
  };

  useEffect(() => {
    // Fetch bowling stats when shouldFetch is triggered
    const fetchBowlingStats = async () => {
      if (!shouldFetch || !selectedPlayer) return;
      
      console.log('Fetching bowling stats for player:', selectedPlayer);
      setLoading(true);
      const params = new URLSearchParams();
      
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);
      if (selectedVenue !== "All Venues") params.append('venue', selectedVenue);
      
      competitionFilters.leagues.forEach(league => params.append('leagues', league));
      params.append('include_international', competitionFilters.international);
      if (competitionFilters.international && competitionFilters.topTeams) {
        params.append('top_teams', competitionFilters.topTeams);
      }
  
      try {
        // Fetch both bowling stats endpoints in parallel
        const [statsResponse, ballStatsResponse] = await Promise.all([
          fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayer)}/bowling_stats?${params}`),
          fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayer)}/bowling_ball_stats?${params}`)
        ]);
    
        const [statsData, ballStatsData] = await Promise.all([
          statsResponse.json(),
          ballStatsResponse.json()
        ]);
    
        setStats({
          ...statsData,
          bowling_ball_stats: ballStatsData.bowling_ball_stats || []
        });
        setDnaFetchTrigger(prev => prev + 1);
        console.log('Bowling stats loaded successfully:', statsData);
        console.log('Bowling ball stats loaded successfully:', ballStatsData);
      } catch (error) {
        console.error('Error loading bowling stats:', error);
        setError('Failed to load player bowling statistics');
      } finally {
        setLoading(false);
        setShouldFetch(false);
      }
    };

    fetchBowlingStats();
  }, [shouldFetch, selectedPlayer, dateRange, selectedVenue, competitionFilters]);

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 2, mb: 4 }}>
          <Autocomplete
            value={selectedPlayer}
            onChange={(_, newValue) => setSelectedPlayer(newValue)}
            options={players}
            sx={{ width: { xs: '100%', md: 300 } }}
            getOptionLabel={(option) => {
              // If option is a string, return it directly
              if (typeof option === 'string') {
                return option;
              }
              // If option is an object, return option.name or default to empty string
              return option || '';
            }}
            isOptionEqualToValue={(option, value) => {
              // Handle string values (from URL) and object values
              if (typeof value === 'string') {
                return option === value;
              }
              return option === value;
            }}
            renderInput={(params) => <TextField {...params} label="Select Player" variant="outlined" required />}
          />

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              label="Start Date"
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="End Date"
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <Autocomplete
              value={selectedVenue}
              onChange={(_, newValue) => setSelectedVenue(newValue)}
              options={venues}
              sx={{ width: 250 }}
              renderInput={(params) => <TextField {...params} label="Select Venue" />}
            />
            <Button 
              variant="contained"
              onClick={handleFetch}
              disabled={!selectedPlayer || loading}
              id="go-button"
            >
              GO
            </Button>
          </Box>
        </Box>

        <CompetitionFilter onFilterChange={setCompetitionFilters} />

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {stats && !loading && (
          <Box sx={{ mt: 4 }}>
            {/* Career Stats Cards */}
            <BowlingCareerStatsCards stats={stats} />
            
            {/* Player DNA Summary */}
            <PlayerDNASummary
              playerName={selectedPlayer}
              playerType="bowler"
              startDate={dateRange.start}
              endDate={dateRange.end}
              leagues={competitionFilters.leagues}
              includeInternational={competitionFilters.international}
              topTeams={competitionFilters.topTeams}
              venue={selectedVenue !== 'All Venues' ? selectedVenue : null}
              fetchTrigger={dnaFetchTrigger}
            />
            
            {/* Contextual Query Prompts */}
            <ContextualQueryPrompts 
              queries={getBowlerContextualQueries(selectedPlayer, {
                startDate: dateRange.start,
                endDate: dateRange.end,
                leagues: competitionFilters.leagues,
                venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
              })}
              title={`🔍 Explore ${selectedPlayer.split(' ').pop()}'s Bowling Data`}
            />
            
            {/* Main 2x2 Grid Layout */}
            <Box sx={{ mt: 4, display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
              {/* Replacing BowlingPhasePerformanceRadar with WicketDistribution */}
              <WicketDistribution stats={stats} />
              <OverEconomyChart stats={stats} />
              <FrequentOversChart stats={stats} />
              <OverCombinationsChart stats={stats} />
            </Box>
            
            {/* Innings Performance Table */}
            <Box sx={{ mt: 4 }}>
              <BowlingInningsTable stats={stats} />
            </Box>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default BowlerProfile;