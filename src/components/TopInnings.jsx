import React, { useMemo, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Box
} from '@mui/material';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';

const TopInnings = ({ innings, count = 10, isMobile = false, wrapInCard = true }) => {
  const [viewMode, setViewMode] = useState('topScoring');
  const Wrapper = wrapInCard ? Card : Box;
  const wrapperProps = wrapInCard ? { isMobile } : { sx: { width: '100%' } };

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

  const filterConfig = [
    {
      key: 'view',
      label: 'View',
      options: [
        { value: 'topScoring', label: 'Top Scoring' },
        { value: 'recentForm', label: 'Recent Form' }
      ]
    }
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'view') setViewMode(value);
  };

  return (
    <Wrapper {...wrapperProps}>
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: isMobile ? 1.5 : 3,
        gap: 1,
        flexWrap: isMobile ? 'wrap' : 'nowrap'
      }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, flexShrink: 0 }}>
          {viewMode === 'topScoring' ? 'Top Innings' : 'Recent Form'}
        </Typography>
        <Box sx={{ flexShrink: 1, minWidth: 0 }}>
          <FilterBar
            filters={filterConfig}
            activeFilters={{ view: viewMode }}
            onFilterChange={handleFilterChange}
            isMobile={isMobile}
          />
        </Box>
      </Box>

      <TableContainer>
        <Table size={isMobile ? "small" : "medium"} sx={{
          '& .MuiTableCell-root': {
            borderBottom: '1px solid rgba(224, 224, 224, 1)',
            py: isMobile ? 0.75 : 1.5,
            px: isMobile ? 0.5 : 2,
            fontSize: isMobile ? '0.7rem' : undefined
          }
        }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>{isMobile ? 'Date' : 'Date'}</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Score</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>{isMobile ? 'Opp' : 'Opposition'}</TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>SR</TableCell>
              {!isMobile && <TableCell align="right" sx={{ fontWeight: 600 }}>SR Diff</TableCell>}
              {!isMobile && <TableCell align="right" sx={{ fontWeight: 600 }}>% Team</TableCell>}
              {!isMobile && <TableCell sx={{ fontWeight: 600 }}>Context</TableCell>}
              {!isMobile && <TableCell align="right" sx={{ fontWeight: 600 }}>Winner</TableCell>}
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
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  {isMobile
                    ? inning.date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
                    : inning.date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
                  }
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>{inning.runs}({inning.balls_faced})</TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: isMobile ? 60 : 'auto' }}>
                  {isMobile ? inning.bowling_team.substring(0, 3).toUpperCase() : inning.bowling_team}
                </TableCell>
                <TableCell align="right">{inning.strike_rate.toFixed(1)}</TableCell>
                {!isMobile && <TableCell align="right">{inning.team_comparison.sr_diff.toFixed(1)}</TableCell>}
                {!isMobile && (
                  <TableCell align="right">
                    {inning.runPercentage.toFixed(1)}% ({inning.runs}/{inning.totalTeamRuns})
                  </TableCell>
                )}
                {!isMobile && <TableCell>{inning.venue}, {inning.competition}</TableCell>}
                {!isMobile && <TableCell align="right">{inning.winner}</TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Wrapper>
  );
};

export default TopInnings;
