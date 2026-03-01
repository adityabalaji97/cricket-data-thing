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
    </Grid>
  </Box>
);

export default CreditsPage;
