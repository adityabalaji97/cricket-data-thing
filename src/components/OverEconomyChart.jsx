import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, ButtonGroup, Button } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Bar,
  ComposedChart,
  Label
} from 'recharts';
import { spacing, colors, typography, borderRadius } from '../theme/designSystem';

const OverEconomyChart = ({ stats, isMobile = false, wrapInCard = true }) => {
  const [selectedMetrics, setSelectedMetrics] = useState(['economy', 'wickets']);

  // Early return if no data is provided
  if (!stats || !stats.over_distribution || stats.over_distribution.length === 0) {
    return null;
  }

  // Process the data for the chart
  const chartData = stats.over_distribution.map(over => ({
    over: over.over_number,
    economy: parseFloat(over.economy.toFixed(2)),
    wickets: over.wickets,
    dot_percentage: parseFloat(over.dot_percentage.toFixed(2)),
    bowling_strike_rate: over.bowling_strike_rate >= 999 ? 0 : parseFloat(over.bowling_strike_rate.toFixed(2)),
    instances: over.instances_bowled,
    matches_percentage: parseFloat(over.matches_percentage.toFixed(1))
  })).sort((a, b) => a.over - b.over);

  // Find the min and max values for better Y-axis scaling
  const minEconomy = Math.max(0, Math.floor(Math.min(...chartData.map(item => item.economy)) * 0.9));
  const maxEconomy = Math.ceil(Math.max(...chartData.map(item => item.economy)) * 1.1);
  
  const maxWickets = Math.ceil(Math.max(...chartData.map(item => item.wickets)) * 1.2);
  const maxDotPercentage = Math.ceil(Math.max(...chartData.map(item => item.dot_percentage)) * 1.1);

  // Toggle a metric in the selected metrics array
  const toggleMetric = (metric) => {
    if (selectedMetrics.includes(metric)) {
      // Don't allow removing the last metric
      if (selectedMetrics.length > 1) {
        setSelectedMetrics(selectedMetrics.filter(m => m !== metric));
      }
    } else {
      setSelectedMetrics([...selectedMetrics, metric]);
    }
  };

  // Custom tooltip to display detailed info
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const overData = chartData.find(d => d.over === label);
      
      return (
        <Box
          sx={{
            backgroundColor: colors.neutral[0],
            padding: `${spacing.base}px`,
            border: `1px solid ${colors.neutral[300]}`,
            borderRadius: `${borderRadius.base}px`,
            boxShadow: '0 1px 2px rgba(0,0,0,0.06)'
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: typography.fontWeight.semibold }}>
            Over {label}
          </Typography>

          {selectedMetrics.includes('economy') && (
            <Typography variant="body2" sx={{ fontSize: typography.fontSize.xs }}>
              Economy: <strong>{overData.economy}</strong>
            </Typography>
          )}

          {selectedMetrics.includes('wickets') && (
            <Typography variant="body2" sx={{ fontSize: typography.fontSize.xs }}>
              Wickets: <strong>{overData.wickets}</strong>
            </Typography>
          )}

          {selectedMetrics.includes('dot_percentage') && (
            <Typography variant="body2" sx={{ fontSize: typography.fontSize.xs }}>
              Dot %: <strong>{overData.dot_percentage}%</strong>
            </Typography>
          )}

          <Typography variant="body2" sx={{ fontSize: typography.fontSize.xs }}>
            Bowled in <strong>{overData.instances}</strong> innings
            ({overData.matches_percentage}% of matches)
          </Typography>

          {overData.bowling_strike_rate > 0 && (
            <Typography variant="body2" sx={{ fontSize: typography.fontSize.xs }}>
              Strike Rate: <strong>{overData.bowling_strike_rate}</strong>
            </Typography>
          )}
        </Box>
      );
    }
    return null;
  };

  const metricColors = {
    economy: '#8884d8',
    wickets: '#82ca9d',
    dot_percentage: '#ffc658'
  };

  const metricLabels = {
    economy: 'Economy Rate',
    wickets: 'Wickets',
    dot_percentage: 'Dot %'
  };

  const chartHeight = isMobile ? 220 : 280;

  const content = (
    <>
      {!isMobile && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: `${spacing.base}px` }}>
          <ButtonGroup variant="outlined" size="small">
            <Button
              onClick={() => toggleMetric('economy')}
              variant={selectedMetrics.includes('economy') ? 'contained' : 'outlined'}
              sx={{ fontSize: typography.fontSize.xs }}
            >
              Economy
            </Button>
            <Button
              onClick={() => toggleMetric('wickets')}
              variant={selectedMetrics.includes('wickets') ? 'contained' : 'outlined'}
              sx={{ fontSize: typography.fontSize.xs }}
            >
              Wickets
            </Button>
            <Button
              onClick={() => toggleMetric('dot_percentage')}
              variant={selectedMetrics.includes('dot_percentage') ? 'contained' : 'outlined'}
              sx={{ fontSize: typography.fontSize.xs }}
            >
              Dot %
            </Button>
          </ButtonGroup>
        </Box>
      )}

      <Box sx={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{
              top: 5,
              right: isMobile ? 15 : 30,
              left: isMobile ? 10 : 20,
              bottom: isMobile ? 5 : 30,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="over"
              scale="point"
              tick={{ fontSize: isMobile ? 10 : 12 }}
            >
              {!isMobile && <Label value="Over Number" position="bottom" offset={10} />}
            </XAxis>

            {selectedMetrics.includes('economy') && (
              <YAxis
                yAxisId="economy"
                domain={[minEconomy, maxEconomy]}
                orientation="left"
                tick={{ fontSize: isMobile ? 9 : 11 }}
              >
                {!isMobile && <Label value="Economy Rate" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />}
              </YAxis>
            )}

            {selectedMetrics.includes('wickets') && (
              <YAxis
                yAxisId="wickets"
                orientation="right"
                domain={[0, maxWickets]}
                tick={{ fontSize: isMobile ? 9 : 11 }}
              >
                {!isMobile && <Label value="Wickets" angle={90} position="insideRight" style={{ textAnchor: 'middle' }} />}
              </YAxis>
            )}

            {selectedMetrics.includes('dot_percentage') && !selectedMetrics.includes('economy') && (
              <YAxis
                yAxisId="dot_percentage"
                orientation="left"
                domain={[0, maxDotPercentage]}
                tick={{ fontSize: isMobile ? 9 : 11 }}
              >
                {!isMobile && <Label value="Dot %" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />}
              </YAxis>
            )}

            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: typography.fontSize.xs }} iconSize={isMobile ? 8 : 14} />

            {selectedMetrics.includes('economy') && (
              <Line
                yAxisId="economy"
                type="monotone"
                dataKey="economy"
                stroke={metricColors.economy}
                strokeWidth={isMobile ? 2 : 3}
                name={metricLabels.economy}
              />
            )}

            {selectedMetrics.includes('wickets') && (
              <Bar
                yAxisId="wickets"
                dataKey="wickets"
                fill={metricColors.wickets}
                name={metricLabels.wickets}
                barSize={isMobile ? 15 : 20}
              />
            )}

            {selectedMetrics.includes('dot_percentage') && (
              <Line
                yAxisId={selectedMetrics.includes('economy') ? 'economy' : 'dot_percentage'}
                type="monotone"
                dataKey="dot_percentage"
                stroke={metricColors.dot_percentage}
                strokeWidth={isMobile ? 2 : 3}
                name={metricLabels.dot_percentage}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </Box>
    </>
  );

  if (!wrapInCard) return content;

  return (
    <Card sx={{
      borderRadius: `${borderRadius.base}px`,
      border: `1px solid ${colors.neutral[200]}`,
      backgroundColor: colors.neutral[0]
    }}>
      <CardContent sx={{ p: `${isMobile ? spacing.base : spacing.lg}px` }}>
        {content}
      </CardContent>
    </Card>
  );
};

export default OverEconomyChart;