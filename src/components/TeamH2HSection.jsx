import React from 'react';
import { Alert, Box, Chip, Typography } from '@mui/material';

const TeamH2HSection = ({ h2hData }) => {
  if (!h2hData) {
    return <Alert severity="info">Head-to-head data is not available yet.</Alert>;
  }

  const rows = h2hData.summary || [];
  if (!rows.length) {
    return <Alert severity="info">No IPL head-to-head records found for this team.</Alert>;
  }

  const overall = h2hData.overall || {};

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Chip
          size="small"
          color="primary"
          label={`Overall: ${overall.wins || 0}-${overall.losses || 0}`}
        />
        <Chip size="small" variant="outlined" label={`Matches: ${overall.matches || 0}`} />
        <Chip size="small" variant="outlined" label={`NR: ${overall.no_results || 0}`} />
        {typeof overall.win_pct === 'number' ? (
          <Chip size="small" variant="outlined" label={`Win%: ${overall.win_pct.toFixed(1)}`} />
        ) : null}
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 1,
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, minmax(0, 1fr))',
            lg: 'repeat(3, minmax(0, 1fr))',
          },
        }}
      >
        {rows.map((row) => (
          <Box
            key={row.opponent}
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 2,
              p: 1.5,
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              {row.opponent} • {row.opponent_full_name}
            </Typography>
            <Typography variant="body2">
              Record: <strong>{row.wins}-{row.losses}</strong> {row.no_results ? `(${row.no_results} NR)` : ''}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Matches: {row.matches} {typeof row.win_pct === 'number' ? `• Win% ${row.win_pct.toFixed(1)}` : ''}
            </Typography>
            {row.recent_form ? (
              <Typography variant="caption" color="text.secondary">
                Recent: {row.recent_form}
              </Typography>
            ) : null}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default TeamH2HSection;
