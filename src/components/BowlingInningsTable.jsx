import React, { useState } from 'react';
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
  
  TableSortLabel,
  Button,
  ButtonGroup,
} from '@mui/material';
import ScrollTable from './ui/ScrollTable';
import { spacing, colors, borderRadius } from '../theme/designSystem';
import CondensedName from './common/CondensedName';
import useIsMobile from '../hooks/useIsMobile';
import DetailSheet from './ui/DetailSheet';

const BowlingInningsTable = ({ stats, wrapInCard = true }) => {
  // Phone layout from the shared hook: callers never passed isMobile, so phones got the desktop chart.
  const { isMobile } = useIsMobile();
  const [displayMode, setDisplayMode] = useState('topWickets');
  const [openInning, setOpenInning] = useState(null);
  const [sortConfig, setSortConfig] = useState({
    key: displayMode === 'topWickets' ? 'wickets' : 'date',
    direction: 'desc'
  });

  // Early return if no data is provided
  if (!stats || !stats.innings || stats.innings.length === 0) {
    return null;
  }

  // Function to format date in dd MMM yyyy format
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const options = { day: '2-digit', month: 'short', year: 'numeric' };
    return date.toLocaleDateString('en-GB', options);
  };

  // Process innings data
  const processInningsData = (innings) => {
    return innings.map(inning => ({
      date: new Date(inning.date),
      formattedDate: formatDate(inning.date),
      match_id: inning.match_id,
      venue: inning.venue,
      competition: inning.competition,
      bowling_team: inning.bowling_team,
      batting_team: inning.batting_team,
      winner: inning.winner,
      overs: parseFloat(inning.overs.toFixed(1)),
      balls: inning.balls,
      runs: inning.runs,
      wickets: inning.wickets,
      economy: parseFloat(inning.economy.toFixed(2)),
      maidens: inning.maidens,
      dots: inning.dots,
      dot_percentage: parseFloat((inning.dots / inning.balls * 100).toFixed(1)),
      result: inning.winner === inning.bowling_team ? 'Won' : inning.winner === inning.batting_team ? 'Lost' : 'No Result'
    }));
  };

  const processedInnings = processInningsData(stats.innings);

  // Sort the innings data based on the sort configuration
  const sortedInnings = [...processedInnings].sort((a, b) => {
    if (sortConfig.key === 'date') {
      return sortConfig.direction === 'asc' 
        ? a.date - b.date 
        : b.date - a.date;
    } 
    else {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      
      if (sortConfig.direction === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    }
  });

  // Get the most recent 10 innings or top wicket-taking innings
  const displayInnings = displayMode === 'recent' 
    ? sortedInnings.sort((a, b) => b.date - a.date).slice(0, 10) 
    : sortedInnings.sort((a, b) => b.wickets - a.wickets || b.date - a.date).slice(0, 10);

  // Handle sort request
  const handleSort = (key) => {
    const direction = sortConfig.key === key && sortConfig.direction === 'desc' ? 'asc' : 'desc';
    setSortConfig({ key, direction });
  };

  // Handle display mode change
  const handleDisplayModeChange = (mode) => {
    setDisplayMode(mode);
    setSortConfig({
      key: mode === 'topWickets' ? 'wickets' : 'date',
      direction: 'desc'
    });
  };

  const content = (
    <Card sx={{
      borderRadius: `${borderRadius.base}px`,
      border: `1px solid ${colors.neutral[200]}`,
      backgroundColor: colors.neutral[0]
    }}>
      <CardContent sx={{ p: `${isMobile ? spacing.base : spacing.lg}px` }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="h6">
            {displayMode === 'topWickets' ? 'Top Wicket-Taking Innings' : 'Recent Form'}
          </Typography>
          <ButtonGroup variant="outlined" size="small">
            <Button
              onClick={() => handleDisplayModeChange('topWickets')}
              variant={displayMode === 'topWickets' ? 'contained' : 'outlined'}
            >
              Top Wickets
            </Button>
            <Button
              onClick={() => handleDisplayModeChange('recent')}
              variant={displayMode === 'recent' ? 'contained' : 'outlined'}
            >
              Recent Form
            </Button>
          </ButtonGroup>
        </Box>
        
        <ScrollTable paper sx={{ maxHeight: 400 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortConfig.key === 'date'}
                    direction={sortConfig.key === 'date' ? sortConfig.direction : 'desc'}
                    onClick={() => handleSort('date')}
                  >
                    Date
                  </TableSortLabel>
                </TableCell>
                <TableCell>{isMobile ? 'Opp' : 'Opposition'}</TableCell>
                {isMobile && <TableCell align="right">Figures</TableCell>}
                {!isMobile && <TableCell>Venue</TableCell>}
                {!isMobile && <TableCell align="right">
                  <TableSortLabel
                    active={sortConfig.key === 'overs'}
                    direction={sortConfig.key === 'overs' ? sortConfig.direction : 'desc'}
                    onClick={() => handleSort('overs')}
                  >
                    Overs
                  </TableSortLabel>
                </TableCell>}
                {!isMobile && <TableCell align="right">
                  <TableSortLabel
                    active={sortConfig.key === 'runs'}
                    direction={sortConfig.key === 'runs' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('runs')}
                  >
                    Runs
                  </TableSortLabel>
                </TableCell>}
                {!isMobile && <TableCell align="right">
                  <TableSortLabel
                    active={sortConfig.key === 'wickets'}
                    direction={sortConfig.key === 'wickets' ? sortConfig.direction : 'desc'}
                    onClick={() => handleSort('wickets')}
                  >
                    Wickets
                  </TableSortLabel>
                </TableCell>}
                <TableCell align="right">
                  <TableSortLabel
                    active={sortConfig.key === 'economy'}
                    direction={sortConfig.key === 'economy' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('economy')}
                  >
                    {isMobile ? 'Econ' : 'Economy'}
                  </TableSortLabel>
                </TableCell>
                {!isMobile && <TableCell align="right">
                  <TableSortLabel
                    active={sortConfig.key === 'dot_percentage'}
                    direction={sortConfig.key === 'dot_percentage' ? sortConfig.direction : 'desc'}
                    onClick={() => handleSort('dot_percentage')}
                  >
                    Dot %
                  </TableSortLabel>
                </TableCell>}
                {!isMobile && <TableCell align="center">Result</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {displayInnings.map((inning, index) => (
                <TableRow 
                  key={index}
                  sx={{ 
                    '&:last-child td, &:last-child th': { border: 0 },
                    backgroundColor: inning.result === 'Won' ? 'rgba(76, 175, 80, 0.1)' : 
                                    inning.result === 'Lost' ? 'rgba(244, 67, 54, 0.1)' : 
                                    'inherit'
                  }}
                  hover
                  // Phones: 4 columns; tap a row for venue, overs, dots and result.
                  onClick={isMobile ? () => setOpenInning(inning) : undefined}
                  style={isMobile ? { cursor: 'pointer' } : undefined}
                >
                  <TableCell>{inning.formattedDate}</TableCell>
                  <TableCell><CondensedName name={inning.batting_team} type="team" /></TableCell>
                  {isMobile && <TableCell align="right" sx={{ fontWeight: 600 }}>{inning.wickets}/{inning.runs}</TableCell>}
                  {!isMobile && <TableCell sx={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {inning.venue}
                  </TableCell>}
                  {!isMobile && <TableCell align="right">{inning.overs}</TableCell>}
                  {!isMobile && <TableCell align="right">{inning.runs}</TableCell>}
                  {!isMobile && <TableCell align="right">{inning.wickets}</TableCell>}
                  <TableCell align="right">{inning.economy}</TableCell>
                  {!isMobile && <TableCell align="right">{inning.dot_percentage}%</TableCell>}
                  {!isMobile && <TableCell align="center" 
                    sx={{ 
                      color: inning.result === 'Won' ? 'success.main' : 
                             inning.result === 'Lost' ? 'error.main' : 
                             'text.secondary',
                      fontWeight: 'medium'
                    }}
                  >
                    {inning.result}
                  </TableCell>}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollTable>
        <DetailSheet
          open={Boolean(openInning)}
          onClose={() => setOpenInning(null)}
          title={openInning ? `${openInning.wickets}/${openInning.runs} v ${openInning.batting_team}` : ''}
          subtitle={openInning ? `${openInning.formattedDate} · ${openInning.venue || ''}` : ''}
          rows={openInning ? [
            { label: 'Overs', value: openInning.overs },
            { label: 'Economy', value: openInning.economy },
            { label: 'Dot %', value: `${openInning.dot_percentage}%` },
            { label: 'Result', value: openInning.result || '–' },
          ] : []}
        />
      </CardContent>
    </Card>
  );

  if (!wrapInCard) {
    return <Box>{content}</Box>;
  }

  return content;
};

export default BowlingInningsTable;