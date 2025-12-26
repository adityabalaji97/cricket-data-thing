import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper
} from '@mui/material';
import CasinoIcon from '@mui/icons-material/Casino';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import SearchBar from './SearchBar';
import PlayerSearchResult from './PlayerSearchResult';
import { API_BASE_URL } from './searchConfig';

const GoogleSearchLanding = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [luckyLoading, setLuckyLoading] = useState(false);

  // Auto-search from URL parameter
  useEffect(() => {
    const query = searchParams.get('q');
    if (query && !selectedEntity) {
      // Auto-select as player search
      setSelectedEntity({ name: query, type: 'player' });
    }
  }, [searchParams, selectedEntity]);

  const handleSelect = (item) => {
    if (item.type === 'player') {
      setSelectedEntity(item);
      // Update URL to reflect the search
      navigate(`/search?q=${encodeURIComponent(item.name)}`, { replace: true });
    } else if (item.type === 'team') {
      navigate(`/team?team=${encodeURIComponent(item.name)}&autoload=true`);
    } else if (item.type === 'venue') {
      navigate(`/venue?venue=${encodeURIComponent(item.name)}&autoload=true`);
    }
  };

  const handleFeelingLucky = async () => {
    setLuckyLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/search/random`);
      const data = response.data;
      
      if (data.type === 'player') {
        // Use legacy name for profile lookup, full object for state
        setSelectedEntity(data);
        navigate(`/search?q=${encodeURIComponent(data.name)}`, { replace: true });
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
    navigate('/search', { replace: true });
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Logo / Header */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 1 }}>
          <SportsCricketIcon sx={{ fontSize: 48, color: 'primary.main' }} />
          <Typography
            variant="h3"
            fontWeight="bold"
            sx={{
              background: 'linear-gradient(45deg, #1976d2 30%, #42a5f5 90%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}
          >
            Hindsight
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Search players, teams, and venues for T20 cricket analytics
        </Typography>
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
        <PlayerSearchResult playerName={selectedEntity.name} />
      )}

      {/* Quick Links when no selection */}
      {!selectedEntity && (
        <Paper elevation={0} sx={{ p: 3, bgcolor: 'grey.50', borderRadius: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Quick Links
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              size="small"
              onClick={() => handleSelect({ name: 'V Kohli', type: 'player' })}
            >
              V Kohli
            </Button>
            <Button
              size="small"
              onClick={() => handleSelect({ name: 'JJ Bumrah', type: 'player' })}
            >
              JJ Bumrah
            </Button>
            <Button
              size="small"
              onClick={() => handleSelect({ name: 'MS Dhoni', type: 'player' })}
            >
              MS Dhoni
            </Button>
            <Button
              size="small"
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
