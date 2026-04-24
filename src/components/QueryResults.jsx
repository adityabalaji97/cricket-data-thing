import React, { useState, useMemo, useRef, useEffect } from 'react';
import CondensedName from './common/CondensedName';
import NLInterpretation from './NLInterpretation';
import axios from 'axios';
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
  TextField,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Popover,
  Collapse,
  Stack
} from '@mui/material';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GetAppIcon from '@mui/icons-material/GetApp';
import AddIcon from '@mui/icons-material/Add';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import MapIcon from '@mui/icons-material/Map';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';
import ThumbDownAltOutlinedIcon from '@mui/icons-material/ThumbDownAltOutlined';
import ChartPanel from './ChartPanel';
import { PitchMapContainer, getPitchMapMode } from './PitchMap';
import config from '../config';

// Column Filter Component
const ColumnFilter = ({ column, displayName, uniqueValues, selectedValues, onChange, onClear, isMobile }) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 200 }}>
      <FormControl size="small" sx={{ minWidth: isMobile ? 80 : 150, maxWidth: isMobile ? 120 : 200 }}>
        <InputLabel sx={isMobile ? { fontSize: '0.75rem' } : {}}>{isMobile ? 'Filter' : `Filter ${displayName}`}</InputLabel>
        <Select
          multiple
          value={selectedValues || []}
          onChange={(e) => onChange(column, e.target.value)}
          input={<OutlinedInput label={isMobile ? 'Filter' : `Filter ${displayName}`} />}
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

const TEAM_NAME_KEYS = new Set([
  'batting_team',
  'bowling_team',
  'team',
  'team1',
  'team2',
  'winner',
  'loser',
  'opposition',
  'opponent_team',
  'toss_winner',
]);

const PLAYER_NAME_KEYS = new Set([
  'batter',
  'bowler',
  'striker',
  'non_striker',
  'player',
  'player_name',
  'player_of_match',
  'captain',
  'vice_captain',
]);

const isTeamNameColumn = (key) => {
  const normalized = String(key || '').toLowerCase();
  return TEAM_NAME_KEYS.has(normalized) || normalized.endsWith('_team');
};

const isPlayerNameColumn = (key) => {
  const normalized = String(key || '').toLowerCase();
  return PLAYER_NAME_KEYS.has(normalized) || normalized.endsWith('_player');
};

const DEFAULT_SELECTED_METRIC_COLUMNS = ['balls', 'runs', 'strike_rate'];

const buildInitialMetricColumns = ({ allColumns, groupBy, recommendedColumns }) => {
  const metricColumns = allColumns.filter(col =>
    !groupBy.includes(col) && !['is_summary', 'summary_level'].includes(col)
  );

  if (metricColumns.length === 0) {
    return [];
  }

  const normalizedRecommended = Array.isArray(recommendedColumns) ? recommendedColumns : [];
  const preferred = normalizedRecommended
    .map(col => String(col || '').trim())
    .filter(Boolean)
    .filter((col, index, arr) => arr.indexOf(col) === index)
    .filter(col => metricColumns.includes(col))
    .slice(0, 6);

  if (preferred.length > 0) {
    return preferred;
  }

  const defaultColumns = DEFAULT_SELECTED_METRIC_COLUMNS.filter(col => metricColumns.includes(col));
  if (defaultColumns.length > 0) {
    return defaultColumns;
  }

  return metricColumns.slice(0, 3);
};

const normalizeRecommendedChart = (recommendedChart) => {
  if (!recommendedChart || typeof recommendedChart !== 'object') {
    return null;
  }

  const chartType = String(recommendedChart.type || '').trim().toLowerCase();
  if (!['bar', 'scatter'].includes(chartType)) {
    return null;
  }

  const xAxis = String(recommendedChart.x_axis || '').trim().toLowerCase();
  const yAxis = String(recommendedChart.y_axis || '').trim().toLowerCase();
  const reason = String(recommendedChart.reason || '').trim();

  return {
    type: chartType,
    x_axis: xAxis,
    y_axis: yAxis,
    reason,
  };
};

const QueryResults = ({
  results,
  groupBy,
  filters,
  recommendedColumns,
  recommendedChart,
  nlInterpretation,
  nlConfidence,
  nlRawFilters,
  nlSourceQuery,
  onSuggestionClick,
  onDismissInterpretation,
  interpretationDisabled = false,
  isMobile,
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(isMobile ? 5 : 10);
  
  // Sorting state
  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: 'asc'
  });
  
  // Column filtering state
  const [columnFilters, setColumnFilters] = useState({});
  const [filterAnchorEl, setFilterAnchorEl] = useState(null);
  const [filterColumn, setFilterColumn] = useState(null);
  
  // Chart panel ref to trigger chart additions
  const chartPanelRef = useRef(null);
  const lastAutoChartKeyRef = useRef(null);
  const [showCharts, setShowCharts] = useState(false);
  const [showPitchMap, setShowPitchMap] = useState(false);
  const [aiChartReason, setAiChartReason] = useState(null);
  const [selectedMetricColumns, setSelectedMetricColumns] = useState(DEFAULT_SELECTED_METRIC_COLUMNS);
  const [headerCollapsed, setHeaderCollapsed] = useState(isMobile);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSelection, setFeedbackSelection] = useState(null);
  const [feedbackNote, setFeedbackNote] = useState('');
  const [feedbackError, setFeedbackError] = useState(null);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);

  // Extract data early to avoid hooks rule violation
  const data = results?.data || [];
  const summaryData = results?.summary_data || null;
  const metadata = results?.metadata || {};
  const isGrouped = groupBy && groupBy.length > 0;
  const normalizedRecommendedChart = useMemo(
    () => normalizeRecommendedChart(recommendedChart),
    [recommendedChart]
  );
  const hasSummaries = metadata.has_summaries || false;
  const pitchMapMode = useMemo(() => getPitchMapMode(groupBy || []), [groupBy]);
  const resultRowCount = useMemo(() => {
    if (typeof metadata.returned_groups === 'number') {
      return metadata.returned_groups;
    }
    if (typeof metadata.total_matching_rows === 'number') {
      return metadata.total_matching_rows;
    }
    return Array.isArray(data) ? data.length : 0;
  }, [metadata, data]);
  
  // Add percent_balls to data (for pitch map and charts, without summary rows)
  const dataWithPercentBalls = useMemo(() => {
    if (!hasSummaries || !summaryData?.percentages || !isGrouped) {
      return data;
    }
    
    // Create a lookup for percentages
    const percentageLookup = {};
    summaryData.percentages.forEach(item => {
      const key = groupBy.map(col => String(item[col] || 'null')).join('|');
      percentageLookup[key] = item.percent_balls;
    });
    
    return data.map(row => {
      const key = groupBy.map(col => String(row[col] || 'null')).join('|');
      return {
        ...row,
        percent_balls: percentageLookup[key] || 0
      };
    });
  }, [data, summaryData, hasSummaries, isGrouped, groupBy]);
  
  // Merge regular data with summary data for table display
  const displayData = useMemo(() => {
    // Always add is_summary: false to regular data first
    const dataWithFlags = dataWithPercentBalls.map(row => ({
      ...row,
      is_summary: false
    }));
    
    // If no summaries requested, just return data with flags
    if (!hasSummaries || !summaryData || !isGrouped) {
      return dataWithFlags;
    }
    
    // If we have multi-level grouping, insert summary rows
    if (groupBy.length > 1 && summaryData[`${groupBy[0]}_summaries`]) {
      const summaries = summaryData[`${groupBy[0]}_summaries`];
      const mergedData = [];
      
      // Group data by first grouping column to insert summaries
      const groupedByFirst = {};
      dataWithFlags.forEach(row => {
        const firstGroupValue = String(row[groupBy[0]] || 'null');
        if (!groupedByFirst[firstGroupValue]) {
          groupedByFirst[firstGroupValue] = [];
        }
        groupedByFirst[firstGroupValue].push(row);
      });
      
      // Sort by the first group column to match order
      const sortedGroups = Object.keys(groupedByFirst).sort((a, b) => {
        if (!isNaN(a) && !isNaN(b)) {
          return Number(b) - Number(a);
        }
        return a.localeCompare(b);
      });
      
      sortedGroups.forEach(groupValue => {
        mergedData.push(...groupedByFirst[groupValue]);
        
        const summary = summaries.find(s => String(s[groupBy[0]]) === groupValue);
        if (summary) {
          const summaryRow = {
            ...summary,
            ...groupBy.slice(1).reduce((acc, col) => ({ ...acc, [col]: null }), {}),
            balls: summary.total_balls,
            runs: summary.total_runs,
            wickets: summary.total_wickets,
            dots: summary.total_dots,
            boundaries: summary.total_boundaries,
            fours: summary.total_fours,
            sixes: summary.total_sixes,
            average: summary.total_wickets > 0 ? summary.total_runs / summary.total_wickets : null,
            strike_rate: summary.total_balls > 0 ? (summary.total_runs * 100) / summary.total_balls : 0,
            balls_per_dismissal: summary.total_wickets > 0 ? summary.total_balls / summary.total_wickets : null,
            dot_percentage: summary.total_balls > 0 ? (summary.total_dots * 100) / summary.total_balls : 0,
            boundary_percentage: summary.total_balls > 0 ? (summary.total_boundaries * 100) / summary.total_balls : 0,
            percent_balls: 100.0,
            is_summary: true,
            summary_level: 1
          };
          mergedData.push(summaryRow);
        }
      });
      
      return mergedData;
    }
    
    return dataWithFlags;
  }, [dataWithPercentBalls, summaryData, hasSummaries, isGrouped, groupBy]);
  
  // Available metric columns for mobile column selector
  const availableMetricColumns = useMemo(() => {
    if (displayData.length === 0 || !isGrouped) return [];
    return Object.keys(displayData[0]).filter(col =>
      !groupBy.includes(col) && !['is_summary', 'summary_level'].includes(col)
    );
  }, [displayData, isGrouped, groupBy]);

  useEffect(() => {
    if (!isGrouped || displayData.length === 0) {
      return;
    }

    const initialColumns = buildInitialMetricColumns({
      allColumns: Object.keys(displayData[0]),
      groupBy,
      recommendedColumns,
    });
    setSelectedMetricColumns(initialColumns);
  }, [results, isGrouped, displayData, groupBy, recommendedColumns]);

  const autoChartRecommendation = useMemo(() => {
    if (!normalizedRecommendedChart || !isGrouped) {
      return null;
    }

    const rowCount = Array.isArray(data) ? data.length : 0;
    if (rowCount < 3 || rowCount > 50) {
      return null;
    }

    return normalizedRecommendedChart;
  }, [normalizedRecommendedChart, isGrouped, data]);

  const autoChartRecommendationKey = useMemo(() => {
    if (!autoChartRecommendation) {
      return null;
    }
    const rowCount = Array.isArray(data) ? data.length : 0;
    return [
      autoChartRecommendation.type,
      autoChartRecommendation.x_axis || '',
      autoChartRecommendation.y_axis || '',
      groupBy.join('|'),
      rowCount,
      JSON.stringify(metadata.filters_applied || {}),
    ].join('::');
  }, [autoChartRecommendation, groupBy, data, metadata]);

  const initialChartRecommendation = useMemo(() => {
    if (!autoChartRecommendation || !autoChartRecommendationKey) {
      return null;
    }
    return {
      ...autoChartRecommendation,
      key: autoChartRecommendationKey,
    };
  }, [autoChartRecommendation, autoChartRecommendationKey]);

  useEffect(() => {
    if (!initialChartRecommendation) {
      setAiChartReason(null);
      return;
    }
    if (lastAutoChartKeyRef.current === initialChartRecommendation.key) {
      return;
    }

    lastAutoChartKeyRef.current = initialChartRecommendation.key;
    setShowCharts(true);
    setAiChartReason(
      initialChartRecommendation.reason ||
      'it best fits the grouped metrics returned for this query'
    );
  }, [initialChartRecommendation]);

  useEffect(() => {
    setFeedbackSubmitting(false);
    setFeedbackSelection(null);
    setFeedbackNote('');
    setFeedbackError(null);
    setFeedbackSuccess(false);
  }, [nlSourceQuery, metadata.total_matching_rows, metadata.returned_groups]);

  // Apply column filters to displayData
  const filteredData = useMemo(() => {
    if (!columnFilters || Object.keys(columnFilters).length === 0) {
      return displayData;
    }
    
    return displayData.filter(row => {
      return Object.entries(columnFilters).every(([column, selectedValues]) => {
        if (!selectedValues || selectedValues.length === 0) return true;
        
        const cellValue = row[column];
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
      
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
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
    setTimeout(() => {
      if (chartPanelRef.current && chartPanelRef.current.addBarChart) {
        chartPanelRef.current.addBarChart();
      }
    }, 100);
  };

  const handleAddScatterChart = () => {
    setShowCharts(true);
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
    setPage(0);
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
    setPage(0);
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

  const handleFilterClick = (event, column) => {
    setFilterAnchorEl(event.currentTarget);
    setFilterColumn(column);
  };

  const handleFilterClose = () => {
    setFilterAnchorEl(null);
    setFilterColumn(null);
  };

  const isFilterableColumn = (column) => {
    return groupBy.includes(column) ||
      ['crease_combo', 'ball_direction', 'bowl_style', 'bowl_kind', 'striker_batter_type', 'non_striker_batter_type', 'venue', 'batting_team', 'bowling_team', 'batter', 'bowler', 'competition'].includes(column);
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
    
    const exportData = sortedData;
    const headers = Object.keys(exportData[0]);
    
    const csvContent = [
      headers.join(','),
      ...exportData.map(row => 
        headers.map(header => {
          const value = row[header];
          if (value === null || value === undefined) return '';
          if (typeof value === 'string' && value.includes(',')) {
            return `"${value.replace(/"/g, '""')}"`;  
          }
          return value;
        }).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    
    const filterSuffix = Object.keys(columnFilters).length > 0 ? '-filtered' : '';
    const filename = `cricket-query${filterSuffix}-${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', filename);
    
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const submitFeedback = async ({ feedback, refinedQueryText = null }) => {
    const normalizedQuery = String(nlSourceQuery || '').trim();
    if (!normalizedQuery) {
      setFeedbackError('Feedback is available only for natural-language queries.');
      return false;
    }

    try {
      setFeedbackSubmitting(true);
      setFeedbackError(null);

      const payload = {
        query_text: normalizedQuery,
        feedback,
        execution_success: true,
        result_row_count: Number.isInteger(resultRowCount) ? resultRowCount : 0,
      };

      if (refinedQueryText) {
        payload.refined_query_text = refinedQueryText;
      }

      await axios.post(`${config.API_URL}/nl2query/feedback`, payload);
      setFeedbackSuccess(true);
      return true;
    } catch (err) {
      const detail = err.response?.data?.detail;
      setFeedbackError(typeof detail === 'string' ? detail : 'Failed to submit feedback. Please try again.');
      return false;
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const handleThumbsUp = async () => {
    setFeedbackSelection('good');
    const ok = await submitFeedback({ feedback: 'good' });
    if (!ok) {
      setFeedbackSelection(null);
    }
  };

  const handleThumbsDown = () => {
    setFeedbackSelection('bad');
    setFeedbackSuccess(false);
    setFeedbackError(null);
  };

  const handleBadFeedbackSubmit = async () => {
    const note = feedbackNote.trim();
    const ok = await submitFeedback({
      feedback: 'bad',
      refinedQueryText: note || null,
    });
    if (!ok) {
      return;
    }
    setFeedbackSelection('submitted');
  };
  
  const formatValue = (value, key) => {
    if (value === null || value === undefined) return 'N/A';

    if (typeof value === 'string' && isTeamNameColumn(key)) {
      const normalized = value.trim().toLowerCase();
      if (['no result', 'tie', 'draw', 'abandoned', 'n/a'].includes(normalized)) {
        return value;
      }
      return <CondensedName name={value} type="team" />;
    }

    if (typeof value === 'string' && isPlayerNameColumn(key)) {
      return <CondensedName name={value} type="player" />;
    }

    if (key.includes('percentage') || key === 'percent_balls') {
      return `${Number(value).toFixed(1)}%`;
    }
    if (key === 'strike_rate') {
      return Number(value).toFixed(1);
    }
    if (key === 'average' || key === 'balls_per_dismissal') {
      return Number(value).toFixed(2);
    }
    if (key === 'economy' || key === 'overs' || key === 'balls_per_wicket') {
      return Number(value).toFixed(2);
    }
    if (key === 'year') {
      return value;
    }
    if (typeof value === 'number' && value > 1000) {
      return value.toLocaleString();
    }
    
    return value;
  };
  
  const getColumnDisplayName = (key) => {
    const displayNames = {
      'match_id': 'Match',
      'crease_combo': 'Crease',
      'ball_direction': 'Direction',
      'bowl_style': 'Style',
      'bowl_kind': 'Kind',
      'striker_batter_type': 'Striker',
      'non_striker_batter_type': 'Non-Striker',
      'runs_off_bat': 'Runs',
      'batting_team': 'Bat Team',
      'bowling_team': 'Bowl Team',
      'strike_rate': 'SR',
      'dot_percentage': 'Dot%',
      'boundary_percentage': 'Bndry%',
      'percent_balls': '%Balls',
      'balls_per_dismissal': 'B/W',
      'control_percentage': 'Ctrl%',
      'year': 'Year',
      'runs_conceded': 'Runs',
      'fours_conceded': 'Fours',
      'sixes_conceded': 'Sixes',
      'economy': 'Economy',
      'balls_per_wicket': 'B/W',
      'overs': 'Overs',
      'innings_count': 'Innings',
      'balls_faced': 'Balls'
    };
    
    return displayNames[key] || key.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };
  
  const getGroupingColumns = () => {
    if (!isGrouped || displayData.length === 0) return [];
    
    const sampleRow = displayData[0];
    return Object.keys(sampleRow).filter(key => groupBy.includes(key));
  };
  
  const getVisibleColumns = () => {
    if (displayData.length === 0) return [];
    
    const allColumns = Object.keys(displayData[0]);
    
    if (isMobile) {
      if (isGrouped) {
        return [...getGroupingColumns(), ...selectedMetricColumns].filter(col => allColumns.includes(col));
      } else {
        return ['batter', 'bowler', 'runs_off_bat', 'crease_combo'].filter(col => allColumns.includes(col));
      }
    }
    
    return allColumns.filter(col => !['is_summary', 'summary_level'].includes(col));
  };
  
  const paginatedData = sortedData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  const visibleColumns = getVisibleColumns();

  return (
    <Box>
      {/* Results Summary */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ pb: headerCollapsed ? '12px !important' : undefined }}>
          {/* Compact summary pill — always visible */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
            }}
            onClick={() => setHeaderCollapsed(prev => !prev)}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="h6" sx={{ fontSize: headerCollapsed ? '0.95rem' : undefined }}>
                Query Results
              </Typography>
              {headerCollapsed && (
                <>
                  <Chip
                    label={isGrouped
                      ? `${metadata.total_groups || metadata.returned_groups} rows`
                      : `${(metadata.total_matching_rows || 0).toLocaleString()} deliveries`}
                    color="primary"
                    size="small"
                  />
                  {isGrouped && (
                    <Chip
                      label={`Grouped by ${groupBy.join(', ')}`}
                      variant="outlined"
                      size="small"
                    />
                  )}
                </>
              )}
            </Box>
            <IconButton size="small">
              {headerCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
            </IconButton>
          </Box>

          {/* Full header content — collapsible */}
          <Collapse in={!headerCollapsed}>
            <Grid container spacing={2} alignItems="center" sx={{ mt: 0.5 }}>
              <Grid item xs={12} sm={8}>
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

                  {metadata.total_innings_in_query !== undefined && metadata.total_innings_in_query !== null && (
                    <Chip
                      label={`${Number(metadata.total_innings_in_query).toLocaleString()} total innings`}
                      variant="outlined"
                      size="small"
                    />
                  )}

                  {sortConfig.key && (
                    <Chip
                      label={`Sorted by: ${getColumnDisplayName(sortConfig.key)} (${sortConfig.direction})`}
                      variant="outlined"
                      size="small"
                      color="secondary"
                    />
                  )}

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

                {aiChartReason && (
                  <Alert
                    severity="info"
                    sx={{ mt: 1.25 }}
                    onClose={() => setAiChartReason(null)}
                  >
                    {`AI suggested this chart because: ${aiChartReason}`}
                  </Alert>
                )}
              </Grid>

              <Grid item xs={12} sm={4} sx={{ textAlign: { xs: 'left', sm: 'right' } }}>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: { xs: 'flex-start', sm: 'flex-end' } }}>
                  {isGrouped && data.length > 0 && Object.keys(columnFilters).length > 0 && (
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
          </Collapse>
        </CardContent>
      </Card>
      
      {/* Pitch Map Visualization - use dataWithPercentBalls which has percent_balls */}
      {showPitchMap && pitchMapMode && isGrouped && (
        <Box sx={{ mb: 3 }}>
          <PitchMapContainer
            data={dataWithPercentBalls}
            groupBy={groupBy}
            filters={filters || metadata?.filters_applied || {}}
          />
        </Box>
      )}
      
      {/* Column Selector for Mobile Grouped Results */}
      {isMobile && isGrouped && availableMetricColumns.length > 0 && (
        <Box sx={{ mb: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {availableMetricColumns.map(col => (
            <Chip
              key={col}
              label={getColumnDisplayName(col)}
              size="small"
              variant={selectedMetricColumns.includes(col) ? 'filled' : 'outlined'}
              color={selectedMetricColumns.includes(col) ? 'primary' : 'default'}
              onClick={() => {
                setSelectedMetricColumns(prev =>
                  prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
                );
              }}
            />
          ))}
        </Box>
      )}

      {/* Data Table with Sorting */}
      <Paper>
        <TableContainer sx={{ maxHeight: isMobile ? 400 : 600 }}>
          <Table stickyHeader size={isMobile ? "small" : "medium"}>
            <TableHead>
              <TableRow>
                {visibleColumns.map((column, colIndex) => {
                  const groupByIndex = groupBy.indexOf(column);
                  const isGroupByCol = groupByIndex !== -1;
                  const hasActiveFilter = columnFilters[column] && columnFilters[column].length > 0;
                  const filterable = isGrouped && isFilterableColumn(column);
                  return (
                  <TableCell key={column} sx={{
                    fontWeight: 600,
                    fontSize: isMobile ? '0.7rem' : '0.75rem',
                    whiteSpace: 'nowrap',
                    textTransform: 'uppercase',
                    letterSpacing: '0.03em',
                    color: 'text.secondary',
                    py: isMobile ? 0.5 : 1,
                    px: isMobile ? 0.75 : 1.5,
                    ...(isGroupByCol && {
                      position: 'sticky',
                      left: groupByIndex === 0 ? 0 : 'auto',
                      backgroundColor: 'background.paper',
                      zIndex: groupByIndex === 0 ? 3 : 1,
                    })
                  }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                      <TableSortLabel
                        active={sortConfig.key === column}
                        direction={sortConfig.key === column ? sortConfig.direction : 'asc'}
                        onClick={() => handleSort(column)}
                        hideSortIcon={sortConfig.key !== column}
                        sx={{
                          fontSize: 'inherit',
                          '& .MuiTableSortLabel-icon': {
                            opacity: sortConfig.key === column ? 1 : 0,
                            fontSize: '0.875rem',
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
                      {filterable && (
                        <IconButton
                          size="small"
                          onClick={(e) => handleFilterClick(e, column)}
                          sx={{
                            p: 0.25,
                            ml: 0.25,
                            color: hasActiveFilter ? 'warning.main' : 'action.disabled',
                            '&:hover': { color: hasActiveFilter ? 'warning.dark' : 'primary.main' },
                          }}
                        >
                          <FilterListIcon sx={{ fontSize: '0.875rem' }} />
                        </IconButton>
                      )}
                    </Box>
                  </TableCell>
                  );
                })}
              </TableRow>
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
                  {visibleColumns.map((column) => {
                    const groupByIndex = groupBy.indexOf(column);
                    const isGroupByCol = groupByIndex !== -1;
                    return (
                    <TableCell key={column} sx={{
                      whiteSpace: 'nowrap',
                      ...(isGroupByCol && {
                        position: 'sticky',
                        left: groupByIndex === 0 ? 0 : 'auto',
                        backgroundColor: row.is_summary ? 'grey.100' : 'background.paper',
                        zIndex: groupByIndex === 0 ? 1 : 0,
                      })
                    }}>
                      {row.is_summary && column !== groupBy[0] && groupBy.includes(column) ?
                        '— Total —' :
                        formatValue(row[column], column)
                      }
                    </TableCell>
                    );
                  })}
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

      {/* Filter Popover */}
      <Popover
        open={Boolean(filterAnchorEl)}
        anchorEl={filterAnchorEl}
        onClose={handleFilterClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        slotProps={{ paper: { sx: { p: 1, minWidth: 200 } } }}
      >
        {filterColumn && (
          <ColumnFilter
            column={filterColumn}
            displayName={getColumnDisplayName(filterColumn)}
            uniqueValues={getUniqueValuesForColumn(filterColumn)}
            selectedValues={columnFilters[filterColumn]}
            onChange={handleColumnFilter}
            onClear={clearColumnFilter}
            isMobile={isMobile}
          />
        )}
      </Popover>

      {/* Chart Panel */}
      <ChartPanel 
        ref={chartPanelRef}
        data={sortedData.filter(row => !row.is_summary)}
        groupBy={groupBy}
        initialRecommendation={initialChartRecommendation}
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

      {nlInterpretation && (
        <Box sx={{ mt: 2 }}>
          <NLInterpretation
            interpretation={nlInterpretation}
            confidence={nlConfidence}
            rawFilters={nlRawFilters}
            onSuggestionClick={onSuggestionClick}
            onClose={onDismissInterpretation}
            disabled={interpretationDisabled}
          />
        </Box>
      )}

      {String(nlSourceQuery || '').trim() && (
        <Paper
          elevation={0}
          sx={{
            mt: 2,
            p: 1.5,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'background.default',
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              Was this helpful?
            </Typography>
            <IconButton
              size="small"
              onClick={handleThumbsUp}
              disabled={feedbackSubmitting || feedbackSuccess}
              color={feedbackSelection === 'good' || feedbackSuccess ? 'success' : 'default'}
              aria-label="Helpful"
            >
              <ThumbUpAltOutlinedIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={handleThumbsDown}
              disabled={feedbackSubmitting || feedbackSuccess}
              color={feedbackSelection === 'bad' ? 'error' : 'default'}
              aria-label="Not helpful"
            >
              <ThumbDownAltOutlinedIcon fontSize="small" />
            </IconButton>
          </Stack>

          {feedbackSelection === 'bad' && !feedbackSuccess && (
            <Box sx={{ mt: 1 }}>
              <TextField
                size="small"
                fullWidth
                label="What went wrong?"
                placeholder="e.g. wrong player, should use batting mode"
                value={feedbackNote}
                onChange={(event) => setFeedbackNote(event.target.value)}
                disabled={feedbackSubmitting}
              />
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleBadFeedbackSubmit}
                  disabled={feedbackSubmitting || !feedbackNote.trim()}
                >
                  {feedbackSubmitting ? 'Submitting...' : 'Submit feedback'}
                </Button>
              </Box>
            </Box>
          )}

          {feedbackSuccess && (
            <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 0.75 }}>
              Thanks! Feedback recorded.
            </Typography>
          )}

          {feedbackError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {feedbackError}
            </Alert>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default QueryResults;
