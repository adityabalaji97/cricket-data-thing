import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, Table, TableBody, TableCell, TableHead, TableRow, TableSortLabel, TablePagination } from '@mui/material';
import ScrollTable from './ui/ScrollTable';
import { spacing, colors, borderRadius } from '../theme/designSystem';
import useIsMobile from '../hooks/useIsMobile';
import { SERIES } from '../theme/chartDefaults';

const OverCombinationsChart = ({ stats, wrapInCard = true }) => {
  // Phone layout from the shared hook: callers never passed isMobile, so phones got the desktop chart.
  const { isMobile } = useIsMobile();
  const [orderBy, setOrderBy] = useState('percentage');
  const [order, setOrder] = useState('desc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  // Early return if no data is provided
  if (!stats || !stats.over_combinations || stats.over_combinations.length === 0) {
    return null;
  }

  // Process the data for the chart
  const processedData = stats.over_combinations.map(combo => ({
    overs: combo.overs.join(', '),
    frequency: combo.frequency,
    percentage: parseFloat(combo.percentage.toFixed(1)),
    runs: typeof combo.runs === 'object' ? parseFloat(combo.runs.toFixed(2)) : parseFloat(combo.runs),
    wickets: combo.wickets,
    economy: parseFloat(combo.economy.toFixed(2)),
    wickets_per_innings: parseFloat(combo.wickets_per_innings.toFixed(2))
  }));

  // Sort the data for the table
  const sortedData = [...processedData].sort((a, b) => {
    if (order === 'asc') {
      return a[orderBy] - b[orderBy];
    }
    return b[orderBy] - a[orderBy];
  });

  // Get the top 5 most frequent combinations for the chart
  const top5Data = [...processedData]
    .sort((a, b) => b.percentage - a.percentage)
    .slice(0, 5);



  // Handle sort request
  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Handle pagination
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };


  const content = (
    <Card sx={{
      borderRadius: `${borderRadius.base}px`,
      border: `1px solid ${colors.neutral[200]}`,
      backgroundColor: colors.neutral[0]
    }}>
      <CardContent sx={{ p: `${isMobile ? spacing.base : spacing.lg}px` }}>
        <Typography variant="h6" gutterBottom>
          Over Combination Performance
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Analysis of effectiveness across different over combinations
        </Typography>
        
        {/* Ranked list, one row per combination, each metric on its own scale. Was a dual-axis
            bar chart (wickets/innings v economy on two y-scales) with -45deg x labels and fixed
            margins, unreadable at phone width. */}
        <Box sx={{ display: 'grid', gap: 1.5, mb: 3 }}>
          {(() => {
            const maxW = Math.max(...top5Data.map((d) => Number(d.wickets_per_innings) || 0), 1e-9);
            const maxE = Math.max(...top5Data.map((d) => Number(d.economy) || 0), 1e-9);
            const bar = (v, max, color) => (
              <Box sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: 'rgba(255,255,255,0.06)' }}>
                <Box sx={{ height: '100%', width: `${((Number(v) || 0) / max) * 100}%`, borderRadius: 3, bgcolor: color }} />
              </Box>
            );
            return top5Data.map((d) => (
              <Box key={d.overs}>
                <Typography sx={{ fontWeight: 600, fontSize: 14 }}>Overs {d.overs}</Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '96px minmax(0, 1fr) 44px', alignItems: 'center', columnGap: 1, rowGap: 0.5, mt: 0.5 }}>
                  <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>Wickets / inns</Typography>
                  {bar(d.wickets_per_innings, maxW, SERIES[0])}
                  <Typography sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 12, textAlign: 'right' }}>{Number(d.wickets_per_innings || 0).toFixed(2)}</Typography>
                  <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>Economy</Typography>
                  {bar(d.economy, maxE, SERIES[1])}
                  <Typography sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 12, textAlign: 'right' }}>{Number(d.economy || 0).toFixed(2)}</Typography>
                </Box>
              </Box>
            ));
          })()}
        </Box>
        
        <ScrollTable paper>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Overs</TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'percentage'}
                    direction={orderBy === 'percentage' ? order : 'asc'}
                    onClick={() => handleRequestSort('percentage')}
                  >
                    %
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'runs'}
                    direction={orderBy === 'runs' ? order : 'asc'}
                    onClick={() => handleRequestSort('runs')}
                  >
                    Runs
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'wickets'}
                    direction={orderBy === 'wickets' ? order : 'asc'}
                    onClick={() => handleRequestSort('wickets')}
                  >
                    Wickets
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'economy'}
                    direction={orderBy === 'economy' ? order : 'asc'}
                    onClick={() => handleRequestSort('economy')}
                  >
                    Economy
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'wickets_per_innings'}
                    direction={orderBy === 'wickets_per_innings' ? order : 'asc'}
                    onClick={() => handleRequestSort('wickets_per_innings')}
                  >
                    W/I
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedData
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((row, index) => (
                  <TableRow
                    key={index}
                    sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                    hover
                  >
                    <TableCell component="th" scope="row">
                      {row.overs}
                    </TableCell>
                    <TableCell align="right">{row.percentage}%</TableCell>
                    <TableCell align="right">{row.runs}</TableCell>
                    <TableCell align="right">{row.wickets}</TableCell>
                    <TableCell align="right">{row.economy}</TableCell>
                    <TableCell align="right">{row.wickets_per_innings}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={sortedData.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </ScrollTable>
      </CardContent>
    </Card>
  );

  if (!wrapInCard) {
    return <Box>{content}</Box>;
  }

  return content;
};

export default OverCombinationsChart;