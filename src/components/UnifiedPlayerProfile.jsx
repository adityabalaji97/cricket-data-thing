import React, { useState, useEffect, useMemo } from 'react';
import {
  Container, Box, Button, Typography, TextField, CircularProgress,
  Alert, Autocomplete, ToggleButtonGroup, ToggleButton, Divider
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import CompetitionFilter from './CompetitionFilter';
import TopInnings from './TopInnings';
import BowlingMatchupMatrix from './BowlingMatchupMatrix';
import OverviewSection from './playerProfile/sections/OverviewSection';
import PerformanceSection from './playerProfile/sections/PerformanceSection';
import DismissalSection from './playerProfile/sections/DismissalSection';
import VisualizationsSection from './playerProfile/sections/VisualizationsSection';
import ExploreSection from './playerProfile/sections/ExploreSection';
import usePlayerData from '../hooks/usePlayerData';
import config from '../config';

const DEFAULT_START_DATE = "2020-01-01";
const TODAY = new Date().toISOString().split('T')[0];

const UnifiedPlayerProfile = ({ isMobile }) => {
  const location = useLocation();
  const navigate = useNavigate();

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
  const [activeTab, setActiveTab] = useState('batting');
  const [shouldFetch, setShouldFetch] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);

  const {
    battingStats, bowlingStats, dismissalStats, bowlingDismissalStats,
    playerType, loading, error, fetchPlayerType, fetchAllData
  } = usePlayerData(selectedPlayer, dateRange, selectedVenue, competitionFilters);

  // Determine which tabs to show
  const showBattingTab = useMemo(() => {
    if (playerType) return playerType.has_batting_data;
    return battingStats !== null;
  }, [playerType, battingStats]);

  const showBowlingTab = useMemo(() => {
    if (playerType) return playerType.has_bowling_data;
    return bowlingStats !== null;
  }, [playerType, bowlingStats]);

  // Load initial data (players list + venues)
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

        // Parse URL parameters
        const playerNameFromURL = getQueryParam('name');
        const autoload = getQueryParam('autoload') === 'true';
        const tabFromURL = getQueryParam('tab');
        const startDateFromURL = getQueryParam('start_date');
        const endDateFromURL = getQueryParam('end_date');
        const venueFromURL = getQueryParam('venue');

        if (tabFromURL === 'bowling') {
          setActiveTab('bowling');
        }

        if (startDateFromURL || endDateFromURL) {
          setDateRange({
            start: startDateFromURL || DEFAULT_START_DATE,
            end: endDateFromURL || TODAY
          });
        }

        if (venueFromURL) {
          setSelectedVenue(venueFromURL);
        }

        if (playerNameFromURL && playersList.includes(playerNameFromURL)) {
          setSelectedPlayer(playerNameFromURL);
          if (autoload) {
            setTimeout(() => setShouldFetch(true), 500);
          }
        }

        setInitialLoadComplete(true);
      } catch (err) {
        console.error('Error fetching initial data:', err);
        setInitialLoadComplete(true);
      }
    };
    fetchInitialData();
  }, []);

  // Fetch player type when player is selected
  useEffect(() => {
    if (selectedPlayer) {
      fetchPlayerType();
    }
  }, [selectedPlayer, fetchPlayerType]);

  useEffect(() => {
    if (!playerType) return;
    if (!playerType.has_batting_data && playerType.has_bowling_data) {
      setActiveTab('bowling');
      return;
    }
    if (playerType.has_batting_data && !playerType.has_bowling_data) {
      setActiveTab('batting');
    }
  }, [playerType]);

  // Auto-click GO button for autoload
  useEffect(() => {
    if (initialLoadComplete && selectedPlayer && getQueryParam('autoload') === 'true' && !battingStats && !bowlingStats && !loading && !shouldFetch) {
      const timer = setTimeout(() => setShouldFetch(true), 500);
      return () => clearTimeout(timer);
    }
  }, [initialLoadComplete, selectedPlayer, battingStats, bowlingStats, loading, shouldFetch]);

  // Update URL when filters change
  useEffect(() => {
    if (!initialLoadComplete) return;
    const searchParams = new URLSearchParams();
    if (selectedPlayer) searchParams.set('name', selectedPlayer);
    if (selectedVenue !== 'All Venues') searchParams.set('venue', selectedVenue);
    if (dateRange.start !== DEFAULT_START_DATE) searchParams.set('start_date', dateRange.start);
    if (dateRange.end !== TODAY) searchParams.set('end_date', dateRange.end);
    if (activeTab === 'bowling') searchParams.set('tab', 'bowling');
    if (battingStats || bowlingStats) searchParams.set('autoload', 'true');
    const newUrl = searchParams.toString() ? `?${searchParams.toString()}` : '';
    navigate(newUrl, { replace: true });
  }, [selectedPlayer, selectedVenue, dateRange, activeTab, battingStats, bowlingStats, initialLoadComplete, navigate]);

  // Trigger data fetch
  useEffect(() => {
    if (shouldFetch && selectedPlayer) {
      fetchAllData();
      setShouldFetch(false);
    }
  }, [shouldFetch, selectedPlayer, fetchAllData]);

  const handleFetch = () => {
    if (!selectedPlayer) return;
    setShouldFetch(true);
  };

  const handleTabChange = (_, newTab) => {
    if (newTab !== null) {
      setActiveTab(newTab);
    }
  };

  const currentStats = activeTab === 'bowling' ? bowlingStats : battingStats;
  const currentDismissalStats = activeTab === 'bowling' ? bowlingDismissalStats : dismissalStats;
  const hasData = currentStats !== null;

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Filter Bar */}
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 2, mb: 4 }}>
          <Autocomplete
            value={selectedPlayer}
            onChange={(_, newValue) => setSelectedPlayer(newValue)}
            options={players}
            sx={{ width: { xs: '100%', md: 300 } }}
            getOptionLabel={(option) => typeof option === 'string' ? option : option || ''}
            isOptionEqualToValue={(option, value) => option === value}
            renderInput={(params) => <TextField {...params} label="Select Player" variant="outlined" required />}
          />

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              label="Start Date" type="date" value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="End Date" type="date" value={dateRange.end}
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

        <CompetitionFilter onFilterChange={setCompetitionFilters} isMobile={isMobile} />

        {/* Loading state */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Main content */}
        {hasData && !loading && (
          <Box sx={{ mt: 4 }}>
            {/* Tab toggle - only show if player has both batting and bowling data */}
            {(showBattingTab && showBowlingTab) && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
                <ToggleButtonGroup
                  value={activeTab}
                  exclusive
                  onChange={handleTabChange}
                  size={isMobile ? 'small' : 'medium'}
                >
                  <ToggleButton value="batting" sx={{ px: 3 }}>
                    Batting
                  </ToggleButton>
                  <ToggleButton value="bowling" sx={{ px: 3 }}>
                    Bowling
                  </ToggleButton>
                </ToggleButtonGroup>
              </Box>
            )}

            {/* Player name header */}
            <Typography variant={isMobile ? 'h5' : 'h4'} gutterBottom sx={{ mb: 3 }}>
              {selectedPlayer}
              <Typography variant="subtitle1" color="text.secondary" component="span" sx={{ ml: 1 }}>
                {activeTab === 'bowling' ? 'Bowling' : 'Batting'} Profile
              </Typography>
            </Typography>

            {/* Overview Section */}
            <Box sx={{ mb: 4 }}>
              <OverviewSection stats={currentStats} mode={activeTab} />
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Performance Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom>Performance Breakdown</Typography>
              <PerformanceSection stats={currentStats} mode={activeTab} isMobile={isMobile} />
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Dismissals Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom>
                {activeTab === 'bowling' ? 'Wicket-Taking Methods' : 'Dismissal Analysis'}
              </Typography>
              <DismissalSection
                dismissalData={currentDismissalStats}
                mode={activeTab}
                playerName={selectedPlayer}
                dateRange={dateRange}
                selectedVenue={selectedVenue}
                competitionFilters={competitionFilters}
                isMobile={isMobile}
              />
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Visualizations Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom>Detailed Analysis</Typography>
              <VisualizationsSection
                stats={currentStats}
                mode={activeTab}
                selectedPlayer={selectedPlayer}
                dateRange={dateRange}
                selectedVenue={selectedVenue}
                competitionFilters={competitionFilters}
              />
            </Box>

            {/* Batting-specific extras */}
            {activeTab === 'batting' && battingStats && (
              <>
                <TopInnings innings={battingStats.innings || []} count={10} />
                <BowlingMatchupMatrix stats={battingStats} />
              </>
            )}

            <Divider sx={{ my: 3 }} />

            {/* Explore Section */}
            <Box sx={{ mb: 4 }}>
              <ExploreSection
                playerName={selectedPlayer}
                mode={activeTab}
                dateRange={dateRange}
                venue={selectedVenue}
              />
            </Box>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default UnifiedPlayerProfile;
