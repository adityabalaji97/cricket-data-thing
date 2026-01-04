import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Typography, Box, useMediaQuery, useTheme } from '@mui/material';
import Card from './ui/Card';
import { colors as designColors } from '../theme/designSystem';
import config from '../config';

const StrikeRateProgression = ({ selectedPlayer, dateRange, selectedVenue, competitionFilters, shouldFetch, isMobile: isMobileProp, wrapInCard = true }) => {
  const [data, setData] = useState([]);
  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;
  const Wrapper = wrapInCard ? Card : Box;
  const wrapperProps = wrapInCard ? { isMobile } : { sx: { width: '100%' } };

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

  const chartHeight = isMobile ? 350 : 400;

  return (
    <Wrapper {...wrapperProps}>
      <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, mb: 2 }}>
        nth Ball SR
      </Typography>
      <Box sx={{ height: chartHeight, width: '100%' }}>
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 20, right: isMobile ? 10 : 40, bottom: isMobile ? 15 : 30, left: isMobile ? 10 : 50 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="ball_number"
              label={isMobile ? undefined : { value: 'Ball Number', position: 'bottom', offset: 10 }}
              tick={{ fontSize: isMobile ? 10 : 12 }}
            />
            <YAxis
              yAxisId="left"
              domain={[minSR, maxSR]}
              label={isMobile ? undefined : { value: 'Strike Rate', angle: -90, position: 'insideLeft' }}
              tick={{ fontSize: isMobile ? 10 : 12 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              label={isMobile ? undefined : { value: 'Number of Innings', angle: 90, position: 'insideRight' }}
              tick={{ fontSize: isMobile ? 10 : 12 }}
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
              contentStyle={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              wrapperStyle={{
                paddingTop: '10px',
                paddingBottom: '0px',
                display: 'flex',
                justifyContent: 'center',
                gap: isMobile ? '20px' : '50px',
                fontSize: isMobile ? '0.75rem' : '0.875rem'
              }}
            />
            <Line
              type="monotone"
              dataKey="strike_rate"
              stroke={designColors.chart.blue}
              name="Strike Rate"
              yAxisId="left"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="innings_with_n_balls"
              stroke={designColors.chart.orange}
              name="Innings Count"
              yAxisId="right"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Wrapper>
  );
};

export default StrikeRateProgression;
