import React, { useState } from 'react';
import { Typography, Box, useMediaQuery, useTheme } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { EmptyState } from './ui';
import { colors as designColors } from '../theme/designSystem';

const StrikeRateIntervals = ({ ballStats = [], isMobile: isMobileProp, wrapInCard = true }) => {  // Add default empty array
  const [interval, setInterval] = useState(5);
  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;
  const Wrapper = wrapInCard ? Card : Box;
  const wrapperProps = wrapInCard ? { isMobile } : { sx: { width: '100%' } };

  const processData = () => {
    // Return early if no data
    if (!ballStats || ballStats.length === 0) return [];

    const data = [];
    for (let i = interval - 1; i < ballStats.length; i += interval) {
      const currentBall = ballStats[i];
      
      // Get previous ball stats for calculating ball-by-ball data
      const prevBall = i > 0 ? ballStats[i - 1] : { total_runs: 0 };

      // Calculate runs and boundaries in this interval
      const runsInInterval = currentBall.total_runs - prevBall.total_runs;
    
      data.push({
        ballNumber: currentBall.ball_number,
        strikeRate: currentBall.strike_rate,
        noBalls: currentBall.innings_with_n_balls,
        dotPercentage: currentBall.dot_percentage,
        boundaryPercentage: currentBall.boundary_percentage
      });
    }
    return data;
  };

  const data = processData();

  // If no data, show a message
  if (!ballStats || ballStats.length === 0) {
    return (
      <Wrapper {...wrapperProps}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, mb: 1 }}>
          Strike Rate Progression by Intervals
        </Typography>
        <EmptyState
          title="No innings match these filters"
          description="Try adjusting the filters to see strike rate intervals."
          isMobile={isMobile}
          minHeight={isMobile ? 280 : 320}
          sx={{ mt: 1 }}
        />
      </Wrapper>
    );
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Card noPadding sx={{ p: 1, bgcolor: 'background.paper' }}>
          <Typography variant="body1" sx={{ fontWeight: 'bold', fontSize: isMobile ? '0.75rem' : undefined }}>
            {`Ball ${label}`}
          </Typography>
          <Typography variant="body2" sx={{ fontSize: isMobile ? '0.7rem' : undefined }}>
            {`${payload[0].payload.noBalls} innings`}
          </Typography>
          {payload.map((item) => (
            <Typography key={item.dataKey} variant="body2" style={{ color: item.color, fontSize: isMobile ? '0.7rem' : undefined }}>
              {`${item.name}: ${item.value.toFixed(1)}${item.unit || ''}`}
            </Typography>
          ))}
        </Card>
      );
    }
    return null;
  };

  const filterConfig = [
    {
      key: 'interval',
      label: 'Interval',
      options: [5, 10, 15, 20].map(value => ({ value, label: `${value}` }))
    }
  ];

  const handleFilterChange = (key, value) => {
    if (key === 'interval') setInterval(value);
  };

  const chartHeight = isMobile ? 350 : 400;

  return (
    <Wrapper {...wrapperProps}>
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: 2,
        gap: 1,
        flexWrap: isMobile ? 'wrap' : 'nowrap'
      }}>
        <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, flexShrink: 0 }}>
          SR Progression
        </Typography>
        <Box sx={{ flexShrink: 1, minWidth: 0 }}>
          <FilterBar
            filters={filterConfig}
            activeFilters={{ interval }}
            onFilterChange={handleFilterChange}
            isMobile={isMobile}
          />
        </Box>
      </Box>
      <Box sx={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer>
          <BarChart
            data={data}
            margin={{ top: 20, right: isMobile ? 5 : 30, left: isMobile ? 5 : 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="ballNumber"
              label={isMobile ? undefined : {
                value: 'Ball Number',
                position: 'bottom',
                offset: -5
              }}
              tick={{ fontSize: isMobile ? 10 : 12, fill: designColors.neutral[800] }}
            />
            <YAxis
              yAxisId="left"
              orientation="left"
              domain={[0, 200]}
              label={isMobile ? undefined : {
                value: 'Strike Rate',
                angle: -90,
                position: 'insideLeft',
                offset: 10
              }}
              tick={{ fontSize: isMobile ? 10 : 12, fill: designColors.neutral[800] }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              label={isMobile ? undefined : {
                value: 'Percentage',
                angle: 90,
                position: 'insideRight',
                offset: 10
              }}
              tick={{ fontSize: isMobile ? 10 : 12, fill: designColors.neutral[800] }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{
                fontSize: isMobile ? '0.75rem' : '0.875rem',
                color: designColors.neutral[800],
              }}
            />
            <Bar
              yAxisId="left"
              dataKey="strikeRate"
              name="Strike Rate"
              fill={designColors.chart.blue}
            />
            <Bar
              yAxisId="right"
              dataKey="boundaryPercentage"
              name="Boundary %"
              fill={designColors.chart.green}
            />
            <Bar
              yAxisId="right"
              dataKey="dotPercentage"
              name="Dot %"
              fill={designColors.chart.orange}
            />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Wrapper>
  );
};

export default StrikeRateIntervals;
