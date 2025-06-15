import React, { useState, useMemo } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  Paper,
  Tooltip
} from '@mui/material';

const ComparisonInningsTable = ({ batters }) => {
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [visiblePlayers, setVisiblePlayers] = useState(
    batters.map(b => b.id)
  );
  const [filterPhase, setFilterPhase] = useState('all');
  const [filterPosition, setFilterPosition] = useState('all');

  // Color assignment for players (same as scatter chart)
  const playerColors = useMemo(() => {
    const colors = [
      '#ff6b6b', '#4ecdc4', '#feca57', '#ff9ff3', '#54a0ff',
      '#5f27cd', '#00d2d3', '#ff9f43', '#1dd1a1', '#c44569'
    ];
    return batters.reduce((acc, batter, index) => {
      acc[batter.id] = colors[index % colors.length];
      return acc;
    }, {});
  }, [batters]);

  const getPhase = (over) => {
    if (over < 6) return 'Powerplay';
    if (over < 10) return 'Middle 1';
    if (over < 15) return 'Middle 2';
    return 'Death';
  };

  // Process and combine all innings data
  const processedData = useMemo(() => {
    return batters.flatMap(batter => 
      batter.stats.innings.map(inning => ({
        ...inning,
        playerId: batter.id,
        playerName: batter.name,
        playerLabel: batter.label,
        color: playerColors[batter.id],
        
        // Enhanced calculated fields (with null checks)
        entryPhase: getPhase(inning.entry_point?.overs || 0),
        entryWickets: (inning.batting_position || 1) - 1,
        entryScore: inning.entry_point?.runs || 0,
        entryOvers: inning.entry_point?.overs || 0,
        
        // Team context (with null checks)
        teamTotalRuns: inning.runs + (inning.team_comparison?.team_runs_excl_batter || 0),
        teamTotalBalls: inning.balls_faced + (inning.team_comparison?.team_balls_excl_batter || 0),
        teamSR: inning.team_comparison?.team_sr_excl_batter || 0,
        srDiff: inning.team_comparison?.sr_diff || 0,
        
        // Match result context (with fallback for missing data)
        isWin: inning.match_result === 'win',
        matchResult: inning.match_result || 'unknown',
        
        // Performance metrics (with null checks)
        efficiency: ((inning.runs || 0) / (inning.balls_faced || 1)) * 100,
        contribution: ((inning.runs || 0) / ((inning.runs || 0) + (inning.team_comparison?.team_runs_excl_batter || 0) || 1)) * 100
      }))
    ).filter(inning => visiblePlayers.includes(inning.playerId));
  }, [batters, playerColors, visiblePlayers]);

  // Apply filters
  const filteredData = useMemo(() => {
    let filtered = processedData;
    
    if (filterPhase !== 'all') {
      filtered = filtered.filter(inning => inning.entryPhase === filterPhase);
    }
    
    if (filterPosition !== 'all') {
      const posRange = filterPosition.split('-');
      if (posRange.length === 2) {
        const min = parseInt(posRange[0]);
        const max = parseInt(posRange[1]);
        filtered = filtered.filter(inning => 
          inning.batting_position >= min && inning.batting_position <= max
        );
      }
    }
    
    return filtered;
  }, [processedData, filterPhase, filterPosition]);

  // Sort data
  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      // Handle date sorting
      if (sortBy === 'date') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      }
      
      // Handle numeric sorting
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      // Handle string sorting
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
  }, [filteredData, sortBy, sortOrder]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const togglePlayer = (playerId) => {
    setVisiblePlayers(prev => 
      prev.includes(playerId) 
        ? prev.filter(id => id !== playerId)
        : [...prev, playerId]
    );
  };

  const getResultChip = (result, isWin) => {
    // Handle null/undefined result values
    const displayResult = result || 'unknown';
    const chipColor = displayResult === 'unknown' ? 'default' : (isWin ? 'success' : 'error');
    
    return (
      <Chip 
        label={displayResult.toUpperCase()} 
        color={chipColor}
        size="small"
        variant="outlined"
      />
    );
  };

  const getSRDiffChip = (srDiff) => {
    const safeSrDiff = srDiff || 0;
    const isPositive = safeSrDiff > 0;
    return (
      <Chip 
        label={`${isPositive ? '+' : ''}${safeSrDiff.toFixed(1)}`}
        color={safeSrDiff === 0 ? 'default' : (isPositive ? 'success' : 'error')}
        size="small"
        variant="filled"
        sx={{ minWidth: '60px' }}
      />
    );
  };

  if (!batters || batters.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Innings Details Table</Typography>
          <Typography variant="body2" color="text.secondary">
            No batter data available for comparison.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">Innings Details Comparison</Typography>
          <Typography variant="caption" color="text.secondary">
            {sortedData.length} innings shown
          </Typography>
        </Box>
        
        {/* Controls Row */}
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 2,
          mb: 3 
        }}>
          {/* Filter Controls */}
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControl sx={{ minWidth: 120 }}>
              <InputLabel>Entry Phase</InputLabel>
              <Select
                value={filterPhase}
                label="Entry Phase"
                onChange={(e) => setFilterPhase(e.target.value)}
              >
                <MenuItem value="all">All Phases</MenuItem>
                <MenuItem value="Powerplay">Powerplay</MenuItem>
                <MenuItem value="Middle 1">Middle 1</MenuItem>
                <MenuItem value="Middle 2">Middle 2</MenuItem>
                <MenuItem value="Death">Death</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl sx={{ minWidth: 120 }}>
              <InputLabel>Position</InputLabel>
              <Select
                value={filterPosition}
                label="Position"
                onChange={(e) => setFilterPosition(e.target.value)}
              >
                <MenuItem value="all">All Positions</MenuItem>
                <MenuItem value="1-3">Top Order (1-3)</MenuItem>
                <MenuItem value="4-6">Middle Order (4-6)</MenuItem>
                <MenuItem value="7-11">Lower Order (7+)</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {/* Player Toggle Chips */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {batters.map(batter => (
              <Chip
                key={batter.id}
                label={batter.label}
                clickable
                variant={visiblePlayers.includes(batter.id) ? 'filled' : 'outlined'}
                onClick={() => togglePlayer(batter.id)}
                sx={{ 
                  backgroundColor: visiblePlayers.includes(batter.id) 
                    ? playerColors[batter.id] 
                    : 'transparent',
                  color: visiblePlayers.includes(batter.id) ? 'white' : playerColors[batter.id],
                  borderColor: playerColors[batter.id],
                  '&:hover': {
                    backgroundColor: playerColors[batter.id],
                    color: 'white'
                  }
                }}
              />
            ))}
          </Box>
        </Box>

        {/* Table */}
        <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortBy === 'playerLabel'}
                    direction={sortBy === 'playerLabel' ? sortOrder : 'asc'}
                    onClick={() => handleSort('playerLabel')}
                  >
                    Player
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortBy === 'date'}
                    direction={sortBy === 'date' ? sortOrder : 'asc'}
                    onClick={() => handleSort('date')}
                  >
                    Date
                  </TableSortLabel>
                </TableCell>
                <TableCell>Venue</TableCell>
                <TableCell>Competition</TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'batting_position'}
                    direction={sortBy === 'batting_position' ? sortOrder : 'asc'}
                    onClick={() => handleSort('batting_position')}
                  >
                    Pos
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Team score when batter entered">
                    <TableSortLabel
                      active={sortBy === 'entryScore'}
                      direction={sortBy === 'entryScore' ? sortOrder : 'asc'}
                      onClick={() => handleSort('entryScore')}
                    >
                      Entry Score
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Over when batter entered">
                    <TableSortLabel
                      active={sortBy === 'entryOvers'}
                      direction={sortBy === 'entryOvers' ? sortOrder : 'asc'}
                      onClick={() => handleSort('entryOvers')}
                    >
                      Entry Over
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">Entry Phase</TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'runs'}
                    direction={sortBy === 'runs' ? sortOrder : 'asc'}
                    onClick={() => handleSort('runs')}
                  >
                    Runs (Balls)
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'strike_rate'}
                    direction={sortBy === 'strike_rate' ? sortOrder : 'asc'}
                    onClick={() => handleSort('strike_rate')}
                  >
                    SR
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Strike rate difference vs team (excluding this batter)">
                    <TableSortLabel
                      active={sortBy === 'srDiff'}
                      direction={sortBy === 'srDiff' ? sortOrder : 'asc'}
                      onClick={() => handleSort('srDiff')}
                    >
                      SR vs Team
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Team's total score in this innings">
                    <TableSortLabel
                      active={sortBy === 'teamTotalRuns'}
                      direction={sortBy === 'teamTotalRuns' ? sortOrder : 'asc'}
                      onClick={() => handleSort('teamTotalRuns')}
                    >
                      Team Total
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Percentage contribution to team score">
                    <TableSortLabel
                      active={sortBy === 'contribution'}
                      direction={sortBy === 'contribution' ? sortOrder : 'asc'}
                      onClick={() => handleSort('contribution')}
                    >
                      Contribution %
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'matchResult'}
                    direction={sortBy === 'matchResult' ? sortOrder : 'asc'}
                    onClick={() => handleSort('matchResult')}
                  >
                    Result
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedData.map((inning, index) => (
                <TableRow 
                  key={`${inning.playerId}-${inning.match_id}-${index}`}
                  sx={{ 
                    '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04)' },
                    backgroundColor: inning.matchResult === 'unknown' 
                      ? 'rgba(0, 0, 0, 0.02)' 
                      : (inning.isWin ? 'rgba(76, 175, 80, 0.05)' : 'rgba(244, 67, 54, 0.05)')
                  }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box 
                        sx={{ 
                          width: 12, 
                          height: 12, 
                          borderRadius: '50%', 
                          backgroundColor: inning.color 
                        }} 
                      />
                      <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                        {inning.playerLabel}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(inning.date).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {inning.venue}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {inning.competition}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                      {inning.batting_position || 'N/A'}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {inning.entryScore}/{inning.entryWickets}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {inning.entryOvers.toFixed(1)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip 
                      label={inning.entryPhase} 
                      size="small" 
                      variant="outlined"
                      color="primary"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                      {inning.runs || 0} ({inning.balls_faced || 0})
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {(inning.strike_rate || 0).toFixed(1)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {getSRDiffChip(inning.srDiff)}
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {inning.teamTotalRuns}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2">
                      {inning.contribution.toFixed(1)}%
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {getResultChip(inning.matchResult, inning.isWin)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Summary Info */}
        <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {batters.map(batter => {
              const playerInnings = sortedData.filter(d => d.playerId === batter.id);
              const wins = playerInnings.filter(d => d.isWin).length;
              
              return (
                <Typography 
                  key={batter.id}
                  variant="caption" 
                  sx={{ 
                    color: playerColors[batter.id],
                    opacity: visiblePlayers.includes(batter.id) ? 1 : 0.5,
                    fontWeight: 'medium'
                  }}
                >
                  {batter.label}: {playerInnings.length} innings ({wins}W-{playerInnings.length - wins}L)
                </Typography>
              );
            })}
          </Box>
          
          <Typography variant="caption" color="text.secondary">
            Wins highlighted in green • Losses highlighted in red
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ComparisonInningsTable;