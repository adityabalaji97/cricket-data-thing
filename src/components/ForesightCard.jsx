import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Chip,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material';
import axios from 'axios';
import config from '../config';
import CondensedName from './common/CondensedName';

const ForesightCard = ({
  venue,
  team1,
  team2,
  enabled = true,
  isMobile = false,
}) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  const requestKey = useMemo(
    () => JSON.stringify({ venue, team1, team2 }),
    [venue, team1, team2]
  );

  useEffect(() => {
    if (!enabled || !venue || !team1 || !team2) return;
    let cancelled = false;

    const fetchPrediction = async () => {
      setData(null);
      setError(false);
      try {
        const response = await axios.get(
          `${config.API_URL}/predictions/${encodeURIComponent(venue)}/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}`
        );
        if (!cancelled) {
          setData(response.data);
        }
      } catch (err) {
        console.error('Error fetching ML prediction:', err);
        if (!cancelled) setError(true);
      }
    };

    fetchPrediction();
    return () => { cancelled = true; };
  }, [enabled, requestKey, venue, team1, team2]);

  // Don't render anything if no prediction available
  if (!data?.available) return null;
  if (error) return null;

  const t1Prob = data.team1_win_prob ? (data.team1_win_prob * 100) : 50;
  const t2Prob = data.team2_win_prob ? (data.team2_win_prob * 100) : 50;
  const score1st = data.predicted_1st_innings_score ? Math.round(data.predicted_1st_innings_score) : null;
  const score2nd = data.predicted_2nd_innings_score ? Math.round(data.predicted_2nd_innings_score) : null;
  const topFeatures = data.top_features || [];

  return (
    <Box sx={{
      p: { xs: 1.5, sm: 2 },
      borderRadius: 2,
      bgcolor: 'rgba(156, 39, 176, 0.04)',
      border: '1px solid rgba(156, 39, 176, 0.15)',
    }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ fontWeight: 700 }}>
          ML Foresight
        </Typography>
        <Stack direction="row" spacing={0.5}>
          {data.gates_passed && (
            <Chip size="small" label={`${data.gates_passed} gates`} variant="outlined" color="secondary" />
          )}
          {data.model_version && (
            <Chip size="small" label={data.model_version} variant="outlined" />
          )}
        </Stack>
      </Box>

      {/* Win probability bar */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            <CondensedName name={data.team1} type="team" />
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            <CondensedName name={data.team2} type="team" />
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={t1Prob}
          sx={{
            height: 10,
            borderRadius: 5,
            bgcolor: 'rgba(244, 67, 54, 0.2)',
            '& .MuiLinearProgress-bar': {
              borderRadius: 5,
              bgcolor: 'rgba(25, 118, 210, 0.8)',
            },
          }}
        />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            {t1Prob.toFixed(1)}%
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            {t2Prob.toFixed(1)}%
          </Typography>
        </Box>
      </Box>

      {/* Predicted scores */}
      {(score1st || score2nd) && (
        <Box sx={{ mb: 1.5 }}>
          {score1st && (
            <Typography variant="body2" color="text.secondary">
              Predicted 1st innings: <strong>{score1st}</strong>
            </Typography>
          )}
          {score2nd && (
            <Typography variant="body2" color="text.secondary">
              Predicted 2nd innings: <strong>{score2nd}</strong>
            </Typography>
          )}
        </Box>
      )}

      {/* Key factors */}
      {topFeatures.length > 0 && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Key factors:
          </Typography>
          {topFeatures.slice(0, 5).map((f, idx) => (
            <Typography key={idx} variant="body2" sx={{ lineHeight: 1.4, color: 'text.secondary' }}>
              {f.direction === 'positive' ? '\u25B2' : '\u25BC'}{' '}
              {f.team === 'team1' ? data.team1 : f.team === 'team2' ? data.team2 : ''}{' '}
              {f.feature}
            </Typography>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default ForesightCard;
