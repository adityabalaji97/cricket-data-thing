import React from 'react';
import {
  Alert,
  Box,
  CircularProgress,
  LinearProgress,
  Typography,
} from '@mui/material';

const formatCategoryLabel = (key) => {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const TeamChampionshipSection = ({ championshipData, teamLabel }) => {
  if (!championshipData) {
    return (
      <Alert severity="info">
        Championship model output is not available yet for {teamLabel}. This section will populate in Phase 3.
      </Alert>
    );
  }

  const compositeScore = Number(championshipData.composite_score || 0);
  const rank = championshipData.rank;
  const totalTeams = championshipData.total_teams;
  const categoryScores = championshipData.category_scores || {};

  const categoryRows = Object.entries(categoryScores).map(([key, value]) => {
    const score = typeof value === 'number' ? value : Number(value?.score || 0);
    return { key, score };
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box sx={{ position: 'relative', display: 'inline-flex' }}>
          <CircularProgress
            variant="determinate"
            value={Math.max(0, Math.min(100, compositeScore))}
            size={88}
            thickness={4.5}
          />
          <Box
            sx={{
              inset: 0,
              position: 'absolute',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              {compositeScore.toFixed(1)}
            </Typography>
          </Box>
        </Box>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Championship Composite Score
          </Typography>
          {rank && totalTeams ? (
            <Typography variant="body2" color="text.secondary">
              Rank: {rank} of {totalTeams}
            </Typography>
          ) : null}
        </Box>
      </Box>

      {categoryRows.length ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          {categoryRows.map((row) => (
            <Box key={row.key}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2">{formatCategoryLabel(row.key)}</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {row.score.toFixed(1)}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.max(0, Math.min(100, row.score))}
                sx={{ height: 8, borderRadius: 6 }}
              />
            </Box>
          ))}
        </Box>
      ) : null}
    </Box>
  );
};

export default TeamChampionshipSection;
