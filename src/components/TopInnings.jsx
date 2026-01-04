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
import { EmptyState } from './ui';
import { spacing } from '../theme/designSystem';

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
        mb: isMobile ? `${spacing.md}px` : `${spacing.lg}px`,
        gap: `${spacing.sm}px`,
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

      {processedInnings.length === 0 ? (
        <EmptyState
          title="No innings match these filters"
          description="Adjust filters or expand the date range to see innings."
          isMobile={isMobile}
          minHeight={isMobile ? 240 : 280}
        />
      ) : (
      <TableContainer sx={{ width: '100%', overflowX: 'auto' }}>
        <Table size={isMobile ? "small" : "medium"} sx={{
          tableLayout: 'fixed',
          width: '100%',
          '& .MuiTableCell-root': {
            borderBottom: '1px solid rgba(224, 224, 224, 1)',
            py: isMobile ? `${spacing.xs}px` : `${spacing.md}px`,
            px: isMobile ? `${spacing.xs}px` : `${spacing.base}px`
          }
        }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>
                <Typography variant={isMobile ? 'caption' : 'body2'}>Date</Typography>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>
                <Typography variant={isMobile ? 'caption' : 'body2'}>Score</Typography>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>
                <Typography variant={isMobile ? 'caption' : 'body2'}>
                  {isMobile ? 'Opp' : 'Opposition'}
                </Typography>
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 600 }}>
                <Typography variant={isMobile ? 'caption' : 'body2'}>SR</Typography>
              </TableCell>
              {!isMobile && (
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  <Typography variant="body2">SR Diff</Typography>
                </TableCell>
              )}
              {!isMobile && (
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  <Typography variant="body2">% Team</Typography>
                </TableCell>
              )}
              {!isMobile && (
                <TableCell sx={{ fontWeight: 600 }}>
                  <Typography variant="body2">Context</Typography>
                </TableCell>
              )}
              {!isMobile && (
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  <Typography variant="body2">Winner</Typography>
                </TableCell>
              )}
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
                  <Typography variant={isMobile ? 'caption' : 'body2'}>
                    {isMobile
                      ? inning.date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
                      : inning.date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
                    }
                  </Typography>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <Typography variant={isMobile ? 'caption' : 'body2'}>
                    {inning.runs}({inning.balls_faced})
                  </Typography>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: isMobile ? 60 : 'auto' }}>
                  <Typography variant={isMobile ? 'caption' : 'body2'}>
                    {isMobile ? inning.bowling_team.substring(0, 3).toUpperCase() : inning.bowling_team}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant={isMobile ? 'caption' : 'body2'}>
                    {inning.strike_rate.toFixed(1)}
                  </Typography>
                </TableCell>
                {!isMobile && (
                  <TableCell align="right">
                    <Typography variant="body2">{inning.team_comparison.sr_diff.toFixed(1)}</Typography>
                  </TableCell>
                )}
                {!isMobile && (
                  <TableCell align="right">
                    <Typography variant="body2">
                      {inning.runPercentage.toFixed(1)}% ({inning.runs}/{inning.totalTeamRuns})
                    </Typography>
                  </TableCell>
                )}
                {!isMobile && (
                  <TableCell>
                    <Typography variant="body2">{inning.venue}, {inning.competition}</Typography>
                  </TableCell>
                )}
                {!isMobile && (
                  <TableCell align="right">
                    <Typography variant="body2">{inning.winner}</Typography>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      )}
    </Wrapper>
  );
};

export default TopInnings;
