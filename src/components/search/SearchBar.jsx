import React, { useState, useEffect, useRef } from 'react';
import {
  TextField,
  Paper,
  List,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  InputAdornment,
  CircularProgress,
  Box,
  Typography,
  ClickAwayListener
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import PersonIcon from '@mui/icons-material/Person';
import GroupsIcon from '@mui/icons-material/Groups';
import StadiumIcon from '@mui/icons-material/Stadium';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL, SEARCH_DEBOUNCE_MS, MIN_SEARCH_LENGTH } from './searchConfig';

export const normalizeSearchText = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');

export const findExactSearchMatch = (query, suggestions = []) => {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) return null;

  return suggestions.find((item) => {
    const candidates = [item?.name, item?.display_name, item?.details_name]
      .map(normalizeSearchText)
      .filter(Boolean);
    return candidates.includes(normalizedQuery);
  }) || null;
};

const SearchBar = ({
  onSelect,
  onSubmit,
  onFallback,
  placeholder = "Search players, teams, or venues...",
  autoFocus = false,
}) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debounceRef = useRef(null);

  const fetchSuggestions = async (queryText, limit = 10) => {
    const q = queryText.trim();
    if (q.length < MIN_SEARCH_LENGTH) {
      return [];
    }

    const response = await axios.get(`${API_BASE_URL}/search/suggestions`, {
      params: { q, limit }
    });
    return response.data.suggestions || [];
  };

  const getIcon = (type) => {
    switch (type) {
      case 'player': return <PersonIcon color="primary" />;
      case 'team': return <GroupsIcon color="success" />;
      case 'venue': return <StadiumIcon color="secondary" />;
      default: return <SearchIcon />;
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'player': return 'Player';
      case 'team': return 'Team';
      case 'venue': return 'Venue';
      default: return '';
    }
  };

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.length < MIN_SEARCH_LENGTH) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const nextSuggestions = await fetchSuggestions(query, 10);
        setSuggestions(nextSuggestions);
        setShowSuggestions(true);
      } catch (error) {
        console.error('Search error:', error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query]);

  const handleSelect = (item) => {
    // Use display_name for the input field if available
    setQuery(item.display_name || item.name);
    setShowSuggestions(false);
    if (onSelect) {
      // Pass the full item with both name (legacy) and display_name
      onSelect(item);
    }
  };

  const routeToQueryBuilder = (queryText) => {
    const q = queryText.trim();
    if (!q) return;

    if (onFallback) {
      onFallback(q);
      return;
    }

    navigate(`/query?nl=${encodeURIComponent(q)}`);
  };

  const handleSubmit = async (event) => {
    event?.preventDefault();
    const q = query.trim();
    if (!q || submitting) return;

    setSubmitting(true);
    try {
      const freshSuggestions = await fetchSuggestions(q, 20);
      setSuggestions(freshSuggestions);
      const exactMatch = findExactSearchMatch(q, freshSuggestions);

      if (onSubmit) {
        onSubmit({ query: q, exactMatch, suggestions: freshSuggestions });
      }

      if (exactMatch) {
        handleSelect(exactMatch);
      } else {
        setShowSuggestions(false);
        routeToQueryBuilder(q);
      }
    } catch (error) {
      console.error('Search submit error:', error);
      setShowSuggestions(false);
      routeToQueryBuilder(q);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClickAway = () => {
    setShowSuggestions(false);
  };

  return (
    <ClickAwayListener onClickAway={handleClickAway}>
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          position: 'relative',
          width: '100%',
          maxWidth: 680,
          zIndex: 1300,
          display: 'flex',
          gap: 1,
          alignItems: 'stretch'
        }}
      >
        <TextField
          fullWidth
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          variant="outlined"
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
            endAdornment: loading && (
              <InputAdornment position="end">
                <CircularProgress size={20} />
              </InputAdornment>
            ),
            sx: {
              borderRadius: 3,
              bgcolor: 'white',
              '& fieldset': { borderColor: '#dfe1e5' },
              '&:hover fieldset': { borderColor: '#c0c0c0' },
            }
          }}
        />
        <Box
          component="button"
          type="submit"
          disabled={!query.trim() || submitting}
          sx={{
            border: 0,
            px: { xs: 1.8, sm: 2.5 },
            borderRadius: 3,
            bgcolor: '#1976d2',
            color: 'white',
            fontWeight: 700,
            cursor: query.trim() && !submitting ? 'pointer' : 'default',
            opacity: query.trim() && !submitting ? 1 : 0.55,
            minWidth: { xs: 50, sm: 94 },
            fontFamily: 'inherit',
            '&:hover': {
              bgcolor: query.trim() && !submitting ? '#1565c0' : '#1976d2'
            }
          }}
          aria-label="Search"
        >
          {submitting ? (
            <CircularProgress size={18} color="inherit" />
          ) : (
            <>
              <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                Search
              </Box>
              <SearchIcon sx={{ display: { xs: 'inline-flex', sm: 'none' }, verticalAlign: 'middle' }} />
            </>
          )}
        </Box>
        
        {showSuggestions && suggestions.length > 0 && (
          <Paper
            elevation={3}
            sx={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              mt: 0.5,
              maxHeight: 400,
              overflow: 'auto',
              zIndex: 1000,
              borderRadius: 2
            }}
          >
            <List dense>
              {suggestions.map((item, index) => (
                <ListItemButton
                  key={`${item.type}-${item.name}-${index}`}
                  onClick={() => handleSelect(item)}
                  sx={{
                    '&:hover': { bgcolor: 'action.hover' },
                    py: 1
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {getIcon(item.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.display_name || item.name}
                    secondary={
                      <Typography variant="caption" color="text.secondary">
                        {getTypeLabel(item.type)}
                      </Typography>
                    }
                  />
                </ListItemButton>
              ))}
            </List>
          </Paper>
        )}
      </Box>
    </ClickAwayListener>
  );
};

export default SearchBar;
