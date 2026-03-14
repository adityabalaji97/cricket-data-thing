import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  FormControlLabel,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

import CustomPlayerSelector from './CustomPlayerSelector';
import EloStatsCard from './EloStatsCard';
import TeamBattingOrderCard from './TeamBattingOrderCard';
import TeamBowlingOrderCard from './TeamBowlingOrderCard';
import TeamBowlingPhasePerformanceRadar from './TeamBowlingPhasePerformanceRadar';
import TeamChampionshipSection from './TeamChampionshipSection';
import TeamH2HSection from './TeamH2HSection';
import TeamPhasePerformanceRadar from './TeamPhasePerformanceRadar';
import TeamSquadSection from './TeamSquadSection';
import TeamStatsCards from './TeamStatsCards';
import VenueNotesCardShell from './VenueNotesCardShell';
import VenueNotesDesktopNav from './VenueNotesDesktopNav';
import VenueSectionTabs from './VenueSectionTabs';
import RecentFormStrip from './playerProfile/RecentFormStrip';
import config from '../config';
import { DEFAULT_START_DATE, TODAY } from '../utils/dateDefaults';

const OVERVIEW_SECTION_ID = 'overview';

const parseRunsFromScore = (scoreText) => {
  if (!scoreText) {
    return 0;
  }
  const [runsPart] = String(scoreText).split('/');
  const parsed = Number.parseInt(runsPart, 10);
  return Number.isFinite(parsed) ? parsed : 0;
};

const TeamProfile = ({ isMobile }) => {
  const navigate = useNavigate();

  const [isCustomMode, setIsCustomMode] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teams, setTeams] = useState([]);
  const [customPlayers, setCustomPlayers] = useState([]);

  const [dateRange, setDateRange] = useState({ start: DEFAULT_START_DATE, end: TODAY });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [teamData, setTeamData] = useState(null);
  const [phaseStats, setPhaseStats] = useState(null);
  const [bowlingPhaseStats, setBowlingPhaseStats] = useState(null);
  const [eloStats, setEloStats] = useState(null);
  const [battingOrderData, setBattingOrderData] = useState(null);
  const [bowlingOrderData, setBowlingOrderData] = useState(null);
  const [rosterData, setRosterData] = useState(null);
  const [h2hSummaryData, setH2HSummaryData] = useState(null);
  const [championshipData, setChampionshipData] = useState(null);

  const [shouldFetch, setShouldFetch] = useState(false);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);

  const [activeSectionId, setActiveSectionId] = useState(OVERVIEW_SECTION_ID);
  const sectionRefs = useRef({});

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const teamsRes = await fetch(`${config.API_URL}/teams`);
        const teamsList = await teamsRes.json();
        setTeams(teamsList);

        const searchParams = new URLSearchParams(window.location.search);
        const teamNameFromURL = searchParams.get('team');
        const autoload = searchParams.get('autoload') === 'true';
        const startDateFromURL = searchParams.get('start_date');
        const endDateFromURL = searchParams.get('end_date');

        if (startDateFromURL || endDateFromURL) {
          setDateRange({
            start: startDateFromURL || DEFAULT_START_DATE,
            end: endDateFromURL || TODAY,
          });
        }

        if (teamNameFromURL) {
          const team = teamsList.find(
            (candidate) =>
              candidate.full_name === teamNameFromURL || candidate.abbreviated_name === teamNameFromURL,
          );
          if (team) {
            setSelectedTeam(team);
            if (autoload) {
              setTimeout(() => setShouldFetch(true), 500);
            }
          }
        }

        setInitialLoadComplete(true);
      } catch (fetchError) {
        console.error('Error fetching initial data:', fetchError);
        setError('Failed to load initial data');
        setInitialLoadComplete(true);
      }
    };

    fetchInitialData();
  }, []);

  useEffect(() => {
    if (!initialLoadComplete) {
      return;
    }

    const searchParams = new URLSearchParams();
    if (!isCustomMode && selectedTeam) {
      searchParams.set('team', selectedTeam.abbreviated_name);
    }
    if (dateRange.start !== DEFAULT_START_DATE) {
      searchParams.set('start_date', dateRange.start);
    }
    if (dateRange.end !== TODAY) {
      searchParams.set('end_date', dateRange.end);
    }
    if (teamData || (isCustomMode && (phaseStats || bowlingPhaseStats || battingOrderData || bowlingOrderData))) {
      searchParams.set('autoload', 'true');
    }

    const newUrl = searchParams.toString() ? `?${searchParams.toString()}` : '';
    navigate(newUrl, { replace: true });
  }, [
    selectedTeam,
    dateRange,
    teamData,
    phaseStats,
    bowlingPhaseStats,
    battingOrderData,
    bowlingOrderData,
    initialLoadComplete,
    navigate,
    isCustomMode,
  ]);

  const resetFetchedData = useCallback(() => {
    setTeamData(null);
    setPhaseStats(null);
    setBowlingPhaseStats(null);
    setEloStats(null);
    setBattingOrderData(null);
    setBowlingOrderData(null);
    setRosterData(null);
    setH2HSummaryData(null);
    setChampionshipData(null);
  }, []);

  const handleFetch = () => {
    if (isCustomMode && customPlayers.length === 0) {
      setError('Please select at least one player');
      return;
    }
    if (!isCustomMode && !selectedTeam) {
      setError('Please select a team');
      return;
    }
    setShouldFetch(true);
  };

  const handleModeToggle = (event) => {
    setIsCustomMode(event.target.checked);
    setError(null);
    resetFetchedData();
    setShouldFetch(false);
    setActiveSectionId(OVERVIEW_SECTION_ID);
  };

  useEffect(() => {
    const fetchData = async () => {
      if (!shouldFetch) {
        return;
      }

      if (isCustomMode && customPlayers.length === 0) {
        setError('Please select at least one player');
        return;
      }
      if (!isCustomMode && !selectedTeam) {
        setError('Please select a team');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (dateRange.start) {
          params.append('start_date', dateRange.start);
        }
        if (dateRange.end) {
          params.append('end_date', dateRange.end);
        }

        if (isCustomMode) {
          customPlayers.forEach((player) => params.append('players', player));

          const requests = await Promise.all([
            fetch(`${config.API_URL}/teams/phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/bowling-phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/batting-order?${params}`),
            fetch(`${config.API_URL}/teams/bowling-order?${params}`),
          ]);

          if (requests.some((response) => !response.ok)) {
            const statuses = requests.map((response) => response.status).join(', ');
            throw new Error(`Failed custom-mode requests: ${statuses}`);
          }

          const [phaseStatsPayload, bowlingPhasePayload, battingOrderPayload, bowlingOrderPayload] = await Promise.all(
            requests.map((response) => response.json()),
          );

          setPhaseStats(phaseStatsPayload.phase_stats);
          setBowlingPhaseStats(bowlingPhasePayload.bowling_phase_stats);
          setBattingOrderData(battingOrderPayload);
          setBowlingOrderData(bowlingOrderPayload);

          setTeamData(null);
          setEloStats(null);
          setRosterData(null);
          setH2HSummaryData(null);
          setChampionshipData(null);
        } else {
          params.append('team_name', selectedTeam.abbreviated_name);
          const teamKey = encodeURIComponent(selectedTeam.abbreviated_name);

          const primaryResponses = await Promise.all([
            fetch(`${config.API_URL}/teams/${teamKey}/matches?${params}&include_elo=true`),
            fetch(`${config.API_URL}/teams/phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/bowling-phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/${teamKey}/elo-stats?${params}`),
            fetch(`${config.API_URL}/teams/batting-order?${params}`),
            fetch(`${config.API_URL}/teams/bowling-order?${params}`),
          ]);

          if (primaryResponses.some((response) => !response.ok)) {
            const statuses = primaryResponses.map((response) => response.status).join(', ');
            throw new Error(`Failed team-mode requests: ${statuses}`);
          }

          const [
            matchesPayload,
            phaseStatsPayload,
            bowlingPhasePayload,
            eloPayload,
            battingOrderPayload,
            bowlingOrderPayload,
          ] = await Promise.all(primaryResponses.map((response) => response.json()));

          const [rosterPayload, h2hPayload, championshipPayload] = await Promise.all([
            fetch(`${config.API_URL}/teams/${teamKey}/roster`)
              .then(async (response) => (response.ok ? response.json() : null))
              .catch(() => null),
            fetch(`${config.API_URL}/teams/${teamKey}/h2h-summary`)
              .then(async (response) => (response.ok ? response.json() : null))
              .catch(() => null),
            fetch(`${config.API_URL}/teams/${teamKey}/championship-score`)
              .then(async (response) => (response.ok ? response.json() : null))
              .catch(() => null),
          ]);

          setTeamData(matchesPayload);
          setPhaseStats(phaseStatsPayload.phase_stats);
          setBowlingPhaseStats(bowlingPhasePayload.bowling_phase_stats);
          setEloStats(eloPayload);
          setBattingOrderData(battingOrderPayload);
          setBowlingOrderData(bowlingOrderPayload);
          setRosterData(rosterPayload);
          setH2HSummaryData(h2hPayload);
          setChampionshipData(championshipPayload);
        }
      } catch (fetchError) {
        console.error('Error loading team profile data:', fetchError);
        setError('Failed to load data');
      } finally {
        setLoading(false);
        setShouldFetch(false);
      }
    };

    fetchData();
  }, [shouldFetch, selectedTeam, dateRange, isCustomMode, customPlayers]);

  useEffect(() => {
    setActiveSectionId(OVERVIEW_SECTION_ID);
  }, [selectedTeam?.abbreviated_name, isCustomMode]);

  const calculateMetrics = useCallback(
    (matches) => {
      if (!matches || matches.length === 0) {
        return {
          totalMatches: 0,
          wins: 0,
          losses: 0,
          noResults: 0,
          winLossRatio: '0:0',
          wonBattingFirst: 0,
          wonFieldingFirst: 0,
          battedFirstMatches: 0,
          fieldedFirstMatches: 0,
          tossWins: 0,
          tossBatFirst: 0,
          tossBowlFirst: 0,
        };
      }

      const wins = matches.filter((match) => match.result === 'W').length;
      const losses = matches.filter((match) => match.result === 'L').length;
      const noResults = matches.filter((match) => match.result === 'NR').length;
      const wonBattingFirst = matches.filter((match) => match.result === 'W' && match.batted_first).length;
      const wonFieldingFirst = matches.filter((match) => match.result === 'W' && !match.batted_first).length;
      const battedFirstMatches = matches.filter((match) => match.batted_first).length;
      const fieldedFirstMatches = matches.filter((match) => !match.batted_first).length;

      const tossWins = matches.filter(
        (match) => match.toss_winner === selectedTeam?.abbreviated_name || match.toss_winner === selectedTeam?.full_name,
      ).length;
      const tossBatFirst = matches.filter(
        (match) =>
          (match.toss_winner === selectedTeam?.abbreviated_name || match.toss_winner === selectedTeam?.full_name) &&
          match.toss_decision === 'bat',
      ).length;
      const tossBowlFirst = matches.filter(
        (match) =>
          (match.toss_winner === selectedTeam?.abbreviated_name || match.toss_winner === selectedTeam?.full_name) &&
          match.toss_decision === 'field',
      ).length;

      return {
        totalMatches: matches.length,
        wins,
        losses,
        noResults,
        winLossRatio: `${wins}:${losses}`,
        wonBattingFirst,
        wonFieldingFirst,
        battedFirstMatches,
        fieldedFirstMatches,
        tossWins,
        tossBatFirst,
        tossBowlFirst,
      };
    },
    [selectedTeam],
  );

  const metrics = teamData ? calculateMetrics(teamData.matches) : null;
  const displayName = isCustomMode
    ? `Custom Players (${customPlayers.length})`
    : selectedTeam
      ? `${selectedTeam.full_name} (${selectedTeam.abbreviated_name})`
      : '';

  const recentFormInnings = useMemo(() => {
    const matches = teamData?.matches || [];
    return matches.slice(0, 5).map((match) => ({
      runs: parseRunsFromScore(match.team_score),
      opponent: match.opponent || '?',
    }));
  }, [teamData]);

  const sectionGroups = useMemo(() => {
    if (isCustomMode || !selectedTeam) {
      return [];
    }

    return [
      {
        id: 'overview',
        label: 'Overview',
        content: (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {teamData && metrics ? (
              <TeamStatsCards metrics={metrics} teamName={displayName} dateRange={dateRange} />
            ) : (
              <Alert severity="info">No recent match summary available for this date range.</Alert>
            )}
            <EloStatsCard eloStats={eloStats} teamName={displayName} dateRange={dateRange} />
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Recent Form
                </Typography>
                {recentFormInnings.length ? (
                  <RecentFormStrip innings={recentFormInnings} mode="batting" isMobile={isMobile} />
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    No matches available to compute recent form.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Box>
        ),
      },
      {
        id: 'squad',
        label: 'Squad',
        content: <TeamSquadSection rosterData={rosterData} />,
      },
      {
        id: 'phases',
        label: 'Phases',
        content: (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {phaseStats ? (
              <TeamPhasePerformanceRadar phaseStats={phaseStats} teamName={selectedTeam.abbreviated_name} />
            ) : (
              <Alert severity="info">Batting phase stats are unavailable.</Alert>
            )}
            {bowlingPhaseStats ? (
              <TeamBowlingPhasePerformanceRadar
                bowlingPhaseStats={bowlingPhaseStats}
                teamName={selectedTeam.abbreviated_name}
              />
            ) : (
              <Alert severity="info">Bowling phase stats are unavailable.</Alert>
            )}
          </Box>
        ),
      },
      {
        id: 'batting',
        label: 'Batting',
        content: battingOrderData ? (
          <TeamBattingOrderCard battingOrderData={battingOrderData} teamName={selectedTeam.abbreviated_name} />
        ) : (
          <Alert severity="info">Batting order data is unavailable.</Alert>
        ),
      },
      {
        id: 'bowling',
        label: 'Bowling',
        content: bowlingOrderData ? (
          <TeamBowlingOrderCard bowlingOrderData={bowlingOrderData} teamName={selectedTeam.abbreviated_name} />
        ) : (
          <Alert severity="info">Bowling order data is unavailable.</Alert>
        ),
      },
      {
        id: 'h2h',
        label: 'Head-to-Head',
        content: <TeamH2HSection h2hData={h2hSummaryData} />,
      },
      {
        id: 'prediction',
        label: 'Title Odds',
        content: <TeamChampionshipSection championshipData={championshipData} teamLabel={selectedTeam.abbreviated_name} />,
      },
    ];
  }, [
    isCustomMode,
    selectedTeam,
    teamData,
    metrics,
    displayName,
    dateRange,
    eloStats,
    recentFormInnings,
    isMobile,
    rosterData,
    phaseStats,
    bowlingPhaseStats,
    battingOrderData,
    bowlingOrderData,
    h2hSummaryData,
    championshipData,
  ]);

  const handleSectionSelect = useCallback((sectionId) => {
    setActiveSectionId(sectionId);
    const sectionElement = sectionRefs.current[sectionId];
    if (sectionElement) {
      sectionElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  useEffect(() => {
    if (!sectionGroups.length || isCustomMode) {
      return undefined;
    }

    const visibleSections = new Map();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const sectionId = entry.target.dataset.sectionId;
          if (!sectionId) {
            return;
          }
          if (entry.isIntersecting) {
            visibleSections.set(sectionId, entry.intersectionRatio);
          } else {
            visibleSections.delete(sectionId);
          }
        });

        const nextActive = [...visibleSections.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
        if (nextActive) {
          setActiveSectionId(nextActive);
        }
      },
      {
        rootMargin: '-15% 0px -60% 0px',
        threshold: [0.1, 0.35, 0.6],
      },
    );

    sectionGroups.forEach((section) => {
      const element = sectionRefs.current[section.id];
      if (element) {
        observer.observe(element);
      }
    });

    return () => observer.disconnect();
  }, [sectionGroups, isCustomMode]);

  const hasCustomResults = Boolean(isCustomMode && (phaseStats || bowlingPhaseStats || battingOrderData || bowlingOrderData));
  const hasTeamResults = Boolean(!isCustomMode && (teamData || rosterData || h2hSummaryData || championshipData));

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>
          Team Profile
        </Typography>

        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

        <Box sx={{ mb: 3 }}>
          <FormControlLabel
            control={<Switch checked={isCustomMode} onChange={handleModeToggle} name="customMode" />}
            label="Custom Player Analysis"
          />
        </Box>

        {!isCustomMode ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: { xs: 'column', md: 'row' },
              gap: 2,
              mb: 4,
              alignItems: { xs: 'stretch', md: 'flex-end' },
            }}
          >
            <Autocomplete
              value={selectedTeam}
              onChange={(_, nextTeam) => setSelectedTeam(nextTeam)}
              options={teams}
              sx={{ width: { xs: '100%', md: 300 } }}
              getOptionLabel={(option) => option?.abbreviated_name || ''}
              renderOption={(props, option) => (
                <li {...props}>
                  <Typography>
                    {option.abbreviated_name} - {option.full_name}
                  </Typography>
                </li>
              )}
              renderInput={(params) => <TextField {...params} label="Select Team" variant="outlined" required />}
              isOptionEqualToValue={(option, value) => option?.full_name === value?.full_name}
            />

            <TextField
              label="Start Date"
              type="date"
              value={dateRange.start}
              onChange={(event) => setDateRange((prev) => ({ ...prev, start: event.target.value }))}
              InputLabelProps={{ shrink: true }}
              sx={{ width: { xs: '100%', md: 'auto' } }}
            />

            <TextField
              label="End Date"
              type="date"
              value={dateRange.end}
              onChange={(event) => setDateRange((prev) => ({ ...prev, end: event.target.value }))}
              InputLabelProps={{ shrink: true }}
              inputProps={{ max: TODAY }}
              sx={{ width: { xs: '100%', md: 'auto' } }}
            />

            <Button
              variant="contained"
              onClick={handleFetch}
              disabled={!selectedTeam || loading}
              id="go-button"
              sx={{
                height: '56px',
                width: { xs: '100%', md: 'auto' },
                minWidth: '80px',
              }}
            >
              GO
            </Button>
          </Box>
        ) : (
          <Box>
            <Box
              sx={{
                display: 'flex',
                flexDirection: { xs: 'column', md: 'row' },
                gap: 2,
                mb: 2,
                alignItems: { xs: 'stretch', md: 'flex-end' },
              }}
            >
              <TextField
                label="Start Date"
                type="date"
                value={dateRange.start}
                onChange={(event) => setDateRange((prev) => ({ ...prev, start: event.target.value }))}
                InputLabelProps={{ shrink: true }}
                sx={{ width: { xs: '100%', md: 'auto' } }}
              />

              <TextField
                label="End Date"
                type="date"
                value={dateRange.end}
                onChange={(event) => setDateRange((prev) => ({ ...prev, end: event.target.value }))}
                InputLabelProps={{ shrink: true }}
                inputProps={{ max: TODAY }}
                sx={{ width: { xs: '100%', md: 'auto' } }}
              />

              <Button
                variant="contained"
                onClick={handleFetch}
                disabled={customPlayers.length === 0 || loading}
                id="go-button"
                sx={{
                  height: '56px',
                  width: { xs: '100%', md: 'auto' },
                  minWidth: '80px',
                }}
              >
                GO
              </Button>
            </Box>

            <CustomPlayerSelector
              selectedPlayers={customPlayers}
              onPlayersChange={setCustomPlayers}
              label="Select Players for Analysis"
            />
          </Box>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : null}

        {hasCustomResults ? (
          <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
            {phaseStats ? (
              <TeamPhasePerformanceRadar phaseStats={phaseStats} teamName="Custom Players" />
            ) : (
              <Alert severity="info">Batting phase stats are unavailable.</Alert>
            )}
            {bowlingPhaseStats ? (
              <TeamBowlingPhasePerformanceRadar bowlingPhaseStats={bowlingPhaseStats} teamName="Custom Players" />
            ) : (
              <Alert severity="info">Bowling phase stats are unavailable.</Alert>
            )}
            {battingOrderData ? (
              <TeamBattingOrderCard battingOrderData={battingOrderData} teamName="Custom Players" />
            ) : (
              <Alert severity="info">Batting order data is unavailable.</Alert>
            )}
            {bowlingOrderData ? (
              <TeamBowlingOrderCard bowlingOrderData={bowlingOrderData} teamName="Custom Players" />
            ) : (
              <Alert severity="info">Bowling order data is unavailable.</Alert>
            )}
          </Box>
        ) : null}

        {hasTeamResults && sectionGroups.length ? (
          <Box sx={{ mt: 4 }}>
            {isMobile ? (
              <>
                <VenueSectionTabs
                  sections={sectionGroups.map((section) => ({ id: section.id, label: section.label }))}
                  activeSectionId={activeSectionId}
                  onSectionSelect={handleSectionSelect}
                />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, px: 1, pb: 2 }}>
                  {sectionGroups.map((section) => (
                    <Box
                      key={section.id}
                      ref={(element) => {
                        sectionRefs.current[section.id] = element;
                      }}
                      data-section-id={section.id}
                      sx={{ scrollMarginTop: '56px' }}
                    >
                      <VenueNotesCardShell
                        groupLabel="Team Profile"
                        cardLabel={section.label}
                        metaText={selectedTeam?.abbreviated_name}
                        isMobile
                        fitContent
                      >
                        <Box sx={{ p: 1.5 }}>{section.content}</Box>
                      </VenueNotesCardShell>
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
                  sections={sectionGroups.map((section) => ({ id: section.id, label: section.label }))}
                  activeSectionId={activeSectionId}
                  onSectionSelect={handleSectionSelect}
                />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {sectionGroups.map((section) => (
                    <Box
                      key={section.id}
                      ref={(element) => {
                        sectionRefs.current[section.id] = element;
                      }}
                      data-section-id={section.id}
                      sx={{ scrollMarginTop: '88px' }}
                    >
                      <VenueNotesCardShell
                        groupLabel="Team Profile"
                        cardLabel={section.label}
                        metaText={selectedTeam?.abbreviated_name}
                      >
                        {section.content}
                      </VenueNotesCardShell>
                    </Box>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        ) : null}
      </Box>
    </Container>
  );
};

export default TeamProfile;
