import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Container, Box, Button, Typography, Chip, useMediaQuery, useTheme } from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import { useLocation, useNavigate } from 'react-router-dom';

// Design System
import { AlertBanner, MobileStickyHeader, Section, VisualizationCard } from './ui';
import { colors, spacing, typography, borderRadius, zIndex } from '../theme/designSystem';

// Filter Architecture
import FilterBar from './playerProfile/FilterBar';
import FilterSheet from './playerProfile/FilterSheet';
import { buildBowlerProfileFilters, DEFAULT_START_DATE, TODAY } from './bowlerProfile/filterConfig';
import BowlerProfileLoadingState from './bowlerProfile/BowlerProfileLoadingState';

// Bowling Components
import BowlingCareerStatsCards from './BowlingCareerStatsCards';
import WicketDistribution from './WicketDistribution';
import OverEconomyChart from './OverEconomyChart';
import OverCombinationsChart from './OverCombinationsChart';
import FrequentOversChart from './FrequentOversChart';
import ContributionGraph from './ContributionGraph';
import BowlerWagonWheel from './BowlerWagonWheel';
import BowlerPitchMap from './BowlerPitchMap';
import ContextualQueryPrompts from './ContextualQueryPrompts';
import { getBowlerContextualQueries } from '../utils/queryBuilderLinks';
import config from '../config';
import PlayerDNASummary from './PlayerDNASummary';
import PlayerDoppelgangers from './PlayerDoppelgangers';

const BowlerProfile = () => {
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
  const [playerOptions, setPlayerOptions] = useState([]);
  const [playerSearchInput, setPlayerSearchInput] = useState('');
  const [playerSearchLoading, setPlayerSearchLoading] = useState(false);
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

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const venuesRes = await fetch(`${config.API_URL}/venues`);
        setVenues(['All Venues', ...await venuesRes.json()]);
        
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
        
        if (playerNameFromURL) {
          try {
            const response = await fetch(
              `${config.API_URL}/search/player/${encodeURIComponent(playerNameFromURL)}`
            );
            if (response.ok) {
              const playerData = await response.json();
              if (playerData?.found) {
                const resolvedPlayer = {
                  name: playerData.player_name,
                  display_name: playerData.display_name || playerData.player_name,
                };
                console.log('Setting player from URL:', resolvedPlayer);
                setSelectedPlayer(resolvedPlayer);
                setPlayerSearchInput(resolvedPlayer.display_name);
                setPlayerOptions((prev) => {
                  if (prev.some((option) => option.name === resolvedPlayer.name)) {
                    return prev;
                  }
                  return [resolvedPlayer, ...prev];
                });
                if (autoload) {
                  setShouldFetch(true);
                }
              }
            } else {
              console.warn('Player name in URL not found:', playerNameFromURL);
            }
          } catch (resolveError) {
            console.error('Error resolving player name:', resolveError);
          }
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

  // Update URL when user changes filters
  useEffect(() => {
    if (!initialLoadComplete) return; // Skip on initial load
    
    const searchParams = new URLSearchParams();
    
    const selectedPlayerName = typeof selectedPlayer === 'string' ? selectedPlayer : selectedPlayer?.name;
    if (selectedPlayerName) {
      searchParams.set('name', selectedPlayerName);
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
    const selectedPlayerName = typeof selectedPlayer === 'string' ? selectedPlayer : selectedPlayer?.name;
    if (!selectedPlayerName) return;
    console.log('Manually triggered fetch for player:', selectedPlayerName);
    setShouldFetch(true);
  };

  const handleFilterChange = (key, value) => {
    if (key === 'player') {
      setSelectedPlayer(value);
      if (value) {
        const label = typeof value === 'string' ? value : (value.display_name || value.name);
        setPlayerSearchInput(label);
      }
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
    if (nextValues.player) {
      const label = typeof nextValues.player === 'string'
        ? nextValues.player
        : (nextValues.player.display_name || nextValues.player.name);
      setPlayerSearchInput(label);
    }
    setSelectedVenue(nextValues.venue);
    setDateRange({ start: nextValues.startDate, end: nextValues.endDate });
    setCompetitionFilters(nextCompetitionFilters);

    if (nextValues.player) {
      setShouldFetch(true);
    }

    setFilterDrawerOpen(false);
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
    () => buildBowlerProfileFilters({
      players: playerOptions,
      venues,
      playerSearch: {
        inputValue: playerSearchInput,
        onInputChange: (_, nextInput, reason) => {
          setPlayerSearchInput(nextInput);
          if (reason === 'input') {
            setSelectedPlayer(null);
          }
        },
        loading: playerSearchLoading,
        filterOptions: (options) => options,
      },
    }),
    [playerOptions, playerSearchInput, playerSearchLoading, venues]
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

  const selectedPlayerName = useMemo(() => {
    if (!selectedPlayer) return null;
    return typeof selectedPlayer === 'string' ? selectedPlayer : selectedPlayer.name;
  }, [selectedPlayer]);

  const selectedPlayerLabel = useMemo(() => {
    if (!selectedPlayer) return null;
    return typeof selectedPlayer === 'string' ? selectedPlayer : (selectedPlayer.display_name || selectedPlayer.name);
  }, [selectedPlayer]);

  const searchDebounceRef = useRef(null);

  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }

    if (!playerSearchInput || playerSearchInput.trim().length < 2) {
      setPlayerOptions([]);
      setPlayerSearchLoading(false);
      return;
    }

    searchDebounceRef.current = setTimeout(async () => {
      setPlayerSearchLoading(true);
      try {
        const response = await fetch(
          `${config.API_URL}/search/suggestions?q=${encodeURIComponent(playerSearchInput.trim())}&limit=10`
        );
        const data = await response.json();
        const players = (data.suggestions || []).filter((item) => item.type === 'player');
        setPlayerOptions(players);
      } catch (searchError) {
        console.error('Error fetching player suggestions:', searchError);
        setPlayerOptions([]);
      } finally {
        setPlayerSearchLoading(false);
      }
    }, 250);

    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, [playerSearchInput]);

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

  useEffect(() => {
    // Fetch bowling stats when shouldFetch is triggered
    const fetchBowlingStats = async () => {
      if (!shouldFetch || !selectedPlayerName) return;
      setShouldFetch(false);
      
      console.log('Fetching bowling stats for player:', selectedPlayerName);
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
          fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayerName)}/bowling_stats?${params}`),
          fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayerName)}/bowling_ball_stats?${params}`)
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
      }
    };

    fetchBowlingStats();
  }, [shouldFetch, selectedPlayerName, dateRange, selectedVenue, competitionFilters]);

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
            title={selectedPlayerLabel || 'Bowler Profile'}
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
              Bowler Profile
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
            {loading && <BowlerProfileLoadingState isMobile={isMobile} />}

            {stats && !loading && (
              <Box sx={{ mt: isMobile ? 2 : 0 }}>
                <Section title="Overview" isMobile={isMobile} columns="1fr" disableTopSpacing>
                  <BowlingCareerStatsCards stats={stats} isMobile={isMobile} />

                  <PlayerDNASummary
                    playerName={selectedPlayerName}
                    playerType="bowler"
                    startDate={dateRange.start}
                    endDate={dateRange.end}
                    leagues={competitionFilters.leagues}
                    includeInternational={competitionFilters.international}
                    topTeams={competitionFilters.topTeams}
                    venue={selectedVenue !== 'All Venues' ? selectedVenue : null}
                    fetchTrigger={dnaFetchTrigger}
                    isMobile={isMobile}
                  />

                  <PlayerDoppelgangers
                    playerName={selectedPlayerName}
                    playerType="bowler"
                    startDate={dateRange.start}
                    endDate={dateRange.end}
                    leagues={competitionFilters.leagues}
                    includeInternational={competitionFilters.international}
                    topTeams={competitionFilters.topTeams}
                    fetchTrigger={dnaFetchTrigger}
                    isMobile={isMobile}
                  />

                  <ContextualQueryPrompts
                    queries={getBowlerContextualQueries(selectedPlayerName, {
                      startDate: dateRange.start,
                      endDate: dateRange.end,
                      leagues: competitionFilters.leagues,
                      venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
                    })}
                    title={`🔍 Explore ${(selectedPlayerLabel || 'Bowler').split(' ').pop()}'s Bowling Data`}
                    isMobile={isMobile}
                  />
                </Section>

                <Section
                  title="Bowling Performance"
                  subtitle="Phase-wise wickets, economy rates, and over-by-over analysis"
                  isMobile={isMobile}
                  columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
                >
                  <VisualizationCard
                    title="Wicket Distribution"
                    ariaLabel="Wicket distribution by phase"
                    isMobile={isMobile}
                  >
                    <WicketDistribution stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>

                  <VisualizationCard
                    title="Over Economy"
                    ariaLabel="Over-by-over economy analysis"
                    isMobile={isMobile}
                  >
                    <OverEconomyChart stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>

                  <VisualizationCard
                    title="Frequent Overs"
                    ariaLabel="Frequent overs bowled"
                    isMobile={isMobile}
                  >
                    <FrequentOversChart stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>

                  <VisualizationCard
                    title="Over Combinations"
                    ariaLabel="Over combination patterns"
                    isMobile={isMobile}
                  >
                    <OverCombinationsChart stats={stats} isMobile={isMobile} wrapInCard={false} />
                  </VisualizationCard>
                </Section>

                <Section
                  title="Shot Analysis"
                  subtitle="Where the bowler was hit and pitch map distribution"
                  isMobile={isMobile}
                  columns={{ xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }}
                >
                  <VisualizationCard isMobile={isMobile} ariaLabel="Wagon wheel showing where bowler was hit">
                    <BowlerWagonWheel
                      playerName={selectedPlayerName}
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
                  <VisualizationCard isMobile={isMobile} ariaLabel="Pitch map distribution for bowler">
                    <BowlerPitchMap
                      playerName={selectedPlayerName}
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
                  title="Performance Timeline"
                  subtitle="Fantasy points contribution over time"
                  isMobile={isMobile}
                  columns="1fr"
                >
                  <VisualizationCard title="Contribution Timeline" isMobile={isMobile}>
                    <ContributionGraph
                      innings={stats.innings || []}
                      mode="bowler"
                      dateRange={dateRange}
                      isMobile={isMobile}
                    />
                  </VisualizationCard>
                </Section>
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

export default BowlerProfile;
