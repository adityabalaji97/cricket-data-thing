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

const TeamBowlingOrderCard = ({ bowlingOrderData, teamName }) => {
  const [selectedPhase, setSelectedPhase] = useState('overall');
  const [selectedStatsFilter, setSelectedStatsFilter] = useState('all');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (!bowlingOrderData || !bowlingOrderData.bowling_order || bowlingOrderData.bowling_order.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Bowling Order
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No bowling order data available for the selected period.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const handlePhaseChange = (event) => {
    setSelectedPhase(event.target.value);
  };

  const handleStatsFilterChange = (event) => {
    setSelectedStatsFilter(event.target.value);
  };

  const filterPlayersByStats = (players) => {
    let filteredPlayers = players;
    
    // Filter by performance criteria
    if (selectedStatsFilter !== 'all') {
      filteredPlayers = filteredPlayers.filter(player => {
        const phaseData = player[selectedPhase];
        
        switch (selectedStatsFilter) {
          case 'wicket_takers':
            return phaseData && phaseData.wickets > 0;
          case 'economical':
            return phaseData && phaseData.balls > 0 && phaseData.economy <= 8.0;
          case 'attacking':
            return phaseData && phaseData.wickets > 0 && phaseData.strike_rate <= 18;
          default:
            return true;
        }
      });
    }
    
    // Filter out players with 0 balls bowled in the selected phase
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
    const filteredPlayers = filterPlayersByStats(bowlingOrderData.bowling_order);
    
    return (
      <Box sx={{ maxHeight: '600px', overflowY: 'auto' }}>
        {filteredPlayers.map((player, index) => {
          const phaseData = player[selectedPhase];
          return (
            <Card key={player.player} variant="outlined" sx={{ mb: 2 }}>
              <CardContent sx={{ pb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h6" component="div">
                    {player.player}
                  </Typography>
                  <Chip
                    label={`${player.over_combination_frequency || 0} times`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </Box>
                
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Most Frequent Overs: {player.most_frequent_overs || 'N/A'}
                  </Typography>
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
                    <Typography variant="body2" color="text.secondary">Economy</Typography>
                    <Typography variant="body2" fontWeight="bold">{formatValue(phaseData.economy, 2)}</Typography>
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
            No players found with the selected filters or all players have 0 balls bowled in this phase.
          </Typography>
        )}
      </Box>
    );
  };

  const renderDesktopView = () => {
    const filteredPlayers = filterPlayersByStats(bowlingOrderData.bowling_order);
    
    return (
      <TableContainer component={Paper} sx={{ maxHeight: '600px', overflowY: 'auto' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell><strong>Over Combo</strong></TableCell>
              <TableCell><strong>Player</strong></TableCell>
              <TableCell align="center"><strong>Freq</strong></TableCell>
              <TableCell align="right"><strong>Runs</strong></TableCell>
              <TableCell align="right"><strong>Balls</strong></TableCell>
              <TableCell align="right"><strong>Wkts</strong></TableCell>
              <TableCell align="right"><strong>Avg</strong></TableCell>
              <TableCell align="right"><strong>SR</strong></TableCell>
              <TableCell align="right"><strong>Econ</strong></TableCell>
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
                    <Box>
                      <Typography variant="body2" fontWeight="bold" sx={{ fontSize: '0.75rem' }}>
                        {player.most_frequent_overs || 'N/A'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {player.over_combination_frequency || 0}x
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {player.player}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" color="text.secondary">
                      {player.over_combination_frequency || 0}/{player.total_innings}
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
                    <Typography variant="body2" fontWeight="bold">
                      {formatValue(phaseData.wickets, 0)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {formatValue(phaseData.average, 2)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {formatValue(phaseData.strike_rate, 2)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight="bold" sx={{ color: getPhaseColor(selectedPhase) }}>
                      {formatValue(phaseData.economy, 2)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      {formatValue(phaseData.boundary_percentage, 1)}%
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" sx={{ color: getPhaseColor(selectedPhase) }}>
                      {formatValue(phaseData.dot_percentage, 1)}%
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
            {filteredPlayers.length === 0 && (
              <TableRow>
                <TableCell colSpan={11} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    No players found with the selected filters or all players have 0 balls bowled in this phase.
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
            Bowling Order - {teamName}
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={selectedStatsFilter}
                onChange={handleStatsFilterChange}
                displayEmpty
                sx={{
                  '& .MuiSelect-select': {
                    py: 1,
                    fontSize: '0.875rem'
                  }
                }}
              >
                <MenuItem value="all">All Bowlers</MenuItem>
                <MenuItem value="wicket_takers">Wicket Takers</MenuItem>
                <MenuItem value="economical">Economical (≤8.0)</MenuItem>
                <MenuItem value="attacking">Attacking (SR≤18)</MenuItem>
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
            {filterPlayersByStats(bowlingOrderData.bowling_order).length} of {bowlingOrderData.total_players} players • 
            {bowlingOrderData.date_range.start && bowlingOrderData.date_range.end ? (
              ` ${bowlingOrderData.date_range.start} to ${bowlingOrderData.date_range.end}`
            ) : ' All time'}
          </Typography>
          {selectedPhase !== 'overall' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Showing {selectedPhase.replace('_', ' ')} statistics (excluding players with 0 balls bowled)
            </Typography>
          )}
          {selectedPhase === 'overall' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Showing overall statistics (excluding players with 0 balls bowled)
            </Typography>
          )}
          {selectedStatsFilter !== 'all' && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Filtered by: {selectedStatsFilter === 'wicket_takers' ? 'Wicket Takers Only' : 
                            selectedStatsFilter === 'economical' ? 'Economical Bowlers (≤8.0 economy)' : 
                            'Attacking Bowlers (≤18 strike rate)'}
            </Typography>
          )}
        </Box>

        {isMobile ? renderMobileView() : renderDesktopView()}

        <Box sx={{ mt: 2, pt: 1, borderTop: '1px solid #e0e0e0' }}>
          <Typography variant="caption" color="text.secondary">
            Over Combo: Most frequent over combination • Freq: Times bowled this combo / Total innings
            <br />
            Avg: Bowling average (runs/wickets) • SR: Strike rate (balls/wickets) • Econ: Economy rate (runs/over)
            <br />
            Bnd%: Boundary percentage • Dot%: Dot ball percentage
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TeamBowlingOrderCard;