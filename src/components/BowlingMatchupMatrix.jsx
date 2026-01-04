import React from 'react';
import { Typography, Box, Tooltip, useMediaQuery, useTheme } from '@mui/material';
import { Info as InfoIcon } from 'lucide-react';
import Card from './ui/Card';
import { EmptyState } from './ui';

const MetricCell = ({ stats, isMobile }) => {
  if (!stats || !stats.runs) return <td style={{ textAlign: 'center', padding: '8px' }}>-</td>;

  const wickets = stats.average === 0 ? 0 : stats.runs / stats.average;
  const balls = stats.runs / (stats.strike_rate / 100);

  const getColor = (sr, balls) => {
    if (balls < 6) return '#6B7280';
    if (sr >= 150) return '#2E7D32';
    if (sr <= 100) return '#D32F2F';
    return '#ED6C02';
  };

  const displayValue = `${stats.runs}-${Math.round(wickets)} (${Math.round(balls)}) @ ${stats.strike_rate.toFixed(1)}`;

  return (
    <td style={{ 
      textAlign: 'center', 
      padding: '8px',
      color: getColor(stats.strike_rate, balls)
    }}>
      <Tooltip title={
        <Box>
          <Typography variant="body2">
            Average: {stats.average ? stats.average.toFixed(1) : '-'}
            <br />
            Boundary %: {stats.boundary_percentage.toFixed(1)}%
            <br />
            Dot %: {stats.dot_percentage.toFixed(1)}%
          </Typography>
        </Box>
      }>
        <Box>{displayValue}</Box>
      </Tooltip>
    </td>
  );
};

const BowlingMatchupMatrix = ({ stats, isMobile: isMobileProp, wrapInCard = true }) => {
  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;
  const Wrapper = wrapInCard ? Card : Box;
  const wrapperProps = wrapInCard ? { isMobile } : { sx: { width: '100%' } };

  // Dynamically get all bowling types from the stats data
  const bowlingTypes = stats?.phase_stats?.bowling_types
    ? Object.keys(stats.phase_stats.bowling_types).sort()
    : [];
  const phases = ['powerplay', 'middle', 'death', 'overall'];

  if (!bowlingTypes.length) {
    return (
      <Wrapper {...wrapperProps}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600 }}>
            Bowling Type Matchups
          </Typography>
          <Tooltip title="Runs-Wickets (Balls) @ Strike Rate | Hover for more stats">
            <InfoIcon size={isMobile ? 14 : 16} />
          </Tooltip>
        </Box>
        <EmptyState
          title="No innings match these filters"
          description="Bowling matchup data is unavailable for the selected filters."
          isMobile={isMobile}
          minHeight={isMobile ? 220 : 260}
        />
      </Wrapper>
    );
  }

  return (
    <Wrapper {...wrapperProps}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600 }}>
          Bowling Type Matchups
        </Typography>
        <Tooltip title="Runs-Wickets (Balls) @ Strike Rate | Hover for more stats">
          <InfoIcon size={isMobile ? 14 : 16} />
        </Tooltip>
      </Box>
      <Box sx={{ overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: isMobile ? '0.75rem' : undefined }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: isMobile ? '6px' : '8px' }}>Phase</th>
              {bowlingTypes.map(type => (
                <th key={type} style={{ textAlign: 'center', padding: isMobile ? '6px' : '8px', minWidth: isMobile ? '100px' : '120px' }}>
                  {type}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {phases.map(phase => (
              <tr key={phase}>
                <td style={{ padding: isMobile ? '6px' : '8px', textTransform: 'capitalize' }}>{phase}</td>
                {bowlingTypes.map(type => (
                  <MetricCell
                    key={type}
                    stats={stats?.phase_stats?.bowling_types?.[type]?.[phase]}
                    isMobile={isMobile}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Box>
    </Wrapper>
  );
};

export default BowlingMatchupMatrix;
