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

const OverEconomyChart = ({ stats }) => {
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
            backgroundColor: '#fff',
            padding: 1.5,
            border: '1px solid #ccc',
            borderRadius: 1,
            boxShadow: 2
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
            Over {label}
          </Typography>
          
          {selectedMetrics.includes('economy') && (
            <Typography variant="body2">
              Economy: <strong>{overData.economy}</strong>
            </Typography>
          )}
          
          {selectedMetrics.includes('wickets') && (
            <Typography variant="body2">
              Wickets: <strong>{overData.wickets}</strong>
            </Typography>
          )}
          
          {selectedMetrics.includes('dot_percentage') && (
            <Typography variant="body2">
              Dot %: <strong>{overData.dot_percentage}%</strong>
            </Typography>
          )}
          
          <Typography variant="body2">
            Bowled in <strong>{overData.instances}</strong> innings 
            ({overData.matches_percentage}% of matches)
          </Typography>
          
          {overData.bowling_strike_rate > 0 && (
            <Typography variant="body2">
              Strike Rate: <strong>{overData.bowling_strike_rate}</strong>
            </Typography>
          )}
        </Box>
      );
    }
    return null;
  };

  // Define colors for each metric
  const metricColors = {
    economy: '#8884d8',
    wickets: '#82ca9d',
    dot_percentage: '#ffc658'
  };

  // Define labels for each metric
  const metricLabels = {
    economy: 'Economy Rate',
    wickets: 'Wickets',
    dot_percentage: 'Dot %'
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Over-by-Over Performance Analysis
          </Typography>
          <ButtonGroup variant="outlined" size="small">
            <Button
              onClick={() => toggleMetric('economy')}
              variant={selectedMetrics.includes('economy') ? 'contained' : 'outlined'}
            >
              Economy
            </Button>
            <Button
              onClick={() => toggleMetric('wickets')}
              variant={selectedMetrics.includes('wickets') ? 'contained' : 'outlined'}
            >
              Wickets
            </Button>
            <Button
              onClick={() => toggleMetric('dot_percentage')}
              variant={selectedMetrics.includes('dot_percentage') ? 'contained' : 'outlined'}
            >
              Dot %
            </Button>
          </ButtonGroup>
        </Box>
        
        <Box sx={{ width: '100%', height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 30,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="over"
                scale="point"
              >
                <Label value="Over Number" position="bottom" offset={10} />
              </XAxis>
              
              {/* Economy Rate Y-Axis */}
              {selectedMetrics.includes('economy') && (
                <YAxis 
                  yAxisId="economy"
                  domain={[minEconomy, maxEconomy]}
                  orientation="left"
                >
                  <Label value="Economy Rate" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
                </YAxis>
              )}
              
              {/* Wickets Y-Axis */}
              {selectedMetrics.includes('wickets') && (
                <YAxis 
                  yAxisId="wickets" 
                  orientation="right" 
                  domain={[0, maxWickets]}
                >
                  <Label value="Wickets" angle={90} position="insideRight" style={{ textAnchor: 'middle' }} />
                </YAxis>
              )}
              
              {/* Dot Percentage Y-Axis */}
              {selectedMetrics.includes('dot_percentage') && !selectedMetrics.includes('economy') && (
                <YAxis 
                  yAxisId="dot_percentage" 
                  orientation="left" 
                  domain={[0, maxDotPercentage]}
                >
                  <Label value="Dot %" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
                </YAxis>
              )}
              
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              
              {/* Economy Rate Line */}
              {selectedMetrics.includes('economy') && (
                <Line
                  yAxisId="economy"
                  type="monotone"
                  dataKey="economy"
                  stroke={metricColors.economy}
                  strokeWidth={3}
                  name={metricLabels.economy}
                />
              )}
              
              {/* Wickets Bar */}
              {selectedMetrics.includes('wickets') && (
                <Bar
                  yAxisId="wickets"
                  dataKey="wickets"
                  fill={metricColors.wickets}
                  name={metricLabels.wickets}
                  barSize={20}
                />
              )}
              
              {/* Dot Percentage Line */}
              {selectedMetrics.includes('dot_percentage') && (
                <Line
                  yAxisId={selectedMetrics.includes('economy') ? 'economy' : 'dot_percentage'}
                  type="monotone"
                  dataKey="dot_percentage"
                  stroke={metricColors.dot_percentage}
                  strokeWidth={3}
                  name={metricLabels.dot_percentage}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
          This chart shows your bowling performance across different overs.
          Toggle metrics to focus on specific aspects of your performance.
        </Typography>
      </CardContent>
    </Card>
  );
};

export default OverEconomyChart;