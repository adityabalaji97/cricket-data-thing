import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  ButtonGroup,
  Button,
  Box,
  useMediaQuery,
  useTheme,
  FormControl,
  InputLabel,
  Select,
  MenuItem
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

const PhasePerformanceRadar = ({ stats, isMobile: isMobileProp }) => {
  const [selectedView, setSelectedView] = useState('overall');
  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;

  const data = transformPhaseData(stats, selectedView);

  const metrics = ['Strike Rate', 'Average', 'Boundary %', 'Dot %'];
  const colors = {
    'Strike Rate': '#8884d8',
    'Average': '#82ca9d',
    'Boundary %': '#ffc658',
    'Dot %': '#ff7300'
  };

  // Responsive height calculation - fits in mobile viewport for screenshots
  const chartHeight = isMobile ?
    Math.min(typeof window !== 'undefined' ? window.innerHeight * 0.5 : 350, 380) :
    400;

  return (
    <Card sx={{
      backgroundColor: isMobile ? 'transparent' : undefined,
      boxShadow: isMobile ? 0 : undefined
    }}>
      <CardContent sx={{ p: isMobile ? 1.5 : 2 }}>
        <Box sx={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'flex-start' : 'center',
          mb: 2,
          gap: isMobile ? 1 : 0
        }}>
          <Typography variant={isMobile ? "body1" : "h6"} sx={{ fontWeight: 600, fontSize: isMobile ? '0.875rem' : undefined }}>
            Phase-wise Performance
          </Typography>
          {isMobile ? (
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel sx={{ fontSize: '0.75rem' }}>View</InputLabel>
              <Select
                value={selectedView}
                onChange={(e) => setSelectedView(e.target.value)}
                label="View"
                sx={{ fontSize: '0.75rem' }}
              >
                <MenuItem value="overall" sx={{ fontSize: '0.75rem' }}>Overall</MenuItem>
                <MenuItem value="pace" sx={{ fontSize: '0.75rem' }}>vs Pace</MenuItem>
                <MenuItem value="spin" sx={{ fontSize: '0.75rem' }}>vs Spin</MenuItem>
              </Select>
            </FormControl>
          ) : (
            <ButtonGroup
              variant="outlined"
              size="small"
            >
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
          )}
        </Box>

        <Box sx={{ width: '100%', height: chartHeight }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart
              outerRadius={isMobile ? "70%" : 150}
              data={data}
              margin={{ top: 10, right: isMobile ? 5 : 20, bottom: isMobile ? 5 : 20, left: isMobile ? 5 : 20 }}
            >
              <PolarGrid />
              <PolarAngleAxis
                dataKey="phase"
                tick={{ fontSize: isMobile ? 10 : 12 }}
              />
              <PolarRadiusAxis
                tick={{ fontSize: isMobile ? 9 : 11 }}
              />
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
              <Tooltip
                contentStyle={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}
              />
              <Legend
                wrapperStyle={{ fontSize: isMobile ? '0.7rem' : '0.875rem' }}
                iconSize={isMobile ? 8 : 14}
              />
            </RadarChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default PhasePerformanceRadar;