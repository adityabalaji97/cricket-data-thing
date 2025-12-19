import React, { useState, useMemo, useRef } from 'react';
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
  TableSortLabel,
  Autocomplete,
  TextField,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GetAppIcon from '@mui/icons-material/GetApp';
import BarChartIcon from '@mui/icons-material/BarChart';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';
import AddIcon from '@mui/icons-material/Add';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import MapIcon from '@mui/icons-material/Map';
import FilterListOffIcon from '@mui/icons-material/FilterListOff';
import ChartPanel from './ChartPanel';
import { PitchMapContainer, getPitchMapMode } from './PitchMap';

// Column Filter Component
const ColumnFilter = ({ column, displayName, uniqueValues, selectedValues, onChange, onClear, isMobile }) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 200 }}>
      <FormControl size="small" sx={{ minWidth: 150, maxWidth: 200 }}>
        <InputLabel>{`Filter ${displayName}`}</InputLabel>
        <Select
          multiple
          value={selectedValues || []}
          onChange={(e) => onChange(column, e.target.value)}
          input={<OutlinedInput label={`Filter ${displayName}`} />}
          renderValue={(selected) => (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {selected.slice(0, isMobile ? 1 : 2).map((value) => (
                <Chip key={value} label={value} size="small" />
              ))}
              {selected.length > (isMobile ? 1 : 2) && (
                <Chip 
                  label={`+${selected.length - (isMobile ? 1 : 2)} more`} 
                  size="small" 
                  variant="outlined" 
                />
              )}
            </Box>
          )}
          sx={{ fontSize: '0.875rem' }}
        >
          {uniqueValues.map((value) => (
            <MenuItem key={value} value={value}>
              {value}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      
      {selectedValues && selectedValues.length > 0 && (
        <Tooltip title="Clear filter">
          <IconButton 
            size="small" 
            onClick={() => onClear(column)}
            sx={{ p: 0.5 }}
          >
            <ClearIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Box>
  );
};

const QueryResults = ({ results, groupBy, filters, isMobile }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(isMobile ? 5 : 10);
  
  // Sorting state
  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: 'asc'
  });
  
  // Column filtering state
  const [columnFilters, setColumnFilters] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  
  // Chart panel ref to trigger chart additions
  const chartPanelRef = useRef(null);
  const [showCharts, setShowCharts] = useState(false);
  const [showPitchMap, setShowPitchMap] = useState(false);
  
  // Extract data early to avoid hooks rule violation
  const data = results?.data || [];
  const summaryData = results?.summary_data || null;
  const metadata = results?.metadata || {};
  const isGrouped = groupBy && groupBy.length > 0;
  const hasSummaries = metadata.has_summaries || false;
  const pitchMapMode = useMemo(() => getPitchMapMode(groupBy || []), [groupBy]);
  
  // Merge regular data with summary data and percentages for display
  const displayData = useMemo(() => {
    // Always add is_summary: false to regular data first
    const dataWithFlags = data.map(row => ({
      ...row,
      is_summary: false
    }));
    
    // If no summaries requested, just return data with flags
    if (!hasSummaries || !summaryData || !isGrouped) {
      return dataWithFlags;
    }
    
    // Create a lookup for percentages
    const percentageLookup = {};
    if (summaryData.percentages) {
      summaryData.percentages.forEach(item => {
        const key = groupBy.map(col => String(item[col] || 'null')).join('|');
        percentageLookup[key] = item.percent_balls;
      });
    }
    
    // Add percent_balls to regular data
    const dataWithPercentages = dataWithFlags.map(row => {
      const key = groupBy.map(col => String(row[col] || 'null')).join('|');
      const percent_balls = percentageLookup[key] || 0;
      return {
        ...row,
        percent_balls
      };
    });
    
    // If we have multi-level grouping, insert summary rows
    if (groupBy.length > 1 && summaryData[`${groupBy[0]}_summaries`]) {
      const summaries = summaryData[`${groupBy[0]}_summaries`];
      const mergedData = [];
      
      // Group data by first grouping column to insert summaries
      const groupedByFirst = {};
      dataWithPercentages.forEach(row => {
        const firstGroupValue = String(row[groupBy[0]] || 'null');
        if (!groupedByFirst[firstGroupValue]) {
          groupedByFirst[firstGroupValue] = [];
        }
        groupedByFirst[firstGroupValue].push(row);
      });
      
      // Sort by the first group column to match order
      const sortedGroups = Object.keys(groupedByFirst).sort((a, b) => {
        // Handle numeric sorting for years
        if (!isNaN(a) && !isNaN(b)) {
          return Number(b) - Number(a); // Descending order for years
        }
        return a.localeCompare(b);
      });
      
      sortedGroups.forEach(groupValue => {
        // Add the regular rows for this group
        mergedData.push(...groupedByFirst[groupValue]);
        
        // Add summary row for this group
        const summary = summaries.find(s => String(s[groupBy[0]]) === groupValue);
        if (summary) {
          const summaryRow = {
            ...summary,
            // Set other grouping columns to null to indicate this is a summary
            ...groupBy.slice(1).reduce((acc, col) => ({ ...acc, [col]: null }), {}),
            // Rename total_ fields to regular field names for display
            balls: summary.total_balls,
            runs: summary.total_runs,
            wickets: summary.total_wickets,
            dots: summary.total_dots,
            boundaries: summary.total_boundaries,
            fours: summary.total_fours,
            sixes: summary.total_sixes,
            // Add calculated fields for summaries
            average: summary.total_wickets > 0 ? summary.total_runs / summary.total_wickets : null,
            strike_rate: summary.total_balls > 0 ? (summary.total_runs * 100) / summary.total_balls : 0,
            balls_per_dismissal: summary.total_wickets > 0 ? summary.total_balls / summary.total_wickets : null,
            dot_percentage: summary.total_balls > 0 ? (summary.total_dots * 100) / summary.total_balls : 0,
            boundary_percentage: summary.total_balls > 0 ? (summary.total_boundaries * 100) / summary.total_balls : 0,
            percent_balls: 100.0, // Summary rows represent 100% of their group
            is_summary: true,
            summary_level: 1
          };
          mergedData.push(summaryRow);
        }
      });
      
      return mergedData;
    }
    
    return dataWithPercentages;
  }, [data, summaryData, hasSummaries, isGrouped, groupBy]);
  
  // Apply column filters to displayData
  const filteredData = useMemo(() => {
    if (!columnFilters || Object.keys(columnFilters).length === 0) {
      return displayData;
    }
    
    return displayData.filter(row => {
      return Object.entries(columnFilters).every(([column, selectedValues]) => {
        if (!selectedValues || selectedValues.length === 0) return true;
        
        const cellValue = row[column];
        // Handle null values and convert to string for comparison
        const valueStr = cellValue === null || cellValue === undefined ? 'N/A' : String(cellValue);
        
        return selectedValues.includes(valueStr);
      });
    });
  }, [displayData, columnFilters]);
  
  // Memoized sorted data
  const sortedData = useMemo(() => {
    if (!sortConfig.key || filteredData.length === 0) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      
      // Handle null/undefined values
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;
      
      // Handle different data types
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      // Handle strings and dates
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      
      if (aStr < bStr) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aStr > bStr) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortConfig]);
  
  // Early return after all hooks
  if (!results || !results.data) {
    return (
      <Alert severity="info">
        No results to display. Execute a query to see results here.
      </Alert>
    );
  }
  

  // Chart management functions
  const handleAddBarChart = () => {
    setShowCharts(true);
    // Small delay to ensure ChartPanel is rendered before calling addBarChart
    setTimeout(() => {
      if (chartPanelRef.current && chartPanelRef.current.addBarChart) {
        chartPanelRef.current.addBarChart();
      }
    }, 100);
  };

  const handleAddScatterChart = () => {
    setShowCharts(true);
    // Small delay to ensure ChartPanel is rendered before calling addScatterChart
    setTimeout(() => {
      if (chartPanelRef.current && chartPanelRef.current.addScatterChart) {
        chartPanelRef.current.addScatterChart();
      }
    }, 100);
  };

  // Sorting logic
  const handleSort = (columnKey) => {
    let direction = 'asc';
    if (sortConfig.key === columnKey && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key: columnKey, direction });
    setPage(0); // Reset to first page when sorting
  };
  
  // Column filtering logic
  const getUniqueValuesForColumn = (column) => {
    const values = new Set();
    displayData.forEach(row => {
      const value = row[column];
      const valueStr = value === null || value === undefined ? 'N/A' : String(value);
      values.add(valueStr);
    });
    return Array.from(values).sort();
  };
  
  const handleColumnFilter = (column, selectedValues) => {
    setColumnFilters(prev => ({
      ...prev,
      [column]: selectedValues
    }));
    setPage(0); // Reset to first page when filtering
  };
  
  const clearColumnFilter = (column) => {
    setColumnFilters(prev => {
      const updated = { ...prev };
      delete updated[column];
      return updated;
    });
    setPage(0);
  };
  
  const clearAllFilters = () => {
    setColumnFilters({});
    setPage(0);
  };
  
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };
  
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  const exportToCSV = () => {
    if (!sortedData || sortedData.length === 0) return;
    
    // Use filtered and sorted data for export
    const exportData = sortedData;
    
    // Get all unique keys from the data
    const headers = Object.keys(exportData[0]);
    
    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...exportData.map(row => 
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
    
    // Include filter info in filename if filters are active
    const filterSuffix = Object.keys(columnFilters).length > 0 ? '-filtered' : '';
    const filename = `cricket-query${filterSuffix}-${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', filename);
    
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  const formatValue = (value, key) => {
    if (value === null || value === undefined) return 'N/A';
    
    // Format different types of values
    if (key.includes('percentage') || key === 'percent_balls') {
      return `${Number(value).toFixed(1)}%`;
    }
    if (key === 'strike_rate') {
      return Number(value).toFixed(1);  // Strike rate is NOT a percentage - just display the number
    }
    if (key === 'average' || key === 'balls_per_dismissal') {
      return Number(value).toFixed(2);
    }
    if (key === 'year') {
      return value; // Display year without comma formatting
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
      'percent_balls': '% Balls',
      'balls_per_dismissal': 'Balls/Wicket',
      'year': 'Year'
    };
    
    return displayNames[key] || key.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };
  
  const getCricketMetrics = () => {
    if (!isGrouped || displayData.length === 0) return null;
    
    const sampleRow = displayData[0];
    const cricketKeys = ['balls', 'runs', 'wickets', 'dots', 'boundaries', 'fours', 'sixes', 
                         'average', 'strike_rate', 'balls_per_dismissal', 'dot_percentage', 'boundary_percentage'];
    
    return cricketKeys.filter(key => key in sampleRow);
  };
  
  const getGroupingColumns = () => {
    if (!isGrouped || displayData.length === 0) return [];
    
    const sampleRow = displayData[0];
    return Object.keys(sampleRow).filter(key => groupBy.includes(key));
  };
  
  const getVisibleColumns = () => {
    if (displayData.length === 0) return [];
    
    const allColumns = Object.keys(displayData[0]);
    
    // For mobile, show fewer columns
    if (isMobile) {
      if (isGrouped) {
        const baseColumns = [...getGroupingColumns(), 'balls', 'runs', 'strike_rate'];
        // Add percent_balls if available
        if (hasSummaries && allColumns.includes('percent_balls')) {
          baseColumns.push('percent_balls');
        }
        return baseColumns.filter(col => allColumns.includes(col));
      } else {
        return ['batter', 'bowler', 'runs_off_bat', 'crease_combo'].filter(col => allColumns.includes(col));
      }
    }
    
    // For desktop, show all columns except internal ones
    return allColumns.filter(col => !['is_summary', 'summary_level'].includes(col));
  };
  
  // Use sorted data for pagination
  const paginatedData = sortedData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
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
                    {hasSummaries && (
                      <Chip 
                        label="With Summary Rows" 
                        color="secondary" 
                        size="small" 
                      />
                    )}
                  </>
                ) : (
                  <>
                    <Chip 
                      label={`${(metadata.total_matching_rows || 0).toLocaleString()} total deliveries`} 
                      color="primary" 
                      size="small" 
                    />
                    <Chip 
                      label={`Showing ${sortedData.length}`} 
                      variant="outlined" 
                      size="small" 
                    />
                  </>
                )}
                
                {/* Sort indicator */}
                {sortConfig.key && (
                  <Chip 
                    label={`Sorted by: ${getColumnDisplayName(sortConfig.key)} (${sortConfig.direction})`} 
                    variant="outlined" 
                    size="small"
                    color="secondary"
                  />
                )}
                
                {/* Filter indicator */}
                {Object.keys(columnFilters).length > 0 && (
                  <Chip 
                    label={`${Object.keys(columnFilters).length} column filter${Object.keys(columnFilters).length > 1 ? 's' : ''} active`} 
                    color="warning" 
                    size="small"
                    icon={<FilterListIcon />}
                  />
                )}
              </Box>
              
              {metadata.filters_applied && (
                <Typography variant="body2" color="text.secondary">
                  {metadata.note}
                </Typography>
              )}
            </Grid>
            
            <Grid item xs={12} sm={4} sx={{ textAlign: { xs: 'left', sm: 'right' } }}>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: { xs: 'flex-start', sm: 'flex-end' } }}>
                {/* Filter toggle button - only show for grouped data */}
                {isGrouped && data.length > 0 && (
                  <>
                    <Button
                      variant={showFilters ? "contained" : "outlined"}
                      startIcon={showFilters ? <FilterListOffIcon /> : <FilterListIcon />}
                      onClick={() => setShowFilters(!showFilters)}
                      size="small"
                      color={Object.keys(columnFilters).length > 0 ? "warning" : "primary"}
                    >
                      {showFilters ? 'Hide Filters' : 'Show Filters'}
                    </Button>
                    
                    {Object.keys(columnFilters).length > 0 && (
                      <Button
                        variant="outlined"
                        startIcon={<ClearIcon />}
                        onClick={clearAllFilters}
                        size="small"
                        color="warning"
                      >
                        Clear Filters
                      </Button>
                    )}
                  </>
                )}
                
                {/* Pitch Map button - show when line or length is in groupBy */}
                {isGrouped && pitchMapMode && data.length > 0 && (
                  <Button
                    variant={showPitchMap ? "contained" : "outlined"}
                    startIcon={<MapIcon />}
                    onClick={() => setShowPitchMap(!showPitchMap)}
                    size="small"
                    color="success"
                  >
                    {showPitchMap ? 'Hide Pitch Map' : 'Show Pitch Map'}
                  </Button>
                )}
                
                {/* Chart buttons only for grouped data */}
                {isGrouped && data.length > 0 && (
                  <>
                    <Button
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={handleAddBarChart}
                      size="small"
                      sx={{ mr: 1 }}
                    >
                      Add Bar Chart
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={handleAddScatterChart}
                      size="small"
                    >
                      Add Scatter Plot
                    </Button>
                  </>
                )}
                <Button
                  variant="outlined"
                  startIcon={<GetAppIcon />}
                  onClick={exportToCSV}
                  disabled={!data || data.length === 0}
                  size="small"
                >
                  Export CSV
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* Pitch Map Visualization */}
      {showPitchMap && pitchMapMode && isGrouped && (
        <Box sx={{ mb: 3 }}>
          <PitchMapContainer
            data={data}
            groupBy={groupBy}
            filters={filters || metadata?.filters_applied || {}}
          />
        </Box>
      )}

      
      {/* Cricket Metrics Summary (for grouped results) */}
      {isGrouped && cricketMetrics && (
        <Accordion defaultExpanded sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">📊 Cricket Metrics Overview</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {sortedData.slice(0, 3).map((row, index) => (
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
      
      {/* Data Table with Sorting */}
      <Paper>
        <TableContainer sx={{ maxHeight: isMobile ? 400 : 600 }}>
          <Table stickyHeader size={isMobile ? "small" : "medium"}>
            <TableHead>
              <TableRow>
                {visibleColumns.map((column) => (
                  <TableCell key={column} sx={{ fontWeight: 'bold' }}>
                    <TableSortLabel
                      active={sortConfig.key === column}
                      direction={sortConfig.key === column ? sortConfig.direction : 'asc'}
                      onClick={() => handleSort(column)}
                      hideSortIcon={sortConfig.key !== column}
                      sx={{ 
                        '& .MuiTableSortLabel-icon': {
                          opacity: sortConfig.key === column ? 1 : 0
                        },
                        '&:hover .MuiTableSortLabel-icon': {
                          opacity: 0.5
                        },
                        '&:hover': {
                          color: 'primary.main'
                        }
                      }}
                    >
                      {getColumnDisplayName(column)}
                    </TableSortLabel>
                  </TableCell>
                ))}
              </TableRow>
              
              {/* Filter Row */}
              {showFilters && isGrouped && (
                <TableRow sx={{ backgroundColor: 'grey.50' }}>
                  {visibleColumns.map((column) => {
                    // Only show filters for grouping columns and string/categorical columns
                    const isFilterableColumn = groupBy.includes(column) || 
                      ['crease_combo', 'ball_direction', 'bowler_type', 'striker_batter_type', 'non_striker_batter_type', 'venue', 'batting_team', 'bowling_team', 'batter', 'bowler', 'competition'].includes(column);
                    
                    return (
                      <TableCell key={column} sx={{ py: 1 }}>
                        {isFilterableColumn ? (
                          <ColumnFilter
                            column={column}
                            displayName={getColumnDisplayName(column)}
                            uniqueValues={getUniqueValuesForColumn(column)}
                            selectedValues={columnFilters[column]}
                            onChange={handleColumnFilter}
                            onClear={clearColumnFilter}
                            isMobile={isMobile}
                          />
                        ) : (
                          <Box sx={{ height: 40 }} /> // Empty space for non-filterable columns
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              )}
            </TableHead>
            <TableBody>
              {paginatedData.map((row, index) => (
                <TableRow 
                  key={index} 
                  hover={!row.is_summary}
                  sx={{
                    backgroundColor: row.is_summary ? 'grey.100' : 'inherit',
                    fontWeight: row.is_summary ? 'bold' : 'normal',
                    '& .MuiTableCell-root': {
                      fontWeight: row.is_summary ? 'bold' : 'normal',
                      borderTop: row.is_summary ? '2px solid' : 'none',
                      borderTopColor: row.is_summary ? 'grey.400' : 'transparent'
                    }
                  }}
                >
                  {visibleColumns.map((column) => (
                    <TableCell key={column}>
                      {row.is_summary && column !== groupBy[0] && groupBy.includes(column) ? 
                        '— Total —' : 
                        formatValue(row[column], column)
                      }
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
          count={sortedData.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
      
      {/* Chart Panel */}
      <ChartPanel 
        ref={chartPanelRef}
        data={sortedData.filter(row => !row.is_summary)} // Filter out summary rows for charts
        groupBy={groupBy}
        isVisible={showCharts && isGrouped}
        onToggle={() => setShowCharts(!showCharts)}
        isMobile={isMobile}
      />
      
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