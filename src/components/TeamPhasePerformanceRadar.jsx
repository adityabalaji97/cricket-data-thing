import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  
} from '@mui/material';
import ScrollTable from './ui/ScrollTable';
import PhasePercentileBars from './charts/PhasePercentileBars';

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

const TeamPhasePerformanceRadar = ({ phaseStats, teamName }) => {
  const tableData = createTableData(phaseStats);
  
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {teamName} - Phase-wise Batting Performance
        </Typography>
        
        {/* Context Information */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Normalized against: {phaseStats?.context || 'Unknown'} 
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
          <Box>
            {/* Percentile bars around the median replace the radar (rotated axis, 10px ticks). */}
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>Batting percentile by phase</Typography>
            <PhasePercentileBars phaseStats={phaseStats} metrics={[{ key: 'normalized_average', label: 'Average' }, { key: 'normalized_strike_rate', label: 'Strike rate' }]} ariaLabel="Batting percentile by phase" />
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              Centre line = median team; right of it is better.
            </Typography>
          </Box>
          
          {/* Data Table */}
          <ScrollTable paper sx={{ maxHeight: 350 }}>
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
          </ScrollTable>
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
