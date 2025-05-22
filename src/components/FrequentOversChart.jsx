import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TableSortLabel, TablePagination } from '@mui/material';
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

const FrequentOversChart = ({ stats }) => {
  const [orderBy, setOrderBy] = useState('instances_bowled');
  const [order, setOrder] = useState('desc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  // Early return if no data is provided
  if (!stats || !stats.over_distribution || stats.over_distribution.length === 0) {
    return null;
  }

  // Process the data for the chart
  const processedData = stats.over_distribution.map(over => ({
    over: `Over ${over.over_number}`,
    instances_bowled: over.instances_bowled,
    matches_percentage: parseFloat(over.matches_percentage.toFixed(1)),
    runs: typeof over.runs === 'object' ? parseFloat(over.runs.toFixed(2)) : parseFloat(over.runs),
    balls: over.balls,
    wickets: over.wickets,
    economy: parseFloat(over.economy.toFixed(2)),
    bowling_strike_rate: parseFloat(over.bowling_strike_rate.toFixed(2)),
    dot_percentage: parseFloat(over.dot_percentage.toFixed(2))
  }));

  // Sort the data for the table
  const sortedData = [...processedData].sort((a, b) => {
    if (order === 'asc') {
      return a[orderBy] - b[orderBy];
    }
    return b[orderBy] - a[orderBy];
  });

  // Get the top 5 most frequent overs for the chart
  const top5Data = [...processedData]
    .sort((a, b) => b.instances_bowled - a.instances_bowled)
    .slice(0, 5);

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Paper sx={{ p: 2, boxShadow: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            {label}
          </Typography>
          <Typography variant="body2">
            Wickets: <strong>{payload[0].value}</strong>
          </Typography>
          <Typography variant="body2">
            Economy Rate: <strong>{payload[1].value}</strong>
          </Typography>
          <Typography variant="body2">
            Frequency: <strong>{processedData.find(d => d.over === label)?.instances_bowled || 0} times ({processedData.find(d => d.over === label)?.matches_percentage || 0}%)</strong>
          </Typography>
          <Typography variant="body2">
            Dot Ball %: <strong>{processedData.find(d => d.over === label)?.dot_percentage || 0}%</strong>
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

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Most Frequently Bowled Overs
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Analysis of performance in specific overs of the innings
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
              <XAxis dataKey="over" angle={0} textAnchor="middle" height={50}>
                <Label value="Over Number" position="bottom" offset={20} />
              </XAxis>
              <YAxis yAxisId="left">
                <Label value="Wickets" angle={-90} position="insideLeft" />
              </YAxis>
              <YAxis yAxisId="right" orientation="right">
                <Label value="Economy Rate" angle={90} position="insideRight" />
              </YAxis>
              <RechartsTooltip content={<CustomTooltip />} />
              <Legend />
              <Bar yAxisId="left" dataKey="wickets" name="Wickets" fill="#8884d8" />
              <Bar yAxisId="right" dataKey="economy" name="Economy Rate" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
        
        <TableContainer component={Paper}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Over</TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'instances_bowled'}
                    direction={orderBy === 'instances_bowled' ? order : 'asc'}
                    onClick={() => handleRequestSort('instances_bowled')}
                  >
                    Frequency
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'matches_percentage'}
                    direction={orderBy === 'matches_percentage' ? order : 'asc'}
                    onClick={() => handleRequestSort('matches_percentage')}
                  >
                    %
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
                    active={orderBy === 'dot_percentage'}
                    direction={orderBy === 'dot_percentage' ? order : 'asc'}
                    onClick={() => handleRequestSort('dot_percentage')}
                  >
                    Dot %
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
                      {row.over}
                    </TableCell>
                    <TableCell align="right">{row.instances_bowled}</TableCell>
                    <TableCell align="right">{row.matches_percentage}%</TableCell>
                    <TableCell align="right">{row.wickets}</TableCell>
                    <TableCell align="right">{row.economy}</TableCell>
                    <TableCell align="right">{row.dot_percentage}%</TableCell>
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
};

export default FrequentOversChart;