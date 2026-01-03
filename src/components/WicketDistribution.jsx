import React from 'react';
import { Card, CardContent, Typography, Box, useMediaQuery, useTheme } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Label
} from 'recharts';

const WicketDistribution = ({ stats }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Early return if no data is provided
  if (!stats || !stats.phase_stats) {
    return null;
  }

  // Process the data for the chart
  const phaseData = [
    {
      phase: 'Powerplay',
      wickets: stats.phase_stats.powerplay.wickets,
      economy: parseFloat(stats.phase_stats.powerplay.economy.toFixed(2)),
      dot_percentage: parseFloat(stats.phase_stats.powerplay.dot_percentage.toFixed(2)),
      overs: parseFloat(stats.phase_stats.powerplay.overs.toFixed(1)),
      bowling_average: parseFloat(stats.phase_stats.powerplay.bowling_average.toFixed(2)),
      bowling_strike_rate: parseFloat(stats.phase_stats.powerplay.bowling_strike_rate.toFixed(2)),
      color: '#3f51b5'
    },
    {
      phase: 'Middle',
      wickets: stats.phase_stats.middle.wickets,
      economy: parseFloat(stats.phase_stats.middle.economy.toFixed(2)),
      dot_percentage: parseFloat(stats.phase_stats.middle.dot_percentage.toFixed(2)),
      overs: parseFloat(stats.phase_stats.middle.overs.toFixed(1)),
      bowling_average: parseFloat(stats.phase_stats.middle.bowling_average.toFixed(2)),
      bowling_strike_rate: parseFloat(stats.phase_stats.middle.bowling_strike_rate.toFixed(2)),
      color: '#009688'
    },
    {
      phase: 'Death',
      wickets: stats.phase_stats.death.wickets,
      economy: parseFloat(stats.phase_stats.death.economy.toFixed(2)),
      dot_percentage: parseFloat(stats.phase_stats.death.dot_percentage.toFixed(2)),
      overs: parseFloat(stats.phase_stats.death.overs.toFixed(1)),
      bowling_average: parseFloat(stats.phase_stats.death.bowling_average.toFixed(2)),
      bowling_strike_rate: parseFloat(stats.phase_stats.death.bowling_strike_rate.toFixed(2)),
      color: '#f44336'
    }
  ];

  // Custom tooltip to display detailed info
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;

      return (
        <Box
          sx={{
            backgroundColor: '#fff',
            padding: isMobile ? 1 : 1.5,
            border: '1px solid #ccc',
            borderRadius: 1,
            boxShadow: 2
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: data.color, fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
            {label} Phase
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            Wickets: <strong>{data.wickets}</strong>
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            Overs Bowled: <strong>{data.overs}</strong>
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            Economy Rate: <strong>{data.economy}</strong>
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            Dot Percentage: <strong>{data.dot_percentage}%</strong>
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            Bowling Average: <strong>{data.bowling_average}</strong>
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
            Bowling Strike Rate: <strong>{data.bowling_strike_rate}</strong>
          </Typography>
        </Box>
      );
    }
    return null;
  };

  // Responsive height calculation - fits in mobile viewport for screenshots
  const chartHeight = isMobile ?
    Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.5 : 350, 380) :
    400;

  return (
    <Card>
      <CardContent sx={{ p: isMobile ? 1.5 : 2 }}>
        <Typography variant={isMobile ? "body1" : "h6"} gutterBottom sx={{ fontWeight: 600 }}>
          Wicket Distribution by Phase
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom sx={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
          Breakdown of bowling performance across different match phases
        </Typography>

        <Box sx={{ width: '100%', height: chartHeight }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={phaseData}
              margin={{
                top: 10,
                right: isMobile ? 15 : 30,
                left: isMobile ? 10 : 20,
                bottom: isMobile ? 5 : 30,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="phase"
                tick={{ fontSize: isMobile ? 10 : 12 }}
              >
                {!isMobile && <Label value="Match Phase" position="bottom" offset={10} />}
              </XAxis>
              <YAxis
                yAxisId="left"
                tick={{ fontSize: isMobile ? 9 : 11 }}
              >
                {!isMobile && <Label value="Wickets" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />}
              </YAxis>
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[0, 15]}
                tick={{ fontSize: isMobile ? 9 : 11 }}
              >
                {!isMobile && <Label value="Economy Rate" angle={90} position="insideRight" style={{ textAnchor: 'middle' }} />}
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: isMobile ? '0.7rem' : '0.875rem' }}
                iconSize={isMobile ? 8 : 14}
              />
              <Bar
                yAxisId="left"
                dataKey="wickets"
                fill="#8884d8"
                name="Wickets"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                yAxisId="right"
                dataKey="economy"
                fill="#82ca9d"
                name="Economy Rate"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                yAxisId="left"
                dataKey="dot_percentage"
                fill="#ffc658"
                name={isMobile ? "Dot %" : "Dot Percentage (%)"}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mt: isMobile ? 1 : 2, textAlign: 'center', fontSize: isMobile ? '0.7rem' : '0.75rem' }}>
          {isMobile ? "PP (1-6), Mid (7-15), Death (16-20)" : "Powerplay (overs 1-6), Middle (overs 7-15), Death (overs 16-20)"}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default WicketDistribution;