import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import ShareButton from './ui/ShareButton';
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
import PlayerGlance from './playerProfile/PlayerGlance';
import AdvancedBowlingAnalyticsSection from './playerProfile/AdvancedBowlingAnalyticsSection';
import BoundaryAnalysis from './BoundaryAnalysis';
import LazySection from './ui/LazySection';
import CollapsibleSection, { openSection } from './ui/CollapsibleSection';
import useIsMobile from '../hooks/useIsMobile';
import ImpactSection from './playerProfile/sections/ImpactSection';
import FilterSummary, { joinSummary, summarizeCompetitions, summarizeDateRange } from './ui/FilterSummary';
import usePlayerData from '../hooks/usePlayerData';
import config from '../config';
import { PROFILE_START_DATE } from '../utils/dateDefaults';

const DEFAULT_START_DATE = PROFILE_START_DATE;
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

const GlobalT20RankSection = ({ mode, rankPayload, loading, failed }) => {
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

  if (failed) {
    return (
      <Typography variant="body2" color="text.secondary">
        Couldn&apos;t load the global ranking. Long date windows can take too long to compute;
        try a shorter range.
      </Typography>
    );
  }

  if (!ranking) {
    // Used to say only "no ranking found", which read like missing data for players like Kohli.
    return (
      <Typography variant="body2" color="text.secondary">
        Not ranked in this window. The global T20 ranking covers men&apos;s T20 players with at
        least 50 balls {mode === 'bowling' ? 'bowled' : 'faced'} at each length (full, good, short
        of good{mode === 'bowling' ? '' : ', short'}) in the selected dates; a longer window
        usually qualifies more players.
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
            color: 'primary.contrastText',
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
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
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
  // Page layout (folded sections + chip nav) runs to md, so portrait tablets (600-899px) no longer
  // get the desktop 240px sidebar squeezed beside the cards. Charts still size on isMobile.
  const { isCompact } = useIsMobile();

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
  // The filters as of the last GO. Sections read these, not the live form: they used to refetch on
  // every date keystroke and venue pick while the user was still editing (and while the phone
  // filter sheet was open), before GO.
  const [applied, setApplied] = useState(null);
  const [globalRankPayload, setGlobalRankPayload] = useState(null);
  const [globalRankLoading, setGlobalRankLoading] = useState(false);
  const [globalRankFailed, setGlobalRankFailed] = useState(false);

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

        // The picker lists one canonical spelling per player, but links from elsewhere (query
        // builder, matchups, old shares) carry legacy spellings ("V Kohli"). The API resolves any
        // spelling, so accept the URL name and add it to the options rather than ignoring it.
        if (playerNameFromURL) {
          const match = playersList.find((p) => p.toLowerCase() === playerNameFromURL.toLowerCase());
          if (!match) setPlayers([...playersList, playerNameFromURL]);
          setSelectedPlayer(match || playerNameFromURL);
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
      setApplied({ player: selectedPlayer, dateRange, venue: selectedVenue, competitionFilters });
      setFetchTrigger(prev => prev + 1);
      setShouldFetch(false);
    }
  }, [shouldFetch, selectedPlayer, fetchAllData, dateRange, selectedVenue, competitionFilters]);

  useEffect(() => {
    if (!applied?.player || fetchTrigger <= 0) return;

    let cancelled = false;

    const fetchGlobalRanking = async () => {
      try {
        setGlobalRankLoading(true);
        setGlobalRankFailed(false);
        const params = new URLSearchParams();
        params.set('start_date', applied.dateRange.start);
        params.set('end_date', applied.dateRange.end);
        params.set('snapshots', '6');
        params.set('mode', activeTab === 'bowling' ? 'bowling' : 'batting');

        const response = await fetch(
          `${config.API_URL}/rankings/player/${encodeURIComponent(applied.player)}?${params.toString()}`,
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!cancelled) setGlobalRankPayload(data);
      } catch (err) {
        console.error('Failed to fetch global rank payload', err);
        if (!cancelled) {
          setGlobalRankPayload(null);
          setGlobalRankFailed(true);
        }
      } finally {
        if (!cancelled) setGlobalRankLoading(false);
      }
    };

    fetchGlobalRanking();
    return () => { cancelled = true; };
  }, [applied, fetchTrigger, activeTab]);

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
  const overviewTakeaway = (() => {
    const o = currentStats?.overall;
    if (!o) return undefined;
    if (activeTab === 'bowling') {
      return `${o.wickets || 0} wickets at economy ${(o.economy_rate || 0).toFixed(2)} in ${o.matches || 0} matches`;
    }
    return `${o.runs || 0} runs at average ${(o.average || 0).toFixed(1)}, strike rate ${(o.strike_rate || 0).toFixed(1)}`;
  })();

  const sectionGroups = useMemo(() => {
    if (!hasData || !applied) return [];
    const { player: appliedPlayer, dateRange: appliedRange, venue: appliedVenue, competitionFilters: appliedCompetitions } = applied;

    const groups = [
      ...(activeTab === 'batting' ? [{
        id: 'glance',
        label: 'At a glance',
        defaultOpen: true,
        takeaway: 'Runs, best phase, pace v spin, toughest bowling type',
        content: <PlayerGlance stats={currentStats} />,
      }] : []),
      {
        id: 'overview',
        label: 'Overview',
        defaultOpen: activeTab !== 'batting',
        takeaway: overviewTakeaway,
        content: <OverviewSection stats={currentStats} mode={activeTab} />,
      },
      {
        id: 'impact',
        label: 'Impact',
        defaultOpen: true,
        takeaway: 'Runs added compared with an average player in the same situations',
        content: (
          <ImpactSection
            playerName={appliedPlayer}
            mode={activeTab}
            dateRange={appliedRange}
            selectedVenue={appliedVenue}
            competitionFilters={appliedCompetitions}
          />
        ),
      },
      {
        id: 'global-rank',
        label: 'Global T20 Rank',
        takeaway: 'Where the player ranks among T20 players worldwide',
        content: (
          <GlobalT20RankSection
            mode={activeTab}
            rankPayload={globalRankPayload}
            loading={globalRankLoading}
            failed={globalRankFailed}
          />
        ),
      },
      {
        id: 'dna',
        label: 'DNA & Similar',
        takeaway: 'Playing style in words, and the most similar players',
        content: (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <PlayerDNASummary
              playerName={appliedPlayer}
              playerType={activeTab === 'bowling' ? 'bowler' : 'batter'}
              startDate={appliedRange.start}
              endDate={appliedRange.end}
              leagues={appliedCompetitions.leagues}
              includeInternational={appliedCompetitions.international}
              topTeams={appliedCompetitions.topTeams}
              venue={appliedVenue !== 'All Venues' ? appliedVenue : undefined}
              fetchTrigger={fetchTrigger}
            />
            <PlayerDoppelgangers
              playerName={appliedPlayer}
              playerType={activeTab === 'bowling' ? 'bowler' : 'batter'}
              startDate={appliedRange.start}
              endDate={appliedRange.end}
              leagues={appliedCompetitions.leagues}
              includeInternational={appliedCompetitions.international}
              topTeams={appliedCompetitions.topTeams}
              fetchTrigger={fetchTrigger}
              isMobile={isMobile}
            />
          </Box>
        ),
      },
      {
        id: 'performance',
        label: 'Performance',
        takeaway: 'By phase, against pace and spin, by line and length',
        content: (
          <PerformanceSection
            stats={currentStats}
            mode={activeTab}
            isMobile={isMobile}
            playerName={appliedPlayer}
            dateRange={appliedRange}
            selectedVenue={appliedVenue}
            competitionFilters={appliedCompetitions}
          />
        ),
      },
    ];

    // Matchups — batting only
    if (activeTab === 'batting' && battingStats) {
      groups.push({
        id: 'matchups',
        label: 'Matchups',
        takeaway: 'Against each bowling type',
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
      takeaway: 'Pressure, spells and rolling form',
      content: (
        activeTab === 'bowling' ? (
          <AdvancedBowlingAnalyticsSection
            playerName={appliedPlayer}
            dateRange={appliedRange}
            selectedVenue={appliedVenue}
            competitionFilters={appliedCompetitions}
            isMobile={isMobile}
            // LazySection already defers the mount until the section nears the viewport. Gating
            // on the *active* section blanked the content as soon as you scrolled past it.
            enabled
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
      takeaway: 'How often boundaries come, by phase and bowler type',
      content: (
        <BoundaryAnalysis
          context={activeTab === 'bowling' ? 'bowler' : 'batter'}
          name={appliedPlayer}
          startDate={appliedRange.start}
          endDate={appliedRange.end}
          leagues={appliedCompetitions.leagues}
          includeInternational={appliedCompetitions.international}
          isMobile={isMobile}
        />
      ),
    });

    groups.push({
      id: 'dismissals',
      label: activeTab === 'bowling' ? 'Wickets' : 'Dismissals',
      takeaway: 'How and where wickets fall',
      content: (
        <DismissalSection
          dismissalData={currentDismissalStats}
          mode={activeTab}
          playerName={appliedPlayer}
          dateRange={appliedRange}
          selectedVenue={appliedVenue}
          competitionFilters={appliedCompetitions}
          isMobile={isMobile}
        />
      ),
    });

    groups.push({
      id: 'visualizations',
      label: 'Visualizations',
      takeaway: 'Innings by innings: scores, strike rate, consistency',
      content: (
        <VisualizationsSection
          stats={currentStats}
          mode={activeTab}
          appliedPlayer={appliedPlayer}
          dateRange={appliedRange}
          selectedVenue={appliedVenue}
          competitionFilters={appliedCompetitions}
        />
      ),
    });

    groups.push({
      id: 'explore',
      label: 'Explore',
      takeaway: 'Ready-made questions for the query builder',
      content: (
        <ExploreSection
          playerName={appliedPlayer}
          mode={activeTab}
          dateRange={appliedRange}
          venue={appliedVenue}
        />
      ),
    });

    return groups;
  }, [
    hasData, currentStats, currentDismissalStats, activeTab, battingStats,
    applied, isMobile, fetchTrigger, overviewTakeaway,
    globalRankPayload, globalRankLoading, globalRankFailed,
  ]);

  // Scroll to section handler
  const handleSectionSelect = useCallback((sectionId) => {
    setActiveSectionId(sectionId);
    if (isCompact) {
      // Opens the folded section, then scrolls to it.
      openSection(`section-${sectionId}`);
      return;
    }
    const el = sectionRefs.current[sectionId];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [isCompact]);

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
    // Innings arrive newest first, every one in the window (100+ for a long range); the strip is
    // for recent form, so it shows the last 10.
    if (activeTab === 'bowling' && bowlingStats?.innings) return bowlingStats.innings.slice(0, 10);
    if (activeTab === 'batting' && battingStats?.innings) return battingStats.innings.slice(0, 10);
    return [];
  }, [activeTab, battingStats, bowlingStats]);

  return (
    <Box sx={{ mx: { xs: 0, sm: 2 }, p: { xs: 0, sm: 2 }, maxWidth: 1400, margin: '0 auto' }}>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Filter Bar: one summary line on phones once a profile is showing */}
      <Box sx={{ px: { xs: 1.5, sm: 0 }, mb: 2 }}>
        <FilterSummary
          collapsed={isMobile && hasData}
          title={selectedPlayer}
          summary={joinSummary(
            summarizeDateRange(dateRange.start, dateRange.end),
            selectedVenue && selectedVenue !== 'All Venues' ? selectedVenue.split(',')[0] : null,
            summarizeCompetitions(competitionFilters),
          )}
          sheetTitle="Player filters"
        >
        <Box>
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
              sx={{ width: { xs: '100%', md: 250 } }}
              renderInput={(params) => <TextField {...params} label="Select Venue" />}
            />
            <Button
              variant="contained"
              onClick={handleFetch}
              disabled={!selectedPlayer || loading}
              id="go-button"
              data-filter-submit
            >
              GO
            </Button>
          </Box>
        </Box>
        <CompetitionFilter onFilterChange={setCompetitionFilters} isMobile={isMobile} value={competitionFilters} />
        </Box>
        </FilterSummary>
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
              {/* Name and caption stack, so a phone never splits "V / Kohli Batting / Profile". */}
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant={isMobile ? 'h5' : 'h4'} sx={{ fontWeight: 700, lineHeight: 1.15 }}>
                  {selectedPlayer}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {activeTab === 'bowling' ? 'Bowling' : 'Batting'} profile
                </Typography>
              </Box>

              <ShareButton variant="icon" kind="player" title={`${selectedPlayer} on Hindsight`} />
              {showBattingTab && showBowlingTab && (
                <ToggleButtonGroup
                  value={activeTab}
                  exclusive
                  onChange={handleTabChange}
                  size="small"
                  fullWidth={isMobile}
                  sx={{ flexShrink: 0, flexBasis: { xs: '100%', sm: 'auto' } }}
                >
                  <ToggleButton value="batting" sx={{ px: 2 }}>Batting</ToggleButton>
                  <ToggleButton value="bowling" sx={{ px: 2 }}>Bowling</ToggleButton>
                </ToggleButtonGroup>
              )}
            </Box>

            <RecentFormStrip innings={recentInnings} mode={activeTab} isMobile={isMobile} />
          </Box>

          {/* Section navigation + content */}
          {isCompact ? (
            <>
              <VenueSectionTabs
                sections={sectionGroups.map(({ id, label }) => ({ id, label }))}
                activeSectionId={activeSectionId}
                onSectionSelect={handleSectionSelect}
              />
              {/* Phones and portrait tablets: each section folds to its title and a one-line
                  takeaway; Overview and Impact start open. A section mounts (and fetches) the
                  first time it is opened. */}
              <Box sx={{ display: 'flex', flexDirection: 'column', px: 1, pb: 2 }}>
                {sectionGroups.map((section) => (
                  <Box
                    key={`${activeTab}-${section.id}`}
                    ref={(el) => { sectionRefs.current[section.id] = el; }}
                    data-section-id={section.id}
                  >
                    <CollapsibleSection
                      id={`section-${section.id}`}
                      title={section.label}
                      takeaway={section.takeaway}
                      defaultOpen={Boolean(section.defaultOpen)}
                    >
                      {section.content}
                    </CollapsibleSection>
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
                {sectionGroups.map((section, index) => (
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
                      <LazySection eager={index < 2}>{section.content}</LazySection>
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
