import React, { useState, useMemo, useImperativeHandle, forwardRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Stack,
  Chip,
  Alert,
  IconButton
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ScatterChart,
  Scatter
} from 'recharts';
import BarChartIcon from '@mui/icons-material/BarChart';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';

// Generate vibrant, contrasty colors for better visibility
const generateContrastColor = (index) => {
  const contrastColors = [
    '#E91E63', // Pink
    '#4CAF50', // Green
    '#2196F3', // Blue
    '#FF9800', // Orange
    '#9C27B0', // Purple
    '#F44336', // Red
    '#00BCD4', // Cyan
    '#8BC34A', // Light Green
    '#3F51B5', // Indigo
    '#FF5722', // Deep Orange
    '#607D8B', // Blue Grey
    '#795548', // Brown
    '#009688', // Teal
    '#CDDC39', // Lime
    '#FFC107', // Amber
    '#673AB7', // Deep Purple
    '#FF1744', // Pink Accent
    '#00E676', // Green Accent
    '#2979FF', // Blue Accent
    '#FF6D00'  // Orange Accent
  ];
  
  return contrastColors[index % contrastColors.length];
};

// Team colors for scatter plots (extracted from VenueNotes.jsx)
const getTeamColor = (team) => {
  const teamColors = {
    'CSK': '#eff542',
    'RCB': '#f54242', 
    'MI': '#42a7f5',
    'RR': '#FF2AA8',
    'KKR': '#610048',
    'PBKS': '#FF004D',
    'SRH': '#FF7C01',
    'LSG': '#00BBB3',
    'DC': '#004BC5',
    'GT': '#01295B'
  };
  const currentTeam = team?.split('/')?.pop()?.trim();
  return teamColors[currentTeam] || '#8884d8';
};

const ChartPanel = forwardRef(({ data, groupBy, isVisible, onToggle, isMobile = false }, ref) => {
  const [charts, setCharts] = useState([]);
  const [nextChartId, setNextChartId] = useState(1);

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    addBarChart,
    addScatterChart
  }));

  // Chart management functions
  const addBarChart = () => {
    const newChart = {
      id: nextChartId,
      type: 'bar',
      selectedMetric: 'runs'
    };
    setCharts(prev => [...prev, newChart]);
    setNextChartId(prev => prev + 1);
  };

  const addScatterChart = () => {
    const newChart = {
      id: nextChartId,
      type: 'scatter',
      xMetric: 'runs',
      yMetric: 'strike_rate'
    };
    setCharts(prev => [...prev, newChart]);
    setNextChartId(prev => prev + 1);
  };

  const removeChart = (chartId) => {
    setCharts(prev => prev.filter(chart => chart.id !== chartId));
  };

  const updateChart = (chartId, updates) => {
    setCharts(prev => prev.map(chart => 
      chart.id === chartId ? { ...chart, ...updates } : chart
    ));
  };

  // Format metric values for display
  const formatMetricValue = (value, metric) => {
    if (value === null || value === undefined) return 'N/A';
    
    if (metric.includes('percentage') || metric === 'percent_balls') {
      return `${Number(value).toFixed(1)}%`;
    }
    if (metric === 'strike_rate' || metric === 'average' || metric === 'balls_per_dismissal') {
      return Number(value).toFixed(1);
    }
    if (typeof value === 'number' && value > 1000) {
      return value.toLocaleString();
    }
    
    return value;
  };

  // Get available metrics from the data
  const availableMetrics = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    const sampleRow = data[0];
    const predefinedMetrics = [
      { key: 'runs', label: 'Runs', color: '#8884d8' },
      { key: 'balls', label: 'Balls', color: '#82ca9d' },
      { key: 'wickets', label: 'Wickets', color: '#ffc658' },
      { key: 'dots', label: 'Dot Balls', color: '#ff7c7c' },
      { key: 'boundaries', label: 'Boundaries', color: '#8dd1e1' },
      { key: 'fours', label: 'Fours', color: '#d084d0' },
      { key: 'sixes', label: 'Sixes', color: '#87d068' },
      { key: 'strike_rate', label: 'Strike Rate', color: '#ffb347' },
      { key: 'average', label: 'Average', color: '#ff9999' },
      { key: 'dot_percentage', label: 'Dot %', color: '#ffcc99' },
      { key: 'boundary_percentage', label: 'Boundary %', color: '#99ccff' },
      { key: 'balls_per_dismissal', label: 'Balls/Wicket', color: '#cc99ff' },
      { key: 'percent_balls', label: '% Balls', color: '#ff6b6b' } // Add the new column
    ];

    // Filter to only include metrics that exist in the data
    const availableFromPredefined = predefinedMetrics.filter(metric => metric.key in sampleRow);
    
    // Dynamically add any other numeric columns that aren't in our predefined list
    const dynamicMetrics = [];
    Object.keys(sampleRow).forEach(key => {
      // Check if it's a numeric value and not already in our predefined list
      const value = sampleRow[key];
      const isNumeric = typeof value === 'number' && !isNaN(value);
      const isNotGrouping = !groupBy || !groupBy.includes(key);
      const isNotPredefined = !predefinedMetrics.some(m => m.key === key);
      const isNotInternal = !['is_summary', 'summary_level', 'displayIndex'].includes(key);
      
      if (isNumeric && isNotGrouping && isNotPredefined && isNotInternal) {
        dynamicMetrics.push({
          key,
          label: key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
          color: generateContrastColor(availableFromPredefined.length + dynamicMetrics.length)
        });
      }
    });

    return [...availableFromPredefined, ...dynamicMetrics];
  }, [data, groupBy]);

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!data || data.length === 0 || !groupBy || groupBy.length === 0) return [];

    return data.map((row, index) => {
      // Create a display name from grouping columns with better formatting
      const groupingName = groupBy
        .map(col => {
          const value = row[col];
          if (col === 'year') return value;
          // Don't truncate team names - they're important for identification
          if (col === 'batting_team' || col === 'bowling_team' || col === 'team') {
            return value;
          }
          // Only truncate very long strings (>20 chars)
          if (typeof value === 'string' && value.length > 20) {
            return value.substring(0, 18) + '...';
          }
          return value;
        })
        .join(' • ');

      // Create a shorter name for chart labels
      const shortName = groupBy
        .map(col => {
          const value = row[col];
          if (col === 'year') return value;
          if (typeof value === 'string' && value.length > 10) {
            return value.substring(0, 8) + '..';
          }
          return value;
        })
        .join(' • ');

      // Add vibrant color for scatter plots
      const contrastColor = generateContrastColor(index);

      return {
        ...row,
        name: groupingName,
        shortName: shortName,
        displayIndex: index,
        teamColor: contrastColor // Use vibrant colors for better visibility
      };
    });
  }, [data, groupBy]);

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label, chartConfig }) => {
    if (!active || !payload || !payload[0]) return null;

    const dataPoint = payload[0].payload;
    
    return (
      <Card sx={{ p: 2, maxWidth: 300, border: '1px solid #ccc' }}>
        <Typography variant="subtitle2" gutterBottom>
          {dataPoint.name}
        </Typography>
        
        {chartConfig?.type === 'bar' ? (
          <Typography variant="body2" color="primary">
            {availableMetrics.find(m => m.key === chartConfig.selectedMetric)?.label}: {formatMetricValue(dataPoint[chartConfig.selectedMetric], chartConfig.selectedMetric)}
          </Typography>
        ) : (
          <>
            <Typography variant="body2">
              <strong>{availableMetrics.find(m => m.key === chartConfig.xMetric)?.label}:</strong> {formatMetricValue(dataPoint[chartConfig.xMetric], chartConfig.xMetric)}
            </Typography>
            <Typography variant="body2">
              <strong>{availableMetrics.find(m => m.key === chartConfig.yMetric)?.label}:</strong> {formatMetricValue(dataPoint[chartConfig.yMetric], chartConfig.yMetric)}
            </Typography>
          </>
        )}
        
        {/* Show additional context */}
        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {dataPoint.balls && (
            <Chip size="small" label={`${dataPoint.balls.toLocaleString()} balls`} />
          )}
          {dataPoint.runs && (
            <Chip size="small" label={`${dataPoint.runs.toLocaleString()} runs`} />
          )}
        </Box>
      </Card>
    );
  };

  // Don't render if not visible or no data
  if (!isVisible || !data || data.length === 0 || !groupBy || groupBy.length === 0) {
    return null;
  }

  // Render individual bar chart
  const renderBarChart = (chart) => {
    const selectedMetricData = availableMetrics.find(m => m.key === chart.selectedMetric);
    
    return (
      <Card key={chart.id} sx={{ mb: 3 }}>
        <CardContent>
          {/* Chart Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <BarChartIcon />
              Bar Chart - {selectedMetricData?.label || chart.selectedMetric}
            </Typography>
            <IconButton
              size="small"
              onClick={() => removeChart(chart.id)}
              color="error"
            >
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Chart Controls */}
          <Stack direction={isMobile ? "column" : "row"} spacing={2} sx={{ mb: 3 }}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Metric</InputLabel>
              <Select
                value={chart.selectedMetric}
                onChange={(e) => updateChart(chart.id, { selectedMetric: e.target.value })}
                label="Metric"
              >
                {availableMetrics.map((metric) => (
                  <MenuItem key={metric.key} value={metric.key}>
                    {metric.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>

          {/* Bar Chart */}
          <Box sx={{ width: '100%', height: isMobile ? 300 : 400 }}>
            <ResponsiveContainer>
              <BarChart
                data={chartData}
                margin={{
                  top: 20,
                  right: 30,
                  left: 20,
                  bottom: isMobile ? 60 : 40
                }}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis 
                  dataKey="name"
                  angle={isMobile ? -45 : 0}
                  textAnchor={isMobile ? "end" : "middle"}
                  height={isMobile ? 80 : 40}
                  interval={0}
                  fontSize={isMobile ? 10 : 12}
                />
                <YAxis 
                  tickFormatter={(value) => formatMetricValue(value, chart.selectedMetric)}
                  fontSize={12}
                />
                <Tooltip content={(props) => <CustomTooltip {...props} chartConfig={chart} />} />
                <Legend />
                <Bar 
                  dataKey={chart.selectedMetric} 
                  fill={selectedMetricData?.color || '#8884d8'}
                  name={selectedMetricData?.label || chart.selectedMetric}
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>
    );
  };

  // Render individual scatter chart
  const renderScatterChart = (chart) => {
    const xMetricData = availableMetrics.find(m => m.key === chart.xMetric);
    const yMetricData = availableMetrics.find(m => m.key === chart.yMetric);
    
    // Calculate dynamic domain boundaries from actual data
    const getDataDomain = (dataKey) => {
      const values = chartData
        .map(d => d[dataKey])
        .filter(val => !isNaN(val) && val !== undefined && val !== null);
      
      if (values.length === 0) return [0, 100];
      
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min;
      const padding = range * 0.1; // 10% padding
      
      return [
        Math.max(0, min - padding), // Don't go below 0 for percentages/rates
        max + padding
      ];
    };
    
    const xDomain = getDataDomain(chart.xMetric);
    const yDomain = getDataDomain(chart.yMetric);
    
    return (
      <Card key={chart.id} sx={{ mb: 3 }}>
        <CardContent>
          {/* Chart Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ScatterPlotIcon />
              Scatter Plot - {xMetricData?.label} vs {yMetricData?.label}
            </Typography>
            <IconButton
              size="small"
              onClick={() => removeChart(chart.id)}
              color="error"
            >
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Chart Controls */}
          <Stack direction={isMobile ? "column" : "row"} spacing={2} sx={{ mb: 3 }}>
            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>X-Axis</InputLabel>
              <Select
                value={chart.xMetric}
                onChange={(e) => updateChart(chart.id, { xMetric: e.target.value })}
                label="X-Axis"
              >
                {availableMetrics.map((metric) => (
                  <MenuItem key={metric.key} value={metric.key}>
                    {metric.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>Y-Axis</InputLabel>
              <Select
                value={chart.yMetric}
                onChange={(e) => updateChart(chart.id, { yMetric: e.target.value })}
                label="Y-Axis"
              >
                {availableMetrics.map((metric) => (
                  <MenuItem key={metric.key} value={metric.key}>
                    {metric.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>

          {/* Scatter Chart */}
          <Box sx={{ width: '100%', height: isMobile ? 400 : 500 }}>
            <ResponsiveContainer>
              <ScatterChart
                data={chartData}
                margin={{
                  top: 20,
                  right: 30,
                  left: 20,
                  bottom: 40
                }}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis 
                  type="number"
                  dataKey={chart.xMetric}
                  name={xMetricData?.label}
                  domain={xDomain}
                  tickFormatter={(value) => formatMetricValue(value, chart.xMetric)}
                  fontSize={12}
                />
                <YAxis 
                  type="number"
                  dataKey={chart.yMetric}
                  name={yMetricData?.label}
                  domain={yDomain}
                  tickFormatter={(value) => formatMetricValue(value, chart.yMetric)}
                  fontSize={12}
                />
                <Tooltip content={(props) => <CustomTooltip {...props} chartConfig={chart} />} />
                <Scatter 
                  data={chartData} 
                  shape={(props) => {
                    const { cx, cy, payload } = props;
                    return (
                      <>
                        <circle
                          cx={cx}
                          cy={cy}
                          r={7}
                          fill={payload.teamColor || '#8884d8'}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                        {!isMobile && (
                          <text
                            x={cx}
                            y={cy + 18}
                            textAnchor="middle"
                            fontSize={10}
                            fontWeight="500"
                            fill="#333"
                          >
                            {payload.shortName || payload.name}
                          </text>
                        )}
                      </>
                    );
                  }}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box sx={{ mt: 3 }}>
      {/* Main Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <BarChartIcon />
              Data Visualization
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<CloseIcon />}
              onClick={onToggle}
            >
              Hide Charts
            </Button>
          </Box>

          {/* Add Chart Buttons */}
          <Stack direction={isMobile ? "column" : "row"} spacing={2} sx={{ mb: 2 }}>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={addBarChart}
              disabled={availableMetrics.length === 0}
            >
              Add Bar Chart
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={addScatterChart}
              disabled={availableMetrics.length < 2}
            >
              Add Scatter Plot
            </Button>
          </Stack>

          {/* Info Chips */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip 
              label={`${chartData.length} data points`} 
              variant="outlined" 
              size="small" 
            />
            <Chip 
              label={`Grouped by: ${groupBy.join(', ')}`} 
              variant="outlined" 
              size="small" 
            />
            {charts.length > 0 && (
              <Chip 
                label={`${charts.length} active charts`} 
                color="primary"
                size="small" 
              />
            )}
          </Box>

          {availableMetrics.length === 0 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              No numeric metrics available for visualization. Try grouping your data to see charts.
            </Alert>
          )}

          {availableMetrics.length === 1 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Only one metric available. Add more grouping columns or metrics to enable scatter plots.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Render Charts */}
      {charts.map(chart => (
        chart.type === 'bar' ? renderBarChart(chart) : renderScatterChart(chart)
      ))}

      {/* Chart Tips */}
      {charts.length > 0 && (
        <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            💡 <strong>Chart Tips:</strong> 
            {isMobile ? (
              " Tap data points for details. Use controls to change metrics and axes."
            ) : (
              " Hover over data points for detailed information. Scatter plots show team colors when available."
            )}
          </Typography>
        </Box>
      )}
    </Box>
  );
});

ChartPanel.displayName = 'ChartPanel';

export default ChartPanel;