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
  TableContainer,
  Pagination,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';

const FantasyPointsTable = ({ players, title, isMobile }) => {
  const [sortField, setSortField] = useState('avg_fantasy_points');
  const [sortDirection, setSortDirection] = useState('desc');
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;
  
  const handleSort = (field) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };
  
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
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
  
  // Paginate the data
  const paginatedPlayers = sortedPlayers.slice(
    (page - 1) * rowsPerPage,
    page * rowsPerPage
  );
  
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>{title}</Typography>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 2 }}>
        {isMobile ? (
          <FormControl size="small" fullWidth>
            <InputLabel sx={{ fontSize: '0.875rem' }}>Sort by</InputLabel>
            <Select
              value={sortField}
              onChange={(e) => handleSort(e.target.value)}
              label="Sort by"
              sx={{ fontSize: '0.875rem' }}
            >
              <MenuItem value="avg_fantasy_points" sx={{ fontSize: '0.875rem' }}>Total Points</MenuItem>
              <MenuItem value="avg_batting_points" sx={{ fontSize: '0.875rem' }}>Batting</MenuItem>
              <MenuItem value="avg_bowling_points" sx={{ fontSize: '0.875rem' }}>Bowling</MenuItem>
              <MenuItem value="avg_fielding_points" sx={{ fontSize: '0.875rem' }}>Fielding</MenuItem>
            </Select>
          </FormControl>
        ) : (
          <>
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
          </>
        )}
      </Box>
      
      <TableContainer
        component={Paper}
        sx={{
          maxHeight: 440,
          overflow: 'auto',
          backgroundColor: isMobile ? 'transparent' : undefined,
          boxShadow: isMobile ? 0 : undefined
        }}
      >
        <Table size={isMobile ? "small" : "medium"} sx={{ minWidth: isMobile ? 300 : 650 }} stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Player</TableCell>
              {!isMobile && <TableCell>Team</TableCell>}
              <TableCell>M</TableCell>
              <TableCell>FP</TableCell>
              <TableCell>Bat</TableCell>
              <TableCell>Bowl</TableCell>
              {!isMobile && <TableCell>Field</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedPlayers.map(player => (
              <TableRow key={player.player_name} sx={{ '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}>
                <TableCell>{player.player_name}</TableCell>
                {!isMobile && <TableCell>{player.team}</TableCell>}
                <TableCell>{player.matches_played}</TableCell>
                <TableCell><strong>{player.avg_fantasy_points.toFixed(1)}</strong></TableCell>
                <TableCell>{player.avg_batting_points.toFixed(1)}</TableCell>
                <TableCell>{player.avg_bowling_points.toFixed(1)}</TableCell>
                {!isMobile && <TableCell>{player.avg_fielding_points.toFixed(1)}</TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      
      {sortedPlayers.length > rowsPerPage && (
        <Stack spacing={2} sx={{ mt: 2, alignItems: 'center' }}>
          <Pagination 
            count={Math.ceil(sortedPlayers.length / rowsPerPage)} 
            page={page} 
            onChange={handleChangePage} 
            color="primary" 
            size={isMobile ? "small" : "medium"}
          />
        </Stack>
      )}
    </Box>
  );
};

export default FantasyPointsTable;