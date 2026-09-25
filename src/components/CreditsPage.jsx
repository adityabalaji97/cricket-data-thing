import React from 'react';
import { Box, Grid, Link, Typography } from '@mui/material';

const SectionCard = ({ title, children }) => (
  <Box
    sx={{
      border: '1px solid',
      borderColor: 'divider',
      borderRadius: 3,
      bgcolor: 'background.paper',
      boxShadow: 1,
      p: { xs: 2, md: 3 },
      height: '100%',
    }}
  >
    <Typography
      variant="caption"
      sx={{
        display: 'block',
        mb: 1,
        color: 'primary.main',
        fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}
    >
      {title}
    </Typography>
    {children}
  </Box>
);

const CreditsPage = () => (
  <Box sx={{ my: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 3,
        bgcolor: 'background.paper',
        boxShadow: 1,
        p: { xs: 2, md: 3 },
      }}
    >
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
        Credits & Acknowledgements
      </Typography>
      <Typography variant="body1" color="text.secondary">
        The project pulls together open cricket data, community-driven ideas, and a lot of implementation help.
        This page keeps those attributions in one place instead of burying them inside venue analysis.
      </Typography>
    </Box>

    <Grid container spacing={3}>
      <Grid item xs={12} md={4}>
        <SectionCard title="Data Sources">
          <Typography variant="body1" sx={{ mb: 1.5, fontWeight: 600 }}>
            Ball-by-ball data
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            <Link href="https://cricsheet.org/" target="_blank" rel="noopener noreferrer">
              Cricsheet.org
            </Link>
          </Typography>
          <Typography variant="body1" sx={{ mb: 1.5, fontWeight: 600 }}>
            Player information
          </Typography>
          <Typography variant="body2">
            <Link href="https://cricmetric.com/" target="_blank" rel="noopener noreferrer">
              Cricmetric
            </Link>
          </Typography>
        </SectionCard>
      </Grid>
      <Grid item xs={12} md={4}>
        <SectionCard title="Inspiration">
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            Metrics, visual thinking, and cricket analysis inspiration from:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {[
              ['@prasannalara', 'https://twitter.com/prasannalara'],
              ['@cricketingview', 'https://twitter.com/cricketingview'],
              ['@IndianMourinho', 'https://twitter.com/IndianMourinho'],
              ['@hganjoo_153', 'https://twitter.com/hganjoo_153'],
              ['@randomcricstat', 'https://twitter.com/randomcricstat'],
              ['@kaustats', 'https://twitter.com/kaustats'],
              ['@cricviz', 'https://twitter.com/cricviz'],
              ['@ajarrodkimber', 'https://twitter.com/ajarrodkimber'],
            ].map(([label, href]) => (
              <Link key={label} href={href} target="_blank" rel="noopener noreferrer" underline="hover">
                {label}
              </Link>
            ))}
          </Box>
        </SectionCard>
      </Grid>
      <Grid item xs={12} md={4}>
        <SectionCard title="Development">
          <Typography variant="body2" sx={{ mb: 2 }}>
            Claude and ChatGPT both helped move the project forward during development.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Cricket Data Thing © {new Date().getFullYear()}.
          </Typography>
        </SectionCard>
      </Grid>
      <Grid item xs={12}>
        <SectionCard title="Contextual metrics">
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            Impact, RAA, WAA, WPA and leverage follow{' '}
            <Link href="https://twitter.com/hganjoo_153" target="_blank" rel="noopener noreferrer">Himanish Ganjoo</Link>&apos;s{' '}
            <i>T20 Metrics: A Primer</i> (August 2026), refit on Hindsight&apos;s men&apos;s T20 data (2015 onward, the
            Hundred excluded).
          </Typography>
          <Box component="dl" sx={{ m: 0, display: 'grid', gridTemplateColumns: { xs: '1fr', md: '160px 1fr' }, columnGap: 2, rowGap: 1,
            '& dt': { fontWeight: 700 }, '& dd': { m: 0, color: 'text.secondary', fontSize: 14 } }}>
            <dt>Par</dt>
            <dd>Expected first-innings total for a match, by nested Bayesian shrinkage: league, then season, then ground (T20Is: season, then country).</dd>
            <dt>Impact</dt>
            <dd>How much a ball moved the batting side&apos;s projected final total, using a Duckworth-Lewis (DL Pro) run curve calibrated to the match&apos;s par. Runs added for batters, runs saved for bowlers.</dd>
            <dt>RAA / WAA</dt>
            <dd>Runs and wickets above what an average player produces in the same game state (balls left, wickets down, par or target, innings).</dd>
            <dt>WPA</dt>
            <dd>Win probability added: the change in the batting side&apos;s chance of winning on each ball, from the DL score ratio (P = r⁶ / (1 + r⁶)). 1.0 is one match won.</dd>
            <dt>Leverage</dt>
            <dd>How much was at stake on a ball: the win-probability gap between a six and a wicket.</dd>
          </Box>
        </SectionCard>
      </Grid>
    </Grid>
  </Box>
);

export default CreditsPage;
