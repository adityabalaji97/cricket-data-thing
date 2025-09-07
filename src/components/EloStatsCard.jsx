import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Box,
  Chip
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import StarIcon from '@mui/icons-material/Star';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';

const EloStatsCard = ({ eloStats, teamName, dateRange }) => {
  if (!eloStats || eloStats.total_matches === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            ELO Rating Statistics
          </Typography>
          <Typography variant="body1" color="text.secondary">
            No ELO data available for the selected date range.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const { starting_elo, ending_elo, peak_elo, lowest_elo, elo_change, total_matches } = eloStats;

  // Determine trend icon and color
  const getTrendInfo = (change) => {
    if (change > 0) {
      return {
        icon: <TrendingUpIcon />,
        color: '#4caf50',
        text: 'Increasing'
      };
    } else if (change < 0) {
      return {
        icon: <TrendingDownIcon />,
        color: '#f44336',
        text: 'Decreasing'
      };
    } else {
      return {
        icon: <TrendingFlatIcon />,
        color: '#ff9800',
        text: 'Stable'
      };
    }
  };

  const trendInfo = getTrendInfo(elo_change);

  const formatEloValue = (value) => {
    return value ? Math.round(value) : 'N/A';
  };

  const getEloColor = (elo) => {
    if (elo >= 1600) return '#4caf50'; // Green for high ELO
    if (elo >= 1500) return '#ff9800'; // Orange for medium ELO
    if (elo >= 1400) return '#2196f3'; // Blue for decent ELO
    return '#9c27b0'; // Purple for lower ELO
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ mb: 0, mr: 2 }}>
            ELO Rating Statistics
          </Typography>
          <Chip
            icon={trendInfo.icon}
            label={`${elo_change > 0 ? '+' : ''}${elo_change} (${trendInfo.text})`}
            sx={{
              backgroundColor: trendInfo.color + '20',
              color: trendInfo.color,
              fontWeight: 'bold'
            }}
          />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {teamName} • {dateRange.start} to {dateRange.end} • {total_matches} matches
        </Typography>

        <Grid container spacing={3}>
          {/* Starting ELO */}
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Starting ELO
              </Typography>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 'bold',
                  color: getEloColor(starting_elo)
                }}
              >
                {formatEloValue(starting_elo)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {dateRange.start || 'Start of data'}
              </Typography>
            </Box>
          </Grid>

          {/* Ending ELO */}
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Current ELO
              </Typography>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 'bold',
                  color: getEloColor(ending_elo)
                }}
              >
                {formatEloValue(ending_elo)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {dateRange.end || 'Latest match'}
              </Typography>
            </Box>
          </Grid>

          {/* Peak ELO */}
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                <StarIcon sx={{ color: '#ffd700', fontSize: 16 }} />
                <Typography variant="body2" color="text.secondary">
                  Peak ELO
                </Typography>
              </Box>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 'bold',
                  color: '#ffd700'
                }}
              >
                {formatEloValue(peak_elo)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Best in period
              </Typography>
            </Box>
          </Grid>

          {/* Lowest ELO */}
          <Grid item xs={6} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, mb: 1 }}>
                <LocalFireDepartmentIcon sx={{ color: '#f44336', fontSize: 16 }} />
                <Typography variant="body2" color="text.secondary">
                  Lowest ELO
                </Typography>
              </Box>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 'bold',
                  color: '#f44336'
                }}
              >
                {formatEloValue(lowest_elo)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Lowest in period
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* ELO Range Summary */}
        <Box sx={{ 
          mt: 3, 
          p: 2, 
          backgroundColor: 'rgba(0, 0, 0, 0.02)',
          borderRadius: 1,
          border: '1px solid rgba(0, 0, 0, 0.1)'
        }}>
          <Typography variant="body2" color="text.secondary" align="center">
            <strong>ELO Range:</strong> {formatEloValue(lowest_elo)} - {formatEloValue(peak_elo)} 
            (Range: {formatEloValue(peak_elo - lowest_elo)} points)
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default EloStatsCard;
