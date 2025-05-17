import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { 
  EmojiEvents as TrophyIcon,
  PercentOutlined as PercentIcon, 
  Timer as TimerIcon,
  TrendingUp as TrendingUpIcon, 
  GpsFixed as TargetIcon,  // Changed from Target
  Bolt as FlashIcon  // Changed from FlashOn
} from '@mui/icons-material';

const StatCard = ({ title, value, icon: Icon, subtitle = null }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Typography color="text.secondary" variant="body2">
            {title}
          </Typography>
          <Typography variant="h4" sx={{ mt: 1 }}>
            {value}
          </Typography>
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

const CareerStatsCards = ({ stats }) => {
  const { overall } = stats;
  
  return (
    <Box sx={{ 
      display: 'grid', 
      gap: 2,
      gridTemplateColumns: {
        xs: '1fr',
        sm: '1fr 1fr',
        md: '1fr 1fr 1fr',
        lg: 'repeat(6, 1fr)'
      }
    }}>
      <StatCard
        title="Matches"
        value={overall.matches}
        icon={TrophyIcon}
        subtitle="Total Innings"
      />
      <StatCard
        title="Runs"
        value={overall.runs}
        icon={TrendingUpIcon}
        subtitle={`Avg: ${overall.average.toFixed(2)}`}
      />
      <StatCard
        title="Strike Rate"
        value={overall.strike_rate.toFixed(2)}
        icon={TimerIcon}
      />
      <StatCard
        title="50s/100s"
        value={`${overall.fifties}/${overall.hundreds}`}
        icon={TargetIcon}
        subtitle={`${overall.fifties + overall.hundreds} milestone innings`}
      />
      <StatCard
        title="Dot %"
        value={`${overall.dot_percentage.toFixed(1)}%`}
        icon={PercentIcon}
        subtitle="Dot ball percentage"
      />
      <StatCard
        title="Boundary %"
        value={`${overall.boundary_percentage.toFixed(1)}%`}
        icon={FlashIcon}
        subtitle="Boundary percentage"
      />
    </Box>
  );
};

export default CareerStatsCards;