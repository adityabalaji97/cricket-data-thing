import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  LinearProgress,
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
  const narrativeInsights = data.narrative_insights || [];

  return (
    <Box sx={{
      p: { xs: 1.5, sm: 2 },
      borderRadius: 2,
      bgcolor: 'rgba(156, 39, 176, 0.04)',
      border: '1px solid rgba(156, 39, 176, 0.15)',
    }}>
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

      {/* Narrative insights */}
      {narrativeInsights.length > 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {narrativeInsights.map((insight, idx) => (
            <Typography key={idx} variant="body2" sx={{
              lineHeight: 1.5,
              color: 'text.secondary',
              pl: 1.5,
              borderLeft: '2px solid rgba(156, 39, 176, 0.3)',
            }}>
              {insight}
            </Typography>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default ForesightCard;
