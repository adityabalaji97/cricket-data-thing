/**
 * PitchMapContainer
 * 
 * Wraps PitchMapVisualization with:
 * - Dimension selector (when grouping by line/length + other columns)
 * - Metric selector for color scale
 * - Min balls threshold control
 */

import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Chip,
  ToggleButton,
  ToggleButtonGroup,
  IconButton,
  Collapse,
  Divider
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PitchMapVisualization from './PitchMapVisualization';
import {
  getPitchMapMode,
  getNonPitchDimensions,
  getUniqueDimensionValues,
  filterDataBySelections,
  transformToPitchMapCells
} from './pitchMapUtils';
import {
  METRICS,
  DEFAULT_CELL_METRICS,
  DEFAULT_COLOR_METRIC,
  DEFAULT_MIN_BALLS,
  MIN_BALLS_OPTIONS
} from './pitchMapConstants';

const PitchMapContainer = ({
  data,
  groupBy,
  title = 'Pitch Map Analysis',
  initialColorMetric = DEFAULT_COLOR_METRIC,
  initialDisplayMetrics = DEFAULT_CELL_METRICS,
  initialMinBalls = DEFAULT_MIN_BALLS,
  width = 400
}) => {
  // Determine mode and non-pitch dimensions
  const mode = useMemo(() => getPitchMapMode(groupBy), [groupBy]);
  const nonPitchDimensions = useMemo(() => getNonPitchDimensions(groupBy), [groupBy]);
  
  // State for dimension selections
  const [dimensionSelections, setDimensionSelections] = useState({});
  
  // State for visualization settings
  const [colorMetric, setColorMetric] = useState(initialColorMetric);
  const [displayMetrics, setDisplayMetrics] = useState(initialDisplayMetrics);
  const [minBalls, setMinBalls] = useState(initialMinBalls);
  const [showSettings, setShowSettings] = useState(false);
  
  // Get unique values for each non-pitch dimension
  const dimensionOptions = useMemo(() => {
    const options = {};
    nonPitchDimensions.forEach(dim => {
      options[dim] = getUniqueDimensionValues(data, dim);
    });
    return options;
  }, [data, nonPitchDimensions]);
  
  // Initialize selections to first value of each dimension
  useMemo(() => {
    const initial = {};
    nonPitchDimensions.forEach(dim => {
      const options = dimensionOptions[dim];
      if (options && options.length > 0 && !dimensionSelections[dim]) {
        initial[dim] = options[0];
      }
    });
    if (Object.keys(initial).length > 0) {
      setDimensionSelections(prev => ({ ...prev, ...initial }));
    }
  }, [dimensionOptions, nonPitchDimensions]);
  
  // Filter and transform data
  const cells = useMemo(() => {
    const filtered = filterDataBySelections(data, dimensionSelections);
    return transformToPitchMapCells(filtered, mode);
  }, [data, dimensionSelections, mode]);
  
  // Calculate dynamic min balls based on data
  const suggestedMinBalls = useMemo(() => {
    const allBalls = cells.map(c => c.balls).filter(b => b > 0);
    if (allBalls.length === 0) return 0;
    const median = allBalls.sort((a, b) => a - b)[Math.floor(allBalls.length / 2)];
    return Math.max(5, Math.floor(median * 0.1));
  }, [cells]);
  
  // Handle dimension selection change
  const handleDimensionChange = (dimension, value) => {
    setDimensionSelections(prev => ({
      ...prev,
      [dimension]: value
    }));
  };
  
  // Handle display metrics toggle
  const handleDisplayMetricsChange = (event, newMetrics) => {
    if (newMetrics && newMetrics.length > 0) {
      setDisplayMetrics(newMetrics);
    }
  };
  
  // Build subtitle from selections
  const subtitle = useMemo(() => {
    const parts = [];
    Object.entries(dimensionSelections).forEach(([dim, value]) => {
      if (value) {
        parts.push(`${dim}: ${value}`);
      }
    });
    return parts.join(' • ');
  }, [dimensionSelections]);
  
  if (!mode) {
    return null; // No line or length in groupBy
  }
  
  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">{title}</Typography>
        <IconButton 
          size="small" 
          onClick={() => setShowSettings(!showSettings)}
          color={showSettings ? 'primary' : 'default'}
        >
          <SettingsIcon />
        </IconButton>
      </Box>
      
      {/* Dimension Selectors */}
      {nonPitchDimensions.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2 }}>
          {nonPitchDimensions.map(dim => (
            <FormControl key={dim} size="small" sx={{ minWidth: 150 }}>
              <InputLabel>{dim.charAt(0).toUpperCase() + dim.slice(1)}</InputLabel>
              <Select
                value={dimensionSelections[dim] || ''}
                label={dim.charAt(0).toUpperCase() + dim.slice(1)}
                onChange={(e) => handleDimensionChange(dim, e.target.value)}
              >
                {dimensionOptions[dim]?.map(value => (
                  <MenuItem key={value} value={value}>
                    {value}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ))}
        </Box>
      )}
      
      {/* Settings Panel */}
      <Collapse in={showSettings}>
        <Box sx={{ bgcolor: 'grey.50', p: 2, borderRadius: 1, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Visualization Settings</Typography>
          
          {/* Color Metric Selector */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Color Scale Metric
            </Typography>
            <FormControl size="small" fullWidth>
              <Select
                value={colorMetric}
                onChange={(e) => setColorMetric(e.target.value)}
              >
                {Object.entries(METRICS).map(([key, config]) => (
                  <MenuItem key={key} value={key}>
                    {config.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          
          {/* Display Metrics Toggle */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Metrics to Display
            </Typography>
            <ToggleButtonGroup
              value={displayMetrics}
              onChange={handleDisplayMetricsChange}
              size="small"
              sx={{ flexWrap: 'wrap' }}
            >
              {Object.entries(METRICS).map(([key, config]) => (
                <ToggleButton key={key} value={key} sx={{ textTransform: 'none', px: 1.5 }}>
                  {config.shortLabel}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
          
          {/* Min Balls Slider */}
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Minimum Balls: {minBalls}
              {suggestedMinBalls > 0 && minBalls !== suggestedMinBalls && (
                <Chip 
                  label={`Suggested: ${suggestedMinBalls}`} 
                  size="small" 
                  sx={{ ml: 1 }}
                  onClick={() => setMinBalls(suggestedMinBalls)}
                />
              )}
            </Typography>
            <Slider
              value={minBalls}
              onChange={(e, value) => setMinBalls(value)}
              min={0}
              max={100}
              step={5}
              marks={MIN_BALLS_OPTIONS.map(v => ({ value: v, label: v.toString() }))}
              valueLabelDisplay="auto"
              size="small"
            />
          </Box>
        </Box>
      </Collapse>
      
      {/* Pitch Map Visualization */}
      <PitchMapVisualization
        cells={cells}
        mode={mode}
        colorMetric={colorMetric}
        displayMetrics={displayMetrics}
        minBalls={minBalls}
        subtitle={subtitle}
        width={width}
      />
      
      {/* Data Summary */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Total Balls: {cells.reduce((sum, c) => sum + (c.balls || 0), 0).toLocaleString()}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Cells with Data: {cells.filter(c => c.balls >= minBalls).length} / {cells.length}
        </Typography>
      </Box>
    </Paper>
  );
};

export default PitchMapContainer;
