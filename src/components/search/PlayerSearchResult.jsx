import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  Button,
  Card,
  CardContent,
  Collapse
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import BoltIcon from '@mui/icons-material/Bolt';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE_URL } from './searchConfig';

const StatCard = ({ label, value, subtitle }) => (
  <Box sx={{ textAlign: 'center', p: 1 }}>
    <Typography variant="h5" fontWeight="bold" color="primary">
      {value}
    </Typography>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
    {subtitle && (
      <Typography variant="caption" color="text.secondary">
        {subtitle}
      </Typography>
    )}
  </Box>
);

// DNA Summary sub-component
const DNASummary = ({ playerName, playerType, color, startDate, endDate }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      setLoading(true);
      setError(null);
      try {
        const endpoint = playerType === 'bowler' ? 'bowler' : 'batter';
        
        // Build query params with date range
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        const url = `${API_BASE_URL}/player-summary/${endpoint}/${encodeURIComponent(playerName)}?${params.toString()}`;
        const response = await axios.get(url);
        
        if (response.data.success) {
          setSummary(response.data.summary);
        } else {
          setError(response.data.error || 'Failed to generate summary');
        }
      } catch (err) {
        console.error('DNA fetch error:', err);
        setError(err.response?.data?.detail || err.response?.data?.error || 'Failed to load DNA summary');
      } finally {
        setLoading(false);
      }
    };

    if (playerName) {
      fetchSummary();
    }
  }, [playerName, playerType, startDate, endDate]);

  const parseSummary = (text) => {
    if (!text) return [];
    return text.split('\n').filter(line => line.trim()).map((line) => {
      const match = line.match(/^([🎯⚡💪⚠️📊]+)\s*(.+?):\s*(.+)$/);
      if (match) return { emoji: match[1], label: match[2], text: match[3] };
      const simpleMatch = line.match(/^([^\s]+)\s+(.+)$/);
      if (simpleMatch) return { emoji: simpleMatch[1], label: '', text: simpleMatch[2] };
      return { emoji: '•', label: '', text: line };
    });
  };

  return (
    <Card variant="outlined" sx={{ mt: 2, borderColor: color }}>
      <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1, 
            cursor: 'pointer' 
          }}
          onClick={() => setExpanded(!expanded)}
        >
          <BoltIcon sx={{ color, fontSize: 18 }} />
          <Typography variant="subtitle2" fontWeight="bold" sx={{ flexGrow: 1 }}>
            {playerType === 'bowler' ? 'Bowler' : 'Batter'} DNA
          </Typography>
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </Box>

        <Collapse in={expanded}>
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1.5 }}>
              <CircularProgress size={16} />
              <Typography variant="body2" color="text.secondary">
                Analyzing patterns...
              </Typography>
            </Box>
          )}

          {error && !loading && (
            <Alert severity="warning" sx={{ mt: 1, py: 0.5 }}>
              <Typography variant="caption">{error}</Typography>
            </Alert>
          )}

          {summary && !loading && (
            <Box sx={{ mt: 1.5, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {parseSummary(summary).map((bullet, index) => (
                <Box key={index} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                  <Typography component="span" sx={{ flexShrink: 0, fontSize: '0.85rem' }}>
                    {bullet.emoji}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                    {bullet.label && <strong>{bullet.label}: </strong>}
                    {bullet.text}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

const PlayerSearchResult = ({ playerName }) => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get(`${API_BASE_URL}/search/player/${encodeURIComponent(playerName)}`);
        setProfile(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load player profile');
      } finally {
        setLoading(false);
      }
    };

    if (playerName) {
      fetchProfile();
    }
  }, [playerName]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!profile) {
    return null;
  }

  const { player_info, batting, bowling, date_range } = profile;

  return (
    <Paper elevation={2} sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <PersonIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        <Box>
          <Typography variant="h5" fontWeight="bold">
            {profile.player_name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
            {player_info.batter_type && (
              <Chip size="small" label={player_info.batter_type} variant="outlined" />
            )}
            {player_info.bowler_type && (
              <Chip size="small" label={player_info.bowler_type} variant="outlined" />
            )}
            <Chip 
              size="small" 
              label={player_info.role} 
              color={player_info.role === 'all-rounder' ? 'success' : 'default'}
            />
          </Box>
        </Box>
      </Box>

      {/* Teams */}
      {player_info.recent_teams?.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Recent Teams: {player_info.recent_teams.join(', ')}
          </Typography>
        </Box>
      )}

      {/* Date Range */}
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
        Stats from {date_range.start_date} to {date_range.end_date}
      </Typography>

      <Divider sx={{ my: 2 }} />

      {/* Batting Stats */}
      {batting.has_stats && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <SportsCricketIcon color="error" />
            Batting
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={4} sm={2}>
              <StatCard label="Matches" value={batting.matches} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Runs" value={batting.runs} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Average" value={batting.average} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Strike Rate" value={batting.strike_rate} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="50s/100s" value={`${batting.fifties}/${batting.hundreds}`} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="High Score" value={batting.highest_score} />
            </Grid>
          </Grid>
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              4s: {batting.fours} | 6s: {batting.sixes} | Dot%: {batting.dot_percentage}%
            </Typography>
          </Box>
          
          {/* Batter DNA Summary - pass date range */}
          <DNASummary 
            playerName={playerName} 
            playerType="batter" 
            color="#d32f2f"
            startDate={date_range.start_date}
            endDate={date_range.end_date}
          />
          
          <Button
            component={Link}
            to={`/player?name=${encodeURIComponent(playerName)}&autoload=true`}
            variant="outlined"
            size="small"
            sx={{ mt: 2 }}
          >
            View Full Batting Profile →
          </Button>
        </Box>
      )}

      {/* Bowling Stats */}
      {bowling.has_stats && (
        <Box>
          {batting.has_stats && <Divider sx={{ my: 3 }} />}
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <SportsCricketIcon color="warning" />
            Bowling
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={4} sm={2}>
              <StatCard label="Matches" value={bowling.matches} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Wickets" value={bowling.wickets} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Average" value={bowling.average} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Economy" value={bowling.economy} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Strike Rate" value={bowling.strike_rate} />
            </Grid>
            <Grid item xs={4} sm={2}>
              <StatCard label="Best" value={`${bowling.best_wickets}w`} />
            </Grid>
          </Grid>
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Overs: {bowling.overs} | 3W: {bowling.three_wickets} | 5W: {bowling.five_wickets} | Dot%: {bowling.dot_percentage}%
            </Typography>
          </Box>
          
          {/* Bowler DNA Summary - pass date range */}
          <DNASummary 
            playerName={playerName} 
            playerType="bowler" 
            color="#ed6c02"
            startDate={date_range.start_date}
            endDate={date_range.end_date}
          />
          
          <Button
            component={Link}
            to={`/bowler?name=${encodeURIComponent(playerName)}&autoload=true`}
            variant="outlined"
            size="small"
            sx={{ mt: 2 }}
          >
            View Full Bowling Profile →
          </Button>
        </Box>
      )}

      {/* No Stats Message */}
      {!batting.has_stats && !bowling.has_stats && (
        <Alert severity="info">
          No batting or bowling statistics found for this player in the selected date range.
        </Alert>
      )}
    </Paper>
  );
};

export default PlayerSearchResult;
