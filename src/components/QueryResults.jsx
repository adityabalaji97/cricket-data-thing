import React, { useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  Chip,
  Button,
  Card,
  CardContent,
  Grid,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GetAppIcon from '@mui/icons-material/GetApp';
import InfoIcon from '@mui/icons-material/Info';

const QueryResults = ({ results, groupBy, isMobile }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(isMobile ? 5 : 10);
  
  if (!results || !results.data) {
    return (
      <Alert severity="info">
        No results to display. Execute a query to see results here.
      </Alert>
    );
  }
  
  const { data, metadata } = results;
  const isGrouped = groupBy && groupBy.length > 0;
  
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };
  
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  const exportToCSV = () => {
    if (!data || data.length === 0) return;
    
    // Get all unique keys from the data
    const headers = Object.keys(data[0]);
    
    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => {
          const value = row[header];
          // Handle null/undefined values and escape commas
          if (value === null || value === undefined) return '';
          if (typeof value === 'string' && value.includes(',')) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',')
      )
    ].join('\n');
    
    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `cricket-query-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  const formatValue = (value, key) => {
    if (value === null || value === undefined) return 'N/A';
    
    // Format different types of values
    if (key.includes('percentage')) {
      return `${Number(value).toFixed(1)}%`;
    }
    if (key === 'strike_rate') {
      return Number(value).toFixed(1);  // Strike rate is NOT a percentage - just display the number
    }
    if (key === 'average' || key === 'balls_per_dismissal') {
      return Number(value).toFixed(2);
    }
    if (typeof value === 'number' && value > 1000) {
      return value.toLocaleString();
    }
    
    return value;
  };
  
  const getColumnDisplayName = (key) => {
    const displayNames = {
      'match_id': 'Match ID',
      'crease_combo': 'Crease Combo',
      'ball_direction': 'Ball Direction',
      'bowler_type': 'Bowler Type',
      'striker_batter_type': 'Striker Type',
      'non_striker_batter_type': 'Non-Striker Type',
      'runs_off_bat': 'Runs off Bat',
      'batting_team': 'Batting Team',
      'bowling_team': 'Bowling Team',
      'strike_rate': 'Strike Rate',
      'dot_percentage': 'Dot %',
      'boundary_percentage': 'Boundary %',
      'balls_per_dismissal': 'Balls/Wicket'
    };
    
    return displayNames[key] || key.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };
  
  const getCricketMetrics = () => {
    if (!isGrouped || data.length === 0) return null;
    
    const sampleRow = data[0];
    const cricketKeys = ['balls', 'runs', 'wickets', 'dots', 'boundaries', 'fours', 'sixes', 
                         'average', 'strike_rate', 'balls_per_dismissal', 'dot_percentage', 'boundary_percentage'];
    
    return cricketKeys.filter(key => key in sampleRow);
  };
  
  const getGroupingColumns = () => {
    if (!isGrouped || data.length === 0) return [];
    
    const sampleRow = data[0];
    return Object.keys(sampleRow).filter(key => groupBy.includes(key));
  };
  
  const getVisibleColumns = () => {
    if (data.length === 0) return [];
    
    const allColumns = Object.keys(data[0]);
    
    // For mobile, show fewer columns
    if (isMobile) {
      if (isGrouped) {
        return [...getGroupingColumns(), 'balls', 'runs', 'strike_rate'].filter(col => allColumns.includes(col));
      } else {
        return ['batter', 'bowler', 'runs_off_bat', 'crease_combo'].filter(col => allColumns.includes(col));
      }
    }
    
    return allColumns;
  };
  
  const paginatedData = data.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  const visibleColumns = getVisibleColumns();
  const cricketMetrics = getCricketMetrics();
  
  return (
    <Box>
      {/* Results Summary */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={8}>
              <Typography variant="h6" gutterBottom>
                Query Results
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                {isGrouped ? (
                  <>
                    <Chip 
                      label={`${metadata.total_groups || metadata.returned_groups} groups`} 
                      color="primary" 
                      size="small" 
                    />
                    <Chip 
                      label={`Grouped by: ${groupBy.join(', ')}`} 
                      variant="outlined" 
                      size="small" 
                    />
                  </>
                ) : (
                  <>
                    <Chip 
                      label={`${(metadata.total_matching_rows || 0).toLocaleString()} total deliveries`} 
                      color="primary" 
                      size="small" 
                    />
                    <Chip 
                      label={`Showing ${metadata.returned_rows || 0}`} 
                      variant="outlined" 
                      size="small" 
                    />
                  </>
                )}
              </Box>
              
              {metadata.filters_applied && (
                <Typography variant="body2" color="text.secondary">
                  {metadata.note}
                </Typography>
              )}
            </Grid>
            
            <Grid item xs={12} sm={4} sx={{ textAlign: { xs: 'left', sm: 'right' } }}>
              <Button
                variant="outlined"
                startIcon={<GetAppIcon />}
                onClick={exportToCSV}
                disabled={!data || data.length === 0}
                size="small"
              >
                Export CSV
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* Cricket Metrics Summary (for grouped results) */}
      {isGrouped && cricketMetrics && (
        <Accordion defaultExpanded sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">📊 Cricket Metrics Overview</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {data.slice(0, 3).map((row, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Card variant="outlined">
                    <CardContent sx={{ py: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        {getGroupingColumns().map(col => `${getColumnDisplayName(col)}: ${row[col]}`).join(' • ')}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                        <Chip label={`${row.balls?.toLocaleString()} balls`} size="small" />
                        <Chip label={`${row.runs?.toLocaleString()} runs`} size="small" color="primary" />
                        {row.strike_rate && <Chip label={`SR: ${formatValue(row.strike_rate, 'strike_rate')}`} size="small" />}
                        {row.dot_percentage && <Chip label={`Dot: ${formatValue(row.dot_percentage, 'dot_percentage')}`} size="small" />}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}
      
      {/* Data Table */}
      <Paper>
        <TableContainer sx={{ maxHeight: isMobile ? 400 : 600 }}>
          <Table stickyHeader size={isMobile ? "small" : "medium"}>
            <TableHead>
              <TableRow>
                {visibleColumns.map((column) => (
                  <TableCell key={column} sx={{ fontWeight: 'bold' }}>
                    {getColumnDisplayName(column)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedData.map((row, index) => (
                <TableRow key={index} hover>
                  {visibleColumns.map((column) => (
                    <TableCell key={column}>
                      {formatValue(row[column], column)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          rowsPerPageOptions={isMobile ? [5, 10, 25] : [5, 10, 25, 50]}
          component="div"
          count={data.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
      
      {/* Applied Filters Info */}
      {metadata.filters_applied && (
        <Accordion sx={{ mt: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">🔍 Applied Filters</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={1}>
              {Object.entries(metadata.filters_applied).map(([key, value]) => {
                if (!value || (Array.isArray(value) && value.length === 0)) return null;
                
                return (
                  <Grid item key={key}>
                    <Chip 
                      label={`${getColumnDisplayName(key)}: ${Array.isArray(value) ? value.join(', ') : value}`}
                      variant="outlined"
                      size="small"
                    />
                  </Grid>
                );
              })}
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
};

export default QueryResults;
