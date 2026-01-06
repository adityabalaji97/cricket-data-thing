import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, Tooltip, TablePagination } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Label
} from 'recharts';
import { spacing, colors, borderRadius } from '../theme/designSystem';

const OverCombinationsChart = ({ stats, isMobile = false, wrapInCard = true }) => {
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

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Paper sx={{ p: 2, boxShadow: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Overs: {label}
          </Typography>
          <Typography variant="body2">
            Wickets/Innings: <strong>{payload[0].value}</strong>
          </Typography>
          <Typography variant="body2">
            Economy Rate: <strong>{payload[1].value}</strong>
          </Typography>
          <Typography variant="body2">
            Frequency: <strong>{processedData.find(d => d.overs === label)?.percentage}%</strong>
          </Typography>
        </Paper>
      );
    }
    return null;
  };

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

  const chartHeight = isMobile ? 220 : 280;

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
        
        <Box sx={{ width: '100%', height: 300, mb: 4 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={top5Data}
              margin={{
                top: 20,
                right: 30,
                left: 20,
                bottom: 50,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="overs" angle={-45} textAnchor="end" height={80}>
                <Label value="Over Combinations (Top 5)" position="bottom" offset={20} />
              </XAxis>
              <YAxis yAxisId="left">
                <Label value="Wickets per Innings" angle={-90} position="insideLeft" />
              </YAxis>
              <YAxis yAxisId="right" orientation="right">
                <Label value="Economy Rate" angle={90} position="insideRight" />
              </YAxis>
              <RechartsTooltip content={<CustomTooltip />} />
              <Legend />
              <Bar yAxisId="left" dataKey="wickets_per_innings" name="Wickets/Innings" fill="#8884d8" />
              <Bar yAxisId="right" dataKey="economy" name="Economy Rate" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
        
        <TableContainer component={Paper}>
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
        </TableContainer>
      </CardContent>
    </Card>
  );

  if (!wrapInCard) {
    return <Box>{content}</Box>;
  }

  return content;
};

export default OverCombinationsChart;