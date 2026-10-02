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

const TeamBowlingPhasePerformanceRadar = ({ bowlingPhaseStats, teamName }) => {
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
          <Box>
            {/* Percentile bars around the median replace the radar (rotated axis, 10px ticks). */}
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>Bowling percentile by phase</Typography>
            <PhasePercentileBars phaseStats={bowlingPhaseStats} metrics={[{ key: 'normalized_average', label: 'Average' }, { key: 'normalized_strike_rate', label: 'Strike rate' }, { key: 'normalized_economy', label: 'Economy' }]} ariaLabel="Bowling percentile by phase" />
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
          </ScrollTable>
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
