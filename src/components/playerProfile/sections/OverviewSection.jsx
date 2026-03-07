import React from 'react';
import { Box, Card, CardContent, Typography } from '@mui/material';
import {
  EmojiEvents as TrophyIcon,
  PercentOutlined as PercentIcon,
  Timer as TimerIcon,
  TrendingUp as TrendingUpIcon,
  GpsFixed as TargetIcon,
  Bolt as FlashIcon,
  Sports as SportsIcon,
  Speed as SpeedIcon,
  FitnessCenter as FitnessCenterIcon,
  FormatListNumbered as FormatListNumberedIcon,
  PieChart as PieChartIcon
} from '@mui/icons-material';

const StatCard = ({ title, value, icon: Icon, subtitle = null }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Typography color="text.secondary" variant="body2">{title}</Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>{value}</Typography>
          {subtitle && (
            <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
              {subtitle}
            </Typography>
          )}
        </div>
        <Box sx={{ p: 1, bgcolor: 'primary.light', borderRadius: '50%' }}>
          <Icon sx={{ color: 'primary.main' }} />
        </Box>
      </Box>
    </CardContent>
  </Card>
);

const BattingOverview = ({ stats }) => {
  if (!stats?.overall) return null;
  const { overall } = stats;

  return (
    <Box sx={{
      display: 'grid', gap: 2,
      gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)', lg: 'repeat(6, 1fr)' }
    }}>
      <StatCard title="Matches" value={overall.matches || 0} icon={TrophyIcon} subtitle="Total Innings" />
      <StatCard title="Runs" value={overall.runs || 0} icon={TrendingUpIcon}
        subtitle={`Avg: ${(overall.average || 0).toFixed(2)}`} />
      <StatCard title="Strike Rate" value={(overall.strike_rate || 0).toFixed(2)} icon={TimerIcon} />
      <StatCard title="50s/100s" value={`${overall.fifties || 0}/${overall.hundreds || 0}`}
        icon={TargetIcon} subtitle={`${(overall.fifties || 0) + (overall.hundreds || 0)} milestone innings`} />
      <StatCard title="Dot %" value={`${(overall.dot_percentage || 0).toFixed(1)}%`}
        icon={PercentIcon} subtitle="Dot ball percentage" />
      <StatCard title="Boundary %" value={`${(overall.boundary_percentage || 0).toFixed(1)}%`}
        icon={FlashIcon} subtitle="Boundary percentage" />
    </Box>
  );
};

const BowlingOverview = ({ stats }) => {
  if (!stats?.overall) return null;
  const { overall } = stats;

  return (
    <Box sx={{
      display: 'grid', gap: 2,
      gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)', lg: 'repeat(6, 1fr)' }
    }}>
      <StatCard title="Matches" value={overall.matches || 0} icon={SportsIcon} subtitle="Total Matches" />
      <StatCard title="Wickets" value={overall.wickets || 0} icon={FitnessCenterIcon} subtitle="Total Wickets" />
      <StatCard title="Strike Rate" value={overall.bowling_strike_rate?.toFixed(2) || '0.00'}
        icon={TimerIcon} subtitle="Bowling Strike Rate" />
      <StatCard title="Economy" value={overall.economy_rate?.toFixed(2) || '0.00'}
        icon={SpeedIcon} subtitle="Economy Rate" />
      <StatCard title="Wicket Hauls" value={`${overall.three_wicket_hauls || 0}/${overall.five_wicket_hauls || 0}`}
        icon={FormatListNumberedIcon} subtitle="3WI/5WI" />
      <StatCard title="Dot %" value={`${overall.dot_percentage?.toFixed(1) || '0.0'}%`}
        icon={PieChartIcon} subtitle="Dot ball percentage" />
    </Box>
  );
};

const OverviewSection = ({ stats, mode }) => {
  if (mode === 'bowling') {
    return <BowlingOverview stats={stats} />;
  }
  return <BattingOverview stats={stats} />;
};

export default OverviewSection;
