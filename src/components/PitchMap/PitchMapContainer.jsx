/**
 * PitchMapContainer
 * 
 * Wraps PitchMapVisualization with:
 * - Dimension selector (when grouping by line/length + other columns)
 * - Metric selector for color scale and display
 * - Min balls threshold control
 * - PNG export
 * - Auto-generated title from filters
 */

import React, { useState, useMemo, useRef } from 'react';
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
  IconButton,
  Collapse,
  Button,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Divider
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import DownloadIcon from '@mui/icons-material/Download';
import html2canvas from 'html2canvas';
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
  DEFAULT_SECONDARY_METRICS,
  DEFAULT_COLOR_METRIC,
  DEFAULT_MIN_BALLS,
  MIN_BALLS_OPTIONS
} from './pitchMapConstants';

const PitchMapContainer = ({
  data,
  groupBy,
  filters = {},
  initialColorMetric = DEFAULT_COLOR_METRIC,
  initialDisplayMetrics = DEFAULT_CELL_METRICS,
  initialSecondaryMetrics = DEFAULT_SECONDARY_METRICS,
  initialMinBalls = DEFAULT_MIN_BALLS
}) => {
  // Refs for export
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  
  // Determine mode and non-pitch dimensions
  const mode = useMemo(() => getPitchMapMode(groupBy), [groupBy]);
  const nonPitchDimensions = useMemo(() => getNonPitchDimensions(groupBy), [groupBy]);
  
  // State for dimension selections
  const [dimensionSelections, setDimensionSelections] = useState({});
  
  // State for visualization settings
  const [colorMetric, setColorMetric] = useState(initialColorMetric);
  const [displayMetrics, setDisplayMetrics] = useState(initialDisplayMetrics);
  const [secondaryMetrics, setSecondaryMetrics] = useState(initialSecondaryMetrics);
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
  
  // Generate title from filters
  const generatedTitle = useMemo(() => {
    const parts = [];
    
    // Add specific players from filters first
    if (filters.batters?.length > 0) {
      parts.push(filters.batters.join(', '));
    }
    if (filters.bowlers?.length > 0) {
      parts.push(filters.bowlers.join(', '));
    }
    if (filters.players?.length > 0) {
      parts.push(filters.players.join(', '));
    }
    
    // Add dimension selections (but avoid duplicates)
    Object.entries(dimensionSelections).forEach(([dim, value]) => {
      if (value && !parts.includes(value)) {
        parts.push(value);
      }
    });
    
    // Add teams from filters
    if (filters.batting_teams?.length > 0) {
      const teamStr = filters.batting_teams.join(', ');
      if (!parts.some(p => p.includes(teamStr))) {
        parts.push(teamStr);
      }
    }
    if (filters.bowling_teams?.length > 0) {
      parts.push(`vs ${filters.bowling_teams.join(', ')}`);
    }
    if (filters.teams?.length > 0 && !filters.batting_teams?.length && !filters.bowling_teams?.length) {
      parts.push(filters.teams.join(', '));
    }
    
    // Add league/venue info
    if (filters.leagues?.length > 0) {
      parts.push(filters.leagues.join(', '));
    }
    if (filters.venue) {
      parts.push(`@ ${filters.venue}`);
    }
    
    // Add phase info if over filters are set
    if (filters.over_min !== null && filters.over_min !== undefined) {
      if (filters.over_min === 0 && filters.over_max === 5) {
        parts.push('Powerplay');
      } else if (filters.over_min === 6 && filters.over_max === 14) {
        parts.push('Middle Overs');
      } else if (filters.over_min === 15) {
        parts.push('Death Overs');
      }
    }
    
    if (parts.length === 0) {
      return 'Pitch Map Analysis';
    }
    
    return parts.join(' • ');
  }, [filters, dimensionSelections]);
  
  // Handle dimension selection change
  const handleDimensionChange = (dimension, value) => {
    setDimensionSelections(prev => ({
      ...prev,
      [dimension]: value
    }));
  };
  
  // Handle metric checkbox change
  const handleMetricToggle = (metricKey, isPrimary) => {
    if (isPrimary) {
      setDisplayMetrics(prev => {
        if (prev.includes(metricKey)) {
          return prev.filter(k => k !== metricKey);
        }
        return [...prev, metricKey];
      });
    } else {
      setSecondaryMetrics(prev => {
        if (prev.includes(metricKey)) {
          return prev.filter(k => k !== metricKey);
        }
        return [...prev, metricKey];
      });
    }
  };
  
  // Export as PNG
  const handleExport = async () => {
    if (!containerRef.current) return;
    
    try {
      const canvas = await html2canvas(containerRef.current, {
        backgroundColor: '#ffffff',
        scale: 2,
        logging: false
      });
      
      const link = document.createElement('a');
      link.download = `pitch-map-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error('Export failed:', error);
    }
  };
  
  // Build subtitle from selections not in title
  const subtitle = useMemo(() => {
    // If there are dimension selections that aren't already shown, show them
    const parts = [];
    Object.entries(dimensionSelections).forEach(([dim, value]) => {
      if (value && !generatedTitle.toLowerCase().includes(String(value).toLowerCase())) {
        const dimLabel = dim.charAt(0).toUpperCase() + dim.slice(1).replace(/_/g, ' ');
        parts.push(`${dimLabel}: ${value}`);
      }
    });
    return parts.length > 0 ? parts.join(' • ') : null;
  }, [dimensionSelections, generatedTitle]);
  
  if (!mode) {
    return null;
  }
  
  const totalBalls = cells.reduce((sum, c) => sum + (c.balls || 0), 0);
  const cellsWithData = cells.filter(c => c.balls >= minBalls).length;
  
  return (
    <Paper elevation={2} sx={{ p: 2, width: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontSize: { xs: '1rem', sm: '1.25rem' } }}>
          Pitch Map
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton 
            size="small" 
            onClick={handleExport}
            title="Export as PNG"
          >
            <DownloadIcon />
          </IconButton>
          <IconButton 
            size="small" 
            onClick={() => setShowSettings(!showSettings)}
            color={showSettings ? 'primary' : 'default'}
          >
            <SettingsIcon />
          </IconButton>
        </Box>
      </Box>
      
      {/* Dimension Selectors */}
      {nonPitchDimensions.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
          {nonPitchDimensions.map(dim => (
            <FormControl key={dim} size="small" sx={{ minWidth: 140, flex: '1 1 140px' }}>
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
          {/* Color Metric Selector */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
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
          
          <Divider sx={{ my: 2 }} />
          
          {/* Primary Metrics Checkboxes */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Primary Metrics (top line)
            </Typography>
            <FormGroup row sx={{ flexWrap: 'wrap' }}>
              {Object.entries(METRICS).map(([key, config]) => (
                <FormControlLabel
                  key={key}
                  control={
                    <Checkbox
                      checked={displayMetrics.includes(key)}
                      onChange={() => handleMetricToggle(key, true)}
                      size="small"
                    />
                  }
                  label={config.shortLabel}
                  sx={{ mr: 1, minWidth: 80 }}
                />
              ))}
            </FormGroup>
          </Box>
          
          {/* Secondary Metrics Checkboxes */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Secondary Metrics (bottom line)
            </Typography>
            <FormGroup row sx={{ flexWrap: 'wrap' }}>
              {Object.entries(METRICS).map(([key, config]) => (
                <FormControlLabel
                  key={key}
                  control={
                    <Checkbox
                      checked={secondaryMetrics.includes(key)}
                      onChange={() => handleMetricToggle(key, false)}
                      size="small"
                    />
                  }
                  label={config.shortLabel}
                  sx={{ mr: 1, minWidth: 80 }}
                />
              ))}
            </FormGroup>
          </Box>
          
          <Divider sx={{ my: 2 }} />
          
          {/* Min Balls Slider */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
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
      
      {/* Pitch Map Visualization - wrapped in ref for export */}
      <Box 
        ref={containerRef} 
        sx={{ 
          bgcolor: '#fff', 
          p: 1,
          maxWidth: 420,
          mx: 'auto'
        }}
      >
        <PitchMapVisualization
          cells={cells}
          mode={mode}
          colorMetric={colorMetric}
          displayMetrics={displayMetrics}
          secondaryMetrics={secondaryMetrics}
          minBalls={minBalls}
          title={generatedTitle}
          subtitle={subtitle}
          width={null} // Will use container width
          svgRef={svgRef}
        />
      </Box>
      
      {/* Data Summary */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="caption" color="text.secondary">
          Total Balls: {totalBalls.toLocaleString()}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Cells with Data: {cellsWithData} / {cells.length}
        </Typography>
      </Box>
    </Paper>
  );
};

export default PitchMapContainer;
