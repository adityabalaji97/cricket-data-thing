import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  useMediaQuery,
  useTheme,
  Card,
  CardContent,
  Grid,
  Chip
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import QueryFilters from './QueryFilters';
import QueryResults from './QueryResults';
import { useUrlParams, filtersToUrlParams } from '../utils/urlParamParser';
import axios from 'axios';
import config from '../config';

// Helpful prefilled query links
const PREFILLED_QUERIES = [
  {
    title: "Chennai Super Kings batters grouped by phase and batter in 2025",
    description: "Analyze CSK batting performance across different match phases",
    filters: {
      batting_teams: ["Chennai Super Kings"],
      start_date: "2025-01-01",
      leagues: ["IPL"],
      min_balls: 30
    },
    groupBy: ["batter", "phase"],
    tags: ["IPL", "CSK", "Batting", "Phase Analysis"]
  },
  {
    title: "V Kohli facing spinners (LC, LO, RL, RO) grouped by phase and ball direction in IPL since 2023",
    description: "Study how Kohli performs against spin bowling by phase and ball direction",
    filters: {
      batters: ["V Kohli"],
      bowler_type: ["LC", "LO", "RL", "RO"],
      leagues: ["IPL"],
      start_date: "2023-01-01",
      min_balls: 10
    },
    groupBy: ["phase", "ball_direction"],
    tags: ["Kohli", "Spinners", "IPL", "Phase", "Ball Direction"]
  },
  {
    title: "T20 batting since 2020 grouped by crease_combo",
    description: "Analyze left-right batting combinations against spinners across all T20s",
    filters: {
      start_date: "2020-01-01",
      bowler_type: ["LO", "LC", "RO", "RL"],
      min_balls: 100
    },
    groupBy: ["crease_combo"],
    tags: ["T20", "Crease Combo", "Spinners", "Left-Right"]
  },
  {
    title: "Powerplay bowling by type in IPL 2025",
    description: "Study bowling strategies in powerplay overs",
    filters: {
      leagues: ["IPL"],
      start_date: "2025-01-01",
      end_date: "2025-12-31",
      over_min: 0,
      over_max: 5,
      min_balls: 50
    },
    groupBy: ["bowler_type"],
    tags: ["IPL", "Powerplay", "Bowling", "Strategy"]
  },
  {
    title: "Death overs performance by venue in IPL 2025",
    description: "Compare how different IPL venues affect death overs scoring",
    filters: {
      leagues: ["IPL"],
      start_date: "2025-01-01",
      over_min: 16,
      over_max: 19,
      min_balls: 20
    },
    groupBy: ["venue", "phase"],
    tags: ["Death Overs", "IPL", "Venues", "2025"]
  },
  {
    title: "Mumbai Indians' pace bowling at Wankhede",
    description: "Analyze MI's pace bowling performance at their home venue",
    filters: {
      bowling_teams: ["Mumbai Indians"],
      venue: "Wankhede Stadium, Mumbai",
      bowler_type: ["RF", "RM", "LF", "LM"],
      min_balls: 20
    },
    groupBy: ["bowler_type", "phase"],
    tags: ["MI", "Wankhede", "Pace Bowling", "Home Venue"]
  }
];

const PrefilledQueryCard = ({ query, onSelect }) => (
  <Card 
    sx={{ 
      cursor: 'pointer', 
      transition: 'all 0.2s',
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: 3
      }
    }}
    onClick={() => onSelect(query)}
  >
    <CardContent sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 1 }}>
        {query.title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {query.description}
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {query.tags.map((tag, index) => (
          <Chip 
            key={index} 
            label={tag} 
            size="small" 
            variant="outlined" 
            sx={{ fontSize: '0.7rem', height: 20 }}
          />
        ))}
      </Box>
    </CardContent>
  </Card>
);

const QueryBuilder = ({ isMobile }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { getFiltersFromUrl, getGroupByFromUrl, currentParams } = useUrlParams();
  
  const [filters, setFilters] = useState({
    // Basic filters
    venue: null,
    start_date: null,
    end_date: null,
    leagues: [],
    teams: [],
    batting_teams: [],
    bowling_teams: [],
    players: [],
    batters: [],
    bowlers: [],
    
    // Column-specific filters
    crease_combo: null,
    ball_direction: null,
    bowler_type: [],
    striker_batter_type: null,
    non_striker_batter_type: null,
    innings: null,
    over_min: null,
    over_max: null,
    wicket_type: null,
    
    // Grouped result filters
    min_balls: null,
    max_balls: null,
    min_runs: null,
    max_runs: null,
    
    // Pagination
    limit: 1000,
    offset: 0,
    
    // International matches
    include_international: false,
    top_teams: 10
  });
  
  const [groupBy, setGroupBy] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [availableColumns, setAvailableColumns] = useState(null);
  const [queryTab, setQueryTab] = useState(0); // 0: Filters, 1: Results
  const [showPrefilledQueries, setShowPrefilledQueries] = useState(true);
  const [isAutoExecuting, setIsAutoExecuting] = useState(false); // Track if we're auto-executing from URL
  const [hasLoadedFromUrl, setHasLoadedFromUrl] = useState(false); // Track if we've loaded from URL
  
  // Load filters from URL on component mount
  useEffect(() => {
    const urlFilters = getFiltersFromUrl();
    const urlGroupBy = getGroupByFromUrl();
    
    // Only update if there are actual URL parameters and we haven't loaded from URL yet
    if (currentParams && currentParams.length > 1 && !hasLoadedFromUrl) {
      console.log('Loading filters from URL:', urlFilters, 'GroupBy:', urlGroupBy);
      
      setFilters(prevFilters => ({
        ...prevFilters,
        ...urlFilters
      }));
      setGroupBy(urlGroupBy);
      setShowPrefilledQueries(false);
      setHasLoadedFromUrl(true);
      
      // Set flag that we're about to auto-execute
      setIsAutoExecuting(true);
      
      // If URL has filters, auto-execute the query after a short delay
      // Give time for the state to update before executing
      setTimeout(() => {
        executeQueryFromUrl(urlFilters, urlGroupBy);
      }, 500);
    }
  }, [currentParams, hasLoadedFromUrl]);
  
  // Fetch available columns for dropdowns
  useEffect(() => {
    const fetchAvailableColumns = async () => {
      try {
        const response = await axios.get(`${config.API_URL}/query/deliveries/columns`);
        setAvailableColumns(response.data);
      } catch (error) {
        console.error('Error fetching available columns:', error);
        setError('Failed to load column metadata');
      }
    };
    
    fetchAvailableColumns();
  }, []);
  
  // Function to execute query from URL parameters (doesn't update URL)
  const executeQueryFromUrl = async (urlFilters, urlGroupBy) => {
    try {
      setLoading(true);
      setError(null);
      
      // Build query parameters using URL filters directly
      const params = new URLSearchParams();
      
      // Add filters
      Object.entries(urlFilters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => params.append(key, item));
          } else {
            params.append(key, value);
          }
        }
      });
      
      // Add grouping
      urlGroupBy.forEach(col => params.append('group_by', col));
      
      // Debug: Log the final query parameters
      console.log('Auto-executing query with URL parameters:', Object.fromEntries(params.entries()));
      
      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
      
      // Switch to results tab
      setQueryTab(1);
      setShowPrefilledQueries(false);
      
    } catch (error) {
      console.error('Error executing query from URL:', error);
      setError(error.response?.data?.detail || 'Failed to execute query');
    } finally {
      setLoading(false);
      setIsAutoExecuting(false);
    }
  };
  
  // Function for manual query execution (updates URL)
  const executeQuery = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Build query parameters
      const params = new URLSearchParams();
      
      // Add filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => params.append(key, item));
          } else {
            params.append(key, value);
          }
        }
      });
      
      // Add grouping
      groupBy.forEach(col => params.append('group_by', col));
      
      // Only update URL if this is a manual execution (not auto-executing from URL)
      if (!isAutoExecuting) {
        const newParams = filtersToUrlParams(filters, groupBy);
        const newUrl = `${window.location.pathname}?${newParams}`;
        window.history.replaceState({}, '', newUrl);
      }
      
      // Debug: Log the final query parameters
      console.log('Manual query execution. Parameters being sent:', Object.fromEntries(params.entries()));
      console.log('Date filters:', {
        start_date: filters.start_date,
        end_date: filters.end_date
      });
      
      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
      
      // Switch to results tab
      setQueryTab(1);
      setShowPrefilledQueries(false);
      
    } catch (error) {
      console.error('Error executing query:', error);
      setError(error.response?.data?.detail || 'Failed to execute query');
    } finally {
      setLoading(false);
    }
  };
  
  const clearFilters = () => {
    setFilters({
      venue: null,
      start_date: null,
      end_date: null,
      leagues: [],
      teams: [],
      batting_teams: [],
      bowling_teams: [],
      players: [],
      batters: [],
      bowlers: [],
      crease_combo: null,
      ball_direction: null,
      bowler_type: [],
      striker_batter_type: null,
      non_striker_batter_type: null,
      innings: null,
      over_min: null,
      over_max: null,
      wicket_type: null,
      min_balls: null,
      max_balls: null,
      min_runs: null,
      max_runs: null,
      limit: 1000,
      offset: 0,
      include_international: false,
      top_teams: 10
    });
    setGroupBy([]);
    setResults(null);
    setQueryTab(0);
    setShowPrefilledQueries(true);
    
    // Reset URL loading state
    setHasLoadedFromUrl(false);
    setIsAutoExecuting(false);
    
    // Clear URL parameters
    window.history.replaceState({}, '', window.location.pathname);
  };
  
  const selectPrefilledQuery = (query) => {
    setFilters(prevFilters => ({
      ...prevFilters,
      ...query.filters
    }));
    setGroupBy(query.groupBy);
    setShowPrefilledQueries(false);
    setQueryTab(0); // Show filters tab so user can see what was selected
    
    // Reset URL loading state so user can execute manually
    setHasLoadedFromUrl(false);
    setIsAutoExecuting(false);
  };
  
  const hasValidFilters = () => {
    // At least one filter must be applied (excluding pagination and international settings)
    const filterKeys = ['venue', 'start_date', 'end_date', 'leagues', 'teams', 'batting_teams', 'bowling_teams',
                       'players', 'batters', 'bowlers', 'crease_combo', 'ball_direction', 'bowler_type', 
                       'striker_batter_type', 'non_striker_batter_type', 'innings', 'over_min', 'over_max', 'wicket_type'];
    
    return filterKeys.some(key => {
      const value = filters[key];
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== null && value !== undefined && value !== '';
    });
  };
  
  return (
    <Box sx={{ my: 3 }}>
      <Typography variant="h4" gutterBottom>
        🏏 Query Builder
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Build custom queries to analyze cricket deliveries with flexible filtering and grouping.
        Perfect for studying left-right combinations, bowling matchups, venue patterns, and more.
      </Typography>
      
      {/* Prefilled Query Cards */}
      {showPrefilledQueries && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            🚀 Quick Start Queries
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click on any query below to get started instantly:
          </Typography>
          <Grid container spacing={2}>
            {PREFILLED_QUERIES.map((query, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <PrefilledQueryCard 
                  query={query} 
                  onSelect={selectPrefilledQuery}
                />
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Paper elevation={2} sx={{ overflow: 'hidden' }}>
        <Tabs 
          value={queryTab} 
          onChange={(e, newValue) => setQueryTab(newValue)}
          variant={isMobile ? "fullWidth" : "standard"}
          sx={{ 
            borderBottom: 1, 
            borderColor: 'divider',
            bgcolor: 'grey.50'
          }}
        >
          <Tab 
            label="Filters & Grouping" 
            sx={{ minHeight: 48 }}
          />
          <Tab 
            label={`Results ${results ? `(${results.data?.length || 0})` : ''}`}
            disabled={!results}
            sx={{ minHeight: 48 }}
          />
        </Tabs>
        
        <Box sx={{ p: 3 }}>
          {queryTab === 0 && (
            <QueryFilters
              filters={filters}
              setFilters={setFilters}
              groupBy={groupBy}
              setGroupBy={setGroupBy}
              availableColumns={availableColumns}
              isMobile={isMobile}
            />
          )}
          
          {queryTab === 1 && results && (
            <QueryResults
              results={results}
              groupBy={groupBy}
              isMobile={isMobile}
            />
          )}
        </Box>
        
        <Box sx={{ 
          p: 2, 
          bgcolor: 'grey.50', 
          borderTop: 1, 
          borderColor: 'divider',
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          gap: 2,
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <Box sx={{ 
            display: 'flex', 
            flexDirection: isMobile ? 'column' : 'row',
            gap: 1,
            width: isMobile ? '100%' : 'auto'
          }}>
            <Button 
              variant="contained"
              onClick={executeQuery}
              disabled={loading || !hasValidFilters() || !availableColumns}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
              sx={{ minWidth: 120 }}
            >
              {loading ? 'Querying...' : 'Execute Query'}
            </Button>
            
            <Button 
              variant="outlined"
              onClick={clearFilters}
              disabled={loading}
              sx={{ minWidth: 100 }}
            >
              Clear All
            </Button>
            
            {!showPrefilledQueries && (
              <Button 
                variant="text"
                onClick={() => setShowPrefilledQueries(true)}
                disabled={loading}
                sx={{ minWidth: 120 }}
              >
                Show Quick Queries
              </Button>
            )}
          </Box>
          
          <Typography variant="caption" color="text.secondary" sx={{ 
            textAlign: isMobile ? 'center' : 'right',
            maxWidth: isMobile ? '100%' : 300
          }}>
            {!hasValidFilters() && 'Select at least one filter to execute query'}
            {hasValidFilters() && !loading && 'Ready to execute query'}
            {groupBy.length > 0 && ` • Grouping by: ${groupBy.join(', ')}`}
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default QueryBuilder;
