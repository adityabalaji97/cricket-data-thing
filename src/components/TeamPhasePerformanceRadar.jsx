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

const transformTeamPhaseData = (phaseStats) => {
  if (!phaseStats) return [];

  // Create radar chart data with 6 vertices using normalized values (0-100 scale)
  return [
    {
      phase: 'PP Avg',
      value: phaseStats.powerplay?.normalized_average || 50,
      absoluteValue: phaseStats.powerplay?.average || 0
    },
    {
      phase: 'PP SR',
      value: phaseStats.powerplay?.normalized_strike_rate || 50,
      absoluteValue: phaseStats.powerplay?.strike_rate || 0
    },
    {
      phase: 'Mid Avg',
      value: phaseStats.middle_overs?.normalized_average || 50,
      absoluteValue: phaseStats.middle_overs?.average || 0
    },
    {
      phase: 'Mid SR',
      value: phaseStats.middle_overs?.normalized_strike_rate || 50,
      absoluteValue: phaseStats.middle_overs?.strike_rate || 0
    },
    {
      phase: 'Death Avg',
      value: phaseStats.death_overs?.normalized_average || 50,
      absoluteValue: phaseStats.death_overs?.average || 0
    },
    {
      phase: 'Death SR',
      value: phaseStats.death_overs?.normalized_strike_rate || 50,
      absoluteValue: phaseStats.death_overs?.strike_rate || 0
    }
  ];
};

const createTableData = (phaseStats) => {
  if (!phaseStats) return [];

  return [
    {
      phase: 'Powerplay (1-6)',
      runs: phaseStats.powerplay?.runs || 0,
      balls: phaseStats.powerplay?.balls || 0,
      wickets: phaseStats.powerplay?.wickets || 0,
      average: phaseStats.powerplay?.average?.toFixed(2) || '0.00',
      strikeRate: phaseStats.powerplay?.strike_rate?.toFixed(2) || '0.00',
      normalizedAvg: phaseStats.powerplay?.normalized_average?.toFixed(1) || '50.0',
      normalizedSR: phaseStats.powerplay?.normalized_strike_rate?.toFixed(1) || '50.0'
    },
    {
      phase: 'Middle Overs (7-15)',
      runs: phaseStats.middle_overs?.runs || 0,
      balls: phaseStats.middle_overs?.balls || 0,
      wickets: phaseStats.middle_overs?.wickets || 0,
      average: phaseStats.middle_overs?.average?.toFixed(2) || '0.00',
      strikeRate: phaseStats.middle_overs?.strike_rate?.toFixed(2) || '0.00',
      normalizedAvg: phaseStats.middle_overs?.normalized_average?.toFixed(1) || '50.0',
      normalizedSR: phaseStats.middle_overs?.normalized_strike_rate?.toFixed(1) || '50.0'
    },
    {
      phase: 'Death Overs (16-20)',
      runs: phaseStats.death_overs?.runs || 0,
      balls: phaseStats.death_overs?.balls || 0,
      wickets: phaseStats.death_overs?.wickets || 0,
      average: phaseStats.death_overs?.average?.toFixed(2) || '0.00',
      strikeRate: phaseStats.death_overs?.strike_rate?.toFixed(2) || '0.00',
      normalizedAvg: phaseStats.death_overs?.normalized_average?.toFixed(1) || '50.0',
      normalizedSR: phaseStats.death_overs?.normalized_strike_rate?.toFixed(1) || '50.0'
    }
  ];
};

// Custom tooltip for the radar chart
const CustomTooltip = ({ active, payload, label }) => {
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

const TeamPhasePerformanceRadar = ({ phaseStats, teamName }) => {
  const radarData = transformTeamPhaseData(phaseStats);
  const tableData = createTableData(phaseStats);
  
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {teamName} - Phase-wise Performance (Normalized)
        </Typography>
        
        {/* Context Information */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Benchmarked against: {phaseStats?.context || 'Unknown'} 
          {phaseStats?.benchmark_teams ? `(${phaseStats.benchmark_teams} teams)` : ''}
          • Values shown as percentiles (0-100 scale)
        </Typography>
        
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, 
          gap: 3,
          alignItems: 'start'
        }}>
          {/* Radar Chart */}
          <Box sx={{ width: '100%', height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart outerRadius={120} data={radarData}>
                <PolarGrid />
                <PolarAngleAxis 
                  dataKey="phase" 
                  tick={{ fontSize: 12 }}
                />
                <PolarRadiusAxis 
                  tick={{ fontSize: 10 }}
                  domain={[0, 100]}
                  tickCount={6}
                />
                <Radar
                  name="Percentile"
                  dataKey="value"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <CustomTooltip />
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
                  <TableCell align="right"><strong>Avg</strong></TableCell>
                  <TableCell align="right"><strong>SR</strong></TableCell>
                  <TableCell align="right"><strong>Avg %ile</strong></TableCell>
                  <TableCell align="right"><strong>SR %ile</strong></TableCell>
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
                        color={parseFloat(row.average) >= 30 ? 'success.main' : 'text.primary'}
                        fontWeight="medium"
                      >
                        {row.average}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        variant="body2" 
                        color={parseFloat(row.strikeRate) >= 130 ? 'success.main' : 'text.primary'}
                        fontWeight="medium"
                      >
                        {row.strikeRate}
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
        
        {/* Summary Stats */}
        <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="body2" color="text.secondary">
            Total Matches: {phaseStats?.total_matches || 0}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TeamPhasePerformanceRadar;
