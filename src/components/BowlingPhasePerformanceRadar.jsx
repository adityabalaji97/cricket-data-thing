import React, { useState } from 'react';
import { 
  Card, 
  CardContent,
  Typography,
  ButtonGroup,
  Button,
  Box
} from '@mui/material';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

// Restructure data to make metrics the vertices and phases as series
const transformMetricsData = (stats) => {
  if (!stats || !stats.phase_stats) return [];
  
  const phases = ['powerplay', 'middle', 'death'];
  const metrics = ['Economy Rate', 'Strike Rate', 'Average', 'Dot %'];
  const metricsData = [];
  
  // Create a data point for each metric (as vertices)
  metrics.forEach(metric => {
    const dataPoint = { metric };
    
    // Add each phase's value for this metric
    phases.forEach(phase => {
      const phaseStats = stats.phase_stats[phase] || {};
      
      // Map the metric name to the correct property in phaseStats
      let value = 0;
      if (metric === 'Economy Rate') {
        value = phaseStats.economy || 0;
      } else if (metric === 'Strike Rate') {
        value = phaseStats.bowling_strike_rate || 0;
      } else if (metric === 'Average') {
        value = phaseStats.bowling_average || 0;
      } else if (metric === 'Dot %') {
        value = phaseStats.dot_percentage || 0;
      }
      
      // Store the value for this phase
      dataPoint[phase.charAt(0).toUpperCase() + phase.slice(1)] = value;
    });
    
    metricsData.push(dataPoint);
  });
  
  return metricsData;
};

// Helper function to normalize values for better radar chart display
const normalizeValue = (value, metric) => {
  // For metrics where lower is better (economy, average), invert the scale
  if (metric === 'Economy Rate') {
    // Transform economy rate: lower is better, so invert
    return 15 - Math.min(value, 15); // Cap at 15
  } else if (metric === 'Average') {
    // Transform average: lower is better, so invert
    return 50 - Math.min(value, 50); // Cap at 50
  } else if (metric === 'Strike Rate') {
    // Transform strike rate: lower is better, so invert
    return 40 - Math.min(value, 40); // Cap at 40
  } else {
    // For dot %, higher is better, so keep as is
    return value;
  }
};

const BowlingPhasePerformanceRadar = ({ stats }) => {
  const [showNormalized, setShowNormalized] = useState(true);
  
  const data = transformMetricsData(stats);
  
  // Define the phases and their colors
  const phases = ['Powerplay', 'Middle', 'Death'];
  const colors = {
    'Powerplay': '#8884d8',
    'Middle': '#82ca9d',
    'Death': '#ff7300'
  };

  // Normalize data for better visualization if required
  const normalizedData = data.map(item => {
    const newItem = { ...item };
    
    phases.forEach(phase => {
      // Only normalize the data if showNormalized is true
      if (showNormalized) {
        newItem[phase] = normalizeValue(item[phase], item.metric);
      }
    });
    
    return newItem;
  });

  // Helper function to format the tooltip values
  const formatTooltipValue = (value, name, props) => {
    if (showNormalized) {
      // Retrieve the original value from data
      const originalData = data.find(item => item.metric === props.payload.metric);
      return [originalData[name].toFixed(2), name];
    }
    return [value.toFixed(2), name];
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Phase-wise Bowling Analysis
          </Typography>
          <ButtonGroup variant="outlined" size="small">
            <Button 
              onClick={() => setShowNormalized(true)}
              variant={showNormalized ? 'contained' : 'outlined'}
            >
              Normalized
            </Button>
            <Button
              onClick={() => setShowNormalized(false)}
              variant={!showNormalized ? 'contained' : 'outlined'}
            >
              Raw Values
            </Button>
          </ButtonGroup>
        </Box>
        
        <Box sx={{ width: '100%', height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart outerRadius={150} data={showNormalized ? normalizedData : data}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" />
              <PolarRadiusAxis />
              {phases.map((phase) => (
                <Radar
                  key={phase}
                  name={phase}
                  dataKey={phase}
                  stroke={colors[phase]}
                  fill={colors[phase]}
                  fillOpacity={0.3}
                />
              ))}
              <Tooltip formatter={formatTooltipValue} />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
          {showNormalized 
            ? "Normalized view: metrics adjusted for better comparison (for economy, strike rate, and average, lower values are better)"
            : "Raw values: actual figures from bowling statistics"
          }
        </Typography>
      </CardContent>
    </Card>
  );
};

export default BowlingPhasePerformanceRadar;