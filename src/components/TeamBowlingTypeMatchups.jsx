import React, { useState, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  CircularProgress
} from '@mui/material';

const TeamBowlingTypeMatchups = ({ 
  players, 
  startDate, 
  endDate, 
  team1_players = [], 
  team2_players = [], 
  team1Name = "Team 1", 
  team2Name = "Team 2" 
}) => {
  const [matchupData, setMatchupData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [phase, setPhase] = useState('overall');

  const fetchMatchupData = async () => {
    if (!players || players.length === 0) return;
    
    setLoading(true);
    try {
      const playerParams = players.map(player => `players=${encodeURIComponent(player)}`).join('&');
      const dateParams = `start_date=${startDate}&end_date=${endDate}`;
      const response = await axios.get(`${config.API_URL}/teams/bowling-type-matchups?${playerParams}&phase=${phase}&${dateParams}`);
      setMatchupData(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching bowling type matchups:', err);
      setError('Failed to load bowling type matchup data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatchupData();
  }, [players, phase, startDate, endDate]);

  const handlePhaseChange = (event) => {
    setPhase(event.target.value);
  };

  const phaseOptions = [
    { value: 'overall', label: 'Overall (0-20)' },
    { value: 'powerplay', label: 'Powerplay (0-6)' },
    { value: 'middle', label: 'Middle (6-15)' },
    { value: 'death', label: 'Death (15-20)' }
  ];

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (!matchupData || !matchupData.players || matchupData.players.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>No bowling type matchup data available for the selected players.</Typography>
      </Box>
    );
  }

  // Sort players by powerplay percentage (already sorted in API response)
  const { players: playerData, bowling_types: bowlingTypes = [] } = matchupData;
  
  // Filter out the NaN column
  const filteredBowlingTypes = bowlingTypes.filter(type => type !== 'NaN');

  const team1Data = playerData.filter(player => team1_players.includes(player.name));
  const team2Data = playerData.filter(player => team2_players.includes(player.name));
  const otherData = team1_players.length && team2_players.length ? 
                    playerData.filter(player => !team1_players.includes(player.name) && !team2_players.includes(player.name)) :
                    playerData;
                    
  // Filter out players with no data
  const filterEmptyRows = (playersData) => {
    return playersData.filter(player => {
      // Check if player has at least one non-empty matchup
      return filteredBowlingTypes.some(type => {
        const matchup = player.bowling_types[type];
        return matchup && matchup.balls > 0;
      });
    });
  };

  const team1FilteredData = filterEmptyRows(team1Data);
  const team2FilteredData = filterEmptyRows(team2Data);
  const otherFilteredData = filterEmptyRows(otherData);

  const renderPlayerTable = (playersData, title) => (
    <TableContainer component={Paper} sx={{ mb: 4 }}>
      <Table size="small" sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 'bold', width: '200px' }}>
              {title}
            </TableCell>
            {filteredBowlingTypes.map(type => (
              <TableCell key={type} align="center" sx={{ fontWeight: 'bold' }}>
                {type}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {playersData.map((player) => (
            <TableRow key={player.name} sx={{ height: '52px' }}>
              <TableCell component="th" scope="row">
                {player.name}
              </TableCell>
              {filteredBowlingTypes.map(type => {
                const matchup = player.bowling_types[type];
                
                if (!matchup || matchup.balls === 0) {
                  return (
                    <TableCell key={type} align="center">
                      -
                    </TableCell>
                  );
                }

                return (
                  <Tooltip
                    key={type}
                    title={
                      <Box sx={{ p: 1 }}>
                        <Typography variant="body2">Dot %: {matchup.dot_percentage?.toFixed(1)}%</Typography>
                        <Typography variant="body2">Boundary %: {matchup.boundary_percentage?.toFixed(1)}%</Typography>
                        <Typography variant="body2">Average: {matchup.average > 0 ? matchup.average?.toFixed(1) : '-'}</Typography>
                      </Box>
                    }
                  >
                    <TableCell
                      align="center"
                      sx={{ 
                        color: matchup.strike_rate >= 150 ? '#4caf50' : 
                               matchup.strike_rate <= 100 ? '#f44336' : 
                               '#ff9800',
                        fontWeight: 'medium',
                        '&:hover': { opacity: 0.8 }
                      }}
                    >
                      {matchup.runs}-{matchup.wickets} ({matchup.balls}) @ {matchup.strike_rate?.toFixed(1)}
                    </TableCell>
                  </Tooltip>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box sx={{ width: '100%', overflow: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Team vs Bowling Types</Typography>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel id="phase-select-label">Phase</InputLabel>
          <Select
            labelId="phase-select-label"
            id="phase-select"
            value={phase}
            label="Phase"
            onChange={handlePhaseChange}
          >
            {phaseOptions.map(option => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      
      {/* If we have distinct team1 and team2 players, render separate tables */}
      {team1_players.length > 0 && team2_players.length > 0 ? (
        <>
          {team1FilteredData.length > 0 && renderPlayerTable(team1FilteredData, `${team1Name} Players vs Bowling Types`)}
          {team2FilteredData.length > 0 && renderPlayerTable(team2FilteredData, `${team2Name} Players vs Bowling Types`)}
          {otherFilteredData.length > 0 && renderPlayerTable(otherFilteredData, "Other Players vs Bowling Types")}
        </>
      ) : (
        // Otherwise render all players in one table
        renderPlayerTable(filterEmptyRows(playerData), "Player vs Bowling Types")
      )}
    </Box>
  );
};

export default TeamBowlingTypeMatchups;