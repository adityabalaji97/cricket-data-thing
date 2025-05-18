import React, { useState, useEffect } from 'react';
import { Container, Box, Button, Typography, TextField, CircularProgress, Alert, Autocomplete } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import CareerStatsCards from './CareerStatsCards';
import PhasePerformanceRadar from './PhasePerformanceRadar';
import PaceSpinBreakdown from './PaceSpinBreakdown';
import BowlingMatchupMatrix from './BowlingMatchupMatrix';
import InningsScatter from './InningsScatter';
import StrikeRateProgression from './StrikeRateProgression';
import CompetitionFilter from './CompetitionFilter';
import TopInnings from './TopInnings'
import BallRunDistribution from './BallRunDistribution'
import StrikeRateIntervals from './StrikeRateIntervals'
import config from '../config';

const DEFAULT_START_DATE = "2020-01-01";
const TODAY = new Date().toISOString().split('T')[0];

const PlayerProfile = () => {
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
        console.log('URL parameters:', { name: getQueryParam('name'), autoload: getQueryParam('autoload') });
        
        // Get player name from URL if present
        const playerNameFromURL = getQueryParam('name');
        const autoload = getQueryParam('autoload') === 'true';
        
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
    // Inside fetchPlayerStats function in useEffect
    const fetchPlayerStats = async () => {
        if (!shouldFetch || !selectedPlayer) return;
        
        console.log('Fetching stats for player:', selectedPlayer);
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
          // Fetch both stats in parallel
          const [statsResponse, ballStatsResponse] = await Promise.all([
            fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayer)}/stats?${params}`),
            fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayer)}/ball_stats?${params}`)
          ]);
      
          const [statsData, ballStatsData] = await Promise.all([
            statsResponse.json(),
            ballStatsResponse.json()
          ]);
      
          setStats({
            ...statsData,
            ball_by_ball_stats: ballStatsData.ball_by_ball_stats || []  // Ensure we have a default value
          });
          console.log('Stats loaded successfully');
        } catch (error) {
          console.error('Error loading stats:', error);
          setError('Failed to load player statistics');
        } finally {
          setLoading(false);
          setShouldFetch(false);
        }
    };

    fetchPlayerStats();
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
            <CareerStatsCards stats={stats} />
            <Box sx={{ mt: 4, display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3 }}>
              <PhasePerformanceRadar stats={stats} />
              <PaceSpinBreakdown stats={stats} />
              <InningsScatter innings={stats.innings} />
              <StrikeRateProgression 
                selectedPlayer={selectedPlayer}
                dateRange={dateRange}
                selectedVenue={selectedVenue}
                competitionFilters={competitionFilters}
              />
              <BallRunDistribution innings={stats.innings} />
              <StrikeRateIntervals ballStats={stats.ball_by_ball_stats} />
            </Box>
            <TopInnings innings={stats.innings} count={10} />
            <BowlingMatchupMatrix stats={stats} />
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default PlayerProfile;