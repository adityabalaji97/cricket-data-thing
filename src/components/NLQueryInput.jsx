import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  IconButton
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import axios from 'axios';
import config from '../config';

const EXAMPLE_QUERIES = [
  "Kohli vs spin in death overs in IPL",
  "CSK powerplay batting this season",
  "Left arm spinners in middle overs",
  "Top batters against short balls",
  "Yorker effectiveness in death overs",
  "Uncontrolled shots by wagon zone",
  "RCB vs MI head to head batting",
  "Bowled dismissals by length"
];

const QUERY_TIPS = `Try queries like:
- "[Player] vs [bowling type] in [phase]"
- "[Team] batting in [phase] in [league]"
- "[Bowling style] analysis by [grouping]"
- "[Dismissal type] by [grouping]"
- "[Shot type] against [bowling type]"`;

const NLQueryInput = ({ onFiltersGenerated, disabled }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!query.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${config.API_URL}/nl2query/parse`, {
        query: query.trim()
      });

      const data = response.data;

      if (data.success) {
        onFiltersGenerated({
          filters: data.filters,
          groupBy: data.group_by,
          explanation: data.explanation,
          confidence: data.confidence
        });
      } else {
        setError(data.error || 'Failed to parse query');
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to parse query. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChipClick = (exampleQuery) => {
    setQuery(exampleQuery);
    setError(null);
  };

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        mb: 3,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Natural Language Search
        </Typography>
        <Tooltip title={QUERY_TIPS} arrow placement="right">
          <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.8)' }}>
            <HelpOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Typography variant="body2" sx={{ mb: 2, opacity: 0.9 }}>
        Describe what you want to analyze in plain English
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          fullWidth
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Kohli vs spin in death overs in IPL"
          disabled={loading || disabled}
          variant="outlined"
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: 'rgba(255,255,255,0.95)',
              borderRadius: 1,
              '& fieldset': { borderColor: 'transparent' },
              '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.5)' },
              '&.Mui-focused fieldset': { borderColor: 'white' }
            }
          }}
        />
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!query.trim() || loading || disabled}
          sx={{
            bgcolor: 'rgba(255,255,255,0.2)',
            color: 'white',
            minWidth: 100,
            '&:hover': { bgcolor: 'rgba(255,255,255,0.3)' },
            '&.Mui-disabled': { color: 'rgba(255,255,255,0.5)' }
          }}
          startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <SearchIcon />}
        >
          {loading ? 'Parsing...' : 'Search'}
        </Button>
      </Box>

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
        {EXAMPLE_QUERIES.map((example, index) => (
          <Chip
            key={index}
            label={example}
            size="small"
            onClick={() => handleChipClick(example)}
            disabled={loading}
            sx={{
              bgcolor: 'rgba(255,255,255,0.15)',
              color: 'white',
              fontSize: '0.75rem',
              cursor: 'pointer',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.25)' },
              '&.Mui-disabled': { opacity: 0.5 }
            }}
          />
        ))}
      </Box>
    </Paper>
  );
};

export default NLQueryInput;
