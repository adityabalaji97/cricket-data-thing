import React, { useImperativeHandle, useState } from 'react';
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
  Collapse,
  useMediaQuery,
  useTheme
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import axios from 'axios';
import config from '../config';
import { qbButtonSx, qbCardSx, qbColors, qbFonts } from './queryBuilderTheme';

const EXAMPLE_QUERIES = [
  "kohli vs spin since 2023",
  "csk powerplay batting over the years",
  "MS Dhoni in winning vs losing chases in IPL",
  "csk in chasing wins since 2018",
  "varun chakravarthy vs lhb/rhb",
  "bumrah in 2026 grouped by competition",
  "shubman gill batting in first innings vs second innings",
  "rashid khan bowling by year",
  "line and length patterns by phase for arshdeep singh",
  "rohit sharma dismissal types vs each bowling type since 2018"
];

const QUERY_TIPS = `Try queries like:
- Delivery-level asks: "line/length/shot/wagon zone analysis for [player/team]"
- Batting stats asks: "[batter] batting stats by [year/competition/match_outcome/chase_outcome]"
- Bowling stats asks: "[bowler] economy/wickets by [year/competition/team]"
- Grouping: include "grouped by [competition/year/batter/bowler/bat_hand/bowl_style/match_outcome/toss_decision]"
- Context filters: use phrases like "in chases", "winning vs losing", "toss decision bat/field", "since 2023"`;

const NLQueryInput = React.forwardRef(({ onFiltersGenerated, disabled, examplesCollapsed: externalCollapsed }, ref) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showExamples, setShowExamples] = useState(true);

  // Allow parent to collapse examples via prop
  const examplesVisible = showExamples && !externalCollapsed;

  const submitQuery = async (queryText) => {
    const q = (queryText || query).trim();
    if (!q || loading) return null;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${config.API_URL}/nl2query/parse`, {
        query: q
      });

      const data = response.data;

      if (data.success) {
        // Collapse examples after successful query
        setShowExamples(false);
        onFiltersGenerated({
          queryText: q,
          filters: data.filters,
          groupBy: data.group_by,
          explanation: data.explanation,
          confidence: data.confidence,
          suggestions: data.suggestions || [],
          recommendedColumns: data.recommended_columns || [],
          recommendedChart: data.recommended_chart || null,
          interpretation: data.interpretation || null,
        });
        return data;
      } else {
        setError(data.error || 'Failed to parse query');
        return null;
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to parse query. Please try again.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const runQuery = (queryText) => {
    if (queryText) {
      setQuery(queryText);
    }
    return submitQuery(queryText);
  };

  useImperativeHandle(ref, () => ({
    runQuery,
  }));

  const handleSubmit = () => submitQuery();

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChipClick = (exampleQuery) => {
    setQuery(exampleQuery);
    setError(null);
    runQuery(exampleQuery);
  };

  return (
    <Paper
      elevation={2}
      sx={{
        p: isMobile ? 2 : 3,
        ...qbCardSx,
        mb: 0,
        background: 'linear-gradient(150deg,#12160f,#101319 60%)',
        borderColor: 'rgba(182,242,74,0.22)',
        color: qbColors.textHi
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
        <Box sx={{ width: 32, height: 32, borderRadius: '10px', display: 'grid', placeItems: 'center', bgcolor: qbColors.accentSoft }}>
          <SearchIcon sx={{ color: qbColors.accent, fontSize: 18 }} />
        </Box>
        <Typography variant="h6" sx={{ fontFamily: qbFonts.display, fontWeight: 700, fontSize: 17 }}>
          Natural Language Search
        </Typography>
        <Chip
          label="AI"
          size="small"
          sx={{ bgcolor: qbColors.accent, color: qbColors.bg, height: 20, fontFamily: qbFonts.mono, fontWeight: 700 }}
        />
        <Tooltip title={QUERY_TIPS} arrow placement="right">
          <IconButton size="small" sx={{ color: qbColors.textLo }}>
            <HelpOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Typography variant="body2" sx={{ mb: 2, color: qbColors.textLo, fontSize: isMobile ? '0.82rem' : '0.9rem' }}>
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
              bgcolor: qbColors.bg,
              borderRadius: '12px',
              minHeight: 50,
              color: qbColors.textHi,
              '& fieldset': { borderColor: qbColors.borderStrong },
              '&:hover fieldset': { borderColor: 'rgba(182,242,74,0.42)' },
              '&.Mui-focused fieldset': { borderColor: qbColors.accent }
            },
            '& input::placeholder': {
              color: qbColors.textFaint,
              opacity: 1,
            }
          }}
        />
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!query.trim() || loading || disabled}
          sx={{
            ...qbButtonSx,
            minWidth: isMobile ? '100%' : 100,
            minHeight: 50,
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

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.8 }}>
        <Typography
          variant="caption"
          sx={{
            color: qbColors.textLo,
            fontFamily: qbFonts.mono,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            cursor: 'pointer',
            userSelect: 'none',
            '&:hover': { color: qbColors.accent }
          }}
          onClick={() => setShowExamples(prev => !prev)}
        >
          Try
        </Typography>
        <IconButton
          size="small"
          onClick={() => setShowExamples(prev => !prev)}
          sx={{ color: qbColors.textLo, p: 0 }}
        >
          {examplesVisible ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>

      <Collapse in={examplesVisible}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 0.75,
            maxHeight: isMobile ? 140 : 'none',
            overflowY: isMobile ? 'auto' : 'visible',
            pb: isMobile ? 0.5 : 0,
            '::-webkit-scrollbar': { width: isMobile ? 4 : 0 }
          }}
        >
          {EXAMPLE_QUERIES.slice(0, 3).map((example, index) => (
            <Chip
              key={index}
              label={example}
              size="small"
              onClick={() => handleChipClick(example)}
              disabled={loading}
              sx={{
                bgcolor: 'rgba(255,255,255,0.06)',
                color: qbColors.textMed,
                border: `1px solid ${qbColors.borderStrong}`,
                fontSize: '0.75rem',
                fontFamily: qbFonts.mono,
                borderRadius: '8px',
                cursor: 'pointer',
                '&:hover': { bgcolor: qbColors.accentSoft, color: qbColors.accent, borderColor: 'rgba(182,242,74,0.4)' },
                '&.Mui-disabled': { opacity: 0.5 }
              }}
            />
          ))}
        </Box>
      </Collapse>
    </Paper>
  );
});

NLQueryInput.displayName = 'NLQueryInput';

export default NLQueryInput;
