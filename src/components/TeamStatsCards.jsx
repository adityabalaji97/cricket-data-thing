import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { 
  SportsHandball as MatchesIcon,
  TrendingUp as WinsIcon,
  SportsCricket as BattingFirstIcon,
  SportsTennis as FieldingFirstIcon,
  Equalizer as RatioIcon,
  Casino as TossIcon
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

const TeamStatsCards = ({ metrics, teamName, dateRange }) => {
  const winPercentage = metrics.totalMatches > 0 
    ? ((metrics.wins / metrics.totalMatches) * 100).toFixed(1) 
    : '0.0';

  // Calculate batting first success rate
  const battingFirstSuccessRate = metrics.battedFirstMatches > 0
    ? ((metrics.wonBattingFirst / metrics.battedFirstMatches) * 100).toFixed(1)
    : '0.0';

  // Calculate fielding first success rate  
  const fieldingFirstSuccessRate = metrics.fieldedFirstMatches > 0
    ? ((metrics.wonFieldingFirst / metrics.fieldedFirstMatches) * 100).toFixed(1)
    : '0.0';

  // Determine toss decision preference
  const getTossDecision = () => {
    return (
      <span style={{ whiteSpace: 'nowrap' }}>
        {metrics.tossBatFirst} <span style={{ fontSize: '0.7em' }}>🏏</span> / {metrics.tossBowlFirst} <span style={{ fontSize: '0.7em' }}>🏐</span>
      </span>
    );
  };

  const getTossSubtitle = () => {
    return `${metrics.tossWins}/${metrics.totalMatches} tosses won`;
  };

  return (
    <Box sx={{ mb: 4 }}>
      {/* Team Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
          {teamName}
        </Typography>
        <Typography variant="h6" color="text.secondary">
          {dateRange.start} to {dateRange.end}
        </Typography>
      </Box>

      {/* Stats Grid */}
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
          value={metrics.totalMatches}
          icon={MatchesIcon}
          subtitle="Total matches played"
        />
        <StatCard
          title="W/L Ratio"
          value={metrics.winLossRatio}
          icon={RatioIcon}
          subtitle={`${metrics.losses} losses, ${metrics.noResults} NR`}
        />
        <StatCard
          title="Success Rate"
          value={`${winPercentage}%`}
          icon={WinsIcon}
          subtitle={`${metrics.wins}W ${metrics.losses}L ${metrics.noResults}NR`}
        />
        <StatCard
          title="Won Batting First"
          value={metrics.wonBattingFirst}
          icon={BattingFirstIcon}
          subtitle={`${battingFirstSuccessRate}% of ${metrics.battedFirstMatches} matches`}
        />
        <StatCard
          title="Won Fielding First"
          value={metrics.wonFieldingFirst}
          icon={FieldingFirstIcon}
          subtitle={`${fieldingFirstSuccessRate}% of ${metrics.fieldedFirstMatches} matches`}
        />
        <StatCard
          title="Toss Decision"
          value={getTossDecision()}
          icon={TossIcon}
          subtitle={getTossSubtitle()}
        />
      </Box>
    </Box>
  );
};

export default TeamStatsCards;