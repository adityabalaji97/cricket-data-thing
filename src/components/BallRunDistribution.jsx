import React from 'react';
import { Card, CardContent, Typography } from '@mui/material';
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

const BallRunDistribution = ({ innings }) => {
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

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Innings Balls Faced vs Runs Distribution
        </Typography>
        <div style={{ width: '100%', height: 400 }}>
          <ResponsiveContainer>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 20, right: 20, left: 40, bottom: 30 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                type="number"
              >
                <Label
                  value="Number of Innings"
                  position="bottom"
                  offset={10}
                />
              </XAxis>
              <YAxis 
                dataKey="ballRange" 
                type="category"
                tick={{ fontSize: 12 }}
              >
                <Label
                  value="Balls"
                  angle={-90}
                  position="insideLeft"
                  offset={-10}
                  style={{ textAnchor: 'middle' }}
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
        </div>
      </CardContent>
    </Card>
  );
};

export default BallRunDistribution;