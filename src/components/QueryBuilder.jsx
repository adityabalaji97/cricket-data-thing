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

// Prefilled query examples showcasing new delivery_details features
const PREFILLED_QUERIES = [
  {
    title: "Chennai Super Kings batters by phase in 2025",
    description: "Analyze CSK batting performance across different match phases",
    filters: {
      batting_teams: ["Chennai Super Kings"],
      start_date: "2025-01-01",
      leagues: ["IPL"],
      min_balls: 30
    },
    groupBy: ["batter", "phase"],
    tags: ["IPL", "CSK", "Batting", "Phase"]
  },
  {
    title: "Short ball response - shot distribution",
    description: "See what shots batters play to short length deliveries",
    filters: {
      length: ["SHORT"],
      min_balls: 100
    },
    groupBy: ["shot"],
    tags: ["Length", "Shot", "Short Ball"]
  },
  {
    title: "Spin bowling by line and length",
    description: "Analyze spin bowler strategies by line and length combinations",
    filters: {
      bowl_kind: ["spin bowler"],
      min_balls: 50
    },
    groupBy: ["line", "length"],
    tags: ["Spin", "Line", "Length"]
  },
  {
    title: "Controlled vs uncontrolled shots by wagon zone",
    description: "Where do batters hit with control vs without control?",
    filters: {
      min_balls: 100
    },
    groupBy: ["control", "wagon_zone"],
    tags: ["Control", "Wagon Wheel", "Shot Quality"]
  },
  {
    title: "Powerplay pace bowling analysis",
    description: "Study pace bowling strategies in powerplay overs",
    filters: {
      leagues: ["IPL"],
      start_date: "2024-01-01",
      over_min: 0,
      over_max: 5,
      bowl_kind: ["pace bowler"],
      min_balls: 50
    },
    groupBy: ["bowl_style", "length"],
    tags: ["Powerplay", "Pace", "IPL"]
  },
  {
    title: "LHB vs RHB performance against spin",
    description: "Compare left and right hand batters against spin bowling",
    filters: {
      bowl_kind: ["spin bowler"],
      min_balls: 100
    },
    groupBy: ["bat_hand", "bowl_style"],
    tags: ["LHB", "RHB", "Spin", "Matchup"]
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
    
    // Match context
    innings: null,
    over_min: null,
    over_max: null,
    
    // Batter filters
    bat_hand: null,
    
    // Bowler filters
    bowl_style: [],
    bowl_kind: [],
    
    // Delivery detail filters (NEW)
    line: [],
    length: [],
    shot: [],
    control: null,
    wagon_zone: [],
    
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
    top_teams: 10,
    
    // Summary rows
    show_summary_rows: false
  });
  
  const [groupBy, setGroupBy] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [availableColumns, setAvailableColumns] = useState(null);
  const [queryTab, setQueryTab] = useState(0);
  const [showPrefilledQueries, setShowPrefilledQueries] = useState(true);
  const [isAutoExecuting, setIsAutoExecuting] = useState(false);
  const [hasLoadedFromUrl, setHasLoadedFromUrl] = useState(false);
  
  // Load filters from URL on mount
  useEffect(() => {
    const urlFilters = getFiltersFromUrl();
    const urlGroupBy = getGroupByFromUrl();
    
    if (currentParams && currentParams.length > 1 && !hasLoadedFromUrl) {
      setFilters(prevFilters => ({
        ...prevFilters,
        ...urlFilters
      }));
      setGroupBy(urlGroupBy);
      setShowPrefilledQueries(false);
      setHasLoadedFromUrl(true);
      setIsAutoExecuting(true);
      
      setTimeout(() => {
        executeQueryFromUrl(urlFilters, urlGroupBy);
      }, 500);
    }
  }, [currentParams, hasLoadedFromUrl]);
  
  // Fetch available columns
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
  
  const executeQueryFromUrl = async (urlFilters, urlGroupBy) => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      
      Object.entries(urlFilters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => params.append(key, item));
          } else {
            params.append(key, value);
          }
        }
      });
      
      urlGroupBy.forEach(col => params.append('group_by', col));

      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
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
  
  const executeQuery = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => params.append(key, item));
          } else {
            params.append(key, value);
          }
        }
      });
      
      groupBy.forEach(col => params.append('group_by', col));
      
      if (!isAutoExecuting) {
        const newParams = filtersToUrlParams(filters, groupBy);
        const newUrl = `${window.location.pathname}?${newParams}`;
        window.history.replaceState({}, '', newUrl);
      }

      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
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
      innings: null,
      over_min: null,
      over_max: null,
      bat_hand: null,
      bowl_style: [],
      bowl_kind: [],
      line: [],
      length: [],
      shot: [],
      control: null,
      wagon_zone: [],
      min_balls: null,
      max_balls: null,
      min_runs: null,
      max_runs: null,
      limit: 1000,
      offset: 0,
      include_international: false,
      top_teams: 10,
      show_summary_rows: false
    });
    setGroupBy([]);
    setResults(null);
    setQueryTab(0);
    setShowPrefilledQueries(true);
    setHasLoadedFromUrl(false);
    setIsAutoExecuting(false);
    window.history.replaceState({}, '', window.location.pathname);
  };
  
  const selectPrefilledQuery = (query) => {
    setFilters(prevFilters => ({
      ...prevFilters,
      ...query.filters
    }));
    setGroupBy(query.groupBy);
    setShowPrefilledQueries(false);
    setQueryTab(0);
    setHasLoadedFromUrl(false);
    setIsAutoExecuting(false);
  };
  
  const hasValidFilters = () => {
    const filterKeys = [
      'venue', 'start_date', 'end_date', 'leagues', 'teams', 'batting_teams', 'bowling_teams',
      'players', 'batters', 'bowlers', 'bat_hand', 'bowl_style', 'bowl_kind',
      'line', 'length', 'shot', 'control', 'wagon_zone',
      'innings', 'over_min', 'over_max'
    ];
    
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
        Build custom queries to analyze ball-by-ball cricket data. 
        Filter by line, length, shot type, wagon wheel zones, and more.
      </Typography>
      
      {/* Prefilled Query Cards */}
      {showPrefilledQueries && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            🚀 Quick Start Queries
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click on any query below to get started:
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
              filters={filters}
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
