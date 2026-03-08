import React from 'react';
import { Box, Typography, Tooltip } from '@mui/material';

const getBattingColor = (runs) => {
  if (runs >= 50) return '#2e7d32';
  if (runs >= 30) return '#66bb6a';
  if (runs >= 15) return '#ffa726';
  return '#ef5350';
};

const getBowlingColor = (wickets) => {
  if (wickets >= 3) return '#2e7d32';
  if (wickets === 2) return '#66bb6a';
  if (wickets === 1) return '#ffa726';
  return '#ef5350';
};

const RecentFormStrip = ({ innings, mode, isMobile }) => {
  if (!innings || innings.length === 0) return null;

  const recent = innings.slice(0, 5);

  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', mt: 1 }}>
      <Typography
        variant="caption"
        sx={{ color: 'text.secondary', fontWeight: 600, pt: 0.5, flexShrink: 0 }}
      >
        Form
      </Typography>
      <Box sx={{ display: 'flex', gap: 0.75 }}>
        {recent.map((inn, i) => {
          if (mode === 'bowling') {
            const wickets = inn.wickets ?? 0;
            const runs = inn.runs_conceded ?? inn.runs ?? 0;
            const overs = inn.overs ?? '?';
            const econ = inn.economy ?? (overs !== '?' && overs > 0 ? (runs / overs).toFixed(1) : '?');
            const figures = `${wickets}/${runs}`;
            const opponent = inn.opponent || inn.opposition || '?';
            const tooltipText = `${figures} (${overs} ov), Econ ${econ} vs ${opponent}`;

            return (
              <Tooltip key={i} title={tooltipText} arrow>
                <Box sx={{ textAlign: 'center', cursor: 'default' }}>
                  <Box
                    sx={{
                      bgcolor: getBowlingColor(wickets),
                      color: '#fff',
                      borderRadius: 1,
                      px: isMobile ? 0.75 : 1,
                      py: 0.5,
                      fontWeight: 700,
                      fontSize: isMobile ? '0.7rem' : '0.8rem',
                      lineHeight: 1.2,
                      minWidth: isMobile ? 36 : 44,
                    }}
                  >
                    {figures}
                  </Box>
                  <Typography
                    variant="caption"
                    sx={{ fontSize: '0.6rem', color: 'text.secondary', display: 'block', mt: 0.25 }}
                  >
                    vs {(inn.opponent || inn.opposition || '?').slice(0, 3).toUpperCase()}
                  </Typography>
                </Box>
              </Tooltip>
            );
          }

          // Batting mode
          const runs = inn.runs ?? inn.score ?? 0;
          const balls = inn.balls ?? inn.balls_faced ?? '?';
          const sr = balls !== '?' && balls > 0 ? ((runs / balls) * 100).toFixed(1) : '?';
          const opponent = inn.opponent || inn.opposition || '?';
          const tooltipText = `${runs}(${balls}) vs ${opponent}, SR ${sr}`;

          return (
            <Tooltip key={i} title={tooltipText} arrow>
              <Box sx={{ textAlign: 'center', cursor: 'default' }}>
                <Box
                  sx={{
                    bgcolor: getBattingColor(runs),
                    color: '#fff',
                    borderRadius: 1,
                    px: isMobile ? 0.75 : 1,
                    py: 0.5,
                    fontWeight: 700,
                    fontSize: isMobile ? '0.75rem' : '0.85rem',
                    lineHeight: 1.2,
                    minWidth: isMobile ? 28 : 36,
                  }}
                >
                  {runs}
                </Box>
                <Typography
                  variant="caption"
                  sx={{ fontSize: '0.6rem', color: 'text.secondary', display: 'block', mt: 0.25 }}
                >
                  vs {(inn.opponent || inn.opposition || '?').slice(0, 3).toUpperCase()}
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
};

export default RecentFormStrip;
