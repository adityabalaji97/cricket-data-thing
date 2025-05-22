import React from 'react';
import { Box, Card, CardContent, Typography, Grid } from '@mui/material';
import SportsIcon from '@mui/icons-material/Sports';
import SpeedIcon from '@mui/icons-material/Speed';
import TimerIcon from '@mui/icons-material/Timer';
import PieChartIcon from '@mui/icons-material/PieChart';
import FitnessCenterIcon from '@mui/icons-material/FitnessCenter';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import FormatListNumberedIcon from '@mui/icons-material/FormatListNumbered';

const BowlingCareerStatsCards = ({ stats }) => {
  if (!stats || !stats.overall) {
    return null;
  }

  const overall = stats.overall;
  
  // Define the stat cards to display
  const statCards = [
    {
      title: 'Matches',
      value: overall.matches,
      icon: <SportsIcon color="primary" />,
      secondaryText: 'Total Matches'
    },
    {
      title: 'Wickets',
      value: overall.wickets,
      icon: <FitnessCenterIcon color="primary" />,
      secondaryText: 'Total Wickets'
    },
    {
      title: 'Strike Rate',
      value: overall.bowling_strike_rate?.toFixed(2) || '0.00',
      icon: <TimerIcon color="primary" />,
      secondaryText: 'Bowling Strike Rate'
    },
    {
      title: 'Economy Rate',
      value: overall.economy_rate?.toFixed(2) || '0.00',
      icon: <SpeedIcon color="primary" />,
      secondaryText: 'Economy Rate'
    },
    {
      title: 'Wicket Hauls',
      value: `${overall.three_wicket_hauls}/${overall.five_wicket_hauls}`,
      icon: <FormatListNumberedIcon color="primary" />,
      secondaryText: '3WI/5WI'
    },
    {
      title: 'Dot %',
      value: `${overall.dot_percentage?.toFixed(1) || '0.0'}%`,
      icon: <PieChartIcon color="primary" />,
      secondaryText: 'Dot ball percentage'
    }
  ];

  return (
    <Box sx={{ mb: 4 }}>
      <Grid container spacing={2}>
        {statCards.map((card, index) => (
          <Grid item xs={6} sm={4} md={2} key={index}>
            <Card sx={{ height: '100%', boxShadow: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h6" component="div">
                    {card.title}
                  </Typography>
                  {card.icon}
                </Box>
                <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', my: 1 }}>
                  {card.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {card.secondaryText}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default BowlingCareerStatsCards;