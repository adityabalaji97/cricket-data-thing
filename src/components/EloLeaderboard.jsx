import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  TextField
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import TrophyIcon from '@mui/icons-material/EmojiEvents';
import { Link } from 'react-router-dom';
import config from '../config';
import { getTeamColor as getTeamColorFromUtils } from '../utils/teamColors';

const EloLeaderboard = () => {
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('international');
  const [showInfoDialog, setShowInfoDialog] = useState(false);
  const [leagues, setLeagues] = useState([]);
  const [startDate, setStartDate] = useState(''); // empty string = all time
  const [endDate, setEndDate] = useState(''); // empty string = all time

  // Use shared team colors utility
  const getTeamColor = (teamName) => {
    return getTeamColorFromUtils(teamName) || '#666666';
  };

  // Fetch available leagues on component mount
  useEffect(() => {
    const fetchLeagues = async () => {
      try {
        const response = await fetch(`${config.API_URL}/competitions`);
        const data = await response.json();
        setLeagues(data.leagues || []);
      } catch (error) {
        console.error('Error fetching leagues:', error);
      }
    };
    fetchLeagues();
  }, []);

  // Fetch ELO rankings based on selected filter and date range
  useEffect(() => {
    const fetchRankings = async () => {
      setLoading(true);
      setError(null);
      
      try {
        let url = `${config.API_URL}/teams/elo-rankings`;
        const params = new URLSearchParams();
        
        if (selectedFilter === 'international') {
          params.append('include_international', 'true');
          params.append('top_teams', '15'); // Top 15 international teams
        } else {
          // It's a specific league
          params.append('league', selectedFilter);
          params.append('include_international', 'false');
        }
        
        // Add date filters if they are set
        if (startDate) {
          params.append('start_date', startDate);
        }
        if (endDate) {
          params.append('end_date', endDate);
        }
        
        const response = await fetch(`${url}?${params}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setRankings(data.rankings || []);
      } catch (error) {
        console.error('Error fetching ELO rankings:', error);
        setError('Failed to load ELO rankings');
      } finally {
        setLoading(false);
      }
    };

    fetchRankings();
  }, [selectedFilter, startDate, endDate]);

  const handleFilterChange = (event) => {
    setSelectedFilter(event.target.value);
  };

  const handleStartDateChange = (event) => {
    setStartDate(event.target.value);
  };

  const handleEndDateChange = (event) => {
    setEndDate(event.target.value);
  };

  const handleClearDates = () => {
    setStartDate('');
    setEndDate('');
  };

  const getRankColor = (rank) => {
    if (rank === 1) return '#FFD700'; // Gold
    if (rank === 2) return '#C0C0C0'; // Silver
    if (rank === 3) return '#CD7F32'; // Bronze
    return '#666666'; // Default
  };

  const EloInfoDialog = () => (
    <Dialog 
      open={showInfoDialog} 
      onClose={() => setShowInfoDialog(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <InfoIcon color="primary" />
          ELO Rating System
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="h6" gutterBottom>
          What is ELO?
        </Typography>
        <Typography paragraph>
          ELO is a rating system originally developed for chess that calculates the relative skill levels 
          of players or teams. In cricket, we use it to rank teams based on their match results.
        </Typography>

        <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
          How Our ELO System Works
        </Typography>
        
        <Typography variant="subtitle2" gutterBottom>
          Starting Ratings:
        </Typography>
        <Box component="ul" sx={{ pl: 2, mb: 2 }}>
          <li>Top 10 International Teams: 1500 ELO</li>
          <li>Teams 11-20: 1400 ELO</li>
          <li>Other International Teams: 1300 ELO</li>
          <li>League Teams: 1500 ELO</li>
        </Box>

        <Typography variant="subtitle2" gutterBottom>
          Rating Changes:
        </Typography>
        <Box component="ul" sx={{ pl: 2, mb: 2 }}>
          <li>Teams gain/lose ELO points based on match results</li>
          <li>Beating a higher-rated team gives more points</li>
          <li>Losing to a lower-rated team costs more points</li>
          <li>K-Factor: 32 (determines the magnitude of rating changes)</li>
        </Box>

        <Typography variant="subtitle2" gutterBottom>
          Key Features:
        </Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <li>Chronological processing maintains proper order</li>
          <li>Separate ratings for international and league teams</li>
          <li>Real-time updates with each match result</li>
          <li>Historical tracking for trend analysis</li>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowInfoDialog(false)} variant="contained">
          Got it
        </Button>
      </DialogActions>
    </Dialog>
  );

  return (
    <Card sx={{ mt: 4, maxHeight: '700px', overflow: 'hidden' }}>
      <CardContent>
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-start', 
          mb: 3 
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrophyIcon color="primary" />
            <Typography variant="h5" component="h2">
              ELO Team Rankings
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tooltip title="Learn about our ELO rating system">
              <IconButton 
                onClick={() => setShowInfoDialog(true)}
                size="small"
                color="primary"
              >
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Filters Section */}
        <Box sx={{ 
          display: 'flex', 
          flexDirection: { xs: 'column', md: 'row' },
          gap: 2, 
          mb: 3,
          alignItems: { xs: 'stretch', md: 'flex-end' }
        }}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Competition</InputLabel>
            <Select
              value={selectedFilter}
              onChange={handleFilterChange}
              label="Competition"
            >
              <MenuItem value="international">International Teams</MenuItem>
              <Divider />
              {leagues.map((league) => (
                <MenuItem key={league.value} value={league.value}>
                  {league.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <TextField
            label="Start Date"
            type="date"
            value={startDate}
            onChange={handleStartDateChange}
            InputLabelProps={{ shrink: true }}
            size="small"
            sx={{ minWidth: 140 }}
          />
          
          <TextField
            label="End Date"
            type="date"
            value={endDate}
            onChange={handleEndDateChange}
            InputLabelProps={{ shrink: true }}
            size="small"
            sx={{ minWidth: 140 }}
          />
          
          {(startDate || endDate) && (
            <Button 
              variant="outlined" 
              size="small" 
              onClick={handleClearDates}
              sx={{ whiteSpace: 'nowrap' }}
            >
              Clear Dates
            </Button>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ maxHeight: '400px', overflowY: 'auto' }}>
            <List dense>
              {rankings.slice(0, 10).map((team, index) => (
                <ListItem 
                  key={team.team_name}
                  component={Link}
                  to={`/team?team=${encodeURIComponent(team.team_abbreviation)}&autoload=true`}
                  sx={{
                    textDecoration: 'none',
                    color: 'inherit',
                    borderRadius: 1,
                    mb: 0.5,
                    '&:hover': {
                      backgroundColor: 'action.hover',
                      transform: 'translateX(4px)',
                      transition: 'all 0.2s ease-in-out'
                    },
                    transition: 'all 0.2s ease-in-out'
                  }}
                >
                  <Box sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 2, 
                    width: '100%' 
                  }}>
                    {/* Rank Badge */}
                    <Box sx={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      backgroundColor: getTeamColor(team.team_abbreviation),
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 'bold',
                      fontSize: '0.875rem',
                      flexShrink: 0,
                      border: team.rank <= 3 ? '2px solid' : 'none',
                      borderColor: team.rank === 1 ? '#FFD700' : 
                                   team.rank === 2 ? '#C0C0C0' : 
                                   team.rank === 3 ? '#CD7F32' : 'transparent',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                    }}>
                      {team.rank}
                    </Box>

                    {/* Team Info */}
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1" fontWeight="medium">
                            {team.team_abbreviation}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {team.team_name}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                          <Chip 
                            label={`${team.wins}W-${team.losses}L`}
                            size="small" 
                            variant="outlined"
                            sx={{ fontSize: '0.75rem' }}
                          />
                          <Chip 
                            label={`${team.win_percentage}%`}
                            size="small" 
                            variant="outlined"
                            color={team.win_percentage >= 60 ? 'success' : 
                                   team.win_percentage >= 40 ? 'warning' : 'error'}
                            sx={{ fontSize: '0.75rem' }}
                          />
                        </Box>
                      }
                    />

                    {/* ELO Rating */}
                    <Box sx={{ textAlign: 'right', flexShrink: 0 }}>
                      <Typography variant="h6" fontWeight="bold" color="primary">
                        {team.current_elo}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ELO Rating
                      </Typography>
                    </Box>
                  </Box>
                </ListItem>
              ))}
            </List>

            {rankings.length === 0 && !loading && (
              <Typography 
                variant="body1" 
                color="text.secondary" 
                align="center" 
                sx={{ py: 4 }}
              >
                No teams found for the selected competition.
              </Typography>
            )}

            {rankings.length > 10 && (
              <Box sx={{ textAlign: 'center', pt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Showing top 10 teams. Click on any team to view their profile.
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </CardContent>
      
      <EloInfoDialog />
    </Card>
  );
};

export default EloLeaderboard;