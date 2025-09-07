import React from 'react';
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
  Paper
} from '@mui/material';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer
} from 'recharts';

const transformTeamBowlingPhaseData = (bowlingPhaseStats) => {
  if (!bowlingPhaseStats) return [];

  // Create radar chart data with 9 vertices using normalized values (0-100 scale)
  // For bowling, higher percentile = better performance (lower bowling avg/SR/economy)
  return [
    {
      phase: 'PP Avg',
      value: bowlingPhaseStats.powerplay?.normalized_average || 50,
      absoluteValue: bowlingPhaseStats.powerplay?.bowling_average || 0
    },
    {
      phase: 'PP SR',
      value: bowlingPhaseStats.powerplay?.normalized_strike_rate || 50,
      absoluteValue: bowlingPhaseStats.powerplay?.bowling_strike_rate || 0
    },
    {
      phase: 'PP Econ',
      value: bowlingPhaseStats.powerplay?.normalized_economy || 50,
      absoluteValue: bowlingPhaseStats.powerplay?.economy_rate || 0
    },
    {
      phase: 'Mid Avg',
      value: bowlingPhaseStats.middle_overs?.normalized_average || 50,
      absoluteValue: bowlingPhaseStats.middle_overs?.bowling_average || 0
    },
    {
      phase: 'Mid SR',
      value: bowlingPhaseStats.middle_overs?.normalized_strike_rate || 50,
      absoluteValue: bowlingPhaseStats.middle_overs?.bowling_strike_rate || 0
    },
    {
      phase: 'Mid Econ',
      value: bowlingPhaseStats.middle_overs?.normalized_economy || 50,
      absoluteValue: bowlingPhaseStats.middle_overs?.economy_rate || 0
    },
    {
      phase: 'Death Avg',
      value: bowlingPhaseStats.death_overs?.normalized_average || 50,
      absoluteValue: bowlingPhaseStats.death_overs?.bowling_average || 0
    },
    {
      phase: 'Death SR',
      value: bowlingPhaseStats.death_overs?.normalized_strike_rate || 50,
      absoluteValue: bowlingPhaseStats.death_overs?.bowling_strike_rate || 0
    },
    {
      phase: 'Death Econ',
      value: bowlingPhaseStats.death_overs?.normalized_economy || 50,
      absoluteValue: bowlingPhaseStats.death_overs?.economy_rate || 0
    }
  ];
};

const createBowlingTableData = (bowlingPhaseStats) => {
  if (!bowlingPhaseStats) return [];

  return [
    {
      phase: 'Powerplay (1-6)',
      runs: bowlingPhaseStats.powerplay?.runs || 0,
      balls: bowlingPhaseStats.powerplay?.balls || 0,
      wickets: bowlingPhaseStats.powerplay?.wickets || 0,
      bowlingAverage: bowlingPhaseStats.powerplay?.bowling_average?.toFixed(2) || '0.00',
      bowlingStrikeRate: bowlingPhaseStats.powerplay?.bowling_strike_rate?.toFixed(2) || '0.00',
      economyRate: bowlingPhaseStats.powerplay?.economy_rate?.toFixed(2) || '0.00',
      normalizedAvg: bowlingPhaseStats.powerplay?.normalized_average?.toFixed(1) || '50.0',
      normalizedSR: bowlingPhaseStats.powerplay?.normalized_strike_rate?.toFixed(1) || '50.0',
      normalizedEcon: bowlingPhaseStats.powerplay?.normalized_economy?.toFixed(1) || '50.0'
    },
    {
      phase: 'Middle Overs (7-15)',
      runs: bowlingPhaseStats.middle_overs?.runs || 0,
      balls: bowlingPhaseStats.middle_overs?.balls || 0,
      wickets: bowlingPhaseStats.middle_overs?.wickets || 0,
      bowlingAverage: bowlingPhaseStats.middle_overs?.bowling_average?.toFixed(2) || '0.00',
      bowlingStrikeRate: bowlingPhaseStats.middle_overs?.bowling_strike_rate?.toFixed(2) || '0.00',
      economyRate: bowlingPhaseStats.middle_overs?.economy_rate?.toFixed(2) || '0.00',
      normalizedAvg: bowlingPhaseStats.middle_overs?.normalized_average?.toFixed(1) || '50.0',
      normalizedSR: bowlingPhaseStats.middle_overs?.normalized_strike_rate?.toFixed(1) || '50.0',
      normalizedEcon: bowlingPhaseStats.middle_overs?.normalized_economy?.toFixed(1) || '50.0'
    },
    {
      phase: 'Death Overs (16-20)',
      runs: bowlingPhaseStats.death_overs?.runs || 0,
      balls: bowlingPhaseStats.death_overs?.balls || 0,
      wickets: bowlingPhaseStats.death_overs?.wickets || 0,
      bowlingAverage: bowlingPhaseStats.death_overs?.bowling_average?.toFixed(2) || '0.00',
      bowlingStrikeRate: bowlingPhaseStats.death_overs?.bowling_strike_rate?.toFixed(2) || '0.00',
      economyRate: bowlingPhaseStats.death_overs?.economy_rate?.toFixed(2) || '0.00',
      normalizedAvg: bowlingPhaseStats.death_overs?.normalized_average?.toFixed(1) || '50.0',
      normalizedSR: bowlingPhaseStats.death_overs?.normalized_strike_rate?.toFixed(1) || '50.0',
      normalizedEcon: bowlingPhaseStats.death_overs?.normalized_economy?.toFixed(1) || '50.0'
    }
  ];
};

// Custom tooltip for the bowling radar chart
const CustomBowlingTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <Box sx={{ 
        backgroundColor: 'white', 
        p: 1, 
        border: 1, 
        borderColor: 'grey.300',
        borderRadius: 1,
        boxShadow: 2
      }}>
        <Typography variant="body2" fontWeight="bold">{label}</Typography>
        <Typography variant="body2">
          Percentile: {data.value.toFixed(1)}
        </Typography>
        <Typography variant="body2">
          Actual: {data.absoluteValue.toFixed(2)}
        </Typography>
      </Box>
    );
  }
  return null;
};

const TeamBowlingPhasePerformanceRadar = ({ bowlingPhaseStats, teamName }) => {
  const radarData = transformTeamBowlingPhaseData(bowlingPhaseStats);
  const tableData = createBowlingTableData(bowlingPhaseStats);
  
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {teamName} - Phase-wise Bowling Performance
        </Typography>
        
        {/* Context Information */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Normalized against: {bowlingPhaseStats?.context || 'Unknown'} 
          {bowlingPhaseStats?.benchmark_teams ? `(${bowlingPhaseStats.benchmark_teams} teams)` : ''}
          • Values shown as percentiles (0-100 scale, higher = better bowling)
        </Typography>
        
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', md: '350px 1fr' }, 
          gap: 2,
          alignItems: 'start'
        }}>
          {/* Radar Chart */}
          <Box sx={{ width: '100%', height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart outerRadius={100} data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                <PolarGrid />
                <PolarAngleAxis 
                  dataKey="phase" 
                  tick={{ fontSize: 11 }}
                />
                <PolarRadiusAxis 
                  tick={{ fontSize: 10 }}
                  domain={[0, 100]}
                  tickCount={6}
                />
                <Radar
                  name="Percentile"
                  dataKey="value"
                  stroke="#e74c3c"
                  fill="#e74c3c"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <CustomBowlingTooltip />
              </RadarChart>
            </ResponsiveContainer>
          </Box>
          
          {/* Data Table */}
          <TableContainer component={Paper} sx={{ maxHeight: 350 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Phase</strong></TableCell>
                  <TableCell align="right"><strong>Runs</strong></TableCell>
                  <TableCell align="right"><strong>Balls</strong></TableCell>
                  <TableCell align="right"><strong>Wkts</strong></TableCell>
                  <TableCell align="right"><strong>B.Avg</strong></TableCell>
                  <TableCell align="right"><strong>B.SR</strong></TableCell>
                  <TableCell align="right"><strong>Econ</strong></TableCell>
                  <TableCell align="right"><strong>Avg %ile</strong></TableCell>
                  <TableCell align="right"><strong>SR %ile</strong></TableCell>
                  <TableCell align="right"><strong>Eco %ile</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tableData.map((row, index) => (
                  <TableRow key={index} hover>
                    <TableCell component="th" scope="row">
                      <Typography variant="body2" fontWeight="medium">
                        {row.phase}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">{row.runs}</TableCell>
                    <TableCell align="right">{row.balls}</TableCell>
                    <TableCell align="right">{row.wickets}</TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.bowlingAverage) <= 25 ? 'success.main' : 'text.primary'}
                        fontWeight="medium"
                      >
                        {row.bowlingAverage}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.bowlingStrikeRate) <= 18 ? 'success.main' : 'text.primary'}
                        fontWeight="medium"
                      >
                        {row.bowlingStrikeRate}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.economyRate) <= 8 ? 'success.main' : 'text.primary'}
                        fontWeight="medium"
                      >
                        {row.economyRate}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.normalizedAvg) >= 75 ? 'success.main' : 
                               parseFloat(row.normalizedAvg) >= 50 ? 'warning.main' : 'error.main'}
                        fontWeight="medium"
                      >
                        {row.normalizedAvg}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.normalizedSR) >= 75 ? 'success.main' : 
                               parseFloat(row.normalizedSR) >= 50 ? 'warning.main' : 'error.main'}
                        fontWeight="medium"
                      >
                        {row.normalizedSR}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.normalizedEcon) >= 75 ? 'success.main' : 
                               parseFloat(row.normalizedEcon) >= 50 ? 'warning.main' : 'error.main'}
                        fontWeight="medium"
                      >
                        {row.normalizedEcon}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
        
        {/* Summary Stats */}
        <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="body2" color="text.secondary">
            Total Matches: {bowlingPhaseStats?.total_matches || 0}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Note: For bowling stats, lower values (average, strike rate, economy) indicate better performance.
            Percentiles show relative performance where higher percentile = better bowling.
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TeamBowlingPhasePerformanceRadar;
