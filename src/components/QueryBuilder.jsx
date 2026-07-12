import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Collapse,
  Chip,
  IconButton,
  GlobalStyles
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import EditIcon from '@mui/icons-material/Edit';
import MenuIcon from '@mui/icons-material/Menu';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import QueryFilters from './QueryFilters';
import QueryResults from './QueryResults';
import NLQueryInput from './NLQueryInput';
import NLInterpretation from './NLInterpretation';
import { useUrlParams, filtersToUrlParams } from '../utils/urlParamParser';
import axios from 'axios';
import config from '../config';
import { qbButtonSx, qbCardSx, qbColors, qbFonts, qbGhostButtonSx } from './queryBuilderTheme';

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
  day_or_night: null,

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

const ACTIVE_FILTER_KEYS = [
  'venue', 'start_date', 'end_date', 'leagues', 'teams', 'batting_teams', 'bowling_teams',
  'players', 'batters', 'bowlers', 'bat_hand', 'bowl_style', 'bowl_kind',
  'line', 'length', 'shot', 'control', 'wagon_zone', 'dismissal',
  'innings', 'over_min', 'over_max',
  'match_outcome', 'is_chase', 'chase_outcome', 'toss_decision',
  'min_balls', 'max_balls', 'min_runs', 'max_runs', 'min_wickets', 'max_wickets'
];

const getActiveFilterCount = (filters, groupBy) => {
  const filterCount = ACTIVE_FILTER_KEYS.reduce((count, key) => {
    const value = filters[key];
    if (Array.isArray(value)) {
      return count + (value.length > 0 ? 1 : 0);
    }
    return count + (value !== null && value !== undefined && value !== '' ? 1 : 0);
  }, 0);

  return filterCount + (Array.isArray(groupBy) ? groupBy.length : 0);
};

const QueryBuilder = ({ isMobile }) => {
  const { getFiltersFromUrl, getGroupByFromUrl, currentParams } = useUrlParams();
  
  const [filters, setFilters] = useState(getDefaultFilters);
  
  const [groupBy, setGroupBy] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [availableColumns, setAvailableColumns] = useState(null);
  const [, setQueryTab] = useState(0);
  const [, setIsAutoExecuting] = useState(false);
  const [hasLoadedFromUrl, setHasLoadedFromUrl] = useState(false);
  const [nlInterpretation, setNlInterpretation] = useState(null);
  const [nlConfidence, setNlConfidence] = useState('medium');
  const [nlSourceQuery, setNlSourceQuery] = useState('');
  const [nlRawFilters, setNlRawFilters] = useState({});
  const [nlRecommendedColumns, setNlRecommendedColumns] = useState([]);
  const [nlRecommendedChart, setNlRecommendedChart] = useState(null);
  const [isApplyingSuggestion, setIsApplyingSuggestion] = useState(false);
  const [nlExpanded, setNlExpanded] = useState(true);
  const [filtersCollapsed, setFiltersCollapsed] = useState(false);
  // ball_aggregation toggle: only meaningful when ball or ball_in_spell is in
  // the active group_by; otherwise the backend ignores it.
  const [ballAggregation, setBallAggregation] = useState('snapshot');
  const executeQueryRef = useRef(null);
  const nlInputRef = useRef(null);

  // Load filters from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(currentParams || '');
    const nlQuery = params.get('nl');

    if (nlQuery && !hasLoadedFromUrl) {
      setHasLoadedFromUrl(true);
      setNlExpanded(true);
      setFiltersCollapsed(false);
      setTimeout(() => {
        nlInputRef.current?.runQuery?.(nlQuery);
      }, 100);
      return;
    }

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
      setNlExpanded(false);
      setFiltersCollapsed(true);
      
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
      setNlExpanded(false);
      setFiltersCollapsed(true);

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
      setNlExpanded(false);
      setFiltersCollapsed(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      
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
    setHasLoadedFromUrl(true);
    setIsAutoExecuting(false);
    setNlInterpretation(null);
    setNlConfidence('medium');
    setNlSourceQuery('');
    setNlRawFilters({});
    setNlRecommendedColumns([]);
    setNlRecommendedChart(null);
    setNlExpanded(true);
    setFiltersCollapsed(false);
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
    setNlExpanded(false);
    setFiltersCollapsed(true);

    // Keep the typed NL query shareable until execution rewrites the URL with
    // structured filters.
    const newUrl = `${window.location.pathname}?nl=${encodeURIComponent((queryText || '').trim())}`;
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

  const activeCount = getActiveFilterCount(filters, groupBy);
  const canExecute = !!availableColumns && (hasValidFilters() || groupBy.length > 0) && !loading && !isApplyingSuggestion;
  const hasResults = !!results;
  const nlActive = !!nlSourceQuery;
  
  return (
    <Box
      sx={{
        mx: { xs: -1, sm: -2, md: -3 },
        mt: -3,
        mb: -2,
        minHeight: '100vh',
        bgcolor: qbColors.bg,
        color: qbColors.textHi,
        fontFamily: qbFonts.body,
        px: { xs: '14px', md: '30px' },
        py: { xs: '18px', md: '30px' },
        '& .MuiTypography-root': { fontFamily: qbFonts.body },
        '& .MuiPaper-root': { backgroundImage: 'none' },
        '& .MuiInputBase-root': {
          bgcolor: `${qbColors.input} !important`,
          color: qbColors.textHi,
          borderRadius: '12px',
        },
        '& .MuiInputLabel-root, & .MuiFormLabel-root': {
          color: qbColors.textLo,
          fontFamily: qbFonts.mono,
          fontSize: 11,
          letterSpacing: '0.06em',
        },
        '& .MuiOutlinedInput-notchedOutline': { borderColor: qbColors.borderStrong },
        '& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline': {
          borderColor: 'rgba(182,242,74,0.42)',
        },
        '& .MuiChip-root': { fontFamily: qbFonts.mono },
        '& .MuiTableCell-root': {
          borderColor: qbColors.border,
          color: qbColors.textMed,
          fontFamily: qbFonts.body,
        },
        '& .MuiTableHead-root .MuiTableCell-root': {
          bgcolor: `${qbColors.surface2} !important`,
          color: qbColors.textLo,
          fontFamily: qbFonts.mono,
        },
      }}
    >
      <GlobalStyles
        styles={{
          '.MuiAutocomplete-popper .MuiPaper-root, .MuiPopover-paper, .MuiMenu-paper': {
            backgroundColor: qbColors.surface3,
            color: qbColors.textMed,
            border: `1px solid ${qbColors.borderStrong}`,
            boxShadow: '0 24px 48px -18px rgba(0,0,0,0.75)',
          },
          '.MuiAutocomplete-popper .MuiAutocomplete-option': {
            color: qbColors.textMed,
            fontFamily: qbFonts.body,
          },
          '.MuiAutocomplete-popper .MuiAutocomplete-option[aria-selected="true"], .MuiAutocomplete-popper .MuiAutocomplete-option.Mui-focused': {
            backgroundColor: 'rgba(182,242,74,0.12) !important',
            color: qbColors.textHi,
          },
          '.MuiAutocomplete-noOptions, .MuiAutocomplete-loading': {
            color: qbColors.textLo,
          },
        }}
      />
      <Box sx={{ maxWidth: 1180, mx: 'auto' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: { xs: 2.5, md: 4 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 30, height: 30 }} />
            <Typography sx={{ fontFamily: qbFonts.display, fontSize: 19, fontWeight: 700, color: qbColors.textHi }}>
              Hindsight
            </Typography>
            <Typography sx={{ color: qbColors.textGhost }}>/</Typography>
            <Typography sx={{ fontFamily: qbFonts.display, fontSize: 15, fontWeight: 600, color: qbColors.textLo }}>
              Query Builder
            </Typography>
          </Box>
          <Button
            href="/"
            startIcon={<MenuIcon />}
            sx={{
              ...qbGhostButtonSx,
              height: 38,
              bgcolor: qbColors.surface1,
              px: 1.6,
            }}
          >
            Explore
          </Button>
        </Box>

        {!hasResults && (
          <Box sx={{ mb: { xs: 2.8, md: 4 } }}>
            <Typography
              sx={{
                fontFamily: qbFonts.mono,
                fontSize: 10,
                letterSpacing: '0.16em',
                color: qbColors.accent,
                textTransform: 'uppercase',
                mb: 1,
              }}
            >
              00 / Query Builder
            </Typography>
            <Typography
              component="h1"
              sx={{
                fontFamily: qbFonts.display,
                fontSize: { xs: 30, md: 42 },
                lineHeight: 1.02,
                fontWeight: 700,
                color: qbColors.textHi,
                mb: 1,
              }}
            >
              Ask the ball-by-ball data anything.
            </Typography>
            <Typography sx={{ color: qbColors.textLo, fontSize: { xs: 14, md: 15 } }}>
              Search in plain English, or build a query with filters and grouping.
            </Typography>
          </Box>
        )}

        <Box sx={{ display: 'grid', gap: { xs: '22px', md: '28px' } }}>
          {(!hasResults || nlExpanded) ? (
            <NLQueryInput
              ref={nlInputRef}
              onFiltersGenerated={handleNLFilters}
              disabled={loading || isApplyingSuggestion}
            />
          ) : (
            <Paper elevation={0} sx={{ ...qbCardSx, p: 1.25, borderColor: 'rgba(182,242,74,0.18)' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, flexWrap: 'wrap' }}>
                <Box sx={{ width: 32, height: 32, borderRadius: '10px', display: 'grid', placeItems: 'center', bgcolor: qbColors.accentSoft }}>
                  <SearchIcon sx={{ color: qbColors.accent, fontSize: 18 }} />
                </Box>
                <Typography sx={{ color: nlActive ? qbColors.textHi : qbColors.textLo, flex: 1, minWidth: 180 }}>
                  {nlActive ? `"${nlSourceQuery}"` : 'Built from filters - no natural-language query'}
                </Typography>
                <Button
                  size="small"
                  startIcon={<EditIcon />}
                  onClick={() => setNlExpanded(true)}
                  sx={qbGhostButtonSx}
                >
                  New search
                </Button>
              </Box>
            </Paper>
          )}

          {nlInterpretation && (
            <NLInterpretation
              interpretation={nlInterpretation}
              confidence={nlConfidence}
              rawFilters={nlRawFilters}
              onSuggestionClick={applySuggestion}
              onClose={dismissInterpretation}
              disabled={loading || isApplyingSuggestion}
            />
          )}

          {error && (
            <Alert severity="error" sx={{ bgcolor: 'rgba(229,72,77,0.1)', color: qbColors.textHi, border: `1px solid rgba(229,72,77,0.28)` }}>
              {error}
            </Alert>
          )}

          <Paper elevation={0} sx={{ ...qbCardSx, overflow: 'hidden' }}>
            <Box
              onClick={() => setFiltersCollapsed((prev) => !prev)}
              sx={{
                p: { xs: 2, md: 2.4 },
                display: 'flex',
                alignItems: 'center',
                gap: 1.25,
                cursor: 'pointer',
              }}
            >
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontFamily: qbFonts.mono, color: qbColors.accent, fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase' }}>
                  01 / Filters
                </Typography>
                <Typography sx={{ fontFamily: qbFonts.display, fontSize: { xs: 19, md: 23 }, fontWeight: 700 }}>
                  Filters & Grouping
                </Typography>
              </Box>
              <Chip
                label={`${activeCount} active`}
                sx={{
                  bgcolor: qbColors.accent,
                  color: qbColors.bg,
                  height: 26,
                  fontSize: 11,
                  fontWeight: 700,
                }}
              />
              <IconButton size="small" sx={{ color: qbColors.textLo }}>
                {filtersCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
              </IconButton>
            </Box>

            <Collapse in={!filtersCollapsed}>
              <Box sx={{ px: { xs: 2, md: 2.4 }, pb: 2.4 }}>
                <QueryFilters
                  filters={filters}
                  setFilters={setFilters}
                  groupBy={groupBy}
                  setGroupBy={setGroupBy}
                  availableColumns={availableColumns}
                  isMobile={isMobile}
                />
              </Box>
            </Collapse>

            <Box
              sx={{
                p: { xs: 2, md: 2.4 },
                borderTop: `1px solid ${qbColors.border}`,
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                gap: 1.5,
                alignItems: isMobile ? 'stretch' : 'center',
                justifyContent: 'space-between',
              }}
            >
              <Box sx={{ display: 'flex', gap: 1, flexDirection: isMobile ? 'column' : 'row' }}>
                <Button
                  variant="contained"
                  onClick={executeQuery}
                  disabled={!canExecute}
                  startIcon={loading ? <CircularProgress size={18} color="inherit" /> : null}
                  sx={{ ...qbButtonSx, minHeight: 46, px: 2.2 }}
                >
                  {loading ? 'Querying...' : 'Execute query'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={clearFilters}
                  disabled={loading}
                  sx={{ ...qbGhostButtonSx, minHeight: 46, px: 2 }}
                >
                  Clear all
                </Button>
              </Box>
              <Typography sx={{ color: qbColors.textFaint, fontFamily: qbFonts.mono, fontSize: 11, textAlign: isMobile ? 'center' : 'right' }}>
                {!canExecute && !loading && 'Add a filter or group-by dimension to run'}
                {canExecute && !loading && groupBy.length > 0 && `Ready - grouping by ${groupBy.join(', ')}`}
                {canExecute && !loading && groupBy.length === 0 && 'Ready - returns individual deliveries'}
              </Typography>
            </Box>
          </Paper>

          {hasResults ? (
            <Box>
              <Typography
                sx={{
                  fontFamily: qbFonts.mono,
                  color: qbColors.accent,
                  fontSize: 10,
                  letterSpacing: '0.16em',
                  textTransform: 'uppercase',
                  mb: 1,
                }}
              >
                02 / Results
              </Typography>
              <QueryResults
                results={results}
                groupBy={groupBy}
                filters={filters}
                recommendedColumns={nlRecommendedColumns}
                recommendedChart={nlRecommendedChart || results?.metadata?.recommended_chart || null}
                nlInterpretation={null}
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
                  setTimeout(() => executeQueryRef.current && executeQueryRef.current(), 0);
                }}
              />
            </Box>
          ) : (
            <Paper
              elevation={0}
              sx={{
                ...qbCardSx,
                p: { xs: 3, md: 4 },
                borderStyle: 'dashed',
                display: 'grid',
                placeItems: 'center',
                textAlign: 'center',
                color: qbColors.textLo,
              }}
            >
              <SearchIcon sx={{ color: qbColors.accent, mb: 1 }} />
              <Typography sx={{ fontFamily: qbFonts.display, color: qbColors.textHi, fontSize: 20, fontWeight: 700 }}>
                No results yet
              </Typography>
              <Typography sx={{ maxWidth: 420, mt: 0.5 }}>
                Search in plain English or set a filter and hit Execute.
              </Typography>
            </Paper>
          )}
        </Box>

        <Box sx={{ mt: { xs: 3, md: 5 }, pt: 2, borderTop: `1px solid ${qbColors.border}`, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'space-between' }}>
          <Typography sx={{ color: qbColors.textGhost, fontFamily: qbFonts.mono, fontSize: 11 }}>
            Hindsight © 2026 · data via Cricsheet
          </Typography>
          <Typography sx={{ color: qbColors.textGhost, fontFamily: qbFonts.mono, fontSize: 11 }}>
            Shareable query URL updates on execute
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default QueryBuilder;
