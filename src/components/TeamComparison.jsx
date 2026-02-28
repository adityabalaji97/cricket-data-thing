import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Box, 
  Button, 
  Typography, 
  TextField, 
  CircularProgress, 
  Alert, 
  Autocomplete,
  Paper,
  Divider,
  IconButton,
  Grid,
  Card,
  CardContent,
  Tooltip,
  FormControlLabel,
  Switch
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import TeamComparisonTable from './TeamComparisonTable';
import TeamComparisonVisualization from './TeamComparisonVisualization';
import config from '../config';
import { DEFAULT_START_DATE, TODAY } from '../utils/dateDefaults';

const TeamComparison = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // State for handling team selection and data
  const [teams, setTeams] = useState([]);
  const [selectedTeams, setSelectedTeams] = useState([]);
  const [nextTeam, setNextTeam] = useState(null);
  const [nextTeamCustomLabel, setNextTeamCustomLabel] = useState("");
  const [dateRange, setDateRange] = useState({ start: DEFAULT_START_DATE, end: TODAY });
  
  // State for UI status
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [showPercentiles, setShowPercentiles] = useState(false);

  // Handler for comparing teams loaded from URL
  const handleCompareUrlTeams = async (teamsToCompare) => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch data for each team in parallel
      const promises = teamsToCompare.map(async teamEntry => {
        try {
          const params = new URLSearchParams();
          
          if (teamEntry.dateRange.start) params.append('start_date', teamEntry.dateRange.start);
          if (teamEntry.dateRange.end) params.append('end_date', teamEntry.dateRange.end);
          params.append('team_name', teamEntry.team.abbreviated_name);
          
          // Fetch all required data in parallel
          const [phaseStatsRes, bowlingPhaseStatsRes, battingOrderRes, bowlingOrderRes] = await Promise.all([
            fetch(`${config.API_URL}/teams/phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/bowling-phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/batting-order?${params}`),
            fetch(`${config.API_URL}/teams/bowling-order?${params}`)
          ]);
          
          const [phaseStats, bowlingPhaseStats, battingOrder, bowlingOrder] = await Promise.all([
            phaseStatsRes.json(),
            bowlingPhaseStatsRes.json(),
            battingOrderRes.json(),
            bowlingOrderRes.json()
          ]);
          
          return {
            ...teamEntry,
            phaseStats: phaseStats.phase_stats,
            bowlingPhaseStats: bowlingPhaseStats.bowling_phase_stats,
            battingOrder: battingOrder,
            bowlingOrder: bowlingOrder,
            loading: false,
            error: null
          };
        } catch (error) {
          console.error(`Error fetching data for ${teamEntry.team.abbreviated_name}:`, error);
          return {
            ...teamEntry,
            phaseStats: null,
            bowlingPhaseStats: null,
            battingOrder: null,
            bowlingOrder: null,
            loading: false,
            error: `Failed to load data for ${teamEntry.team.abbreviated_name}`
          };
        }
      });
      
      // Wait for all promises to resolve
      const results = await Promise.all(promises);
      setSelectedTeams(results);
      
      // Set the data for the comparison view
      setCompareData(results.filter(team => team.phaseStats || team.bowlingPhaseStats || team.battingOrder || team.bowlingOrder));
      
    } catch (error) {
      console.error('Error during comparison:', error);
      setError('An unexpected error occurred during comparison');
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch teams on component mount
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        const teamsRes = await fetch(`${config.API_URL}/teams`);
        const teamsList = await teamsRes.json();
        setTeams(teamsList);
        
        // Check if there are teams in the URL to auto-load
        const searchParams = new URLSearchParams(location.search);
        const teamParam = searchParams.get('teams');
        
        if (teamParam) {
          const teamNames = teamParam.split(',');
          
          // Add each team from the URL
          const urlTeams = teamNames
            .filter(name => teamsList.some(t => t.abbreviated_name === name || t.full_name === name))
            .map(name => {
              const team = teamsList.find(t => t.abbreviated_name === name || t.full_name === name);
              return {
                id: `${team.abbreviated_name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                team: team,
                label: `${team.abbreviated_name} ${dateRange.start}-${dateRange.end}`,
                dateRange: { ...dateRange },
                phaseStats: null,
                bowlingPhaseStats: null,
                battingOrder: null,
                bowlingOrder: null,
                loading: false,
                error: null
              };
            });
          
          if (urlTeams.length > 0) {
            setSelectedTeams(urlTeams);
            // Auto-trigger comparison
            setTimeout(() => {
              handleCompareUrlTeams(urlTeams);
            }, 500);
          }
        }
        
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setError('Failed to load initial data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchInitialData();
  }, [location.search, dateRange.start, dateRange.end]);

  // Handler for adding a team to the comparison
  const handleAddTeam = () => {
    if (!nextTeam) return;
    
    // Create unique ID for this team instance
    const teamId = `${nextTeam.abbreviated_name}-${Date.now()}`;
    
    // Create label for this team (use custom label if provided, otherwise use default format)
    const teamLabel = nextTeamCustomLabel.trim() || `${nextTeam.abbreviated_name} ${dateRange.start}-${dateRange.end}`;
    
    const newTeam = {
      id: teamId,
      team: nextTeam,
      label: teamLabel,
      dateRange: { ...dateRange },
      phaseStats: null,
      bowlingPhaseStats: null,
      battingOrder: null,
      bowlingOrder: null,
      loading: false,
      error: null
    };
    
    setSelectedTeams([...selectedTeams, newTeam]);
    setNextTeam(null);
    setNextTeamCustomLabel("");
  };
  
  // Handler for removing a team from the comparison
  const handleRemoveTeam = (teamId) => {
    setSelectedTeams(selectedTeams.filter(team => team.id !== teamId));
  };
  
  // Handler for editing a team's label
  const handleEditTeamLabel = (teamId, newLabel) => {
    setSelectedTeams(selectedTeams.map(team => 
      team.id === teamId ? { ...team, label: newLabel } : team
    ));
  };
  
  // Handler for fetching data for all teams
  const handleCompare = async () => {
    if (selectedTeams.length === 0) {
      setError('Please add at least one team to compare');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Create a copy of the teams array to update with loading states
      const updatedTeams = selectedTeams.map(team => ({ ...team, loading: true, error: null }));
      setSelectedTeams(updatedTeams);
      
      // Fetch data for each team in parallel
      const promises = selectedTeams.map(async teamEntry => {
        try {
          const params = new URLSearchParams();
          
          if (teamEntry.dateRange.start) params.append('start_date', teamEntry.dateRange.start);
          if (teamEntry.dateRange.end) params.append('end_date', teamEntry.dateRange.end);
          params.append('team_name', teamEntry.team.abbreviated_name);
          
          // Fetch all required data in parallel
          const [phaseStatsRes, bowlingPhaseStatsRes, battingOrderRes, bowlingOrderRes] = await Promise.all([
            fetch(`${config.API_URL}/teams/phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/bowling-phase-stats?${params}`),
            fetch(`${config.API_URL}/teams/batting-order?${params}`),
            fetch(`${config.API_URL}/teams/bowling-order?${params}`)
          ]);
          
          const [phaseStats, bowlingPhaseStats, battingOrder, bowlingOrder] = await Promise.all([
            phaseStatsRes.json(),
            bowlingPhaseStatsRes.json(),
            battingOrderRes.json(),
            bowlingOrderRes.json()
          ]);
          
          return {
            ...teamEntry,
            phaseStats: phaseStats.phase_stats,
            bowlingPhaseStats: bowlingPhaseStats.bowling_phase_stats,
            battingOrder: battingOrder,
            bowlingOrder: bowlingOrder,
            loading: false,
            error: null
          };
        } catch (error) {
          console.error(`Error fetching data for ${teamEntry.team.abbreviated_name}:`, error);
          return {
            ...teamEntry,
            phaseStats: null,
            bowlingPhaseStats: null,
            battingOrder: null,
            bowlingOrder: null,
            loading: false,
            error: `Failed to load data for ${teamEntry.team.abbreviated_name}`
          };
        }
      });
      
      // Wait for all promises to resolve
      const results = await Promise.all(promises);
      setSelectedTeams(results);
      
      // Set the data for the comparison view
      setCompareData(results.filter(team => team.phaseStats || team.bowlingPhaseStats || team.battingOrder || team.bowlingOrder));
      
    } catch (error) {
      console.error('Error during comparison:', error);
      setError('An unexpected error occurred during comparison');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>Team Comparison</Typography>
        
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        
        {/* Add Team Form */}
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Add Team to Compare</Typography>
          
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <Autocomplete
                value={nextTeam}
                onChange={(_, newValue) => setNextTeam(newValue)}
                options={teams}
                getOptionLabel={(option) => option?.abbreviated_name || ''}
                renderOption={(props, option) => (
                  <li {...props}>
                    <Typography>
                      {option.abbreviated_name} - {option.full_name}
                    </Typography>
                  </li>
                )}
                renderInput={(params) => <TextField {...params} label="Select Team" />}
                fullWidth
                isOptionEqualToValue={(option, value) => 
                  option?.full_name === value?.full_name
                }
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                value={nextTeamCustomLabel}
                onChange={(e) => setNextTeamCustomLabel(e.target.value)}
                label="Custom Label (Optional)"
                placeholder="e.g., KKR Gambhir Era"
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="Start Date"
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={2}>
              <TextField
                label="End Date"
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} md={2}>
              <Button
                variant="contained"
                color="primary"
                startIcon={<AddIcon />}
                onClick={handleAddTeam}
                disabled={!nextTeam || selectedTeams.length >= 10}
                fullWidth
              >
                Add Team
              </Button>
            </Grid>
          </Grid>
          
          {selectedTeams.length >= 10 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Maximum of 10 teams can be compared at once.
            </Alert>
          )}
        </Paper>
        
        {/* Selected Teams */}
        {selectedTeams.length > 0 && (
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Selected Teams ({selectedTeams.length})</Typography>
              
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={showPercentiles}
                      onChange={(e) => setShowPercentiles(e.target.checked)}
                      name="showPercentiles"
                    />
                  }
                  label="Show Percentiles"
                />
                
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<CompareArrowsIcon />}
                  onClick={handleCompare}
                  disabled={loading || selectedTeams.length === 0}
                >
                  Compare
                </Button>
              </Box>
            </Box>
            
            <Divider sx={{ mb: 2 }} />
            
            {selectedTeams.map((team, index) => (
              <Box 
                key={team.id} 
                sx={{ 
                  p: 2, 
                  mb: 1,
                  border: '1px solid #eee',
                  borderRadius: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 1,
                  backgroundColor: team.loading ? '#f5f5f5' : 'white',
                  position: 'relative'
                }}
              >
                <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography variant="body1" sx={{ fontWeight: 'bold', minWidth: 150 }}>
                    {team.label}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                    <Tooltip title="Date Range">
                      <Typography variant="body2" sx={{ mr: 2 }}>
                        {team.dateRange.start} to {team.dateRange.end}
                      </Typography>
                    </Tooltip>
                    
                    <Tooltip title="Team">
                      <Typography variant="body2" sx={{ mr: 2 }}>
                        {team.team.full_name}
                      </Typography>
                    </Tooltip>
                  </Box>
                </Box>
                
                <Box>
                  {team.loading ? (
                    <CircularProgress size={24} />
                  ) : (
                    <IconButton
                      color="error"
                      onClick={() => handleRemoveTeam(team.id)}
                      aria-label="remove team"
                    >
                      <DeleteIcon />
                    </IconButton>
                  )}
                </Box>
                
                {team.error && (
                  <Alert severity="error" sx={{ width: '100%', mt: 1 }}>
                    {team.error}
                  </Alert>
                )}
              </Box>
            ))}
          </Paper>
        )}
        
        {/* Loading indicator */}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        )}
        
        {/* Results */}
        {compareData && compareData.length > 0 && !loading && (
          <Box>
            <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>Comparison Results</Typography>
            
            <TeamComparisonTable 
              teams={compareData} 
              showPercentiles={showPercentiles}
            />
            
            <TeamComparisonVisualization 
              teams={compareData}
              showPercentiles={showPercentiles}
            />
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default TeamComparison;
