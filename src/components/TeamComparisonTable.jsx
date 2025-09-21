import React, { useState } from 'react';
import {
  Box,
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
  Tabs,
  Tab,
  useTheme,
  useMediaQuery,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';

const TeamComparisonTable = ({ teams, showPercentiles }) => {
  const [currentTab, setCurrentTab] = useState(0);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [infoDialogContent, setInfoDialogContent] = useState(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (!teams || teams.length === 0) {
    return null;
  }

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const handleInfoClick = (content) => {
    setInfoDialogContent(content);
    setInfoDialogOpen(true);
  };

  const handleInfoClose = () => {
    setInfoDialogOpen(false);
    setInfoDialogContent(null);
  };

  // Helper function to format values
  const formatValue = (value, decimals = 2) => {
    if (value === null || value === undefined || value === '') return '-';
    if (typeof value === 'number') {
      return decimals === 0 ? value.toString() : value.toFixed(decimals);
    }
    return value.toString();
  };

  // Helper function to get the correct value based on percentiles toggle
  const getValue = (data, baseKey, percentileKey = null) => {
    if (!data) return 0;
    
    if (showPercentiles && percentileKey && data[percentileKey] !== undefined) {
      return data[percentileKey];
    }
    
    return data[baseKey] || 0;
  };

  // Helper function to get cell color based on values
  const getCellColorStyle = (value, isHigherBetter, allValues) => {
    if (allValues.length <= 1 || value === null || value === undefined) return {};
    
    const numericValues = allValues.filter(v => v !== null && v !== undefined && !isNaN(v));
    if (numericValues.length <= 1) return {};
    
    const min = Math.min(...numericValues);
    const max = Math.max(...numericValues);
    const range = max - min;
    
    if (range === 0) return {};
    
    let normalizedValue;
    if (isHigherBetter) {
      normalizedValue = (value - min) / range;
    } else {
      normalizedValue = (max - value) / range;
    }
    
    if (normalizedValue >= 0.7) {
      return { color: '#4CAF50', fontWeight: 'bold' };
    } else if (normalizedValue >= 0.4) {
      return { color: '#FFC107' };
    } else {
      return { color: '#F44336', fontWeight: 'bold' };
    }
  };

  // Phase-wise batting performance comparison
  const renderBattingPhaseComparison = () => {
    const metrics = [
      { 
        key: 'runs', 
        label: 'Runs', 
        higherBetter: true, 
        decimals: 0,
        percentileKey: null
      },
      { 
        key: 'balls', 
        label: 'Balls', 
        higherBetter: true, 
        decimals: 0,
        percentileKey: null
      },
      { 
        key: 'wickets', 
        label: 'Wickets', 
        higherBetter: false, 
        decimals: 0,
        percentileKey: null
      },
      { 
        key: 'average', 
        label: 'Average', 
        higherBetter: true, 
        decimals: 2,
        percentileKey: 'normalized_average'
      },
      { 
        key: 'strike_rate', 
        label: 'Strike Rate', 
        higherBetter: true, 
        decimals: 2,
        percentileKey: 'normalized_strike_rate'
      }
    ];

    const phases = ['powerplay', 'middle_overs', 'death_overs'];
    
    return (
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Phase</strong></TableCell>
              <TableCell><strong>Metric</strong></TableCell>
              {teams.map(team => (
                <TableCell key={team.id} align="center"><strong>{team.label}</strong></TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {phases.map(phase => 
              metrics.map((metric, metricIndex) => {
                const values = teams.map(team => 
                  getValue(team.phaseStats?.[phase], metric.key, metric.percentileKey)
                );
                
                return (
                  <TableRow key={`${phase}-${metric.key}`}>
                    {metricIndex === 0 && (
                      <TableCell rowSpan={metrics.length} sx={{ verticalAlign: 'top', pt: 2 }}>
                        <Chip 
                          label={phase.replace('_', ' ').toUpperCase()} 
                          size="small" 
                          color="primary"
                        />
                      </TableCell>
                    )}
                    <TableCell>{metric.label}</TableCell>
                    {teams.map((team, teamIndex) => {
                      const value = getValue(team.phaseStats?.[phase], metric.key, metric.percentileKey);
                      return (
                        <TableCell 
                          key={team.id} 
                          align="center"
                          sx={getCellColorStyle(value, metric.higherBetter, values)}
                        >
                          {formatValue(value, metric.decimals)}
                          {showPercentiles && metric.percentileKey && value > 0 ? '%' : ''}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Phase-wise bowling performance comparison
  const renderBowlingPhaseComparison = () => {
    const metrics = [
      { 
        key: 'runs', 
        label: 'Runs', 
        higherBetter: false, 
        decimals: 0,
        percentileKey: null
      },
      { 
        key: 'balls', 
        label: 'Balls', 
        higherBetter: true, 
        decimals: 0,
        percentileKey: null
      },
      { 
        key: 'wickets', 
        label: 'Wickets', 
        higherBetter: true, 
        decimals: 0,
        percentileKey: null
      },
      { 
        key: 'bowling_average', 
        label: 'Average', 
        higherBetter: false, 
        decimals: 2,
        percentileKey: 'normalized_average'
      },
      { 
        key: 'bowling_strike_rate', 
        label: 'Strike Rate', 
        higherBetter: false, 
        decimals: 2,
        percentileKey: 'normalized_strike_rate'
      },
      { 
        key: 'economy_rate', 
        label: 'Economy', 
        higherBetter: false, 
        decimals: 2,
        percentileKey: 'normalized_economy'
      }
    ];

    const phases = ['powerplay', 'middle_overs', 'death_overs'];
    
    return (
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Phase</strong></TableCell>
              <TableCell><strong>Metric</strong></TableCell>
              {teams.map(team => (
                <TableCell key={team.id} align="center"><strong>{team.label}</strong></TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {phases.map(phase => 
              metrics.map((metric, metricIndex) => {
                const values = teams.map(team => 
                  getValue(team.bowlingPhaseStats?.[phase], metric.key, metric.percentileKey)
                );
                
                return (
                  <TableRow key={`${phase}-${metric.key}`}>
                    {metricIndex === 0 && (
                      <TableCell rowSpan={metrics.length} sx={{ verticalAlign: 'top', pt: 2 }}>
                        <Chip 
                          label={phase.replace('_', ' ').toUpperCase()} 
                          size="small" 
                          color="secondary"
                        />
                      </TableCell>
                    )}
                    <TableCell>{metric.label}</TableCell>
                    {teams.map((team, teamIndex) => {
                      const value = getValue(team.bowlingPhaseStats?.[phase], metric.key, metric.percentileKey);
                      return (
                        <TableCell 
                          key={team.id} 
                          align="center"
                          sx={getCellColorStyle(value, metric.higherBetter, values)}
                        >
                          {formatValue(value, metric.decimals)}
                          {showPercentiles && metric.percentileKey && value > 0 ? '%' : ''}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Batting order comparison
  const renderBattingOrderComparison = () => {
    // Get all unique batting positions across all teams
    const allPositions = new Set();
    teams.forEach(team => {
      if (team.battingOrder?.batting_order) {
        team.battingOrder.batting_order.forEach(player => {
          if (player.primary_batting_position) {
            allPositions.add(player.primary_batting_position);
          }
        });
      }
    });
    
    const sortedPositions = Array.from(allPositions).sort((a, b) => a - b);
    
    return (
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Position</strong></TableCell>
              {teams.map(team => (
                <TableCell key={team.id} align="center"><strong>{team.label}</strong></TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedPositions.map(position => (
              <TableRow key={position}>
                <TableCell>
                  <Chip 
                    label={`${position}`} 
                    size="small" 
                    color="primary"
                  />
                </TableCell>
                {teams.map(team => {
                  const player = team.battingOrder?.batting_order?.find(
                    p => p.primary_batting_position === position
                  );
                  
                  return (
                    <TableCell key={team.id} align="center">
                      {player ? (
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {player.player}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Avg: {formatValue(player.overall?.average, 2)} | 
                            SR: {formatValue(player.overall?.strike_rate, 2)}
                          </Typography>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">-</Typography>
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Bowling order comparison
  const renderBowlingOrderComparison = () => {
    const phases = ['powerplay', 'middle_overs', 'death_overs'];
    
    return (
      <Box>
        {phases.map(phase => {
          // Get all players who bowl in this phase across all teams
          const phasePlayers = new Map();
          
          teams.forEach(team => {
            if (team.bowlingOrder?.bowling_order) {
              team.bowlingOrder.bowling_order.forEach(player => {
                const phaseData = player[phase];
                if (phaseData && phaseData.balls > 0) {
                  if (!phasePlayers.has(team.id)) {
                    phasePlayers.set(team.id, []);
                  }
                  phasePlayers.get(team.id).push({
                    name: player.player,
                    ...phaseData,
                    overCombo: player.most_frequent_overs || 'N/A'
                  });
                }
              });
            }
          });
          
          return (
            <Box key={phase} sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                {phase.replace('_', ' ').toUpperCase()} Bowling
              </Typography>
              
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Player Rank</strong></TableCell>
                      {teams.map(team => (
                        <TableCell key={team.id} align="center"><strong>{team.label}</strong></TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {[1, 2, 3, 4, 5].map(rank => (
                      <TableRow key={rank}>
                        <TableCell>
                          <Chip 
                            label={`${rank}`} 
                            size="small" 
                            color="secondary"
                          />
                        </TableCell>
                        {teams.map(team => {
                          const teamPlayers = phasePlayers.get(team.id) || [];
                          // Sort by balls bowled descending to get main bowlers
                          const sortedPlayers = teamPlayers.sort((a, b) => b.balls - a.balls);
                          const player = sortedPlayers[rank - 1];
                          
                          return (
                            <TableCell key={team.id} align="center">
                              {player ? (
                                <Box>
                                  <Typography variant="body2" fontWeight="bold">
                                    {player.name}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    Econ: {formatValue(player.economy, 2)} | 
                                    Balls: {formatValue(player.balls, 0)}
                                  </Typography>
                                  <Typography variant="caption" display="block" color="text.secondary">
                                    Overs: {player.overCombo}
                                  </Typography>
                                </Box>
                              ) : (
                                <Typography variant="body2" color="text.secondary">-</Typography>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          );
        })}
      </Box>
    );
  };

  // Info content for different tabs
  const getInfoContent = (tab) => {
    switch(tab) {
      case 2: // Batting Order
        return {
          title: "Batting Order Structure Comparison",
          content: [
            "This table shows how each team structures their batting lineup by comparing players at each batting position.",
            "Each row represents a batting position (1, 2, 3, etc.) and shows which player typically bats at that position for each team.",
            "The statistics shown are the player's overall average and strike rate in that position during the selected time period.",
            "Use this to compare team strategies - some teams prefer aggressive openers, others prefer stability at the top.",
            "You can analyze middle-order depth, finishing capabilities, and overall batting balance across teams."
          ]
        };
      case 3: // Bowling Order
        return {
          title: "Bowling Order Structure Comparison",
          content: [
            "This table shows how each team structures their bowling attack across different phases of the innings.",
            "Players are ranked by the number of balls they bowl in each phase, with 1 being the primary bowler for that phase.",
            "The 'Overs' field shows the most frequent over combinations when this bowler typically operates.",
            "Economy rate and balls bowled help you understand each bowler's role and effectiveness in that phase.",
            "Use this to analyze team bowling strategies - who they trust in the powerplay, middle overs, and death overs.",
            "Compare how different teams utilize their bowling resources and identify tactical patterns."
          ]
        };
      default:
        return null;
    }
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Tabs value={currentTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
        <Tab label="Batting Performance" />
        <Tab label="Bowling Performance" />
        <Tab label="Batting Order" />
        <Tab label="Bowling Order" />
      </Tabs>

      {currentTab === 0 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Phase-wise Batting Performance Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {showPercentiles ? 'Showing SQL percentiles (0-100 scale)' : 'Showing absolute values'}
            </Typography>
            {renderBattingPhaseComparison()}
          </CardContent>
        </Card>
      )}

      {currentTab === 1 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Phase-wise Bowling Performance Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {showPercentiles ? 'Showing SQL percentiles (0-100 scale)' : 'Showing absolute values'}
            </Typography>
            {renderBowlingPhaseComparison()}
          </CardContent>
        </Card>
      )}

      {currentTab === 2 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Typography variant="h6">
                Batting Order Structure Comparison
              </Typography>
              <IconButton 
                size="small" 
                onClick={() => handleInfoClick(getInfoContent(2))}
                color="primary"
              >
                <InfoIcon fontSize="small" />
              </IconButton>
            </Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Comparing how each team structures their batting order by position
            </Typography>
            {renderBattingOrderComparison()}
          </CardContent>
        </Card>
      )}

      {currentTab === 3 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Typography variant="h6">
                Bowling Order Structure Comparison
              </Typography>
              <IconButton 
                size="small" 
                onClick={() => handleInfoClick(getInfoContent(3))}
                color="primary"
              >
                <InfoIcon fontSize="small" />
              </IconButton>
            </Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Comparing how each team structures their bowling across different phases
            </Typography>
            {renderBowlingOrderComparison()}
          </CardContent>
        </Card>
      )}

      {/* Info Dialog */}
      <Dialog 
        open={infoDialogOpen} 
        onClose={handleInfoClose}
        maxWidth="md"
        fullWidth
      >
        {infoDialogContent && (
          <>
            <DialogTitle>{infoDialogContent.title}</DialogTitle>
            <DialogContent>
              <List>
                {infoDialogContent.content.map((item, index) => (
                  <ListItem key={index} sx={{ pl: 0 }}>
                    <ListItemText 
                      primary={`• ${item}`}
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                  </ListItem>
                ))}
              </List>
            </DialogContent>
            <DialogActions>
              <Button onClick={handleInfoClose} color="primary">
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default TeamComparisonTable;