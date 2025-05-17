import React, { useState } from 'react';
import { Card, CardContent, Typography, Select, MenuItem, FormControl, InputLabel, Box } from '@mui/material';
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

const StrikeRateIntervals = ({ ballStats = [] }) => {  // Add default empty array
  const [interval, setInterval] = useState(5);

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
      <Card>
        <CardContent>
          <Typography variant="h6">Strike Rate Progression by Intervals</Typography>
          <Typography variant="body1" sx={{ mt: 2 }}>No data available</Typography>
        </CardContent>
      </Card>
    );
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Card sx={{ p: 1, bgcolor: 'background.paper' }}>
          <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
            {`Ball ${label}`}
          </Typography>
          <Typography variant="body2">
            {`${payload[0].payload.noBalls} innings`}
          </Typography>
          {payload.map((item) => (
            <Typography key={item.dataKey} variant="body2" style={{ color: item.color }}>
              {`${item.name}: ${item.value.toFixed(1)}${item.unit || ''}`}
            </Typography>
          ))}
        </Card>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Strike Rate Progression by Intervals
          </Typography>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Interval</InputLabel>
            <Select
              value={interval}
              label="Interval"
              onChange={(e) => setInterval(e.target.value)}
            >
              {[5, 10, 15, 20].map((value) => (
                <MenuItem key={value} value={value}>{value}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        <div style={{ width: '100%', height: 400 }}>
          <ResponsiveContainer>
            <BarChart
              data={data}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="ballNumber"
                label={{ 
                  value: 'Ball Number',
                  position: 'bottom',
                  offset: -5
                }}
              />
              <YAxis 
                yAxisId="left"
                orientation="left"
                domain={[0, 200]}
                label={{ 
                  value: 'Strike Rate',
                  angle: -90,
                  position: 'insideLeft',
                  offset: 10
                }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                domain={[0, 100]}
                label={{ 
                  value: 'Percentage',
                  angle: 90,
                  position: 'insideRight',
                  offset: 10
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar 
                yAxisId="left"
                dataKey="strikeRate" 
                name="Strike Rate"
                fill="#8884d8" 
              />
              <Bar 
                yAxisId="right"
                dataKey="boundaryPercentage" 
                name="Boundary %" 
                fill="#82ca9d" 
              />
              <Bar 
                yAxisId="right"
                dataKey="dotPercentage" 
                name="Dot %" 
                fill="#ffc658" 
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default StrikeRateIntervals;