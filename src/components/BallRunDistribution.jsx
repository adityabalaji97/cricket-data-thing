import React from 'react';
import { Typography, useMediaQuery, useTheme, Box } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Label,
  LabelList
} from 'recharts';
import _ from 'lodash';
import Card from './ui/Card';

const BallRunDistribution = ({ innings, isMobile: isMobileProp }) => {
  const theme = useTheme();
  const isMobileDetected = useMediaQuery(theme.breakpoints.down('sm'));
  const isMobile = isMobileProp !== undefined ? isMobileProp : isMobileDetected;

  const processData = () => {
    const ballRanges = {};
    innings.forEach(inning => {
      const ballRange = Math.floor(inning.balls_faced / 10) * 10;
      const range = `${ballRange}-${ballRange + 10}`;
      if (!ballRanges[range]) {
        ballRanges[range] = {
          innings: [],
          count: 0
        };
      }
      ballRanges[range].innings.push(inning);
      ballRanges[range].count++;
    });

    const data = Object.entries(ballRanges)
      .sort(([a], [b]) => parseInt(a) - parseInt(b))
      .map(([range, { innings, count }]) => {
        const totalRuns = _.sumBy(innings, 'runs');
        const totalBalls = _.sumBy(innings, 'balls_faced');
        const totalDots = _.sumBy(innings, 'dots');
        const totalBoundaries = _.sumBy(innings, inn => inn.fours + inn.sixes);
        const totalWickets = _.sumBy(innings, 'wickets');
        
        const minRuns = Math.min(...innings.map(inn => inn.runs));
        const maxRuns = Math.max(...innings.map(inn => inn.runs));
        
        return {
          ballRange: range,
          count,
          label: `${minRuns}-${maxRuns} runs`,
          average: (totalRuns / (totalWickets || 1)).toFixed(1),
          strikeRate: ((totalRuns / totalBalls) * 100).toFixed(1),
          boundaryPercent: ((totalBoundaries) / totalBalls * 100).toFixed(1),
          dotPercent: ((totalDots / totalBalls) * 100).toFixed(1)
        };
      });

    const maxCount = Math.max(...data.map(d => d.count));
    
    return data.map(d => ({
      ...d,
      fill: `rgb(76, ${175 + Math.floor((maxCount - d.count) * (80/maxCount))}, 80)`
    }));
  };

  const data = processData();

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload?.[0]?.payload) {
      const { ballRange, count, label, average, strikeRate, boundaryPercent, dotPercent } = payload[0].payload;
      return (
        <Card sx={{ p: 1, bgcolor: 'background.paper' }}>
          <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
            {`${ballRange} balls`}
          </Typography>
          <Typography variant="body2">
            {`${count} innings (${label})`}
          </Typography>
          <Typography variant="body2">
            {`Average: ${average}`}
          </Typography>
          <Typography variant="body2">
            {`Strike Rate: ${strikeRate}`}
          </Typography>
          <Typography variant="body2">
            {`Boundary %: ${boundaryPercent}%`}
          </Typography>
          <Typography variant="body2">
            {`Dot %: ${dotPercent}%`}
          </Typography>
        </Card>
      );
    }
    return null;
  };

  const CustomLabel = ({ x, y, width, height, value }) => (
    <text 
      x={x + (width/2)}
      y={y + (height/2)}
      fill="#fff"
      fontSize={12}
      textAnchor="middle"
      dominantBaseline="middle"
    >
      {value}
    </text>
  );

  const chartHeight = isMobile ? 350 : 400;

  return (
    <Card isMobile={isMobile}>
      <Typography variant={isMobile ? "h6" : "h5"} sx={{ fontWeight: 600, mb: 2 }}>
        Inning Distribution
      </Typography>
      <Box sx={{ width: '100%', height: chartHeight }}>
        <ResponsiveContainer>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 20, right: isMobile ? 5 : 20, left: isMobile ? 20 : 60, bottom: isMobile ? 25 : 40 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              tick={{ fontSize: isMobile ? 10 : 12 }}
            >
              <Label
                value="Number of Innings"
                position="bottom"
                offset={isMobile ? 5 : 0}
                style={{ fontSize: isMobile ? 11 : 12 }}
              />
            </XAxis>
            <YAxis
              dataKey="ballRange"
              type="category"
              tick={{ fontSize: isMobile ? 10 : 12 }}
            >
              <Label
                value="Balls Faced"
                angle={-90}
                position="insideLeft"
                offset={isMobile ? 5 : 15}
                style={{ textAnchor: 'middle', fontSize: isMobile ? 11 : 12 }}
              />
            </YAxis>
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="count"
              minPointSize={2}
              fillOpacity={0.8}
            >
              <LabelList
                dataKey="label"
                content={CustomLabel}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Card>
  );
};

export default BallRunDistribution;