import React, { useState, useEffect } from 'react';
import { Container, Box, Button, Typography, TextField, CircularProgress, Alert, Autocomplete } from '@mui/material';
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

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [playersRes, venuesRes] = await Promise.all([
          fetch(`${config.API_URL}/players`),
          fetch(`${config.API_URL}/venues`)
        ]);
        setPlayers(await playersRes.json());
        setVenues(['All Venues', ...await venuesRes.json()]);
      } catch (error) {
        setError('Failed to load initial data');
      }
    };
    fetchInitialData();
  }, []);

  const handleFetch = () => {
    if (!selectedPlayer) return;
    setShouldFetch(true);
  };

  useEffect(() => {
    // Inside fetchPlayerStats function in useEffect
    const fetchPlayerStats = async () => {
        if (!shouldFetch || !selectedPlayer) return;
        
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
        } catch (error) {
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
            >
              Go
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