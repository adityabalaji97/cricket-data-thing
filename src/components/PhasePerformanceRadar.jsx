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

const transformPhaseData = (stats, type = 'overall') => {
  const phases = ['powerplay', 'middle', 'death'];
  const phaseData = [];
  
  phases.forEach(phase => {
    const phaseStats = type === 'overall' 
      ? stats.phase_stats.overall[phase]
      : stats.phase_stats[type][phase];
    
    phaseData.push({
      phase: phase.charAt(0).toUpperCase() + phase.slice(1),
      'Strike Rate': phaseStats.strike_rate,
      'Average': phaseStats.average || 0,
      'Boundary %': phaseStats.boundary_percentage,
      'Dot %': phaseStats.dot_percentage
    });
  });
  
  return phaseData;
};

const PhasePerformanceRadar = ({ stats }) => {
  const [selectedView, setSelectedView] = useState('overall');
  
  const data = transformPhaseData(stats, selectedView);
  
  const metrics = ['Strike Rate', 'Average', 'Boundary %', 'Dot %'];
  const colors = {
    'Strike Rate': '#8884d8',
    'Average': '#82ca9d',
    'Boundary %': '#ffc658',
    'Dot %': '#ff7300'
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Phase-wise Performance Analysis
          </Typography>
          <ButtonGroup variant="outlined" size="small">
            <Button 
              onClick={() => setSelectedView('overall')}
              variant={selectedView === 'overall' ? 'contained' : 'outlined'}
            >
              Overall
            </Button>
            <Button
              onClick={() => setSelectedView('pace')}
              variant={selectedView === 'pace' ? 'contained' : 'outlined'}
            >
              vs Pace
            </Button>
            <Button
              onClick={() => setSelectedView('spin')}
              variant={selectedView === 'spin' ? 'contained' : 'outlined'}
            >
              vs Spin
            </Button>
          </ButtonGroup>
        </Box>
        
        <Box sx={{ width: '100%', height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart outerRadius={150} data={data}>
              <PolarGrid />
              <PolarAngleAxis dataKey="phase" />
              <PolarRadiusAxis />
              {metrics.map((metric) => (
                <Radar
                  key={metric}
                  name={metric}
                  dataKey={metric}
                  stroke={colors[metric]}
                  fill={colors[metric]}
                  fillOpacity={0.3}
                />
              ))}
              <Tooltip />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default PhasePerformanceRadar;