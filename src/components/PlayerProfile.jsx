import React, { useState, useEffect, useMemo } from 'react';
import {
  Container,
  Box,
  Button,
  Typography,
  useMediaQuery,
  useTheme,
  Chip,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import { useLocation, useNavigate } from 'react-router-dom';
import CareerStatsCards from './CareerStatsCards';
import PhasePerformanceRadar from './PhasePerformanceRadar';
import PaceSpinBreakdown from './PaceSpinBreakdown';
import BowlingMatchupMatrix from './BowlingMatchupMatrix';
import InningsScatter from './InningsScatter';
import StrikeRateProgression from './StrikeRateProgression';
import TopInnings from './TopInnings'
import BallRunDistribution from './BallRunDistribution'
import StrikeRateIntervals from './StrikeRateIntervals'
import ContributionGraph from './ContributionGraph'
import ContextualQueryPrompts from './ContextualQueryPrompts'
import { getBatterContextualQueries } from '../utils/queryBuilderLinks'
import config from '../config';
import PlayerDNASummary from './PlayerDNASummary';
import WagonWheel from './WagonWheel';
import PlayerPitchMap from './PlayerPitchMap';
import { AlertBanner, MobileStickyHeader, Section, VisualizationCard } from './ui';
import { colors, spacing, typography, borderRadius, zIndex } from '../theme/designSystem';
import FilterBar from './playerProfile/FilterBar';
import FilterSheet from './playerProfile/FilterSheet';
import { buildPlayerProfileFilters, DEFAULT_START_DATE, TODAY } from './playerProfile/filterConfig';
import PlayerProfileLoadingState from './playerProfile/PlayerProfileLoadingState';

const PlayerProfile = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

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
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

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
  }, [selectedPlayer, selectedVenue, dateRange, stats, initialLoadComplete]);

  const handleFetch = () => {
    if (!selectedPlayer) return;
    console.log('Manually triggered fetch for player:', selectedPlayer);
    setShouldFetch(true);
  };

  const handleFilterChange = (key, value) => {
    if (key === 'player') {
      setSelectedPlayer(value);
      return;
    }

    if (key === 'venue') {
      setSelectedVenue(value);
      return;
    }

    if (key === 'startDate') {
      setDateRange((prev) => ({ ...prev, start: value }));
      return;
    }

    if (key === 'endDate') {
      setDateRange((prev) => ({ ...prev, end: value }));
    }
  };

  const handleApplyFilters = (nextValues, nextCompetitionFilters) => {
    setSelectedPlayer(nextValues.player);
    setSelectedVenue(nextValues.venue);
    setDateRange({ start: nextValues.startDate, end: nextValues.endDate });
    setCompetitionFilters(nextCompetitionFilters);

    if (nextValues.player) {
      setShouldFetch(true);
    }
  };

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedVenue !== 'All Venues') count += 1;
    if (dateRange.start !== DEFAULT_START_DATE) count += 1;
    if (dateRange.end !== TODAY) count += 1;
    if (competitionFilters.international) count += 1;
    if (competitionFilters.international && competitionFilters.topTeams !== 10) count += 1;
    return count;
  }, [selectedVenue, dateRange, competitionFilters]);

  const filterConfig = useMemo(
    () => buildPlayerProfileFilters({ players, venues }),
    [players, venues]
  );

  const filterValues = useMemo(
    () => ({
      player: selectedPlayer,
      startDate: dateRange.start,
      endDate: dateRange.end,
      venue: selectedVenue,
    }),
    [selectedPlayer, dateRange, selectedVenue]
  );

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
            ball_by_ball_stats: ballStatsData.ball_by_ball_stats || []
          });
          setDnaFetchTrigger(prev => prev + 1);
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

  const mobileFilterButton = (
    <Button
      variant="outlined"
      startIcon={<FilterListIcon />}
      onClick={() => setFilterDrawerOpen(true)}
      sx={{
        minHeight: 44,
        borderRadius: `${borderRadius.base}px`,
        borderColor: colors.neutral[300],
        color: colors.neutral[700],
        textTransform: 'none',
        fontWeight: typography.fontWeight.medium,
        backgroundColor: colors.neutral[0],
        '&:hover': {
          borderColor: colors.primary[400],
          backgroundColor: colors.primary[50],
        },
        '&:focus-visible': {
          outline: `2px solid ${colors.primary[600]}`,
          outlineOffset: 2,
        },
      }}
    >
      Filters
      {activeFilterCount > 0 && (
        <Chip
          label={activeFilterCount}
          size="small"
          sx={{
            ml: `${spacing.sm}px`,
            height: 20,
            minWidth: 20,
            fontSize: typography.fontSize.xs,
            backgroundColor: colors.primary[600],
            color: colors.neutral[0],
          }}
        />
      )}
    </Button>
  );

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: isMobile ? 2 : 4 }}>
        {error && (
          <AlertBanner severity="error" sx={{ mb: 2 }}>
            {error}
          </AlertBanner>
        )}

        {isMobile && stats && (
          <MobileStickyHeader
            title={selectedPlayer || 'Player Profile'}
            stats={[
              { label: 'Matches', value: stats.overall.matches },
              { label: 'Runs', value: stats.overall.runs, subLabel: `Avg ${stats.overall.average.toFixed(2)}` },
              { label: 'Strike Rate', value: stats.overall.strike_rate.toFixed(1) },
            ]}
            action={mobileFilterButton}
            enableCollapse
          />
        )}

        {isMobile && !stats && (
          <Box
            sx={{
              position: 'sticky',
              top: 0,
              zIndex: zIndex.sticky,
              backgroundColor: colors.neutral[0],
              borderBottom: `1px solid ${colors.neutral[200]}`,
              px: `${spacing.base}px`,
              py: `${spacing.base}px`,
              mb: `${spacing.base}px`,
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: typography.fontWeight.semibold }}>
              Player Profile
            </Typography>
            <Box sx={{ mt: `${spacing.sm}px` }}>{mobileFilterButton}</Box>
          </Box>
        )}

        <Box
          sx={{
            display: { xs: 'block', md: 'flex' },
            gap: { xs: 2, md: 4 },
          }}
        >
          {!isMobile && (
            <Box
              sx={{
                width: 280,
                flexShrink: 0,
                position: 'sticky',
                top: `${spacing.xl}px`,
                alignSelf: 'flex-start',
              }}
            >
              <Box
                sx={{
                  borderRadius: `${borderRadius.lg}px`,
                  border: `1px solid ${colors.neutral[200]}`,
                  backgroundColor: colors.neutral[0],
                  p: `${spacing.lg}px`,
                  boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
                }}
              >
                <Typography variant="h6" sx={{ mb: `${spacing.base}px` }}>
                  Filters
                </Typography>
                <FilterBar
                  filters={filterConfig}
                  values={filterValues}
                  onChange={handleFilterChange}
                  onSubmit={handleFetch}
                  loading={loading}
                  competitionFilters={competitionFilters}
                  onCompetitionChange={setCompetitionFilters}
                />
              </Box>
            </Box>
          )}

          <Box sx={{ flex: 1, minWidth: 0 }}>
            {loading && <PlayerProfileLoadingState isMobile={isMobile} />}

            {stats && !loading && (
              <Box sx={{ mt: isMobile ? 2 : 0 }}>
                <Section title="Career Overview" isMobile={isMobile} columns="1fr" disableTopSpacing>
                  <CareerStatsCards stats={stats} isMobile={isMobile} />

                  <PlayerDNASummary
                    playerName={selectedPlayer}
                    startDate={dateRange.start}
                    endDate={dateRange.end}
                    leagues={competitionFilters.leagues}
                    includeInternational={competitionFilters.international}
                    topTeams={competitionFilters.topTeams}
                    venue={selectedVenue !== 'All Venues' ? selectedVenue : null}
                    fetchTrigger={dnaFetchTrigger}
                    isMobile={isMobile}
                  />

                  <VisualizationCard title="Contribution Timeline" isMobile={isMobile}>
                    <ContributionGraph
                      innings={stats.innings || []}
                      mode="batter"
                      dateRange={dateRange}
                      isMobile={isMobile}
                    />
                  </VisualizationCard>
                </Section>

                <Section
                  title="Shot Analysis"
                  isMobile={isMobile}
                  columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
                >
                  <VisualizationCard isMobile={isMobile} ariaLabel="Wagon wheel shot map">
                    <WagonWheel
                      playerName={selectedPlayer}
                      startDate={dateRange.start}
                      endDate={dateRange.end}
                      venue={selectedVenue !== 'All Venues' ? selectedVenue : null}
                      leagues={competitionFilters.leagues}
                      includeInternational={competitionFilters.international}
                      topTeams={competitionFilters.topTeams}
                      isMobile={isMobile}
                      wrapInCard={false}
                    />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Pitch map distribution">
                    <PlayerPitchMap
                      playerName={selectedPlayer}
                      startDate={dateRange.start}
                      endDate={dateRange.end}
                      venue={selectedVenue !== 'All Venues' ? selectedVenue : null}
                      leagues={competitionFilters.leagues}
                      includeInternational={competitionFilters.international}
                      topTeams={competitionFilters.topTeams}
                      isMobile={isMobile}
                      wrapInCard={false}
                    />
                  </VisualizationCard>
                </Section>

                <Section
                  title="Performance Breakdown"
                  isMobile={isMobile}
                  columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
                >
                  <VisualizationCard isMobile={isMobile} ariaLabel="Phase performance radar chart">
                    <PhasePerformanceRadar stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Pace versus spin breakdown chart">
                    <PaceSpinBreakdown stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Innings scatter plot">
                    <InningsScatter innings={stats.innings} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Strike rate progression chart">
                    <StrikeRateProgression
                      selectedPlayer={selectedPlayer}
                      dateRange={dateRange}
                      selectedVenue={selectedVenue}
                      competitionFilters={competitionFilters}
                      isMobile={isMobile}
                      wrapInCard={false}
                    />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Ball-by-ball run distribution">
                    <BallRunDistribution innings={stats.innings} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Strike rate intervals chart">
                    <StrikeRateIntervals ballStats={stats.ball_by_ball_stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                </Section>

                <Section
                  title="Performance Highlights"
                  isMobile={isMobile}
                  columns={{ xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' }}
                >
                  <VisualizationCard isMobile={isMobile} ariaLabel="Top innings table">
                    <TopInnings innings={stats.innings} count={10} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                  <VisualizationCard isMobile={isMobile} ariaLabel="Bowling type matchup matrix">
                    <BowlingMatchupMatrix stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                </Section>

                {/* Contextual Query Prompts */}
                <ContextualQueryPrompts
                  queries={getBatterContextualQueries(selectedPlayer, {
                    startDate: dateRange.start,
                    endDate: dateRange.end,
                    leagues: competitionFilters.leagues,
                    venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
                  })}
                  title={`🔍 Explore ${selectedPlayer.split(' ').pop()}'s Data`}
                  isMobile={isMobile}
                />
              </Box>
            )}
          </Box>
        </Box>

        <FilterSheet
          open={filterDrawerOpen}
          onClose={() => setFilterDrawerOpen(false)}
          filters={filterConfig}
          values={filterValues}
          competitionFilters={competitionFilters}
          onApply={handleApplyFilters}
          loading={loading}
        />
      </Box>
    </Container>
  );
};

export default PlayerProfile;
