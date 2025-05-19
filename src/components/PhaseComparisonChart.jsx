import React from 'react';
import { 
  Paper, 
  Typography, 
  Box, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow
} from '@mui/material';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from 'recharts';

// Colors for different batters
const COLORS = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', 
  '#00C49F', '#FFBB28', '#FF8042', '#a4de6c', '#d0ed57'
];

const PhaseComparisonChart = ({ batters }) => {
  // Check if we have valid data
  if (!batters || batters.length === 0 || !batters.some(b => b.stats)) {
    return (
      <Paper elevation={2} sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Phase Performance Comparison
        </Typography>
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No phase data available for the selected batters.
          </Typography>
        </Box>
      </Paper>
    );
  }
  
  // Prepare data for the radar chart
  const prepareChartData = () => {
    // Define metrics we want to compare, in the specified order
    const metrics = [
      { name: 'Powerplay Avg', key: 'powerplay_avg', max: 70 },
      { name: 'Powerplay SR', key: 'powerplay_sr', max: 160 },
      { name: 'Middle Overs Avg', key: 'middle_avg', max: 80 },
      { name: 'Middle Overs SR', key: 'middle_sr', max: 150 },
      { name: 'Death Overs Avg', key: 'death_avg', max: 40 },
      { name: 'Death Overs SR', key: 'death_sr', max: 200 },
    ];
    
    // First, extract all metrics for each batter
    const batterMetrics = batters.map(batter => {
      if (!batter.stats) return { name: batter.label };
      
      // Based on the correct structure shown in the logs
      const phase_stats = batter.stats.phase_stats || {};
      
      // Extract overall phase data
      const overall = phase_stats.overall || {};
      const powerplay = overall.powerplay || {};
      const middle = overall.middle || {};
      const death = overall.death || {};
      
      const metrics = {
        name: batter.label,
        powerplay_avg: powerplay.average || 0,
        powerplay_sr: powerplay.strike_rate || 0,
        middle_avg: middle.average || 0,
        middle_sr: middle.strike_rate || 0,
        death_avg: death.average || 0,
        death_sr: death.strike_rate || 0,
      };
      
      return metrics;
    });
    
    // Now create data points for the radar chart
    return metrics.map(metric => {
      const dataPoint = { 
        metric: metric.name,
        metricKey: metric.key, // Add the key for reference
        maxValue: metric.max   // Add the max value for reference
      };
      
      batterMetrics.forEach(batterMetric => {
        if (!batterMetric) return;
        
        const actualValue = batterMetric[metric.key] || 0;
        const formattedValue = Number(actualValue.toFixed(2));
        
        // Store both the normalized value (for display) and the actual value (for tooltip)
        dataPoint[`${batterMetric.name}_actual`] = formattedValue;
        
        // Normalize the value as a percentage of the maximum, rounded to 2 decimal places
        dataPoint[batterMetric.name] = Number(((formattedValue / metric.max) * 100).toFixed(2));
      });
      
      return dataPoint;
    });
  };
  
  const radarData = prepareChartData();
  
  // Helper function to get text color based on values - using pastel colors
  const getCellColorStyle = (value, isHigherBetter, allValues) => {
    if (allValues.length <= 1) return {}; // No color for single batter
    
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const range = max - min;
    
    // Avoid division by zero
    if (range === 0) return {};
    
    // Calculate a value between 0 and 1, where 1 is the best
    let normalizedValue;
    if (isHigherBetter) {
      normalizedValue = (value - min) / range;
    } else {
      normalizedValue = (max - value) / range;
    }
    
    // Pastel color palette for better vs worse metrics
    // Best values will be pastel green, worst values will be pastel red
    if (normalizedValue >= 0.7) {
      // Good - pastel green
      return { color: '#4CAF50', fontWeight: 'bold' };
    } else if (normalizedValue >= 0.4) {
      // Average - pastel yellow/amber
      return { color: '#FFC107' };
    } else {
      // Poor - pastel red
      return { color: '#F44336', fontWeight: 'bold' };
    }
  };
  
  // Prepare a detailed table of phase stats
  const renderStatsTable = () => {
    return (
      <TableContainer component={Paper} sx={{ mt: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Phase</TableCell>
              {batters.map(batter => (
                batter.stats && (
                  <TableCell key={batter.id} align="center">{batter.label}</TableCell>
                )
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Powerplay */}
            <TableRow>
              <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                Powerplay
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Average</TableCell>
              {(() => {
                const battingAverages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const powerplay = overall.powerplay || {};
                    return powerplay.average || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const powerplay = overall.powerplay || {};
                  const avg = powerplay.average || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pp-avg`} 
                      align="center" 
                      sx={getCellColorStyle(avg, true, battingAverages)}
                    >
                      {avg.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Strike Rate</TableCell>
              {(() => {
                const strikeRates = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const powerplay = overall.powerplay || {};
                    return powerplay.strike_rate || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const powerplay = overall.powerplay || {};
                  const sr = powerplay.strike_rate || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pp-sr`} 
                      align="center" 
                      sx={getCellColorStyle(sr, true, strikeRates)}
                    >
                      {sr.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Boundary %</TableCell>
              {(() => {
                const boundaryPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const powerplay = overall.powerplay || {};
                    return powerplay.boundary_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const powerplay = overall.powerplay || {};
                  const boundaryPercent = powerplay.boundary_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pp-boundary`} 
                      align="center" 
                      sx={getCellColorStyle(boundaryPercent, true, boundaryPercentages)}
                    >
                      {boundaryPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Dot %</TableCell>
              {(() => {
                const dotPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const powerplay = overall.powerplay || {};
                    return powerplay.dot_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const powerplay = overall.powerplay || {};
                  const dotPercent = powerplay.dot_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pp-dot`} 
                      align="center" 
                      sx={getCellColorStyle(dotPercent, false, dotPercentages)}
                    >
                      {dotPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            
            {/* Middle Overs */}
            <TableRow>
              <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                Middle Overs
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Average</TableCell>
              {(() => {
                const battingAverages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const middle = overall.middle || {};
                    return middle.average || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const middle = overall.middle || {};
                  const avg = middle.average || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-middle-avg`} 
                      align="center" 
                      sx={getCellColorStyle(avg, true, battingAverages)}
                    >
                      {avg.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Strike Rate</TableCell>
              {(() => {
                const strikeRates = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const middle = overall.middle || {};
                    return middle.strike_rate || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const middle = overall.middle || {};
                  const sr = middle.strike_rate || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-middle-sr`} 
                      align="center" 
                      sx={getCellColorStyle(sr, true, strikeRates)}
                    >
                      {sr.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Boundary %</TableCell>
              {(() => {
                const boundaryPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const middle = overall.middle || {};
                    return middle.boundary_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const middle = overall.middle || {};
                  const boundaryPercent = middle.boundary_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-middle-boundary`} 
                      align="center" 
                      sx={getCellColorStyle(boundaryPercent, true, boundaryPercentages)}
                    >
                      {boundaryPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Dot %</TableCell>
              {(() => {
                const dotPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const middle = overall.middle || {};
                    return middle.dot_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const middle = overall.middle || {};
                  const dotPercent = middle.dot_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-middle-dot`} 
                      align="center" 
                      sx={getCellColorStyle(dotPercent, false, dotPercentages)}
                    >
                      {dotPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            
            {/* Death Overs */}
            <TableRow>
              <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                Death Overs
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Average</TableCell>
              {(() => {
                const battingAverages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const death = overall.death || {};
                    return death.average || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const death = overall.death || {};
                  const avg = death.average || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-death-avg`} 
                      align="center" 
                      sx={getCellColorStyle(avg, true, battingAverages)}
                    >
                      {avg.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Strike Rate</TableCell>
              {(() => {
                const strikeRates = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const death = overall.death || {};
                    return death.strike_rate || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const death = overall.death || {};
                  const sr = death.strike_rate || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-death-sr`} 
                      align="center" 
                      sx={getCellColorStyle(sr, true, strikeRates)}
                    >
                      {sr.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Boundary %</TableCell>
              {(() => {
                const boundaryPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const death = overall.death || {};
                    return death.boundary_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const death = overall.death || {};
                  const boundaryPercent = death.boundary_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-death-boundary`} 
                      align="center" 
                      sx={getCellColorStyle(boundaryPercent, true, boundaryPercentages)}
                    >
                      {boundaryPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Dot %</TableCell>
              {(() => {
                const dotPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const overall = phase_stats.overall || {};
                    const death = overall.death || {};
                    return death.dot_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const overall = phase_stats.overall || {};
                  const death = overall.death || {};
                  const dotPercent = death.dot_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-death-dot`} 
                      align="center" 
                      sx={getCellColorStyle(dotPercent, false, dotPercentages)}
                    >
                      {dotPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            
            {/* Pace */}
            <TableRow>
              <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                vs Pace
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Average</TableCell>
              {(() => {
                const paceAverages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const pace = phase_stats.pace || {};
                    const overall = pace.overall || {};
                    return overall.average || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const pace = phase_stats.pace || {};
                  const overall = pace.overall || {};
                  const avg = overall.average || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pace-avg`} 
                      align="center" 
                      sx={getCellColorStyle(avg, true, paceAverages)}
                    >
                      {avg.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Strike Rate</TableCell>
              {(() => {
                const strikeRates = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const pace = phase_stats.pace || {};
                    const overall = pace.overall || {};
                    return overall.strike_rate || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const pace = phase_stats.pace || {};
                  const overall = pace.overall || {};
                  const sr = overall.strike_rate || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pace-sr`} 
                      align="center" 
                      sx={getCellColorStyle(sr, true, strikeRates)}
                    >
                      {sr.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Boundary %</TableCell>
              {(() => {
                const boundaryPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const pace = phase_stats.pace || {};
                    const overall = pace.overall || {};
                    return overall.boundary_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const pace = phase_stats.pace || {};
                  const overall = pace.overall || {};
                  const boundaryPercent = overall.boundary_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pace-boundary`} 
                      align="center" 
                      sx={getCellColorStyle(boundaryPercent, true, boundaryPercentages)}
                    >
                      {boundaryPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Dot %</TableCell>
              {(() => {
                const dotPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const pace = phase_stats.pace || {};
                    const overall = pace.overall || {};
                    return overall.dot_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const pace = phase_stats.pace || {};
                  const overall = pace.overall || {};
                  const dotPercent = overall.dot_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-pace-dot`} 
                      align="center" 
                      sx={getCellColorStyle(dotPercent, false, dotPercentages)}
                    >
                      {dotPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            
            {/* Spin */}
            <TableRow>
              <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                vs Spin
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Average</TableCell>
              {(() => {
                const spinAverages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const spin = phase_stats.spin || {};
                    const overall = spin.overall || {};
                    return overall.average || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const spin = phase_stats.spin || {};
                  const overall = spin.overall || {};
                  const avg = overall.average || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-spin-avg`} 
                      align="center" 
                      sx={getCellColorStyle(avg, true, spinAverages)}
                    >
                      {avg.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Strike Rate</TableCell>
              {(() => {
                const strikeRates = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const spin = phase_stats.spin || {};
                    const overall = spin.overall || {};
                    return overall.strike_rate || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const spin = phase_stats.spin || {};
                  const overall = spin.overall || {};
                  const sr = overall.strike_rate || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-spin-sr`} 
                      align="center" 
                      sx={getCellColorStyle(sr, true, strikeRates)}
                    >
                      {sr.toFixed(2)}
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Boundary %</TableCell>
              {(() => {
                const boundaryPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const spin = phase_stats.spin || {};
                    const overall = spin.overall || {};
                    return overall.boundary_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const spin = phase_stats.spin || {};
                  const overall = spin.overall || {};
                  const boundaryPercent = overall.boundary_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-spin-boundary`} 
                      align="center" 
                      sx={getCellColorStyle(boundaryPercent, true, boundaryPercentages)}
                    >
                      {boundaryPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
            <TableRow>
              <TableCell sx={{ pl: 3 }}>Dot %</TableCell>
              {(() => {
                const dotPercentages = batters
                  .filter(b => b.stats)
                  .map(batter => {
                    const phase_stats = batter.stats.phase_stats || {};
                    const spin = phase_stats.spin || {};
                    const overall = spin.overall || {};
                    return overall.dot_percentage || 0;
                  });
                
                return batters.map(batter => {
                  if (!batter.stats) return null;
                  
                  const phase_stats = batter.stats.phase_stats || {};
                  const spin = phase_stats.spin || {};
                  const overall = spin.overall || {};
                  const dotPercent = overall.dot_percentage || 0;
                  
                  return (
                    <TableCell 
                      key={`${batter.id}-spin-dot`} 
                      align="center" 
                      sx={getCellColorStyle(dotPercent, false, dotPercentages)}
                    >
                      {dotPercent.toFixed(2)}%
                    </TableCell>
                  );
                });
              })()}
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    );
  };
  
  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Phase Performance Comparison
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Compare batting performance across different phases
      </Typography>
      
      <Box sx={{ height: 400, width: '100%', mt: 2 }}>
        <ResponsiveContainer>
          <RadarChart outerRadius="80%" data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="metric" />
            <PolarRadiusAxis 
              domain={[0, 100]} 
              tick={false}
              axisLine={false}
              tickLine={false}
            />
            
            {batters.map((batter, index) => (
              batter.stats && (
                <Radar
                  key={batter.id}
                  name={batter.label}
                  dataKey={batter.label}
                  stroke={COLORS[index % COLORS.length]}
                  fill={COLORS[index % COLORS.length]}
                  fillOpacity={0.2}
                />
              )
            ))}
            
            <Legend />
            <Tooltip 
              formatter={(value, name, props) => {
                // Find the actual value using the batter name
                const actualKey = `${name}_actual`;
                const actualValue = props.payload[actualKey];
                
                // Get the metric key to determine appropriate unit
                const metricKey = props.payload.metricKey;
                const unit = metricKey.includes('sr') ? 'SR' : 'Avg';
                
                return [actualValue.toFixed(2), `${name} (${unit})`];
              }} 
              labelFormatter={(label) => label} // Keep the metric name as is
            />
          </RadarChart>
        </ResponsiveContainer>
      </Box>
      
      {renderStatsTable()}
    </Paper>
  );
};

export default PhaseComparisonChart;