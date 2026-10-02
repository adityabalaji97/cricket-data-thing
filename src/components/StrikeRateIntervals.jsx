import React, { useState } from 'react';
import { Typography, Box, ToggleButton, ToggleButtonGroup } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import Card from './ui/Card';
import FilterBar from './ui/FilterBar';
import { EmptyState } from './ui';
import useIsMobile from '../hooks/useIsMobile';
import {
  SERIES, chartMargin, xAxisProps, yAxisProps, axisLabel, tooltipProps, gridProps, barProps,
  chartHeight as chartHeightFor,
} from '../theme/chartDefaults';

const METRICS = {
  strikeRate: { label: 'Strike rate', short: 'SR', color: SERIES[0], unit: '' },
  boundaryPercentage: { label: 'Boundary %', short: 'Bnd %', color: SERIES[2], unit: '%' },
  dotPercentage: { label: 'Dot %', short: 'Dot %', color: SERIES[1], unit: '%' },
};

/**
 * Strike rate (or boundary % / dot %) by ball-of-innings interval. One metric at a time on one
 * axis: this was three bars per interval on two y-scales (SR 0-200 left, percentages right),
 * which at interval 5 meant ~36 hairline bars on a phone and a misleading cross-scale comparison.
 */
const StrikeRateIntervals = ({ ballStats = [], wrapInCard = true }) => {
  const { isMobile } = useIsMobile();
  const [interval, setInterval] = useState(isMobile ? 10 : 5);
  const [metric, setMetric] = useState('strikeRate');
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
  const m = METRICS[metric];

  const chartHeight = chartHeightFor(isMobile, 'md');

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
      <ToggleButtonGroup
        exclusive
        size="small"
        value={metric}
        onChange={(_, v) => v && setMetric(v)}
        sx={{ mb: 1.5 }}
      >
        {Object.entries(METRICS).map(([key, def]) => (
          <ToggleButton key={key} value={key} sx={{ minHeight: 36, px: 1.5 }}>{isMobile ? def.short : def.label}</ToggleButton>
        ))}
      </ToggleButtonGroup>
      <Box sx={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={chartMargin(isMobile)}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="ballNumber" {...xAxisProps(isMobile)} label={axisLabel(isMobile, 'Ball of innings', { side: 'bottom' })} />
            <YAxis {...yAxisProps(isMobile)} tickFormatter={(v) => `${v}${m.unit}`} />
            <Tooltip content={<CustomTooltip />} {...tooltipProps(isMobile)} />
            <Bar dataKey={metric} name={m.label} fill={m.color} {...barProps(isMobile)} />
          </BarChart>
        </ResponsiveContainer>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        {m.label} in each {interval}-ball stretch of his innings (balls 1-{interval}, {interval + 1}-{interval * 2}, ...).
      </Typography>
    </Wrapper>
  );
};

export default StrikeRateIntervals;
