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
  useTheme
} from '@mui/material';
import QueryFilters from './QueryFilters';
import QueryResults from './QueryResults';
import axios from 'axios';
import config from '../config';

const QueryBuilder = ({ isMobile }) => {
  const theme = useTheme();
  const [filters, setFilters] = useState({
    // Basic filters
    venue: null,
    start_date: null,
    end_date: null,
    leagues: [],
    teams: [],
    players: [],
    
    // Column-specific filters
    crease_combo: null,
    ball_direction: null,
    bowler_type: null,
    striker_batter_type: null,
    non_striker_batter_type: null,
    innings: null,
    over_min: null,
    over_max: null,
    wicket_type: null,
    
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
      
      // Debug: Log the final query parameters
      console.log('Query Parameters being sent:', Object.fromEntries(params.entries()));
      console.log('Date filters:', {
        start_date: filters.start_date,
        end_date: filters.end_date
      });
      
      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
      
      // Switch to results tab
      setQueryTab(1);
      
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
      players: [],
      crease_combo: null,
      ball_direction: null,
      bowler_type: null,
      striker_batter_type: null,
      non_striker_batter_type: null,
      innings: null,
      over_min: null,
      over_max: null,
      wicket_type: null,
      limit: 1000,
      offset: 0,
      include_international: false,
      top_teams: 10
    });
    setGroupBy([]);
    setResults(null);
    setQueryTab(0);
  };
  
  const hasValidFilters = () => {
    // At least one filter must be applied (excluding pagination and international settings)
    const filterKeys = ['venue', 'start_date', 'end_date', 'leagues', 'teams', 'players', 
                       'crease_combo', 'ball_direction', 'bowler_type', 'striker_batter_type',
                       'non_striker_batter_type', 'innings', 'over_min', 'over_max', 'wicket_type'];
    
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
