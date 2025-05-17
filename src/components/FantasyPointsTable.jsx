// FantasyPointsTable.jsx component
import React, { useState } from 'react';
import { 
  Table, 
  TableHead, 
  TableBody, 
  TableRow, 
  TableCell, 
  Button, 
  ButtonGroup, 
  Typography, 
  Box,
  Paper,
  TableContainer
} from '@mui/material';

const FantasyPointsTable = ({ players, title }) => {
  const [sortField, setSortField] = useState('avg_fantasy_points');
  const [sortDirection, setSortDirection] = useState('desc');
  
  const handleSort = (field) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };
  
  // Ensure players is an array and all fields exist before sorting
  const validPlayers = Array.isArray(players) ? players.filter(player => player && typeof player === 'object') : [];
  
  const sortedPlayers = [...validPlayers].sort((a, b) => {
    // Default to 0 for missing or NaN values
    const aValue = typeof a[sortField] === 'number' ? a[sortField] : 0;
    const bValue = typeof b[sortField] === 'number' ? b[sortField] : 0;
    
    if (sortDirection === 'asc') {
      return aValue - bValue;
    } else {
      return bValue - aValue;
    }
  });
  
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>{title}</Typography>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">Sort by:</Typography>
        <ButtonGroup size="small">
          <Button 
            variant={sortField === 'avg_fantasy_points' ? 'contained' : 'outlined'}
            onClick={() => handleSort('avg_fantasy_points')}
          >
            Total Points
          </Button>
          <Button 
            variant={sortField === 'avg_batting_points' ? 'contained' : 'outlined'}
            onClick={() => handleSort('avg_batting_points')}
          >
            Batting
          </Button>
          <Button 
            variant={sortField === 'avg_bowling_points' ? 'contained' : 'outlined'}
            onClick={() => handleSort('avg_bowling_points')}
          >
            Bowling
          </Button>
          <Button 
            variant={sortField === 'avg_fielding_points' ? 'contained' : 'outlined'}
            onClick={() => handleSort('avg_fielding_points')}
          >
            Fielding
          </Button>
        </ButtonGroup>
      </Box>
      
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Player</TableCell>
              <TableCell>Team</TableCell>
              <TableCell>Matches</TableCell>
              <TableCell>Fantasy Points</TableCell>
              <TableCell>Batting</TableCell>
              <TableCell>Bowling</TableCell>
              <TableCell>Fielding</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedPlayers.map(player => (
              <TableRow key={player.player_name} sx={{ '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}>
                <TableCell>{player.player_name}</TableCell>
                <TableCell>{player.team}</TableCell>
                <TableCell>{player.matches_played}</TableCell>
                <TableCell><strong>{player.avg_fantasy_points.toFixed(1)}</strong></TableCell>
                <TableCell>{player.avg_batting_points.toFixed(1)}</TableCell>
                <TableCell>{player.avg_bowling_points.toFixed(1)}</TableCell>
                <TableCell>{player.avg_fielding_points.toFixed(1)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default FantasyPointsTable;