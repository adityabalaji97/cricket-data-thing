import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  CircularProgress,
  Typography,
} from '@mui/material';
import axios from 'axios';
import config from '../config';

const MatchPreviewCard = ({
  venue,
  team1Identifier,
  team2Identifier,
  isMobile = false,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const requestKey = useMemo(
    () => [venue, team1Identifier, team2Identifier].filter(Boolean).join('|'),
    [venue, team1Identifier, team2Identifier]
  );

  useEffect(() => {
    if (!venue || !team1Identifier || !team2Identifier) return;
    let cancelled = false;

    const fetchPreview = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get(
          `${config.API_URL}/match-preview/${encodeURIComponent(venue)}/${encodeURIComponent(team1Identifier)}/${encodeURIComponent(team2Identifier)}`
        );
        if (!cancelled) {
          setData(response.data);
        }
      } catch (err) {
        console.error('Error fetching match preview:', err);
        if (!cancelled) setError('Failed to load match preview');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchPreview();
    return () => {
      cancelled = true;
    };
  }, [requestKey, venue, team1Identifier, team2Identifier]);

  if (!venue || !team1Identifier || !team2Identifier) return null;

  if (loading && !data) {
    return (
      <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(25,118,210,0.04)', border: '1px solid rgba(25,118,210,0.15)' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Generating AI preview...</Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(244,67,54,0.04)', border: '1px solid rgba(244,67,54,0.15)' }}>
        <Typography variant="body2" color="error">{error}</Typography>
      </Box>
    );
  }

  if (!data?.preview) return null;

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, borderRadius: 2, bgcolor: 'rgba(0,0,0,0.02)', border: '1px solid rgba(0,0,0,0.08)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center', mb: 1 }}>
        <Typography variant={isMobile ? 'subtitle1' : 'h6'}>
          AI Match Preview
        </Typography>
        {data.cached && (
          <Typography variant="caption" color="text.secondary">cached</Typography>
        )}
      </Box>
      <Typography
        component="div"
        variant="body2"
        sx={{
          whiteSpace: 'pre-wrap',
          '& h2': { fontSize: isMobile ? '0.95rem' : '1rem', mt: 1.2, mb: 0.4 },
          '& p': { m: 0 },
        }}
      >
        {data.preview}
      </Typography>
    </Box>
  );
};

export default MatchPreviewCard;
