import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  Select,
  MenuItem,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import BarChartIcon from '@mui/icons-material/BarChart';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';

const TeamComparisonVisualization = ({ teams, showPercentiles }) => {
  const [chartDialogOpen, setChartDialogOpen] = useState(false);
  const [selectedChartType, setSelectedChartType] = useState('bar');
  const [selectedMetric, setSelectedMetric] = useState('strike_rate');
  const [selectedPhase, setSelectedPhase] = useState('overall');
  const [selectedDataType, setSelectedDataType] = useState('batting');

  if (!teams || teams.length === 0) {
    return null;
  }

  // Color palette for teams
  const teamColors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
  ];

  // Available metrics for visualization
  const battingMetrics = [
    { key: 'runs', label: 'Runs' },
    { key: 'balls', label: 'Balls' },
    { key: 'wickets', label: 'Wickets' },
    { key: 'average', label: 'Average' },
    { key: 'strike_rate', label: 'Strike Rate' },
    { key: 'boundary_percentage', label: 'Boundary %' },
    { key: 'dot_percentage', label: 'Dot %' }
  ];

  const bowlingMetrics = [
    { key: 'runs', label: 'Runs' },
    { key: 'balls', label: 'Balls' },
    { key: 'wickets', label: 'Wickets' },
    { key: 'average', label: 'Average' },
    { key: 'strike_rate', label: 'Strike Rate' },
    { key: 'economy', label: 'Economy' },
    { key: 'boundary_percentage', label: 'Boundary %' },
    { key: 'dot_percentage', label: 'Dot %' }
  ];

  const phases = [
    { key: 'overall', label: 'Overall' },
    { key: 'powerplay', label: 'Powerplay' },
    { key: 'middle_overs', label: 'Middle Overs' },
    { key: 'death_overs', label: 'Death Overs' }
  ];

  // Prepare data for charts
  const prepareChartData = () => {
    const currentMetrics = selectedDataType === 'batting' ? battingMetrics : bowlingMetrics;
    const dataSource = selectedDataType === 'batting' ? 'phaseStats' : 'bowlingPhaseStats';
    
    if (selectedChartType === 'scatter') {
      // For scatter plot, we need two metrics
      const xMetric = 'average';
      const yMetric = 'strike_rate';
      
      return teams.map((team, index) => {
        const phaseData = team[dataSource]?.[selectedPhase] || {};
        return {
          x: phaseData[xMetric] || 0,
          y: phaseData[yMetric] || 0,
          team: team.label,
          fill: teamColors[index % teamColors.length]
        };
      });
    } else {
      // For bar and line charts
      return teams.map((team, index) => {
        const phaseData = team[dataSource]?.[selectedPhase] || {};
        return {
          team: team.label,
          value: phaseData[selectedMetric] || 0,
          fill: teamColors[index % teamColors.length]
        };
      });
    }
  };

  // Render bar chart
  const renderBarChart = () => {
    const data = prepareChartData();
    const currentMetrics = selectedDataType === 'batting' ? battingMetrics : bowlingMetrics;
    const metricLabel = currentMetrics.find(m => m.key === selectedMetric)?.label || selectedMetric;
    
    return (
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="team" 
            angle={-45}
            textAnchor="end"
            height={100}
            interval={0}
          />
          <YAxis />
          <Tooltip 
            formatter={(value) => [value.toFixed(2), metricLabel]}
            labelFormatter={(label) => `Team: ${label}`}
          />
          <Bar dataKey="value" name={metricLabel} />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  // Render line chart
  const renderLineChart = () => {
    const currentMetrics = selectedDataType === 'batting' ? battingMetrics : bowlingMetrics;
    const dataSource = selectedDataType === 'batting' ? 'phaseStats' : 'bowlingPhaseStats';
    const metricLabel = currentMetrics.find(m => m.key === selectedMetric)?.label || selectedMetric;
    
    // Prepare data for line chart (across phases)
    const data = phases.map(phase => {
      const phaseData = { phase: phase.label };
      teams.forEach((team, index) => {
        const value = team[dataSource]?.[phase.key]?.[selectedMetric] || 0;
        phaseData[team.label] = value;
      });
      return phaseData;
    });
    
    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="phase" />
          <YAxis />
          <Tooltip formatter={(value) => value.toFixed(2)} />
          <Legend />
          {teams.map((team, index) => (
            <Line 
              key={team.id}
              type="monotone" 
              dataKey={team.label} 
              stroke={teamColors[index % teamColors.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  };

  // Render scatter plot
  const renderScatterChart = () => {
    const data = prepareChartData();
    
    return (
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="x" 
            name="Average"
            label={{ value: 'Average', position: 'insideBottom', offset: -10 }}
          />
          <YAxis 
            dataKey="y" 
            name="Strike Rate"
            label={{ value: 'Strike Rate', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip 
            formatter={(value, name) => [value.toFixed(2), name === 'x' ? 'Average' : 'Strike Rate']}
            labelFormatter={(label, payload) => {
              if (payload && payload[0]) {
                return `Team: ${payload[0].payload.team}`;
              }
              return '';
            }}
          />
          <Scatter name="Teams" data={data} />
        </ScatterChart>
      </ResponsiveContainer>
    );
  };

  const handleGenerateChart = () => {
    setChartDialogOpen(true);
  };

  const handleCloseChart = () => {
    setChartDialogOpen(false);
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Generate Visualizations
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Create charts to visualize team comparison data
          </Typography>
          
          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Button
                variant="outlined"
                startIcon={<BarChartIcon />}
                onClick={() => { setSelectedChartType('bar'); handleGenerateChart(); }}
                fullWidth
              >
                Bar Chart
              </Button>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Button
                variant="outlined"
                startIcon={<ShowChartIcon />}
                onClick={() => { setSelectedChartType('line'); handleGenerateChart(); }}
                fullWidth
              >
                Line Chart
              </Button>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Button
                variant="outlined"
                startIcon={<ScatterPlotIcon />}
                onClick={() => { setSelectedChartType('scatter'); handleGenerateChart(); }}
                fullWidth
              >
                Scatter Plot
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Dialog open={chartDialogOpen} onClose={handleCloseChart} maxWidth="lg" fullWidth>
        <DialogTitle>
          Team Comparison Chart - {selectedChartType.charAt(0).toUpperCase() + selectedChartType.slice(1)}
        </DialogTitle>
        
        <DialogContent>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <Typography variant="body2" gutterBottom>Data Type</Typography>
                <Select
                  value={selectedDataType}
                  onChange={(e) => setSelectedDataType(e.target.value)}
                >
                  <MenuItem value="batting">Batting</MenuItem>
                  <MenuItem value="bowling">Bowling</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            {selectedChartType !== 'scatter' && (
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <Typography variant="body2" gutterBottom>Metric</Typography>
                  <Select
                    value={selectedMetric}
                    onChange={(e) => setSelectedMetric(e.target.value)}
                  >
                    {(selectedDataType === 'batting' ? battingMetrics : bowlingMetrics).map(metric => (
                      <MenuItem key={metric.key} value={metric.key}>
                        {metric.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}
            
            {selectedChartType !== 'line' && (
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <Typography variant="body2" gutterBottom>Phase</Typography>
                  <Select
                    value={selectedPhase}
                    onChange={(e) => setSelectedPhase(e.target.value)}
                  >
                    {phases.map(phase => (
                      <MenuItem key={phase.key} value={phase.key}>
                        {phase.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}
          </Grid>
          
          <Box sx={{ height: 450 }}>
            {selectedChartType === 'bar' && renderBarChart()}
            {selectedChartType === 'line' && renderLineChart()}
            {selectedChartType === 'scatter' && renderScatterChart()}
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseChart}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TeamComparisonVisualization;