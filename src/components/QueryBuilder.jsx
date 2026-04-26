import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Tabs,
  Tab
} from '@mui/material';
import QueryFilters from './QueryFilters';
import QueryResults from './QueryResults';
import NLQueryInput from './NLQueryInput';
import { useUrlParams, filtersToUrlParams } from '../utils/urlParamParser';
import axios from 'axios';
import config from '../config';

const getDefaultFilters = () => ({
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
  match_outcome: [],
  is_chase: null,
  chase_outcome: [],
  toss_decision: [],

  // Query mode (default is fully backward-compatible delivery mode)
  query_mode: 'delivery',

  // Batter filters
  bat_hand: null,

  // Bowler filters
  bowl_style: [],
  bowl_kind: [],

  // Delivery detail filters
  line: [],
  length: [],
  shot: [],
  control: null,
  wagon_zone: [],
  dismissal: [],

  // Grouped result filters
  min_balls: null,
  max_balls: null,
  min_runs: null,
  max_runs: null,
  min_wickets: null,
  max_wickets: null,

  // Pagination
  limit: 1000,
  offset: 0,

  // International matches
  include_international: false,
  top_teams: 10,

  // Summary rows
  show_summary_rows: false
});

const parseSuggestionFragment = (suggestion) => {
  const text = String(suggestion || '').trim();
  if (!text) {
    return '';
  }

  const quotedMatch = text.match(/["']([^"']+)["']/);
  if (quotedMatch?.[1]) {
    return quotedMatch[1].trim();
  }

  const lowered = text
    .replace(/^try\s+(adding|using|including)\s+/i, '')
    .replace(/^add\s+/i, '')
    .replace(/^include\s+/i, '')
    .replace(/^group(?:ed)?\s+by\s+/i, 'grouped by ')
    .replace(/\s+to\s+see\b.*$/i, '')
    .replace(/\s+to\s+compare\b.*$/i, '')
    .replace(/\s+for\s+more\b.*$/i, '')
    .trim();

  return lowered.replace(/\.$/, '');
};

const buildRefinedQuery = (baseQuery, suggestion) => {
  const fragment = parseSuggestionFragment(suggestion);
  const source = String(baseQuery || '').trim();

  if (!fragment) {
    return source;
  }
  if (!source) {
    return fragment;
  }
  if (source.toLowerCase().includes(fragment.toLowerCase())) {
    return source;
  }
  return `${source} ${fragment}`.trim();
};

const QueryBuilder = ({ isMobile }) => {
  const { getFiltersFromUrl, getGroupByFromUrl, currentParams } = useUrlParams();
  
  const [filters, setFilters] = useState(getDefaultFilters);
  
  const [groupBy, setGroupBy] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [availableColumns, setAvailableColumns] = useState(null);
  const [queryTab, setQueryTab] = useState(0);
  const [, setIsAutoExecuting] = useState(false);
  const [hasLoadedFromUrl, setHasLoadedFromUrl] = useState(false);
  const [nlInterpretation, setNlInterpretation] = useState(null);
  const [nlConfidence, setNlConfidence] = useState('medium');
  const [nlSourceQuery, setNlSourceQuery] = useState('');
  const [nlRawFilters, setNlRawFilters] = useState({});
  const [nlRecommendedColumns, setNlRecommendedColumns] = useState([]);
  const [nlRecommendedChart, setNlRecommendedChart] = useState(null);
  const [isApplyingSuggestion, setIsApplyingSuggestion] = useState(false);
  // ball_aggregation toggle: only meaningful when ball or ball_in_spell is in
  // the active group_by; otherwise the backend ignores it.
  const [ballAggregation, setBallAggregation] = useState('snapshot');
  const executeQueryRef = useRef(null);
  const nlInputRef = useRef(null);

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
        if (key === 'query_mode' && value === 'delivery') {
          return;
        }
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => params.append(key, item));
          } else {
            params.append(key, value);
          }
        }
      });
      
      urlGroupBy.forEach(col => params.append('group_by', col));
      if (ballAggregation && ballAggregation !== 'snapshot') {
        params.append('ball_aggregation', ballAggregation);
      }

      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
      setQueryTab(1);

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
        if (key === 'query_mode' && value === 'delivery') {
          return;
        }
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => params.append(key, item));
          } else {
            params.append(key, value);
          }
        }
      });
      
      groupBy.forEach(col => params.append('group_by', col));
      if (ballAggregation && ballAggregation !== 'snapshot') {
        params.append('ball_aggregation', ballAggregation);
      }

      // Always update URL so queries are shareable
      const newParams = filtersToUrlParams(filters, groupBy);
      const newUrl = `${window.location.pathname}?${newParams}`;
      window.history.replaceState({}, '', newUrl);

      const response = await axios.get(`${config.API_URL}/query/deliveries?${params.toString()}`);
      setResults(response.data);
      setQueryTab(1);
      
    } catch (error) {
      console.error('Error executing query:', error);
      setError(error.response?.data?.detail || 'Failed to execute query');
    } finally {
      setLoading(false);
    }
  };

  // Keep ref current for async callbacks
  executeQueryRef.current = executeQuery;

  const clearFilters = () => {
    setFilters(getDefaultFilters());
    setGroupBy([]);
    setResults(null);
    setQueryTab(0);
    setHasLoadedFromUrl(false);
    setIsAutoExecuting(false);
    setNlInterpretation(null);
    setNlConfidence('medium');
    setNlSourceQuery('');
    setNlRawFilters({});
    setNlRecommendedColumns([]);
    setNlRecommendedChart(null);
    window.history.replaceState({}, '', window.location.pathname);
  };
  
  const handleNLFilters = ({
    queryText,
    filters: nlFilters,
    groupBy: nlGroupBy,
    explanation,
    confidence,
    suggestions,
    recommendedColumns,
    recommendedChart,
    interpretation,
  }) => {
    // Reset to defaults then apply NL filters
    const defaultFilters = getDefaultFilters();

    const newFilters = { ...defaultFilters, ...(nlFilters || {}) };
    const newGroupBy = nlGroupBy || [];
    const interpretationPayload = interpretation || {
      summary: explanation || '',
      parsed_entities: [],
      suggestions: suggestions || [],
    };

    setFilters(newFilters);
    setGroupBy(newGroupBy);
    setNlInterpretation(interpretationPayload);
    setNlConfidence(confidence || 'medium');
    setNlSourceQuery((queryText || '').trim());
    setNlRawFilters(nlFilters || {});
    setNlRecommendedColumns(Array.isArray(recommendedColumns) ? recommendedColumns : []);
    setNlRecommendedChart(recommendedChart || null);
    setQueryTab(0);
    setHasLoadedFromUrl(false);

    // Update URL immediately so the query is shareable even before execution
    const newParams = filtersToUrlParams(newFilters, newGroupBy);
    const newUrl = `${window.location.pathname}?${newParams}`;
    window.history.replaceState({}, '', newUrl);

    // Auto-execute for high confidence, just populate for medium/low
    if (confidence === 'high') {
      setIsAutoExecuting(true);
      setTimeout(() => {
        executeQueryRef.current();
      }, 300);
    }
  };

  const dismissInterpretation = () => {
    setNlInterpretation(null);
    setNlRawFilters({});
  };

  const applySuggestion = async (suggestion) => {
    if (!nlInputRef.current?.runQuery) {
      return;
    }

    const refinedQuery = buildRefinedQuery(nlSourceQuery, suggestion);
    if (!refinedQuery) {
      return;
    }

    try {
      setIsApplyingSuggestion(true);
      setError(null);
      await nlInputRef.current.runQuery(refinedQuery);
    } finally {
      setIsApplyingSuggestion(false);
    }
  };

  const hasValidFilters = () => {
    const filterKeys = [
      'venue', 'start_date', 'end_date', 'leagues', 'teams', 'batting_teams', 'bowling_teams',
      'players', 'batters', 'bowlers', 'bat_hand', 'bowl_style', 'bowl_kind',
      'line', 'length', 'shot', 'control', 'wagon_zone',
      'innings', 'over_min', 'over_max',
      'match_outcome', 'is_chase', 'chase_outcome', 'toss_decision',
      'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets'
    ];
    
    return filterKeys.some(key => {
      const value = filters[key];
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== null && value !== undefined && value !== '';
    });
  };

  const canExecute = !!availableColumns && hasValidFilters() && !loading && !isApplyingSuggestion;
  const showMobileActionBar = isMobile && queryTab === 0;
  
  return (
    <Box sx={{ my: isMobile ? 2 : 3 }}>
      <Typography variant={isMobile ? "h5" : "h4"} gutterBottom>
        🏏 Query Builder
      </Typography>
      
      <Typography variant={isMobile ? "body2" : "body1"} color="text.secondary" sx={{ mb: 2.5 }}>
        Build custom queries to analyze ball-by-ball cricket data.
        Filter by line, length, shot type, wagon wheel zones, and more.
      </Typography>

      <NLQueryInput
        ref={nlInputRef}
        onFiltersGenerated={handleNLFilters}
        disabled={loading || isApplyingSuggestion}
      />

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
        
        <Box sx={{ p: isMobile ? 2 : 3, pb: showMobileActionBar ? 10 : (isMobile ? 2 : 3) }}>
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
              recommendedColumns={nlRecommendedColumns}
              recommendedChart={nlRecommendedChart || results?.metadata?.recommended_chart || null}
              nlInterpretation={nlInterpretation}
              nlConfidence={nlConfidence}
              nlRawFilters={nlRawFilters}
              nlSourceQuery={nlSourceQuery}
              onSuggestionClick={applySuggestion}
              onDismissInterpretation={dismissInterpretation}
              interpretationDisabled={loading || isApplyingSuggestion}
              isMobile={isMobile}
              ballAggregation={ballAggregation}
              onBallAggregationChange={(mode) => {
                setBallAggregation(mode);
                // Re-fetch with the new mode. executeQueryRef guards against
                // a stale-closure call before mount.
                setTimeout(() => executeQueryRef.current && executeQueryRef.current(), 0);
              }}
            />
          )}
        </Box>
        
        {!showMobileActionBar && (
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
              disabled={!canExecute}
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
        )}
      </Paper>

      {showMobileActionBar && (
        <Box
          sx={{
            position: 'fixed',
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 1200,
            px: 1.5,
            pb: 'max(10px, env(safe-area-inset-bottom))',
            pt: 1,
            bgcolor: 'rgba(255,255,255,0.97)',
            borderTop: 1,
            borderColor: 'divider',
            backdropFilter: 'blur(6px)'
          }}
        >
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              onClick={executeQuery}
              disabled={!canExecute}
              startIcon={loading ? <CircularProgress size={16} color="inherit" /> : null}
              sx={{ flex: 1 }}
            >
              {loading ? 'Querying...' : 'Execute'}
            </Button>
            <Button
              variant="outlined"
              onClick={clearFilters}
              disabled={loading}
              sx={{ minWidth: 96 }}
            >
              Clear
            </Button>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 0.5 }}>
            {!hasValidFilters() ? 'Add at least one filter' : 'Ready to run'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default QueryBuilder;
