import React, { useState, useMemo } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  FormControl, 
  Select, 
  MenuItem, 
  InputLabel,
  Chip
} from '@mui/material';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend
} from 'recharts';

const ComparisonInningsScatter = ({ batters }) => {
  const [xMetric, setXMetric] = useState('balls_faced');
  const [yMetric, setYMetric] = useState('strike_rate');
  const [visiblePlayers, setVisiblePlayers] = useState(
    batters.map(b => b.id)
  );

  // Color assignment for players
  const playerColors = useMemo(() => {
    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#f0932b', '#eb4d4b', '#6c5ce7'];
    return batters.reduce((acc, batter, index) => {
      acc[batter.id] = colors[index % colors.length];
      return acc;
    }, {});
  }, [batters]);

  const getPhase = (over) => {
    if (over < 6) return 0;
    if (over < 10) return 1;
    if (over < 15) return 2;
    return 3;
  };

  // Process data: combine all innings with player identification
  const processedData = useMemo(() => {
    return batters.flatMap(batter => 
      batter.stats.innings.map(inning => ({
        ...inning,
        playerId: batter.id,
        playerName: batter.name,
        playerLabel: batter.label,
        color: playerColors[batter.id],
        // Add calculated fields
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
      }))
    );
  }, [batters, playerColors]);

  const xAxisMetrics = {
    balls_faced: { key: 'balls', label: 'Balls Faced' },
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

  const togglePlayer = (playerId) => {
    setVisiblePlayers(prev => 
      prev.includes(playerId) 
        ? prev.filter(id => id !== playerId)
        : [...prev, playerId]
    );
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const inning = payload[0].payload;
      const phaseNames = ['0-6', '6-10', '10-15', '15-20'];
      
      return (
        <Card sx={{ p: 1, bgcolor: 'background.paper' }}>
          <Typography variant="subtitle2" sx={{ color: inning.color, fontWeight: 'bold' }}>
            {inning.playerLabel}
          </Typography>
          <Typography variant="body2">{`${inning.runs} (${inning.balls})`}</Typography>
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

  // Get data for each visible player
  const getPlayerData = (playerId) => {
    return processedData.filter(d => 
      d.playerId === playerId && visiblePlayers.includes(playerId)
    );
  };

  if (!batters || batters.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Innings Distribution Comparison</Typography>
          <Typography variant="body2" color="text.secondary">
            No batter data available for comparison.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">Innings Distribution Comparison</Typography>
        </Box>
        
        {/* Controls Row */}
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 2,
          mb: 3 
        }}>
          {/* Axis Controls */}
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControl sx={{ minWidth: 150 }}>
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
            
            <FormControl sx={{ minWidth: 150 }}>
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

          {/* Player Toggle Chips */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {batters.map(batter => (
              <Chip
                key={batter.id}
                label={batter.label}
                clickable
                variant={visiblePlayers.includes(batter.id) ? 'filled' : 'outlined'}
                onClick={() => togglePlayer(batter.id)}
                sx={{ 
                  backgroundColor: visiblePlayers.includes(batter.id) 
                    ? playerColors[batter.id] 
                    : 'transparent',
                  color: visiblePlayers.includes(batter.id) ? 'white' : playerColors[batter.id],
                  borderColor: playerColors[batter.id],
                  '&:hover': {
                    backgroundColor: playerColors[batter.id],
                    color: 'white'
                  }
                }}
              />
            ))}
          </Box>
        </Box>

        <div style={{ height: 500, width: '100%' }}>
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
              
              {/* Render one Scatter per player */}
              {batters.map(batter => {
                const playerData = getPlayerData(batter.id);
                if (playerData.length === 0) return null;
                
                return (
                  <Scatter
                    key={batter.id}
                    name={batter.label}
                    data={playerData}
                    fill={playerColors[batter.id]}
                    opacity={0.7}
                  />
                );
              })}
              
              <Legend />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Summary Info */}
        <Box sx={{ mt: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {batters.map(batter => {
            const playerInnings = processedData.filter(d => d.playerId === batter.id);
            const visibleInnings = playerInnings.filter(d => visiblePlayers.includes(batter.id));
            
            return (
              <Typography 
                key={batter.id}
                variant="caption" 
                sx={{ 
                  color: playerColors[batter.id],
                  opacity: visiblePlayers.includes(batter.id) ? 1 : 0.5
                }}
              >
                {batter.label}: {visibleInnings.length} innings
              </Typography>
            );
          })}
        </Box>
      </CardContent>
    </Card>
  );
};

export default ComparisonInningsScatter;