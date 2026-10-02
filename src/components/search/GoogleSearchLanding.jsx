import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper
} from '@mui/material';
import CasinoIcon from '@mui/icons-material/Casino';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import SearchBar from './SearchBar';
import { findExactSearchMatch } from './SearchBar';
import PlayerSearchResult from './PlayerSearchResult';
import { API_BASE_URL } from './searchConfig';
import playerProfileUrl from '../../utils/playerProfileUrl';

const GoogleSearchLanding = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [luckyLoading, setLuckyLoading] = useState(false);
  const [resolvedUrlQuery, setResolvedUrlQuery] = useState('');
  
  // Extract URL parameters for date filtering
  const [dateFilters, setDateFilters] = useState({
    startDate: null,
    endDate: null
  });

  const routeEntity = (item, replace = false) => {
    if (item.type === 'player') {
      // Straight to the profile; the intermediate search-result card was an extra tap.
      navigate(playerProfileUrl(item, dateFilters), { replace });
    } else if (item.type === 'team') {
      navigate(`/team?team=${encodeURIComponent(item.name)}&autoload=true`, { replace });
    } else if (item.type === 'venue') {
      navigate(`/venue?venue=${encodeURIComponent(item.name)}&autoload=true`, { replace });
    }
  };

  // Auto-search from URL parameter and extract date filters
  useEffect(() => {
    const query = searchParams.get('q');
    const startDate = searchParams.get('start_date');
    const endDate = searchParams.get('end_date');
    
    // Update date filters if provided in URL
    if (startDate || endDate) {
      setDateFilters({
        startDate: startDate || null,
        endDate: endDate || null
      });
    }
    
    if (query && !selectedEntity && resolvedUrlQuery !== query) {
      setResolvedUrlQuery(query);
      const resolveQuery = async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/search/suggestions`, {
            params: { q: query, limit: 20 }
          });
          const suggestions = response.data.suggestions || [];
          const exactMatch = findExactSearchMatch(query, suggestions);

          if (exactMatch) {
            routeEntity(exactMatch, true);
          } else {
            navigate(`/query?nl=${encodeURIComponent(query)}`, { replace: true });
          }
        } catch (error) {
          console.error('URL search resolve error:', error);
          navigate(`/query?nl=${encodeURIComponent(query)}`, { replace: true });
        }
      };

      resolveQuery();
    }
  }, [searchParams, selectedEntity, resolvedUrlQuery, navigate, dateFilters.startDate, dateFilters.endDate]);

  const handleSelect = (item) => {
    routeEntity(item, true);
  };

  const handleFeelingLucky = async () => {
    setLuckyLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/search/random`);
      const data = response.data;
      
      if (data.type === 'player') {
        navigate(playerProfileUrl(data, dateFilters));
      } else if (data.type === 'team') {
        navigate(`/team?team=${encodeURIComponent(data.name)}&autoload=true`);
      } else if (data.type === 'venue') {
        navigate(`/venue?venue=${encodeURIComponent(data.name)}&autoload=true`);
      }
    } catch (error) {
      console.error('Lucky search error:', error);
    } finally {
      setLuckyLoading(false);
    }
  };

  const handleClear = () => {
    setSelectedEntity(null);
    setDateFilters({ startDate: null, endDate: null });
    navigate('/search', { replace: true });
  };

  // Format date range for display
  const getDateRangeLabel = () => {
    if (dateFilters.startDate && dateFilters.endDate) {
      return `${dateFilters.startDate} to ${dateFilters.endDate}`;
    } else if (dateFilters.startDate) {
      return `From ${dateFilters.startDate}`;
    } else if (dateFilters.endDate) {
      return `Until ${dateFilters.endDate}`;
    }
    return null;
  };

  const dateRangeLabel = getDateRangeLabel();

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Logo / Header */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 1 }}>
          <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 44, height: 44 }} />
          <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>
            Hindsight
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Search players, teams, and venues for T20 cricket analytics
        </Typography>
        {/* Show date filter badge if dates are applied */}
        {dateRangeLabel && (
          <Box sx={{ mt: 1 }}>
            <Typography 
              variant="caption" 
              sx={{ 
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                px: 1.5, 
                py: 0.5, 
                borderRadius: 1,
                display: 'inline-block'
              }}
            >
              📅 {dateRangeLabel}
            </Typography>
          </Box>
        )}
      </Box>

      {/* Search Bar */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
        <SearchBar onSelect={handleSelect} />
      </Box>

      {/* Buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 4 }}>
        <Button
          variant="outlined"
          startIcon={<CasinoIcon />}
          onClick={handleFeelingLucky}
          disabled={luckyLoading}
          sx={{ borderRadius: 2 }}
        >
          {luckyLoading ? 'Loading...' : "I'm Feeling Lucky"}
        </Button>
        {selectedEntity && (
          <Button
            variant="text"
            onClick={handleClear}
            sx={{ borderRadius: 2 }}
          >
            Clear
          </Button>
        )}
      </Box>

      {/* Results */}
      {selectedEntity && selectedEntity.type === 'player' && (
        <PlayerSearchResult 
          playerName={selectedEntity.name}
          startDate={dateFilters.startDate}
          endDate={dateFilters.endDate}
        />
      )}

      {/* Quick Links when no selection */}
      {!selectedEntity && (
        <Paper elevation={0} sx={{ p: 3, bgcolor: 'action.hover', borderRadius: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Quick Links
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', sm: 'repeat(4, max-content)' }, gap: 1 }}>
            <Button
              size="small"
              sx={{ justifyContent: 'flex-start', minHeight: 36 }}
              onClick={() => handleSelect({ name: 'Virat Kohli', type: 'player' })}
            >
              Virat Kohli
            </Button>
            <Button
              size="small"
              sx={{ justifyContent: 'flex-start', minHeight: 36 }}
              onClick={() => handleSelect({ name: 'Jasprit Bumrah', type: 'player' })}
            >
              Jasprit Bumrah
            </Button>
            <Button
              size="small"
              sx={{ justifyContent: 'flex-start', minHeight: 36 }}
              onClick={() => handleSelect({ name: 'MS Dhoni', type: 'player' })}
            >
              MS Dhoni
            </Button>
            <Button
              size="small"
              sx={{ justifyContent: 'flex-start', minHeight: 36 }}
              onClick={() => handleSelect({ name: 'Hardik Pandya', type: 'player' })}
            >
              Hardik Pandya
            </Button>
          </Box>
        </Paper>
      )}
    </Container>
  );
};

export default GoogleSearchLanding;
