import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, CircularProgress } from '@mui/material';
import { Bolt as BoltIcon } from '@mui/icons-material';
import axios from 'axios';
import { spacing } from '../theme/designSystem';
import config from '../config';
import { AlertBanner } from './ui';

const PlayerDNASummary = ({ 
  playerName, 
  playerType = 'batter', // 'batter' or 'bowler'
  startDate, 
  endDate, 
  leagues, 
  includeInternational, 
  topTeams, 
  venue,
  fetchTrigger // Only fetch when this changes
}) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerName || !fetchTrigger) return;
    
    const fetchSummary = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const params = new URLSearchParams();
        
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (venue) params.append('venue', venue);
        if (includeInternational) params.append('include_international', 'true');
        if (topTeams) params.append('top_teams', topTeams);
        
        if (leagues && leagues.length > 0) {
          leagues.forEach(league => params.append('leagues', league));
        }
        
        const endpoint = playerType === 'bowler' ? 'bowler' : 'batter';
        const response = await axios.get(
          `${config.API_URL}/player-summary/${endpoint}/${encodeURIComponent(playerName)}?${params.toString()}`
        );
        
        if (response.data.success) {
          setSummary(response.data);
        } else {
          setError(response.data.error || 'Failed to generate summary');
        }
      } catch (err) {
        console.error('Error fetching summary:', err);
        setError(err.response?.data?.detail || 'Failed to fetch player summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [fetchTrigger]); // Only re-fetch when trigger changes

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

  if (!playerName || !fetchTrigger) return null;

  return (
    <Box sx={{ mt: `${spacing.lg}px` }}>
      <Card>
        <CardContent sx={{ py: `${spacing.base}px`, '&:last-child': { pb: `${spacing.base}px` } }}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: `${spacing.sm}px`, mb: `${spacing.md}px` }}>
            <BoltIcon sx={{ color: 'primary.main', fontSize: spacing.lg }} />
            <Typography variant="subtitle1" fontWeight="bold">
              Player DNA
            </Typography>
            {summary?.cached && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                💾 Cached
              </Typography>
            )}
          </Box>

          {/* Loading State */}
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: `${spacing.md}px`, py: `${spacing.base}px` }}>
              <CircularProgress size={18} />
              <Typography variant="body2" color="text.secondary">
                Analyzing {playerType === 'bowler' ? 'bowling' : 'batting'} patterns...
              </Typography>
            </Box>
          )}

          {/* Error State */}
          {error && !loading && (
            <AlertBanner severity="error" sx={{ py: `${spacing.xs}px` }}>
              <Typography variant="body2">{error}</Typography>
            </AlertBanner>
          )}

          {/* Summary Items */}
          {summary?.success && summary.summary && !loading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.xs}px` }}>
              {parseSummary(summary.summary).map((bullet, index) => (
                <Box key={index} sx={{ display: 'flex', gap: `${spacing.sm}px`, alignItems: 'flex-start' }}>
                  <Typography component="span" sx={{ flexShrink: 0 }}>
                    {bullet.emoji}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {bullet.label && <strong>{bullet.label}: </strong>}
                    {bullet.text}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default PlayerDNASummary;
