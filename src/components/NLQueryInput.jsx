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
  IconButton,
  useMediaQuery,
  useTheme
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import axios from 'axios';
import config from '../config';

const EXAMPLE_QUERIES = [
  "kohli vs spin since 2023",
  "csk powerplay batting over the years",
  "MS Dhoni in winning vs losing chases in IPL",
  "csk in chasing wins since 2018",
  "varun chakravarthy vs lhb/rhb",
  "bumrah in 2026 grouped by competition",
  "top batters by toss decision in IPL",
  "bowling stats for rashid khan by year",
  "line and length patterns by phase for arshdeep singh",
  "dismissal type by match outcome for RCB"
];

const QUERY_TIPS = `Try queries like:
- Delivery-level asks: "line/length/shot/wagon zone analysis for [player/team]"
- Batting stats asks: "[batter] batting stats by [year/competition/match_outcome/chase_outcome]"
- Bowling stats asks: "[bowler] economy/wickets by [year/competition/team]"
- Grouping: include "grouped by [competition/year/batter/bowler/bat_hand/bowl_style/match_outcome/toss_decision]"
- Context filters: use phrases like "in chases", "winning vs losing", "toss decision bat/field", "since 2023"`;

const NLQueryInput = ({ onFiltersGenerated, disabled }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
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
        p: isMobile ? 2 : 3,
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

      <Typography variant="body2" sx={{ mb: 2, opacity: 0.9, fontSize: isMobile ? '0.82rem' : '0.9rem' }}>
        Describe what you want to analyze in plain English across delivery details, batting stats, or bowling stats
      </Typography>

      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexDirection: isMobile ? 'column' : 'row' }}>
        <TextField
          fullWidth
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isMobile ? 'e.g. dhoni in winning chases' : 'e.g. MS Dhoni in winning vs losing chases in IPL'}
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
            minWidth: isMobile ? '100%' : 100,
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

      <Typography variant="caption" sx={{ opacity: 0.9, display: 'block', mb: 1 }}>
        Tap an example to autofill
      </Typography>

      <Box
        sx={{
          display: 'flex',
          flexWrap: isMobile ? 'nowrap' : 'wrap',
          gap: 0.75,
          overflowX: isMobile ? 'auto' : 'visible',
          pb: isMobile ? 0.5 : 0,
          '::-webkit-scrollbar': { height: isMobile ? 6 : 0 }
        }}
      >
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
              flexShrink: 0,
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
