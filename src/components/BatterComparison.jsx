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
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import CompetitionFilter from './CompetitionFilter';
import ComparisonStrikeRateProgression from './ComparisonStrikeRateProgression';
import PhaseComparisonChart from './PhaseComparisonChart';
import ComparisonInningsScatter from './ComparisonInningsScatter';
import config from '../config';

const DEFAULT_START_DATE = "2020-01-01";
const TODAY = new Date().toISOString().split('T')[0];

const BatterComparison = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // State for handling player selection and data
  const [players, setPlayers] = useState([]);
  const [venues, setVenues] = useState(['All Venues']);
  const [selectedBatters, setSelectedBatters] = useState([]);
  const [nextBatter, setNextBatter] = useState(null);
  const [nextBatterCustomLabel, setNextBatterCustomLabel] = useState("");
  const [dateRange, setDateRange] = useState({ start: DEFAULT_START_DATE, end: TODAY });
  const [selectedVenue, setSelectedVenue] = useState("All Venues");
  
  // State for competition filters
  const [competitionFilters, setCompetitionFilters] = useState({
    leagues: [],
    international: false,
    topTeams: 10
  });
  
  // State for UI status
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [compareData, setCompareData] = useState(null);
  
  // Handler for comparing batters loaded from URL
  const handleCompareUrlBatters = async (battersToCompare) => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch data for each batter in parallel
      const promises = battersToCompare.map(async batter => {
        try {
          const params = new URLSearchParams();
          
          if (batter.dateRange.start) params.append('start_date', batter.dateRange.start);
          if (batter.dateRange.end) params.append('end_date', batter.dateRange.end);
          if (batter.venue !== "All Venues") params.append('venue', batter.venue);
          
          batter.competitionFilters.leagues.forEach(league => {
            params.append('leagues', league);
          });
          
          params.append('include_international', batter.competitionFilters.international);
          if (batter.competitionFilters.international && batter.competitionFilters.topTeams) {
            params.append('top_teams', batter.competitionFilters.topTeams);
          }
          
          // Fetch player stats
          const statsResponse = await fetch(`${config.API_URL}/player/${encodeURIComponent(batter.name)}/stats?${params}`);
          const statsData = await statsResponse.json();
          
          return {
            ...batter,
            stats: statsData,
            loading: false,
            error: null
          };
        } catch (error) {
          console.error(`Error fetching data for ${batter.name}:`, error);
          return {
            ...batter,
            stats: null,
            loading: false,
            error: `Failed to load data for ${batter.name}`
          };
        }
      });
      
      // Wait for all promises to resolve
      const results = await Promise.all(promises);
      setSelectedBatters(results);
      
      // Set the data for the comparison view
      setCompareData(results.filter(batter => batter.stats));
      
    } catch (error) {
      console.error('Error during comparison:', error);
      setError('An unexpected error occurred during comparison');
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch players and venues on component mount
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        const [playersRes, venuesRes] = await Promise.all([
          fetch(`${config.API_URL}/players`),
          fetch(`${config.API_URL}/venues`)
        ]);
        
        const playersList = await playersRes.json();
        setPlayers(playersList);
        
        const venuesList = await venuesRes.json();
        setVenues(['All Venues', ...venuesList]);
        
        // Check if there are batters and leagues in the URL to auto-load
        const searchParams = new URLSearchParams(location.search);
        const batterParam = searchParams.get('batters');
        const leaguesParam = searchParams.get('leagues');
        
        // Create competition filters with leagues from URL
        let updatedFilters = { ...competitionFilters };
        if (leaguesParam) {
          const leagues = leaguesParam.split(',');
          updatedFilters = {
            ...updatedFilters,
            leagues: leagues
          };
          setCompetitionFilters(updatedFilters);
        }
        
        if (batterParam) {
          const batterNames = batterParam.split(',');
          
          // Add each batter from the URL with the updated filters
          const urlBatters = batterNames
            .filter(name => playersList.includes(name)) // Make sure the player exists in our list
            .map(name => ({
              id: `${name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              name,
              label: name,
              dateRange: { ...dateRange },
              venue: selectedVenue,
              competitionFilters: updatedFilters, // Use the updated filters here
              stats: null,
              loading: false,
              error: null
            }));
          
          if (urlBatters.length > 0) {
            setSelectedBatters(urlBatters);
            // Auto-trigger comparison
            setTimeout(() => {
              setSelectedBatters(urlBatters.map(batter => ({ ...batter, loading: true })));
              handleCompareUrlBatters(urlBatters);
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
  }, [location.search]); // Re-run when URL changes
  
  // Handler for adding a batter to the comparison
  const handleAddBatter = () => {
    if (!nextBatter) return;
    
    // Create unique ID for this batter instance (for cases where same batter is compared across different periods)
    const batterId = `${nextBatter}-${Date.now()}`;
    
    // Create label for this batter (use custom label if provided, otherwise use player name)
    const batterLabel = nextBatterCustomLabel.trim() || nextBatter;
    
    const newBatter = {
      id: batterId,
      name: nextBatter,
      label: batterLabel,
      dateRange: { ...dateRange },
      venue: selectedVenue,
      competitionFilters: { ...competitionFilters },
      stats: null,
      loading: false,
      error: null
    };
    
    setSelectedBatters([...selectedBatters, newBatter]);
    setNextBatter(null);
    setNextBatterCustomLabel("");
  };
  
  // Handler for removing a batter from the comparison
  const handleRemoveBatter = (batterId) => {
    setSelectedBatters(selectedBatters.filter(batter => batter.id !== batterId));
  };
  
  // Handler for editing a batter's label
  const handleEditBatterLabel = (batterId, newLabel) => {
    setSelectedBatters(selectedBatters.map(batter => 
      batter.id === batterId ? { ...batter, label: newLabel } : batter
    ));
  };
  
  // Helper function to get text color based on values - using pastel colors
  const getCellColorStyle = (value, isHigherBetter, allValues) => {
    if (allValues.length <= 1) return {}; // No color for single batter
    
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const range = max - min;
    
    // Avoid division by zero
    if (range === 0) return {};
    
    // Calculate a value between 0 and 1, where 1 is the best
    let normalizedValue;
    if (isHigherBetter) {
      normalizedValue = (value - min) / range;
    } else {
      normalizedValue = (max - value) / range;
    }
    
    // Pastel color palette for better vs worse metrics
    // Best values will be pastel green, worst values will be pastel red
    if (normalizedValue >= 0.7) {
      // Good - pastel green
      return { color: '#4CAF50', fontWeight: 'bold' };
    } else if (normalizedValue >= 0.4) {
      // Average - pastel yellow/amber
      return { color: '#FFC107' };
    } else {
      // Poor - pastel red
      return { color: '#F44336', fontWeight: 'bold' };
    }
  };
  
  // Handler for fetching data for all batters
  const handleCompare = async () => {
    if (selectedBatters.length === 0) {
      setError('Please add at least one batter to compare');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Create a copy of the batters array to update with loading states
      const updatedBatters = selectedBatters.map(batter => ({ ...batter, loading: true, error: null }));
      setSelectedBatters(updatedBatters);
      
      // Fetch data for each batter in parallel
      const promises = selectedBatters.map(async batter => {
        try {
          const params = new URLSearchParams();
          
          if (batter.dateRange.start) params.append('start_date', batter.dateRange.start);
          if (batter.dateRange.end) params.append('end_date', batter.dateRange.end);
          if (batter.venue !== "All Venues") params.append('venue', batter.venue);
          
          batter.competitionFilters.leagues.forEach(league => {
            params.append('leagues', league);
          });
          
          params.append('include_international', batter.competitionFilters.international);
          if (batter.competitionFilters.international && batter.competitionFilters.topTeams) {
            params.append('top_teams', batter.competitionFilters.topTeams);
          }
          
          // Fetch player stats
          const statsResponse = await fetch(`${config.API_URL}/player/${encodeURIComponent(batter.name)}/stats?${params}`);
          const statsData = await statsResponse.json();
          
          return {
            ...batter,
            stats: statsData,
            loading: false,
            error: null
          };
        } catch (error) {
          console.error(`Error fetching data for ${batter.name}:`, error);
          return {
            ...batter,
            stats: null,
            loading: false,
            error: `Failed to load data for ${batter.name}`
          };
        }
      });
      
      // Wait for all promises to resolve
      const results = await Promise.all(promises);
      setSelectedBatters(results);
      
      // Set the data for the comparison view
      setCompareData(results.filter(batter => batter.stats));
      
    } catch (error) {
      console.error('Error during comparison:', error);
      setError('An unexpected error occurred during comparison');
    } finally {
      setLoading(false);
    }
  };
  
  // Render the comparison table when data is available
  const renderComparisonTable = () => {
    if (!compareData || compareData.length === 0) return null;
    
    return (
      <TableContainer component={Paper} sx={{ mt: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Metric</TableCell>
              {compareData.map(batter => (
                <TableCell key={batter.id} align="center">{batter.label}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell component="th" scope="row">Innings</TableCell>
              {compareData.map(batter => (
                <TableCell key={batter.id} align="center">{batter.stats.overall?.matches || 0}</TableCell>
              ))}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Runs</TableCell>
              {compareData.map(batter => (
                <TableCell key={batter.id} align="center">{batter.stats.overall?.runs || 0}</TableCell>
              ))}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Average</TableCell>
              {(() => {
                const averages = compareData.map(batter => batter.stats.overall?.average || 0);
                
                return compareData.map(batter => (
                  <TableCell 
                    key={batter.id} 
                    align="center"
                    sx={getCellColorStyle(batter.stats.overall?.average || 0, true, averages)}
                  >
                    {(batter.stats.overall?.average || 0).toFixed(2)}
                  </TableCell>
                ));
              })()}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Strike Rate</TableCell>
              {(() => {
                const strikeRates = compareData.map(batter => batter.stats.overall?.strike_rate || 0);
                
                return compareData.map(batter => (
                  <TableCell 
                    key={batter.id} 
                    align="center"
                    sx={getCellColorStyle(batter.stats.overall?.strike_rate || 0, true, strikeRates)}
                  >
                    {(batter.stats.overall?.strike_rate || 0).toFixed(2)}
                  </TableCell>
                ));
              })()}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">50s/100s</TableCell>
              {compareData.map(batter => (
                <TableCell key={batter.id} align="center">
                  {batter.stats.overall?.fifties || 0}/{batter.stats.overall?.hundreds || 0}
                </TableCell>
              ))}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Boundary %</TableCell>
              {(() => {
                const boundaryPercentages = compareData.map(batter => batter.stats.overall?.boundary_percentage || 0);
                
                return compareData.map(batter => (
                  <TableCell 
                    key={batter.id} 
                    align="center"
                    sx={getCellColorStyle(batter.stats.overall?.boundary_percentage || 0, true, boundaryPercentages)}
                  >
                    {(batter.stats.overall?.boundary_percentage || 0).toFixed(2)}%
                  </TableCell>
                ));
              })()}
            </TableRow>
            <TableRow>
              <TableCell component="th" scope="row">Dot %</TableCell>
              {(() => {
                const dotPercentages = compareData.map(batter => batter.stats.overall?.dot_percentage || 0);
                
                return compareData.map(batter => (
                  <TableCell 
                    key={batter.id} 
                    align="center"
                    sx={getCellColorStyle(batter.stats.overall?.dot_percentage || 0, false, dotPercentages)}
                  >
                    {(batter.stats.overall?.dot_percentage || 0).toFixed(2)}%
                  </TableCell>
                ));
              })()}
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    );
  };
  
  // Render the comparison charts when data is available
  const renderComparisonCharts = () => {
    if (!compareData || compareData.length === 0) return null;
    
    return (
      <Grid container spacing={3} sx={{ mt: 3 }}>
        <Grid item xs={12}>
          <ComparisonStrikeRateProgression batters={compareData} />
        </Grid>
        <Grid item xs={12}>
          <PhaseComparisonChart batters={compareData} />
        </Grid>
        <Grid item xs={12}>
          <ComparisonInningsScatter batters={compareData} />
        </Grid>
      </Grid>
    );
  };
  
  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>Batter Comparison</Typography>
        
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        
        {/* Add Batter Form */}
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Add Batter to Compare</Typography>
          
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <Autocomplete
                value={nextBatter}
                onChange={(_, newValue) => setNextBatter(newValue)}
                options={players}
                renderInput={(params) => <TextField {...params} label="Select Player" />}
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                value={nextBatterCustomLabel}
                onChange={(e) => setNextBatterCustomLabel(e.target.value)}
                label="Custom Label (Optional)"
                placeholder="e.g., Kohli 2016-2019"
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
            
            <Grid item xs={12} sm={6} md={2}>
              <Autocomplete
                value={selectedVenue}
                onChange={(_, newValue) => setSelectedVenue(newValue)}
                options={venues}
                renderInput={(params) => <TextField {...params} label="Select Venue" />}
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12}>
              <CompetitionFilter onFilterChange={setCompetitionFilters} />
            </Grid>
            
            <Grid item xs={12}>
              <Button
                variant="contained"
                color="primary"
                startIcon={<AddIcon />}
                onClick={handleAddBatter}
                disabled={!nextBatter}
              >
                Add Batter
              </Button>
            </Grid>
          </Grid>
        </Paper>
        
        {/* Selected Batters */}
        {selectedBatters.length > 0 && (
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Selected Batters ({selectedBatters.length})</Typography>
              
              <Button
                variant="contained"
                color="primary"
                startIcon={<CompareArrowsIcon />}
                onClick={handleCompare}
                disabled={loading || selectedBatters.length === 0}
              >
                Compare
              </Button>
            </Box>
            
            <Divider sx={{ mb: 2 }} />
            
            {selectedBatters.map((batter, index) => (
              <Box 
                key={batter.id} 
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
                  backgroundColor: batter.loading ? '#f5f5f5' : 'white',
                  position: 'relative'
                }}
              >
                <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography variant="body1" sx={{ fontWeight: 'bold', minWidth: 150 }}>
                    {batter.label}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                    <Tooltip title="Date Range">
                      <Typography variant="body2" sx={{ mr: 2 }}>
                        {batter.dateRange.start} to {batter.dateRange.end}
                      </Typography>
                    </Tooltip>
                    
                    {batter.venue !== "All Venues" && (
                      <Tooltip title="Venue">
                        <Typography variant="body2" sx={{ mr: 2 }}>
                          {batter.venue}
                        </Typography>
                      </Tooltip>
                    )}
                    
                    {batter.competitionFilters.leagues.length > 0 && (
                      <Tooltip title="Leagues">
                        <Typography variant="body2" sx={{ mr: 2 }}>
                          Leagues: {batter.competitionFilters.leagues.join(', ')}
                        </Typography>
                      </Tooltip>
                    )}
                    
                    {batter.competitionFilters.international && (
                      <Tooltip title="International Matches">
                        <Typography variant="body2" sx={{ mr: 2 }}>
                          International
                        </Typography>
                      </Tooltip>
                    )}
                  </Box>
                </Box>
                
                <Box>
                  {batter.loading ? (
                    <CircularProgress size={24} />
                  ) : (
                    <IconButton
                      color="error"
                      onClick={() => handleRemoveBatter(batter.id)}
                      aria-label="remove batter"
                    >
                      <DeleteIcon />
                    </IconButton>
                  )}
                </Box>
                
                {batter.error && (
                  <Alert severity="error" sx={{ width: '100%', mt: 1 }}>
                    {batter.error}
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
            
            {renderComparisonTable()}
            {renderComparisonCharts()}
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default BatterComparison;