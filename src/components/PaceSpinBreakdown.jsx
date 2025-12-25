import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, FormControl, Select, MenuItem } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const metrics = [
  { value: 'strike_rate', label: 'Strike Rate' },
  { value: 'average', label: 'Average' },
  { value: 'boundary_percentage', label: 'Boundary %' },
  { value: 'dot_percentage', label: 'Dot Ball %' }
];

const transformData = (stats, selectedMetric) => {
  const phases = ['All Overs', 'powerplay', 'middle', 'death'];
  return phases.map(phase => {
    if (phase === 'All Overs') {
      return {
        phase,
        pace: stats.phase_stats.pace.overall[selectedMetric],
        spin: stats.phase_stats.spin.overall[selectedMetric],
        overall: stats.overall[selectedMetric]
      };
    }
    return {
      phase: phase.charAt(0).toUpperCase() + phase.slice(1),
      pace: stats.phase_stats.pace[phase][selectedMetric],
      spin: stats.phase_stats.spin[phase][selectedMetric],
      overall: stats.phase_stats.overall[phase][selectedMetric]
    };
  });
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Box sx={{ bgcolor: 'background.paper', p: 1, border: '1px solid #ccc', borderRadius: 1 }}>
        <Typography variant="subtitle2">{label}</Typography>
        {payload.map((entry) => (
          entry.value !== null && (
            <Typography key={entry.name} variant="body2" sx={{ color: entry.color }}>
              {entry.name}: {entry.value.toFixed(2)}
            </Typography>
          )
        ))}
      </Box>
    );
  }
  return null;
};

const PaceSpinBreakdown = ({ stats }) => {
  const [selectedMetric, setSelectedMetric] = useState('strike_rate');
  
  // Null safety check
  if (!stats?.phase_stats?.pace?.overall || !stats?.phase_stats?.spin?.overall) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Pace vs Spin Analysis</Typography>
          <Typography color="text.secondary" sx={{ mt: 2 }}>
            Pace/Spin breakdown data not available
          </Typography>
        </CardContent>
      </Card>
    );
  }
  
  const data = transformData(stats, selectedMetric);
  
  const maxValue = Math.max(
    ...data.flatMap(d => [d.pace, d.spin, d.overall].filter(v => v !== null))
  );

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Pace vs Spin Analysis</Typography>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <Select value={selectedMetric} onChange={(e) => setSelectedMetric(e.target.value)}>
              {metrics.map((metric) => (
                <MenuItem key={metric.value} value={metric.value}>{metric.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        
        <Box sx={{ width: '100%', height: 400, mt: 2 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 20, right: 30, left: 50, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                type="number" 
                domain={[0, maxValue * 1.1]} 
                tickFormatter={(value) => Number(value.toFixed(2))}
              />
              <YAxis type="category" dataKey="phase" axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar dataKey="pace" name="vs Pace" fill="#2196f3" barSize={20} />
              <Bar dataKey="spin" name="vs Spin" fill="#4caf50" barSize={20} />
              <Bar dataKey="overall" name="Overall" fill="#9c27b0" barSize={20} />
            </BarChart>
          </ResponsiveContainer>
        </Box>
        
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 2 }}>
          {selectedMetric === 'strike_rate' 
            ? 'Higher values indicate faster scoring'
            : selectedMetric === 'average'
            ? 'Higher values indicate better consistency'
            : selectedMetric === 'boundary_percentage'
            ? 'Higher values indicate more boundaries'
            : 'Higher values indicate more dot balls'}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default PaceSpinBreakdown;