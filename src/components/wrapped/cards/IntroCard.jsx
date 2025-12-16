import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const PHASE_COLORS = {
  powerplay: '#4CAF50',
  middle: '#2196F3', 
  death: '#f44336'
};

const PHASE_LABELS = {
  powerplay: 'Powerplay (1-6)',
  middle: 'Middle (7-15)',
  death: 'Death (16-20)'
};

const IntroCard = ({ data }) => {
  if (!data.phases || data.phases.length === 0) {
    return <Typography>No phase data available</Typography>;
  }

  const chartData = data.phases.map(phase => ({
    phase: PHASE_LABELS[phase.phase] || phase.phase,
    'Run Rate': phase.run_rate,
    color: PHASE_COLORS[phase.phase] || '#999'
  }));

  return (
    <Box className="intro-card-content">
      {/* Big Number */}
      <Box className="intro-stat-hero">
        <Typography variant="h2" className="hero-number">
          {data.total_matches}
        </Typography>
        <Typography variant="subtitle1" className="hero-label">
          T20 matches analyzed
        </Typography>
      </Box>

      {/* Phase Stats Chart */}
      <Box className="intro-chart">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" domain={[0, 'auto']} tick={{ fontSize: 12, fill: '#b3b3b3' }} />
            <YAxis 
              type="category" 
              dataKey="phase" 
              width={100} 
              tick={{ fontSize: 11, fill: '#b3b3b3' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(0,0,0,0.9)', 
                border: '1px solid #333',
                borderRadius: 8 
              }}
              labelStyle={{ color: '#fff' }}
            />
            <Bar dataKey="Run Rate" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Quick Stats */}
      <Box className="intro-quick-stats">
        {data.phases.map(phase => (
          <Box key={phase.phase} className="quick-stat">
            <Typography variant="h6" style={{ color: PHASE_COLORS[phase.phase] }}>
              {phase.run_rate}
            </Typography>
            <Typography variant="caption">
              {phase.phase} RR
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default IntroCard;
