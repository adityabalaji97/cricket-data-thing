import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  Select,
  MenuItem,
  Box,
  Chip,
  useTheme,
  useMediaQuery
} from '@mui/material';

const TeamBattingOrderCard = ({ battingOrderData, teamName }) => {
  const [selectedPhase, setSelectedPhase] = useState('overall');
  const [selectedPositionFilter, setSelectedPositionFilter] = useState('all');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (!battingOrderData || !battingOrderData.batting_order || battingOrderData.batting_order.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Batting Order
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No batting order data available for the selected period.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const handlePhaseChange = (event) => {
    setSelectedPhase(event.target.value);
  };

  const handlePositionFilterChange = (event) => {
    setSelectedPositionFilter(event.target.value);
  };

  const filterPlayersByPosition = (players) => {
    let filteredPlayers = players;
    
    // Filter by position
    if (selectedPositionFilter !== 'all') {
      filteredPlayers = filteredPlayers.filter(player => {
        const position = player.primary_batting_position || 99;
        
        switch (selectedPositionFilter) {
          case 'top':
            return position >= 1 && position <= 3;
          case 'middle':
            return position >= 4 && position <= 8;
          case 'lower':
            return position >= 9 && position <= 11;
          default:
            return true;
        }
      });
    }
    
    // Filter out players with 0 balls faced in the selected phase
    filteredPlayers = filteredPlayers.filter(player => {
      const phaseData = player[selectedPhase];
      return phaseData && phaseData.balls > 0;
    });
    
    return filteredPlayers;
  };

  const formatValue = (value, decimals = 1) => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      return decimals === 0 ? value.toString() : value.toFixed(decimals);
    }
    return value.toString();
  };

  const getPhaseColor = (phase) => {
    const colors = {
      overall: '#1976d2',
      powerplay: '#2e7d32',
      middle_overs: '#ed6c02',
      death_overs: '#d32f2f'
    };
    return colors[phase] || '#1976d2';
  };

  const renderMobileView = () => {
    const filteredPlayers = filterPlayersByPosition(battingOrderData.batting_order);
    
    return (
      <Box sx={{ maxHeight: '600px', overflowY: 'auto' }}>
        {filteredPlayers.map((player, index) => {
          const phaseData = player[selectedPhase];
          return (
            <Card key={player.player} variant="outlined" sx={{ mb: 2 }}>
              <CardContent sx={{ pb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h6" component="div">
                    {player.primary_batting_position || 'N/A'}. {player.player}
                  </Typography>
                  <Chip
                    label={`${player.position_frequency}/${player.total_innings}`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </Box>
                
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, fontSize: '0.875rem' }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Runs</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.runs, 0)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Balls</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.balls, 0)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Wickets</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.wickets, 0)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Average</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.average, 2)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Strike Rate</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.strike_rate, 2)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Boundary %</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.boundary_percentage, 1)}%</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Dot %</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.dot_percentage, 1)}%</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          );
        })}
        {filteredPlayers.length === 0 && (
          <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ py: 4 }}>
            No players found with the selected filters or all players have 0 balls faced in this phase.
          </Typography>
        )}
      </Box>
    );
  };

  const renderDesktopView = () => {
    const filteredPlayers = filterPlayersByPosition(battingOrderData.batting_order);
    
    return (
      <TableContainer component={Paper} sx={{ maxHeight: '600px', overflowY: 'auto' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell><strong>Pos</strong></TableCell>
              <TableCell><strong>Player</strong></TableCell>
              <TableCell align="center"><strong>Freq</strong></TableCell>
              <TableCell align="right"><strong>Runs</strong></TableCell>
              <TableCell align="right"><strong>Balls</strong></TableCell>
              <TableCell align="right"><strong>Wkts</strong></TableCell>
              <TableCell align="right"><strong>Avg</strong></TableCell>
              <TableCell align="right"><strong>SR</strong></TableCell>
              <TableCell align="right"><strong>Bnd%</strong></TableCell>
              <TableCell align="right"><strong>Dot%</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredPlayers.map((player, index) => {
              const phaseData = player[selectedPhase];
              return (
                <TableRow key={player.player} hover>
                  <TableCell>
                    <Chip
                      label={player.primary_batting_position || 'N/A'}
                      size="small"
                      color="primary"
                      sx={{ minWidth: '32px' }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {player.player}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" color="text.secondary">
                      {player.position_frequency}/{player.total_innings}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight="bold">
                      {formatValue(phaseData.runs, 0)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {formatValue(phaseData.balls, 0)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {formatValue(phaseData.wickets, 0)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {formatValue(phaseData.average, 2)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight="bold">
                      {formatValue(phaseData.strike_rate, 2)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" sx={{ color: getPhaseColor(selectedPhase) }}>
                      {formatValue(phaseData.boundary_percentage, 1)}%
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      {formatValue(phaseData.dot_percentage, 1)}%
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
            {filteredPlayers.length === 0 && (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    No players found with the selected filters or all players have 0 balls faced in this phase.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ mb: 0 }}>
            Batting Order - {teamName}
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={selectedPositionFilter}
                onChange={handlePositionFilterChange}
                displayEmpty
                sx={{
                  '& .MuiSelect-select': {
                    py: 1,
                    fontSize: '0.875rem'
                  }
                }}
              >
                <MenuItem value="all">All Positions</MenuItem>
                <MenuItem value="top">Top Order (1-3)</MenuItem>
                <MenuItem value="middle">Middle Order (4-8)</MenuItem>
                <MenuItem value="lower">Lower Order (9-11)</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={selectedPhase}
                onChange={handlePhaseChange}
                displayEmpty
                sx={{
                  '& .MuiSelect-select': {
                    py: 1,
                    fontSize: '0.875rem'
                  }
                }}
              >
                <MenuItem value="overall">Overall</MenuItem>
                <MenuItem value="powerplay">Powerplay</MenuItem>
                <MenuItem value="middle_overs">Middle Overs</MenuItem>
                <MenuItem value="death_overs">Death Overs</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {filterPlayersByPosition(battingOrderData.batting_order).length} of {battingOrderData.total_players} players • 
            {battingOrderData.date_range.start && battingOrderData.date_range.end ? (
              ` ${battingOrderData.date_range.start} to ${battingOrderData.date_range.end}`
            ) : ' All time'}
          </Typography>
          {selectedPhase !== 'overall' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Showing {selectedPhase.replace('_', ' ')} statistics (excluding players with 0 balls faced)
            </Typography>
          )}
          {selectedPhase === 'overall' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Showing overall statistics (excluding players with 0 balls faced)
            </Typography>
          )}
          {selectedPositionFilter !== 'all' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Filtered by: {selectedPositionFilter === 'top' ? 'Top Order (1-3)' : 
                            selectedPositionFilter === 'middle' ? 'Middle Order (4-8)' : 
                            'Lower Order (9-11)'}
            </Typography>
          )}
        </Box>

        {isMobile ? renderMobileView() : renderDesktopView()}

        <Box sx={{ mt: 2, pt: 1, borderTop: '1px solid #e0e0e0' }}>
          <Typography variant="caption" color="text.secondary">
            Pos: Most frequent batting position • Freq: Times batted at position / Total innings
            <br />
            Bnd%: Boundary percentage • Dot%: Dot ball percentage
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TeamBattingOrderCard;