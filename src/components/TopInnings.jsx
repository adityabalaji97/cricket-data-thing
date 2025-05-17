import React, { useMemo, useState } from 'react';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Box
} from '@mui/material';

const TopInnings = ({ innings, count = 10 }) => {
  const [viewMode, setViewMode] = useState('topScoring');

  const processedInnings = useMemo(() => {
    if (!innings?.length) return [];
    
    const mapped = innings.map(inning => {
      const totalTeamRuns = inning.runs + inning.team_comparison.team_runs_excl_batter;
      const runPercentage = (inning.runs / totalTeamRuns) * 100;
      
      const impactScore = (
        (runPercentage / 100) * 0 +             
        ((inning.team_comparison.sr_diff + 50) / 100) * 0 + 
        (inning.runs / 100) * 1 +               
        (inning.strike_rate / 200) * 0          
      );
      
      return {
        ...inning,
        runPercentage,
        impactScore,
        totalTeamRuns,
        date: new Date(inning.date)
      };
    });

    // Sort based on view mode
    if (viewMode === 'topScoring') {
      return mapped
        .sort((a, b) => b.runs - a.runs)
        .slice(0, count);
    } else {
      return mapped
        .sort((a, b) => b.date - a.date)
        .slice(0, count);
    }
  }, [innings, count, viewMode]);

  const handleViewChange = (event, newView) => {
    if (newView !== null) {
      setViewMode(newView);
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 500 }}>
          {viewMode === 'topScoring' ? 'Top Scoring Innings' : 'Recent Form'}
        </Typography>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewChange}
          size="small"
        >
          <ToggleButton value="topScoring">
            Top Scoring
          </ToggleButton>
          <ToggleButton value="recentForm">
            Recent Form
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
      
      <TableContainer>
        <Table size="medium" sx={{
          '& .MuiTableCell-root': {
            borderBottom: '1px solid rgba(224, 224, 224, 1)',
            py: 1.5
          }
        }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Score</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Opposition</TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>SR</TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>SR Diff</TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>% Team</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Context</TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>Winner</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {processedInnings.map((inning, idx) => (
              <TableRow 
                key={`${inning.match_id}-${idx}`}
                hover
                sx={{
                  '&:last-child td': { borderBottom: 0 }
                }}
              >
                <TableCell>
                  {inning.date.toLocaleDateString('en-GB', { 
                    day: 'numeric', 
                    month: 'short', 
                    year: 'numeric'
                  })}
                </TableCell>
                <TableCell>{inning.runs}({inning.balls_faced})</TableCell>
                <TableCell>{inning.bowling_team}</TableCell>
                <TableCell align="right">{inning.strike_rate.toFixed(1)}</TableCell>
                <TableCell align="right">{inning.team_comparison.sr_diff.toFixed(1)}</TableCell>
                <TableCell align="right">
                  {inning.runPercentage.toFixed(1)}% ({inning.runs}/{inning.totalTeamRuns})
                </TableCell>
                <TableCell>{inning.venue}, {inning.competition}</TableCell>
                <TableCell align="right">{inning.winner}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default TopInnings;