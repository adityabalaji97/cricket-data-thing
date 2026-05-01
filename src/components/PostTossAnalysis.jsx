import React, { useState } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Chip,
  Collapse,
  Grid,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import CondensedName from './common/CondensedName';

const TILE_ORDER = [
  { key: 'first_innings_batting', label: '1st Innings - Batting' },
  { key: 'first_innings_bowling', label: '1st Innings - Bowling' },
  { key: 'second_innings_batting', label: '2nd Innings - Batting' },
  { key: 'second_innings_bowling', label: '2nd Innings - Bowling' },
];

const valueOrDash = (value, digits = 1) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return Number(value).toFixed(digits);
};

const TileMetrics = ({ block }) => {
  if (!block) return null;
  const metrics = block.metrics || {};
  if (block.kind === 'batting') {
    return (
      <Stack spacing={0.5}>
        <Typography variant="body2">SR: <strong>{valueOrDash(metrics.strike_rate, 1)}</strong></Typography>
        <Typography variant="body2">Boundary %: <strong>{valueOrDash(metrics.boundary_percentage, 1)}</strong></Typography>
        <Typography variant="body2">Dot %: <strong>{valueOrDash(metrics.dot_percentage, 1)}</strong></Typography>
      </Stack>
    );
  }
  return (
    <Stack spacing={0.5}>
      <Typography variant="body2">Economy: <strong>{valueOrDash(metrics.economy, 2)}</strong></Typography>
      <Typography variant="body2">Wkts/20 overs: <strong>{valueOrDash(metrics.wickets_per_20_overs, 2)}</strong></Typography>
      <Typography variant="body2">Dot %: <strong>{valueOrDash(metrics.dot_percentage, 1)}</strong></Typography>
    </Stack>
  );
};

const PostTossAnalysis = ({ data, isMobile = false }) => {
  const [mode, setMode] = useState('general');
  const [expanded, setExpanded] = useState(true);

  const blocks = mode === 'venue' ? (data?.venue_blocks || {}) : (data?.blocks || {});
  const links = (data?.drill_down_links || {})[mode] || {};
  const hasData = TILE_ORDER.some((tile) => blocks?.[tile.key]);

  if (!data || !hasData) return null;

  return (
    <Box sx={{ mt: 2, p: { xs: 1.5, sm: 2 }, borderRadius: 2, border: '1px solid rgba(0,0,0,0.08)', bgcolor: 'rgba(0,0,0,0.015)' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5, gap: 1, flexWrap: 'wrap' }}>
        <Typography variant={isMobile ? 'subtitle1' : 'h6'}>
          Post-Toss Analysis
        </Typography>
        <Stack direction="row" spacing={0.75}>
          <ButtonGroup size="small">
            <Button variant={mode === 'general' ? 'contained' : 'outlined'} onClick={() => setMode('general')}>
              General
            </Button>
            <Button variant={mode === 'venue' ? 'contained' : 'outlined'} onClick={() => setMode('venue')}>
              At Venue
            </Button>
          </ButtonGroup>
          <Button size="small" variant="text" onClick={() => setExpanded((prev) => !prev)}>
            {expanded ? 'Hide' : 'Show'}
          </Button>
        </Stack>
      </Box>

      <Collapse in={expanded}>
        <Grid container spacing={1.5}>
          {TILE_ORDER.map((tile) => {
            const block = blocks?.[tile.key];
            if (!block) return null;
            const sampleBalls = block?.metrics?.sample_balls || 0;
            const samplePlayers = block?.metrics?.sample_players || 0;
            return (
              <Grid item xs={12} sm={6} key={tile.key}>
                <Box sx={{ p: 1.25, borderRadius: 1.5, border: '1px solid rgba(0,0,0,0.08)', bgcolor: 'background.paper', height: '100%' }}>
                  <Typography variant="subtitle2" sx={{ mb: 0.5, fontWeight: 700 }}>
                    {tile.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
                    <CondensedName name={block.team} type="team" /> vs <CondensedName name={block.opponent} type="team" />
                  </Typography>

                  <TileMetrics block={block} />

                  <Stack direction="row" spacing={0.75} sx={{ mt: 1, mb: 0.75 }} flexWrap="wrap">
                    <Chip size="small" label={`Sample: ${sampleBalls} balls / ${samplePlayers} players`} />
                    {block.sample_warning && <Chip size="small" color="warning" label="Low sample" />}
                    {block.overall_fallback && <Chip size="small" variant="outlined" label="Overall fallback included" />}
                  </Stack>

                  {links?.[tile.key] && (
                    <Link
                      href={links[tile.key]}
                      target="_blank"
                      rel="noreferrer"
                      underline="hover"
                      sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, fontSize: '0.85rem' }}
                    >
                      Open in query builder <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </Link>
                  )}
                </Box>
              </Grid>
            );
          })}
        </Grid>
      </Collapse>
    </Box>
  );
};

export default PostTossAnalysis;
