import React, { useMemo } from 'react';
import { Alert, Box, Chip, Link, Typography } from '@mui/material';

const ROLE_LABELS = {
  batter: 'Batter',
  bowler: 'Bowler',
  'all-rounder': 'All-Rounder',
};

const ROLE_COLORS = {
  batter: 'primary',
  bowler: 'secondary',
  'all-rounder': 'success',
};

const TeamSquadSection = ({ rosterData }) => {
  const players = useMemo(() => rosterData?.players ?? [], [rosterData]);

  const sortedPlayers = useMemo(() => {
    return [...players].sort((a, b) => {
      if (a.role !== b.role) {
        return a.role.localeCompare(b.role);
      }
      const aName = (a.display_name || a.name || '').toLowerCase();
      const bName = (b.display_name || b.name || '').toLowerCase();
      return aName.localeCompare(bName);
    });
  }, [players]);

  if (!rosterData) {
    return <Alert severity="info">Roster data is not available yet.</Alert>;
  }

  if (!players.length) {
    return <Alert severity="info">No players found for this team.</Alert>;
  }

  const summary = rosterData.role_summary || {};
  const sourceLabel = rosterData.source === 'pre_season' ? 'Pre-season roster' : 'Recent match data';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
        <Chip size="small" label={sourceLabel} variant="outlined" />
        <Chip size="small" label={`Batter: ${summary.batter || 0}`} color="primary" />
        <Chip size="small" label={`Bowler: ${summary.bowler || 0}`} color="secondary" />
        <Chip size="small" label={`All-rounder: ${summary['all-rounder'] || 0}`} color="success" />
      </Box>

      <Box
        sx={{
          display: 'grid',
          gap: 1,
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, minmax(0, 1fr))',
            md: 'repeat(3, minmax(0, 1fr))',
          },
        }}
      >
        {sortedPlayers.map((player) => {
          const role = player.role || 'batter';
          const displayName = player.display_name || player.name;
          const routeName = encodeURIComponent(player.name || displayName);

          return (
            <Box
              key={`${player.name}-${role}`}
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                p: 1.25,
                display: 'flex',
                justifyContent: 'space-between',
                gap: 1,
                alignItems: 'center',
              }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Link
                  href={`/player?name=${routeName}&autoload=true`}
                  underline="hover"
                  sx={{ fontWeight: 600, display: 'block' }}
                >
                  {displayName}
                </Link>
                {player.name && player.name !== displayName ? (
                  <Typography variant="caption" color="text.secondary">
                    {player.name}
                  </Typography>
                ) : null}
              </Box>
              <Chip
                size="small"
                color={ROLE_COLORS[role] || 'default'}
                label={ROLE_LABELS[role] || role}
                sx={{ flexShrink: 0 }}
              />
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

export default TeamSquadSection;
