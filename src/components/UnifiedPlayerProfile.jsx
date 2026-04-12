import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  Box, Button, Typography, TextField, CircularProgress,
  Alert, Autocomplete, ToggleButtonGroup, ToggleButton, Card, Chip, LinearProgress,
  useMediaQuery, useTheme
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  LineChart, Line, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis,
} from 'recharts';
import CompetitionFilter from './CompetitionFilter';
import TopInnings from './TopInnings';
import BowlingMatchupMatrix from './BowlingMatchupMatrix';
import PlayerDNASummary from './PlayerDNASummary';
import PlayerDoppelgangers from './PlayerDoppelgangers';
import VenueSectionTabs from './VenueSectionTabs';
import VenueNotesDesktopNav from './VenueNotesDesktopNav';
import OverviewSection from './playerProfile/sections/OverviewSection';
import PerformanceSection from './playerProfile/sections/PerformanceSection';
import DismissalSection from './playerProfile/sections/DismissalSection';
import VisualizationsSection from './playerProfile/sections/VisualizationsSection';
import ExploreSection from './playerProfile/sections/ExploreSection';
import RecentFormStrip from './playerProfile/RecentFormStrip';
import AdvancedBowlingAnalyticsSection from './playerProfile/AdvancedBowlingAnalyticsSection';
import BoundaryAnalysis from './BoundaryAnalysis';
import usePlayerData from '../hooks/usePlayerData';
import config from '../config';

const DEFAULT_START_DATE = "2020-01-01";
const TODAY = new Date().toISOString().split('T')[0];

const GlobalRankTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <Box sx={{ p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}>
      <Typography variant="caption" sx={{ display: 'block', fontWeight: 700 }}>{label}</Typography>
      <Typography variant="caption" sx={{ display: 'block' }}>
        Score: {payload[0].value ?? 'N/A'}
      </Typography>
    </Box>
  );
};

const GlobalT20RankSection = ({ mode, rankPayload, loading }) => {
  const modePayload = mode === 'bowling' ? rankPayload?.bowling : rankPayload?.batting;
  const ranking = modePayload?.ranking;
  const trajectory = (modePayload?.trajectory || []).slice(-6).map((point) => ({
    ...point,
    label: point.date ? point.date.slice(2, 7) : '--',
    score: point.quality_score,
  }));
  const hasTrajectoryValues = trajectory.some((point) => point.score !== null && point.score !== undefined);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
        <CircularProgress size={20} />
      </Box>
    );
  }

  if (!ranking) {
    return (
      <Typography variant="body2" color="text.secondary">
        No global ranking found for this player in the selected window.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'grid', gap: 1.25 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
          sx={{
            width: 30,
            height: 30,
            borderRadius: '50%',
            bgcolor: 'primary.main',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: '0.78rem',
          }}
        >
          {ranking.rank}
        </Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, flex: 1 }}>
          Global T20 Rank
        </Typography>
        <Chip
          size="small"
          color="primary"
          label={`Quality ${Number(ranking.quality_score || 0).toFixed(1)}`}
          sx={{ fontWeight: 700 }}
        />
      </Box>

      {[
        { label: 'Quality', value: ranking.quality_score },
        { label: 'Strike Factor', value: ranking.strike_factor },
        { label: 'Control Factor', value: ranking.control_factor },
      ].map((metric) => (
        <Box key={metric.label}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="caption" color="text.secondary">{metric.label}</Typography>
            <Typography variant="caption" sx={{ fontWeight: 700 }}>{Number(metric.value || 0).toFixed(1)}</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={Math.max(0, Math.min(100, Number(metric.value || 0)))}
            sx={{ height: 6, borderRadius: 999, mt: 0.25 }}
          />
        </Box>
      ))}

      <Box>
        <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>
          Last 6 Months
        </Typography>
        <Box sx={{ mt: 0.5, height: 120, border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          {hasTrajectoryValues ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trajectory} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis hide domain={[0, 100]} />
                <RechartsTooltip content={<GlobalRankTooltip />} />
                <Line type="monotone" dataKey="score" stroke="#1976d2" strokeWidth={2} dot={false} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography variant="caption" color="text.secondary">No trajectory data</Typography>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};

const UnifiedPlayerProfile = ({ isMobile: isMobileProp }) => {
  const theme = useTheme();
  const isMobileMedia = useMediaQuery(theme.breakpoints.down('md'));
  const isMobile = isMobileProp ?? isMobileMedia;

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
  const [activeSectionId, setActiveSectionId] = useState('overview');
  const [fetchTrigger, setFetchTrigger] = useState(0);
  const [globalRankPayload, setGlobalRankPayload] = useState(null);
  const [globalRankLoading, setGlobalRankLoading] = useState(false);

  const sectionRefs = useRef({});

  const {
    battingStats, bowlingStats, dismissalStats, bowlingDismissalStats,
    playerType, loading, error, fetchPlayerType, fetchAllData
  } = usePlayerData(selectedPlayer, dateRange, selectedVenue, competitionFilters);

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

        const playerNameFromURL = getQueryParam('name');
        const autoload = getQueryParam('autoload') === 'true';
        const tabFromURL = getQueryParam('tab');
        const startDateFromURL = getQueryParam('start_date');
        const endDateFromURL = getQueryParam('end_date');
        const venueFromURL = getQueryParam('venue');

        if (tabFromURL === 'bowling') setActiveTab('bowling');

        if (startDateFromURL || endDateFromURL) {
          setDateRange({
            start: startDateFromURL || DEFAULT_START_DATE,
            end: endDateFromURL || TODAY
          });
        }

        if (venueFromURL) setSelectedVenue(venueFromURL);

        if (playerNameFromURL && playersList.includes(playerNameFromURL)) {
          setSelectedPlayer(playerNameFromURL);
          if (autoload) setTimeout(() => setShouldFetch(true), 500);
        }

        setInitialLoadComplete(true);
      } catch (err) {
        console.error('Error fetching initial data:', err);
        setInitialLoadComplete(true);
      }
    };
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (selectedPlayer) fetchPlayerType();
  }, [selectedPlayer, fetchPlayerType]);

  useEffect(() => {
    setGlobalRankPayload(null);
  }, [selectedPlayer]);

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

  useEffect(() => {
    if (initialLoadComplete && selectedPlayer && getQueryParam('autoload') === 'true' && !battingStats && !bowlingStats && !loading && !shouldFetch) {
      const timer = setTimeout(() => setShouldFetch(true), 500);
      return () => clearTimeout(timer);
    }
  }, [initialLoadComplete, selectedPlayer, battingStats, bowlingStats, loading, shouldFetch]);

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

  useEffect(() => {
    if (shouldFetch && selectedPlayer) {
      fetchAllData();
      setFetchTrigger(prev => prev + 1);
      setShouldFetch(false);
    }
  }, [shouldFetch, selectedPlayer, fetchAllData]);

  useEffect(() => {
    if (!selectedPlayer || fetchTrigger <= 0) return;

    let cancelled = false;

    const fetchGlobalRanking = async () => {
      try {
        setGlobalRankLoading(true);
        const params = new URLSearchParams();
        params.set('start_date', dateRange.start);
        params.set('end_date', dateRange.end);
        params.set('snapshots', '6');
        params.set('mode', activeTab === 'bowling' ? 'bowling' : 'batting');

        const response = await fetch(
          `${config.API_URL}/rankings/player/${encodeURIComponent(selectedPlayer)}?${params.toString()}`,
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!cancelled) setGlobalRankPayload(data);
      } catch (err) {
        console.error('Failed to fetch global rank payload', err);
        if (!cancelled) setGlobalRankPayload(null);
      } finally {
        if (!cancelled) setGlobalRankLoading(false);
      }
    };

    fetchGlobalRanking();
    return () => { cancelled = true; };
  }, [selectedPlayer, fetchTrigger, dateRange.start, dateRange.end, activeTab]);

  const handleFetch = () => {
    if (!selectedPlayer) return;
    setShouldFetch(true);
  };

  const handleTabChange = (_, newTab) => {
    if (newTab !== null) {
      setActiveTab(newTab);
      setActiveSectionId('overview');
    }
  };

  const currentStats = activeTab === 'bowling' ? bowlingStats : battingStats;
  const currentDismissalStats = activeTab === 'bowling' ? bowlingDismissalStats : dismissalStats;
  const hasData = currentStats !== null;

  // Build section groups (mirrors VenueNotes pattern)
  const sectionGroups = useMemo(() => {
    if (!hasData) return [];

    const groups = [
      {
        id: 'overview',
        label: 'Overview',
        content: <OverviewSection stats={currentStats} mode={activeTab} />,
      },
      {
        id: 'global-rank',
        label: 'Global T20 Rank',
        content: (
          <GlobalT20RankSection
            mode={activeTab}
            rankPayload={globalRankPayload}
            loading={globalRankLoading}
          />
        ),
      },
      {
        id: 'dna',
        label: 'DNA & Similar',
        content: (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <PlayerDNASummary
              playerName={selectedPlayer}
              playerType={activeTab === 'bowling' ? 'bowler' : 'batter'}
              startDate={dateRange.start}
              endDate={dateRange.end}
              leagues={competitionFilters.leagues}
              includeInternational={competitionFilters.international}
              topTeams={competitionFilters.topTeams}
              venue={selectedVenue !== 'All Venues' ? selectedVenue : undefined}
              fetchTrigger={fetchTrigger}
            />
            <PlayerDoppelgangers
              playerName={selectedPlayer}
              playerType={activeTab === 'bowling' ? 'bowler' : 'batter'}
              startDate={dateRange.start}
              endDate={dateRange.end}
              leagues={competitionFilters.leagues}
              includeInternational={competitionFilters.international}
              topTeams={competitionFilters.topTeams}
              fetchTrigger={fetchTrigger}
              isMobile={isMobile}
            />
          </Box>
        ),
      },
      {
        id: 'performance',
        label: 'Performance',
        content: (
          <PerformanceSection
            stats={currentStats}
            mode={activeTab}
            isMobile={isMobile}
            playerName={selectedPlayer}
            dateRange={dateRange}
            selectedVenue={selectedVenue}
            competitionFilters={competitionFilters}
          />
        ),
      },
    ];

    // Matchups — batting only
    if (activeTab === 'batting' && battingStats) {
      groups.push({
        id: 'matchups',
        label: 'Matchups',
        content: (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <BowlingMatchupMatrix stats={battingStats} />
            <TopInnings innings={battingStats.innings || []} count={10} />
          </Box>
        ),
      });
    }

    groups.push({
      id: 'advanced-analytics',
      label: 'Advanced Analytics',
      content: (
        activeTab === 'bowling' ? (
          <AdvancedBowlingAnalyticsSection
            playerName={selectedPlayer}
            dateRange={dateRange}
            selectedVenue={selectedVenue}
            competitionFilters={competitionFilters}
            isMobile={isMobile}
            enabled={activeSectionId === 'advanced-analytics'}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">
            Advanced analytics in this section are currently available for bowling view.
          </Typography>
        )
      ),
    });

    groups.push({
      id: 'boundaries',
      label: 'Boundaries',
      content: (
        <BoundaryAnalysis
          context={activeTab === 'bowling' ? 'bowler' : 'batter'}
          name={selectedPlayer}
          startDate={dateRange.start}
          endDate={dateRange.end}
          leagues={competitionFilters.leagues}
          includeInternational={competitionFilters.international}
          isMobile={isMobile}
        />
      ),
    });

    groups.push({
      id: 'dismissals',
      label: activeTab === 'bowling' ? 'Wickets' : 'Dismissals',
      content: (
        <DismissalSection
          dismissalData={currentDismissalStats}
          mode={activeTab}
          playerName={selectedPlayer}
          dateRange={dateRange}
          selectedVenue={selectedVenue}
          competitionFilters={competitionFilters}
          isMobile={isMobile}
        />
      ),
    });

    groups.push({
      id: 'visualizations',
      label: 'Visualizations',
      content: (
        <VisualizationsSection
          stats={currentStats}
          mode={activeTab}
          selectedPlayer={selectedPlayer}
          dateRange={dateRange}
          selectedVenue={selectedVenue}
          competitionFilters={competitionFilters}
        />
      ),
    });

    groups.push({
      id: 'explore',
      label: 'Explore',
      content: (
        <ExploreSection
          playerName={selectedPlayer}
          mode={activeTab}
          dateRange={dateRange}
          venue={selectedVenue}
        />
      ),
    });

    return groups;
  }, [
    hasData, currentStats, currentDismissalStats, activeTab, battingStats,
    selectedPlayer, dateRange, selectedVenue, competitionFilters, isMobile, fetchTrigger,
    globalRankPayload, globalRankLoading, activeSectionId,
  ]);

  // Scroll to section handler
  const handleSectionSelect = useCallback((sectionId) => {
    setActiveSectionId(sectionId);
    const el = sectionRefs.current[sectionId];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  // Reset active section on tab change or new data
  useEffect(() => {
    setActiveSectionId('overview');
  }, [activeTab, selectedPlayer]);

  // IntersectionObserver for auto-tracking active section
  useEffect(() => {
    if (!sectionGroups.length) return undefined;

    const visibleSections = new Map();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const sectionId = entry.target.dataset.sectionId;
        if (!sectionId) return;
        if (entry.isIntersecting) {
          visibleSections.set(sectionId, entry.intersectionRatio);
        } else {
          visibleSections.delete(sectionId);
        }
      });

      const nextActive = [...visibleSections.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
      if (nextActive) setActiveSectionId(nextActive);
    }, {
      rootMargin: '-15% 0px -60% 0px',
      threshold: [0.1, 0.35, 0.6],
    });

    sectionGroups.forEach((group) => {
      const el = sectionRefs.current[group.id];
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sectionGroups]);

  // Get recent innings for the form strip
  const recentInnings = useMemo(() => {
    if (activeTab === 'bowling' && bowlingStats?.innings) return bowlingStats.innings;
    if (activeTab === 'batting' && battingStats?.innings) return battingStats.innings;
    return [];
  }, [activeTab, battingStats, bowlingStats]);

  return (
    <Box sx={{ mx: { xs: 0, sm: 2 }, p: { xs: 0, sm: 2 }, maxWidth: 1400, margin: '0 auto' }}>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Filter Bar */}
      <Box sx={{ px: { xs: 1.5, sm: 0 }, mb: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 2, mb: 2 }}>
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
      </Box>

      {/* Loading state */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Main content */}
      {hasData && !loading && (
        <>
          {/* Header area */}
          <Box
            sx={{
              mb: { xs: 0.5, sm: 2.5 },
              px: { xs: 1.5, sm: 3 },
              py: { xs: 0.5, sm: 2.5 },
              border: isMobile ? 'none' : '1px solid',
              borderColor: 'divider',
              borderRadius: isMobile ? 0 : 3,
              boxShadow: isMobile ? 'none' : 1,
              bgcolor: isMobile ? 'transparent' : 'background.paper',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1.5, flexWrap: 'wrap' }}>
              <Typography
                variant={isMobile ? 'h5' : 'h4'}
                sx={{ fontWeight: 700, lineHeight: 1.15, flex: 1, minWidth: 0 }}
              >
                {selectedPlayer}
                <Typography variant="subtitle1" color="text.secondary" component="span" sx={{ ml: 1 }}>
                  {activeTab === 'bowling' ? 'Bowling' : 'Batting'} Profile
                </Typography>
              </Typography>

              {showBattingTab && showBowlingTab && (
                <ToggleButtonGroup
                  value={activeTab}
                  exclusive
                  onChange={handleTabChange}
                  size="small"
                  sx={{ flexShrink: 0 }}
                >
                  <ToggleButton value="batting" sx={{ px: 2 }}>Batting</ToggleButton>
                  <ToggleButton value="bowling" sx={{ px: 2 }}>Bowling</ToggleButton>
                </ToggleButtonGroup>
              )}
            </Box>

            <RecentFormStrip innings={recentInnings} mode={activeTab} isMobile={isMobile} />
          </Box>

          {/* Section navigation + content */}
          {isMobile ? (
            <>
              <VenueSectionTabs
                sections={sectionGroups.map(({ id, label }) => ({ id, label }))}
                activeSectionId={activeSectionId}
                onSectionSelect={handleSectionSelect}
              />
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, px: 1, pb: 2 }}>
                {sectionGroups.map((section) => (
                  <Box
                    key={section.id}
                    ref={(el) => { sectionRefs.current[section.id] = el; }}
                    data-section-id={section.id}
                    sx={{ scrollMarginTop: '56px' }}
                  >
                    <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5, px: 0.5 }}>
                      {section.label}
                    </Typography>
                    {section.content}
                  </Box>
                ))}
              </Box>
            </>
          ) : (
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: '240px minmax(0, 1fr)',
                gap: 3,
                alignItems: 'start',
              }}
            >
              <VenueNotesDesktopNav
                sections={sectionGroups.map(({ id, label }) => ({ id, label }))}
                activeSectionId={activeSectionId}
                onSectionSelect={handleSectionSelect}
              />
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {sectionGroups.map((section) => (
                  <Box
                    key={section.id}
                    ref={(el) => { sectionRefs.current[section.id] = el; }}
                    data-section-id={section.id}
                    sx={{ scrollMarginTop: '88px' }}
                  >
                    <Card
                      sx={{
                        p: 3,
                        borderRadius: 3,
                        border: '1px solid',
                        borderColor: 'divider',
                        boxShadow: 1,
                      }}
                    >
                      <Typography variant="h5" sx={{ mb: 2.5, fontWeight: 700 }}>
                        {section.label}
                      </Typography>
                      {section.content}
                    </Card>
                  </Box>
                ))}
              </Box>
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default UnifiedPlayerProfile;
