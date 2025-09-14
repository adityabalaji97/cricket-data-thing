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
  Divider
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import TrophyIcon from '@mui/icons-material/EmojiEvents';
import { Link } from 'react-router-dom';
import config from '../config';

const EloLeaderboard = () => {
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('international');
  const [showInfoDialog, setShowInfoDialog] = useState(false);
  const [leagues, setLeagues] = useState([]);

  // Team-specific colors based on your color scheme
  const getTeamColor = (teamName) => {
    // Handle both full names and abbreviations
    const teamColors = {
      // IPL Teams
      'Chennai Super Kings': '#eff542',
      'CSK': '#eff542',
      'Royal Challengers Bangalore': '#f54242',
      'Royal Challengers Bengaluru': '#f54242',
      'RCB': '#f54242',
      'Mumbai Indians': '#42a7f5',
      'MI': '#42a7f5',
      'Rajasthan Royals': '#FF2AA8',
      'Rising Pune Supergiants': '#FF2AA8',
      'Rising Pune Supergiant': '#FF2AA8',
      'RR': '#FF2AA8',
      'RPSG': '#FF2AA8',
      'Kolkata Knight Riders': '#610048',
      'KKR': '#610048',
      'Kings XI Punjab': '#FF004D',
      'Punjab Kings': '#FF004D',
      'PBKS': '#FF004D',
      'Sunrisers Hyderabad': '#FF7C01',
      'SRH': '#FF7C01',
      'Lucknow Super Giants': '#00BBB3',
      'Pune Warriors': '#00BBB3',
      'LSG': '#00BBB3',
      'Delhi Capitals': '#004BC5',
      'Delhi Daredevils': '#004BC5',
      'DC': '#004BC5',
      'Deccan Chargers': '#04378C',
      'DCh': '#04378C',
      'Gujarat Lions': '#FF5814',
      'GL': '#FF5814',
      'Gujarat Titans': '#01295B',
      'GT': '#01295B',
      'Kochi Tuskers Kerala': '#008080',
      'KTK': '#008080',
      
      // International Teams
      'Australia': '#eff542',
      'AUS': '#eff542',
      'England': '#f54242',
      'ENG': '#f54242',
      'India': '#42a7f5',
      'IND': '#42a7f5',
      'South Africa': '#1cba2e',
      'SA': '#1cba2e',
      'Pakistan': '#02450a',
      'PAK': '#02450a',
      'West Indies': '#450202',
      'WI': '#450202',
      'New Zealand': '#050505',
      'NZ': '#050505',
      'Bangladesh': '#022b07',
      'BAN': '#022b07',
      'Afghanistan': '#058bf2',
      'AFG': '#058bf2',
      'Sri Lanka': '#031459',
      'SL': '#031459',
      'Ireland': '#90EE90',
      'IRE': '#90EE90',
      'Netherlands': '#FF7C01',
      'NED': '#FF7C01',
      'Zimbabwe': '#FF7C01',
      'ZIM': '#FF7C01',
      'Scotland': '#4169E1',
      'SCO': '#4169E1',
      'Nepal': '#DC143C',
      'NEP': '#DC143C',
      'USA': '#B22222',
      'Oman': '#8B0000',
      'OMA': '#8B0000',
      'UAE': '#2F4F4F',
      'Papua New Guinea': '#228B22',
      'PNG': '#228B22',
      'Namibia': '#CD853F',
      'NAM': '#CD853F'
    };
    
    return teamColors[teamName] || '#666666'; // Default color if team not found
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

  // Fetch ELO rankings based on selected filter
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
  }, [selectedFilter]);

  const handleFilterChange = (event) => {
    setSelectedFilter(event.target.value);
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
    <Card sx={{ mt: 4, maxHeight: '600px', overflow: 'hidden' }}>
      <CardContent>
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          mb: 3 
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrophyIcon color="primary" />
            <Typography variant="h5" component="h2">
              ELO Team Rankings
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
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