import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const WicketTakingMethods = ({ stats }) => {
  // Since the provided data doesn't have wicket types, we'll simulate this data for now
  // In a real implementation, this would come from the API
  // This is a placeholder until you have the actual wicket type data
  
  // Check if stats exist
  if (!stats || !stats.overall) {
    return null;
  }
  
  // Create mock data based on total wickets
  // Note: Replace this with actual data from your API when available
  const totalWickets = stats.overall.wickets || 0;
  
  // Simulate a reasonable distribution (replace with real data)
  const mockData = [
    { name: 'Caught', value: Math.floor(totalWickets * 0.55) },  // ~55% caught
    { name: 'Bowled', value: Math.floor(totalWickets * 0.25) },  // ~25% bowled
    { name: 'LBW', value: Math.floor(totalWickets * 0.15) },     // ~15% LBW
    { name: 'Run Out', value: Math.floor(totalWickets * 0.03) }, // ~3% run out
    { name: 'Stumped', value: Math.floor(totalWickets * 0.02) }  // ~2% stumped
  ].filter(item => item.value > 0);  // Only include non-zero values
  
  // Adjust the last category to make sure the sum equals totalWickets
  const sum = mockData.reduce((acc, item) => acc + item.value, 0);
  if (mockData.length > 0 && sum !== totalWickets) {
    mockData[0].value += (totalWickets - sum);
  }
  
  // Colors for the pie chart
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#A28DFF'];
  
  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
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
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: data.color }}>
            {data.name}: {data.value} ({((data.value / totalWickets) * 100).toFixed(1)}%)
          </Typography>
        </Box>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Wicket-Taking Methods
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Distribution of wickets by dismissal type
        </Typography>
        
        <Box sx={{ width: '100%', height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mockData}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={150}
                fill="#8884d8"
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {mockData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend layout="vertical" verticalAlign="middle" align="right" />
            </PieChart>
          </ResponsiveContainer>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
          Note: This is simulated data based on typical wicket distributions.
          Replace with actual dismissal data when available.
        </Typography>
      </CardContent>
    </Card>
  );
};

export default WicketTakingMethods;