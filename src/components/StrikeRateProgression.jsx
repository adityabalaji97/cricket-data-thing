import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Paper, Typography, Box } from '@mui/material';
import config from '../config';

const StrikeRateProgression = ({ selectedPlayer, dateRange, selectedVenue, competitionFilters, shouldFetch }) => {
  const [data, setData] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      if (!selectedPlayer) return;
      
      try {
        const params = new URLSearchParams();
        
        if (dateRange.start) params.append('start_date', dateRange.start);
        if (dateRange.end) params.append('end_date', dateRange.end);
        if (selectedVenue !== "All Venues") params.append('venue', selectedVenue);
        
        competitionFilters.leagues.forEach(league => {
          params.append('leagues', league);
        });
        
        params.append('include_international', competitionFilters.international);
        if (competitionFilters.international && competitionFilters.topTeams) {
          params.append('top_teams', competitionFilters.topTeams);
        }
  
        const response = await fetch(`${config.API_URL}/player/${encodeURIComponent(selectedPlayer)}/ball_stats?${params}`);
        const result = await response.json();
        
        if (result.ball_by_ball_stats) {
          setData(result.ball_by_ball_stats);
        }
      } catch (error) {
        console.error('Error fetching strike rate data:', error);
      }
    };
  
    fetchData();
  }, [selectedPlayer, dateRange, selectedVenue, competitionFilters]); // Removed shouldFetch from dependencies

  const minSR = Math.max(0, Math.floor(Math.min(...data.map(d => d.strike_rate || 0)) * 0.9));
  const maxSR = Math.ceil(Math.max(...data.map(d => d.strike_rate || 0)) * 1.1);

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Ball-by-Ball Strike Rate Progression
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Strike rate evolution through innings
      </Typography>
      <Box sx={{ height: 400, width: '100%' }}>
        <ResponsiveContainer>
          <LineChart 
            data={data}
            margin={{ top: 20, right: 30, bottom: 30, left: 40 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="ball_number"
              label={{ value: 'Ball Number', position: 'bottom', offset: 10 }}
            />
            <YAxis 
              yAxisId="left"
              domain={[minSR, maxSR]}
              label={{ value: 'Strike Rate', angle: -90, position: 'insideLeft' }}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              label={{ value: 'Number of Innings', angle: 90, position: 'insideRight' }}
            />
            <Tooltip 
              formatter={(value, name) => {
                switch(name) {
                  case 'Strike Rate':
                    return [`${value.toFixed(2)}`, name];
                  case 'Innings Count':
                    return [value, name];
                  default:
                    return [value, name];
                }
              }}
            />
            <Legend 
              verticalAlign="bottom" 
              height={36}
              wrapperStyle={{
                paddingTop: '20px',
                paddingBottom: '10px',
                display: 'flex',
                justifyContent: 'center',
                gap: '50px'
              }}
            />
            <Line
              type="monotone"
              dataKey="strike_rate"
              stroke="#8884d8"
              name="Strike Rate"
              yAxisId="left"
              dot={false}
            />
            <Line 
              type="monotone"
              dataKey="innings_with_n_balls"
              stroke="#82ca9d"
              name="Innings Count"
              yAxisId="right"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
};

export default StrikeRateProgression;