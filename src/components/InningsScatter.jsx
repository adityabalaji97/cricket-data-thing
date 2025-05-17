import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, FormControl, Select, MenuItem, InputLabel } from '@mui/material';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

const InningsScatter = ({ innings }) => {
  const [xMetric, setXMetric] = useState('balls');
  const [yMetric, setYMetric] = useState('strike_rate');

  const getPhase = (over) => {
    if (over < 6) return 0;
    if (over < 10) return 1;
    if (over < 15) return 2;
    return 3;
  };

  const data = innings.map(inning => ({
    balls: inning.balls_faced,
    position: inning.batting_position,
    entry_over: inning.entry_point.overs,
    phase: getPhase(inning.entry_point.overs),
    runs: inning.runs,
    strike_rate: inning.strike_rate,
    sr_diff: inning.team_comparison.sr_diff,
    average: inning.runs / (inning.wickets || 1),
    date: inning.date,
    competition: inning.competition,
    team_sr: inning.team_comparison.team_sr_excl_batter
  }));

  const xAxisMetrics = {
    balls: { key: 'balls', label: 'Balls Faced' },
    position: { key: 'position', label: 'Batting Position' },
    entry: { key: 'entry_over', label: 'Entry Point (overs)' },
    phase: { key: 'phase', label: 'Entry Phase' }
  };

  const yAxisMetrics = {
    runs: { key: 'runs', label: 'Runs' },
    strike_rate: { key: 'strike_rate', label: 'Strike Rate' },
    sr_diff: { key: 'sr_diff', label: 'SR vs Team' },
    average: { key: 'average', label: 'Average' }
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const inning = payload[0].payload;
      const phaseNames = ['0-6', '6-10', '10-15', '15-20'];
      
      return (
        <Card sx={{ p: 1, bgcolor: 'background.paper' }}>
          <Typography variant="body1">{`${inning.runs} (${inning.balls})`}</Typography>
          <Typography variant="body2" color="text.secondary">{`SR: ${inning.strike_rate.toFixed(1)}`}</Typography>
          <Typography variant="body2" color="text.secondary">
            {`Team SR: ${inning.team_sr.toFixed(1)} (Diff: ${inning.sr_diff.toFixed(1)})`}
          </Typography>
          <Typography variant="body2" color="text.secondary">{`Position: ${inning.position}`}</Typography>
          <Typography variant="body2" color="text.secondary">
            {`Entry: Over ${inning.entry_over.toFixed(1)} (${phaseNames[inning.phase]})`}
          </Typography>
          <Typography variant="caption" display="block">{inning.competition}</Typography>
          <Typography variant="caption" display="block">{new Date(inning.date).toLocaleDateString()}</Typography>
        </Card>
      );
    }
    return null;
  };

  const getAxisProps = (metric) => {
    if (metric === 'phase') {
      return {
        type: 'number',
        domain: [-0.5, 3.5],
        ticks: [0, 1, 2, 3],
        tickFormatter: (value) => ['0-6', '6-10', '10-15', '15-20'][value]
      };
    }
    return {
      type: 'number'
    };
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">Innings Distribution</Typography>
        </Box>
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>X-Axis</InputLabel>
            <Select
              value={xMetric}
              label="X-Axis"
              onChange={(e) => setXMetric(e.target.value)}
            >
              {Object.entries(xAxisMetrics).map(([key, { label }]) => (
                <MenuItem key={key} value={key}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Y-Axis</InputLabel>
            <Select
              value={yMetric}
              label="Y-Axis"
              onChange={(e) => setYMetric(e.target.value)}
            >
              {Object.entries(yAxisMetrics).map(([key, { label }]) => (
                <MenuItem key={key} value={key}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <div style={{ height: 400, width: '100%' }}>
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                {...getAxisProps(xMetric)}
                dataKey={xAxisMetrics[xMetric].key}
                name={xAxisMetrics[xMetric].label}
                label={{ value: xAxisMetrics[xMetric].label, position: 'bottom' }}
              />
              <YAxis 
                type="number"
                dataKey={yAxisMetrics[yMetric].key}
                name={yAxisMetrics[yMetric].label}
                label={{ 
                  value: yAxisMetrics[yMetric].label,
                  angle: -90, 
                  position: 'left' 
                }}
              />
              {yMetric === 'strike_rate' && <ReferenceLine y={100} stroke="#666" strokeDasharray="3 3" />}
              {yMetric === 'sr_diff' && <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />}
              <Tooltip content={<CustomTooltip />} />
              <Scatter 
                name="Innings" 
                data={data} 
                fill="#8884d8"
                opacity={0.6}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default InningsScatter;