import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { EmptyState } from './ui';
import { colors, spacing } from '../theme/designSystem';

const ContributionGraph = ({ innings, isMobile = false }) => {
  const { data, stats } = useMemo(() => {
    if (!innings || innings.length === 0) {
      return { data: [], stats: { total: 0, avgFantasy: 0, maxFantasy: 0 } };
    }

    const sorted = [...innings].sort((a, b) => new Date(a.date) - new Date(b.date));
    const dataPoints = sorted.map((inning) => ({
      date: inning.date,
      label: new Date(inning.date).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
      }),
      fantasyPoints: typeof inning.fantasy_points === 'number' ? inning.fantasy_points : 0,
      runs: inning.runs,
      balls: inning.balls_faced,
      opposition: inning.bowling_team,
    }));

    const fantasyPoints = dataPoints.map(point => point.fantasyPoints);
    const avgFantasy = fantasyPoints.length
      ? fantasyPoints.reduce((sum, value) => sum + value, 0) / fantasyPoints.length
      : 0;
    const maxFantasy = fantasyPoints.length ? Math.max(...fantasyPoints) : 0;

    return {
      data: dataPoints,
      stats: {
        total: dataPoints.length,
        avgFantasy,
        maxFantasy,
      },
    };
  }, [innings]);

  if (!innings || innings.length === 0) {
    return (
      <EmptyState
        title="No innings match these filters"
        description="Try adjusting the date range or venue to see more innings."
      />
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ mb: `${spacing.sm}px`, display: 'flex', flexWrap: 'wrap', gap: `${spacing.md}px`, color: 'text.secondary' }}>
        <Typography variant="body2" component="span">
          {stats.total} innings
        </Typography>
        <Typography variant="body2" component="span">
          Avg Fantasy: {stats.avgFantasy.toFixed(1)} pts
        </Typography>
        <Typography variant="body2" component="span">
          Peak: {stats.maxFantasy.toFixed(1)} pts
        </Typography>
      </Box>

      <Box sx={{ width: '100%', height: isMobile ? 220 : 280 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={colors.neutral[200]} strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: isMobile ? 10 : 12, fill: colors.neutral[600] }}
              interval={isMobile ? 4 : 2}
            />
            <YAxis
              tick={{ fontSize: isMobile ? 10 : 12, fill: colors.neutral[600] }}
              width={isMobile ? 32 : 40}
            />
            <Tooltip
              formatter={(value) => [`${value} pts`, 'Fantasy Points']}
              labelFormatter={(_, payload) => {
                if (!payload?.length) return '';
                const entry = payload[0].payload;
                return `${entry.label} • ${entry.opposition}`;
              }}
            />
            <Line
              type="monotone"
              dataKey="fantasyPoints"
              stroke={colors.primary[600]}
              strokeWidth={2}
              dot={{ r: isMobile ? 2 : 3 }}
              activeDot={{ r: isMobile ? 4 : 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};

export default ContributionGraph;
