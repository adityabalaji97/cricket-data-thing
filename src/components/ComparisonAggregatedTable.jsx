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

const ComparisonAggregatedTable = ({ batters }) => {
  const [groupBy, setGroupBy] = useState('batting_position');
  const [sortBy, setSortBy] = useState('matches');
  const [sortOrder, setSortOrder] = useState('desc');
  const [visiblePlayers, setVisiblePlayers] = useState(
    batters.map(b => b.id)
  );

  // Color assignment for players (same as other components)
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

  const getPositionGroup = (position) => {
    if (position <= 3) return 'Top Order (1-3)';
    if (position <= 6) return 'Middle Order (4-6)';
    return 'Lower Order (7+)';
  };

  // Group by options
  const groupByOptions = {
    'batting_position': { 
      label: 'Batting Position', 
      getValue: (inning) => inning.batting_position?.toString() || 'N/A'
    },
    'position_group': { 
      label: 'Position Group', 
      getValue: (inning) => getPositionGroup(inning.batting_position || 11)
    },
    'entry_phase': { 
      label: 'Entry Phase', 
      getValue: (inning) => getPhase(inning.entry_point?.overs || 0)
    },
    'venue': { 
      label: 'Venue', 
      getValue: (inning) => inning.venue || 'Unknown'
    },
    'competition': { 
      label: 'Competition', 
      getValue: (inning) => inning.competition || 'Unknown'
    },
    'match_result': { 
      label: 'Match Result', 
      getValue: (inning) => inning.winner === inning.batting_team ? 'win' : 'loss'
    }
  };

  // Process and aggregate data
  const aggregatedData = useMemo(() => {
    const getGroupValue = groupByOptions[groupBy].getValue;
    
    // Group data by groupBy field and player
    const grouped = {};
    
    batters.forEach(batter => {
      if (!visiblePlayers.includes(batter.id)) return;
      
      batter.stats.innings.forEach(inning => {
        const groupValue = getGroupValue(inning);
        const key = `${groupValue}|${batter.id}`;
        
        if (!grouped[key]) {
          grouped[key] = {
            groupValue,
            playerId: batter.id,
            playerLabel: batter.label,
            color: playerColors[batter.id],
            innings: [],
            // Aggregated metrics
            matches: 0,
            totalRuns: 0,
            totalBalls: 0,
            totalWickets: 0,
            totalBoundaries: 0,
            totalDots: 0,
            wins: 0,
            losses: 0,
            // Phase-wise totals
            ppRuns: 0,
            ppBalls: 0,
            middleRuns: 0,
            middleBalls: 0,
            deathRuns: 0,
            deathBalls: 0
          };
        }
        
        const group = grouped[key];
        group.innings.push(inning);
        group.matches++;
        group.totalRuns += inning.runs || 0;
        group.totalBalls += inning.balls_faced || 0;
        group.totalWickets += (inning.wickets || 0);
        group.totalBoundaries += (inning.fours || 0) + (inning.sixes || 0);
        group.totalDots += inning.dots || 0;
        
        // Match results (derive from winner vs batting_team)
        const isWin = inning.winner === inning.batting_team;
        if (isWin) group.wins++;
        else group.losses++;
        
        // Phase-wise aggregation (extract from phase_details)
        group.ppRuns += inning.phase_details?.powerplay?.runs || 0;
        group.ppBalls += inning.phase_details?.powerplay?.balls || 0;
        group.middleRuns += (inning.phase_details?.middle?.runs || 0);
        group.middleBalls += (inning.phase_details?.middle?.balls || 0);
        group.deathRuns += inning.phase_details?.death?.runs || 0;
        group.deathBalls += inning.phase_details?.death?.balls || 0;
      });
    });
    
    // Calculate derived metrics
    Object.values(grouped).forEach(group => {
      group.average = group.totalWickets > 0 ? group.totalRuns / group.totalWickets : 0;
      group.strikeRate = group.totalBalls > 0 ? (group.totalRuns * 100) / group.totalBalls : 0;
      group.dotPercentage = group.totalBalls > 0 ? (group.totalDots * 100) / group.totalBalls : 0;
      group.boundaryPercentage = group.totalBalls > 0 ? (group.totalBoundaries * 100) / group.totalBalls : 0;
      group.winPercentage = group.matches > 0 ? (group.wins * 100) / (group.wins + group.losses) : 0;
      group.runsPerInnings = group.matches > 0 ? group.totalRuns / group.matches : 0;
      group.ballsPerInnings = group.matches > 0 ? group.totalBalls / group.matches : 0;
      
      // Phase-wise rates
      group.ppStrikeRate = group.ppBalls > 0 ? (group.ppRuns * 100) / group.ppBalls : 0;
      group.middleStrikeRate = group.middleBalls > 0 ? (group.middleRuns * 100) / group.middleBalls : 0;
      group.deathStrikeRate = group.deathBalls > 0 ? (group.deathRuns * 100) / group.deathBalls : 0;
    });
    
    return Object.values(grouped);
  }, [batters, playerColors, visiblePlayers, groupBy]);

  // Get unique group values for rendering
  const groupValues = useMemo(() => {
    const values = [...new Set(aggregatedData.map(item => item.groupValue))];
    return values.sort();
  }, [aggregatedData]);

  // Sort data
  const sortedData = useMemo(() => {
    return [...aggregatedData].sort((a, b) => {
      // First sort by group value, then by metric
      if (a.groupValue !== b.groupValue) {
        return a.groupValue.localeCompare(b.groupValue);
      }
      
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      return sortOrder === 'asc' ? 
        (aVal > bVal ? 1 : -1) : 
        (aVal < bVal ? 1 : -1);
    });
  }, [aggregatedData, sortBy, sortOrder]);

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

  if (!batters || batters.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Aggregated Comparison Table</Typography>
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
          <Typography variant="h6">Aggregated Performance Comparison</Typography>
          <Typography variant="caption" color="text.secondary">
            Grouped by {groupByOptions[groupBy].label}
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
          {/* Group By Control */}
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControl sx={{ minWidth: 160 }}>
              <InputLabel>Group By</InputLabel>
              <Select
                value={groupBy}
                label="Group By"
                onChange={(e) => setGroupBy(e.target.value)}
              >
                {Object.entries(groupByOptions).map(([key, { label }]) => (
                  <MenuItem key={key} value={key}>{label}</MenuItem>
                ))}
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
                <TableCell sx={{ minWidth: 120 }}>
                  {groupByOptions[groupBy].label}
                </TableCell>
                <TableCell>Player</TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'matches'}
                    direction={sortBy === 'matches' ? sortOrder : 'asc'}
                    onClick={() => handleSort('matches')}
                  >
                    Inns
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'totalRuns'}
                    direction={sortBy === 'totalRuns' ? sortOrder : 'asc'}
                    onClick={() => handleSort('totalRuns')}
                  >
                    Runs
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'average'}
                    direction={sortBy === 'average' ? sortOrder : 'asc'}
                    onClick={() => handleSort('average')}
                  >
                    Avg
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'strikeRate'}
                    direction={sortBy === 'strikeRate' ? sortOrder : 'asc'}
                    onClick={() => handleSort('strikeRate')}
                  >
                    SR
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'runsPerInnings'}
                    direction={sortBy === 'runsPerInnings' ? sortOrder : 'asc'}
                    onClick={() => handleSort('runsPerInnings')}
                  >
                    Runs/Inn
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'ballsPerInnings'}
                    direction={sortBy === 'ballsPerInnings' ? sortOrder : 'asc'}
                    onClick={() => handleSort('ballsPerInnings')}
                  >
                    Balls/Inn
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'dotPercentage'}
                    direction={sortBy === 'dotPercentage' ? sortOrder : 'asc'}
                    onClick={() => handleSort('dotPercentage')}
                  >
                    Dot %
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'boundaryPercentage'}
                    direction={sortBy === 'boundaryPercentage' ? sortOrder : 'asc'}
                    onClick={() => handleSort('boundaryPercentage')}
                  >
                    Boundary %
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Powerplay Strike Rate">
                    <TableSortLabel
                      active={sortBy === 'ppStrikeRate'}
                      direction={sortBy === 'ppStrikeRate' ? sortOrder : 'asc'}
                      onClick={() => handleSort('ppStrikeRate')}
                    >
                      PP SR
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Middle Overs Strike Rate">
                    <TableSortLabel
                      active={sortBy === 'middleStrikeRate'}
                      direction={sortBy === 'middleStrikeRate' ? sortOrder : 'asc'}
                      onClick={() => handleSort('middleStrikeRate')}
                    >
                      Mid SR
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Death Overs Strike Rate">
                    <TableSortLabel
                      active={sortBy === 'deathStrikeRate'}
                      direction={sortBy === 'deathStrikeRate' ? sortOrder : 'asc'}
                      onClick={() => handleSort('deathStrikeRate')}
                    >
                      Death SR
                    </TableSortLabel>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">
                  <TableSortLabel
                    active={sortBy === 'winPercentage'}
                    direction={sortBy === 'winPercentage' ? sortOrder : 'asc'}
                    onClick={() => handleSort('winPercentage')}
                  >
                    Win %
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {groupValues.map(groupValue => {
                const groupData = sortedData.filter(item => item.groupValue === groupValue);
                
                return (
                  <React.Fragment key={groupValue}>
                    {/* Group Header */}
                    <TableRow sx={{ backgroundColor: 'rgba(0, 0, 0, 0.04)' }}>
                      <TableCell 
                        colSpan={13} 
                        sx={{ 
                          fontWeight: 'bold', 
                          fontSize: '0.9rem',
                          py: 1
                        }}
                      >
                        {groupValue} ({groupData.length} players)
                      </TableCell>
                    </TableRow>
                    
                    {/* Player Data */}
                    {groupData.map((item, index) => (
                      <TableRow 
                        key={`${item.groupValue}-${item.playerId}`}
                        sx={{ 
                          '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04)' }
                        }}
                      >
                        <TableCell sx={{ pl: 3 }}>
                          {/* Empty cell under group header */}
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Box 
                              sx={{ 
                                width: 12, 
                                height: 12, 
                                borderRadius: '50%', 
                                backgroundColor: item.color 
                              }} 
                            />
                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                              {item.playerLabel}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.matches}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                            {item.totalRuns}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.average.toFixed(1)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.strikeRate.toFixed(1)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.runsPerInnings.toFixed(1)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.ballsPerInnings.toFixed(1)}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.dotPercentage.toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2">
                            {item.boundaryPercentage.toFixed(1)}%
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2" color={item.ppBalls > 0 ? 'inherit' : 'text.secondary'}>
                            {item.ppBalls > 0 ? item.ppStrikeRate.toFixed(1) : 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2" color={item.middleBalls > 0 ? 'inherit' : 'text.secondary'}>
                            {item.middleBalls > 0 ? item.middleStrikeRate.toFixed(1) : 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Typography variant="body2" color={item.deathBalls > 0 ? 'inherit' : 'text.secondary'}>
                            {item.deathBalls > 0 ? item.deathStrikeRate.toFixed(1) : 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip 
                            label={`${item.winPercentage.toFixed(0)}%`}
                            color={item.winPercentage >= 50 ? 'success' : 'error'}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </React.Fragment>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Summary Info */}
        <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {batters.map(batter => {
              const playerData = aggregatedData.filter(d => d.playerId === batter.id);
              const totalInnings = playerData.reduce((sum, d) => sum + d.matches, 0);
              
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
                  {batter.label}: {totalInnings} innings across {playerData.length} groups
                </Typography>
              );
            })}
          </Box>
          
          <Typography variant="caption" color="text.secondary">
            Data aggregated by {groupByOptions[groupBy].label.toLowerCase()}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ComparisonAggregatedTable;