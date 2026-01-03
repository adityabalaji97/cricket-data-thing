import React from 'react';
import { Card, CardContent, Typography, Box, Tooltip } from '@mui/material';
import { Info as InfoIcon } from 'lucide-react';

const MetricCell = ({ stats }) => {
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

const BowlingMatchupMatrix = ({ stats }) => {
  // Dynamically get all bowling types from the stats data
  const bowlingTypes = stats?.phase_stats?.bowling_types
    ? Object.keys(stats.phase_stats.bowling_types).sort()
    : [];
  const phases = ['powerplay', 'middle', 'death', 'overall'];

  if (!bowlingTypes.length) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
            <Typography variant="h6">Bowling Type Matchups</Typography>
            <Tooltip title="Runs-Wickets (Balls) @ Strike Rate | Hover for more stats">
              <InfoIcon size={16} />
            </Tooltip>
          </Box>
          <Typography variant="body2" color="text.secondary">
            Bowling matchup data not available
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <Typography variant="h6">Bowling Type Matchups</Typography>
          <Tooltip title="Runs-Wickets (Balls) @ Strike Rate | Hover for more stats">
            <InfoIcon size={16} />
          </Tooltip>
        </Box>
        <Box sx={{ overflow: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px' }}>Phase</th>
                {bowlingTypes.map(type => (
                  <th key={type} style={{ textAlign: 'center', padding: '8px', minWidth: '120px' }}>
                    {type}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {phases.map(phase => (
                <tr key={phase}>
                  <td style={{ padding: '8px', textTransform: 'capitalize' }}>{phase}</td>
                  {bowlingTypes.map(type => (
                    <MetricCell 
                      key={type} 
                      stats={stats?.phase_stats?.bowling_types?.[type]?.[phase]}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      </CardContent>
    </Card>
  );
};

export default BowlingMatchupMatrix;