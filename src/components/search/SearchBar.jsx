import React, { useState, useEffect, useRef } from 'react';
import {
  TextField,
  Paper,
  List,
  ListItem,
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
import { API_BASE_URL, SEARCH_DEBOUNCE_MS, MIN_SEARCH_LENGTH } from './searchConfig';

const SearchBar = ({ onSelect, placeholder = "Search players, teams, or venues..." }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debounceRef = useRef(null);

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
        const response = await axios.get(`${API_BASE_URL}/search/suggestions`, {
          params: { q: query, limit: 10 }
        });
        setSuggestions(response.data.suggestions || []);
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

  const handleClickAway = () => {
    setShowSuggestions(false);
  };

  return (
    <ClickAwayListener onClickAway={handleClickAway}>
      <Box sx={{ position: 'relative', width: '100%', maxWidth: 600 }}>
        <TextField
          fullWidth
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
                <ListItem
                  key={`${item.type}-${item.name}-${index}`}
                  button
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
                </ListItem>
              ))}
            </List>
          </Paper>
        )}
      </Box>
    </ClickAwayListener>
  );
};

export default SearchBar;
