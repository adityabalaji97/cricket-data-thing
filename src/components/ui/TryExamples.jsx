import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Chip, Typography } from '@mui/material';

/**
 * One-tap starting points for pages that otherwise open on a lone, empty form (comparisons,
 * matchups). Each example is a link to the page's own URL-parameter form, so it runs exactly as
 * a shared link would.
 *
 *   <TryExamples examples={[{ label: 'Kohli vs Babar', to: '/comparison?batters=V%20Kohli,Babar%20Azam' }]} />
 */
const TryExamples = ({ examples = [], label = 'Try' }) => {
  if (!examples.length) return null;
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1, mb: 2 }}>
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: '0.1em', mr: 0.5 }}>
        {label}
      </Typography>
      {examples.map((example) => (
        <Chip
          key={example.to}
          label={example.label}
          size="small"
          clickable
          component={RouterLink}
          to={example.to}
          variant="outlined"
        />
      ))}
    </Box>
  );
};

export default TryExamples;
