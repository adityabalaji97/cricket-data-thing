import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Paper, Typography, Box, CircularProgress } from '@mui/material';
import config from '../config';

// Colors for different batters
const COLORS = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', 
  '#00C49F', '#FFBB28', '#FF8042', '#a4de6c', '#d0ed57'
];

const ComparisonStrikeRateProgression = ({ batters }) => {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!batters || batters.length === 0) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const batterData = {};
        
        // Fetch strike rate data for each batter in parallel
        await Promise.all(batters.map(async (batter) => {
          try {
            const params = new URLSearchParams();
            
            if (batter.dateRange.start) params.append('start_date', batter.dateRange.start);
            if (batter.dateRange.end) params.append('end_date', batter.dateRange.end);
            if (batter.venue !== "All Venues") params.append('venue', batter.venue);
            
            batter.competitionFilters.leagues.forEach(league => {
              params.append('leagues', league);
            });
            
            params.append('include_international', batter.competitionFilters.international);
            if (batter.competitionFilters.international && batter.competitionFilters.topTeams) {
              params.append('top_teams', batter.competitionFilters.topTeams);
            }
      
            const response = await fetch(`${config.API_URL}/player/${encodeURIComponent(batter.name)}/ball_stats?${params}`);
            const result = await response.json();
            
            // Log the ball stats structure
            console.log(`Ball stats for ${batter.name}:`, result);
            
            if (result.ball_by_ball_stats) {
              batterData[batter.id] = result.ball_by_ball_stats;
            }
          } catch (err) {
            console.error(`Error fetching strike rate data for ${batter.name}:`, err);
          }
        }));
        
        setData(batterData);
      } catch (err) {
        console.error('Error fetching strike rate progression data:', err);
        setError('Failed to load strike rate progression data');
      } finally {
        setLoading(false);
      }
    };
  
    fetchData();
  }, [batters]);

  // Process data for chart when data changes
  useEffect(() => {
    if (Object.keys(data).length === 0) return;
    
    // Debug data
    console.log('Strike rate progression data:', data);
    
    // Get all ball numbers across all batters
    const allBallNumbers = new Set();
    Object.values(data).forEach(batterData => {
      batterData.forEach(point => {
        allBallNumbers.add(point.ball_number);
      });
    });
    
    // Sort ball numbers
    const ballNumbers = [...allBallNumbers].sort((a, b) => a - b);
    
    // Create chart data with a point for each ball number
    const processedData = ballNumbers.map(ballNumber => {
      const dataPoint = { ball_number: ballNumber };
      
      // Add each batter's strike rate for this ball number
      Object.entries(data).forEach(([batterId, batterData]) => {
        const batter = batters.find(b => b.id === batterId);
        if (!batter) return;
        
        const pointForBall = batterData.find(d => d.ball_number === ballNumber);
        dataPoint[batter.label] = pointForBall ? pointForBall.strike_rate : null;
      });
      
      return dataPoint;
    });
    
    setChartData(processedData);
  }, [data, batters]);

  // Calculate min and max values for y-axis
  const allStrikeRates = chartData.flatMap(point => 
    Object.entries(point)
      .filter(([key]) => key !== 'ball_number')
      .map(([_, value]) => value)
      .filter(value => value !== null)
  );
  
  const minSR = Math.max(0, Math.floor(Math.min(...allStrikeRates, 0) * 0.9) || 0);
  const maxSR = Math.ceil(Math.max(...allStrikeRates, 200) * 1.1) || 200;

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Ball-by-Ball Strike Rate Progression
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Strike rate evolution through innings
      </Typography>
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}
      
      {error && (
        <Typography color="error" sx={{ p: 2 }}>
          {error}
        </Typography>
      )}
      
      {!loading && !error && chartData.length > 0 && (
        <Box sx={{ height: 400, width: '100%' }}>
          <ResponsiveContainer>
            <LineChart 
              data={chartData}
              margin={{ top: 20, right: 30, bottom: 30, left: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="ball_number"
                label={{ value: 'Ball Number', position: 'bottom', offset: 10 }}
              />
              <YAxis 
                domain={[minSR, maxSR]}
                label={{ value: 'Strike Rate', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip 
                formatter={(value, name) => [value ? value.toFixed(2) : 'N/A', name]}
              />
              <Legend 
                verticalAlign="bottom" 
                height={36}
                wrapperStyle={{
                  paddingTop: '20px',
                  paddingBottom: '10px',
                  display: 'flex',
                  justifyContent: 'center',
                  gap: '20px'
                }}
              />
              
              {/* Create a line for each batter */}
              {batters.map((batter, index) => (
                data[batter.id] && (
                  <Line
                    key={batter.id}
                    type="monotone"
                    dataKey={batter.label}
                    stroke={COLORS[index % COLORS.length]}
                    dot={false}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                )
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
      
      {!loading && !error && chartData.length === 0 && (
        <Box sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No strike rate progression data available for the selected batters.
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default ComparisonStrikeRateProgression;