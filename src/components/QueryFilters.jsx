import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  TextField,
  Autocomplete,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControlLabel,
  Switch,
  Slider,
  Alert
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import config from '../config';

const QueryFilters = ({ filters, setFilters, groupBy, setGroupBy, availableColumns, isMobile }) => {
  const [venues, setVenues] = useState([]);
  const [teams, setTeams] = useState([]);
  const [players, setPlayers] = useState([]);
  const [batters, setBatters] = useState([]);
  const [bowlers, setBowlers] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  
  // Fetch dropdown data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [venuesResponse, teamsResponse, batterResponse, bowlerResponse] = await Promise.all([
          axios.get(`${config.API_URL}/venues/`),
          axios.get(`${config.API_URL}/teams/`),
          axios.get(`${config.API_URL}/players/batters`),
          axios.get(`${config.API_URL}/players/bowlers`)
        ]);
        
        if (Array.isArray(venuesResponse.data)) {
          setVenues(venuesResponse.data.filter(v => v).sort());
        }
        
        if (Array.isArray(teamsResponse.data)) {
          setTeams(teamsResponse.data.sort((a, b) => a.full_name.localeCompare(b.full_name)));
        }
        
        // Set players data for batters and bowlers from separate endpoints
        if (Array.isArray(batterResponse.data)) {
          const batterNames = batterResponse.data.map(p => p.value || p.label || p).sort();
          setBatters(batterNames);
        }
        
        if (Array.isArray(bowlerResponse.data)) {
          const bowlerNames = bowlerResponse.data.map(p => p.value || p.label || p).sort();
          setBowlers(bowlerNames);
        }
        
      } catch (error) {
        console.error('Error fetching dropdown data:', error);
      } finally {
        setLoadingData(false);
      }
    };
    
    fetchData();
  }, []);
  
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };
  
  const handleGroupByChange = (event, newValue) => {
    setGroupBy(newValue || []);
  };
  
  if (!availableColumns || loadingData) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography>Loading filter options...</Typography>
      </Box>
    );
  }
  
  return (
    <Box>
      {/* Basic Filters */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">📍 Basic Filters</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            {/* Venue */}
            <Grid item xs={12} sm={6} md={4}>
              <Autocomplete
                value={filters.venue}
                onChange={(e, value) => handleFilterChange('venue', value)}
                options={venues}
                renderInput={(params) => (
                  <TextField {...params} label="Venue" size="small" />
                )}
              />
            </Grid>
            
            {/* Date Range */}
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                label="Start Date"
                type="date"
                value={filters.start_date || ''}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                label="End Date"
                type="date"
                value={filters.end_date || ''}
                onChange={(e) => handleFilterChange('end_date', e.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
                fullWidth
              />
            </Grid>
            
            {/* Leagues */}
            <Grid item xs={12} sm={6} md={4}>
              <Autocomplete
                multiple
                value={filters.leagues}
                onChange={(e, value) => handleFilterChange('leagues', value)}
                options={['IPL', 'BBL', 'PSL', 'CPL', 'MSL', 'LPL', 'BPL']}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Leagues" size="small" />
                )}
              />
            </Grid>
            
            {/* Teams */}
            <Grid item xs={12} sm={6} md={4}>
              <Autocomplete
                multiple
                value={filters.teams}
                onChange={(e, value) => handleFilterChange('teams', value)}
                options={teams.map(t => t.full_name)}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Teams" size="small" />
                )}
              />
            </Grid>
            
            {/* International Matches */}
            <Grid item xs={12} sm={6} md={4}>
              <Box sx={{ pt: 1 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={filters.include_international}
                      onChange={(e) => handleFilterChange('include_international', e.target.checked)}
                    />
                  }
                  label="Include International"
                />
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
      
      {/* Player Analysis Filters */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">👤 Player Analysis</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            {/* Batters */}
            <Grid item xs={12} sm={6}>
              <Autocomplete
                multiple
                value={filters.batters || []}
                onChange={(e, value) => handleFilterChange('batters', value)}
                options={batters}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Batters" size="small" />
                )}
              />
            </Grid>
            
            {/* Bowlers */}
            <Grid item xs={12} sm={6}>
              <Autocomplete
                multiple
                value={filters.bowlers || []}
                onChange={(e, value) => handleFilterChange('bowlers', value)}
                options={bowlers}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Bowlers" size="small" />
                )}
              />
            </Grid>
            
            {/* Min Balls */}
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Min Balls"
                type="number"
                value={filters.min_balls || ''}
                onChange={(e) => handleFilterChange('min_balls', e.target.value ? parseInt(e.target.value) : null)}
                inputProps={{ min: 0 }}
                size="small"
                fullWidth
              />
            </Grid>
            
            {/* Max Balls */}
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Max Balls"
                type="number"
                value={filters.max_balls || ''}
                onChange={(e) => handleFilterChange('max_balls', e.target.value ? parseInt(e.target.value) : null)}
                inputProps={{ min: 0 }}
                size="small"
                fullWidth
              />
            </Grid>
            
            {/* Min Runs */}
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Min Runs"
                type="number"
                value={filters.min_runs || ''}
                onChange={(e) => handleFilterChange('min_runs', e.target.value ? parseInt(e.target.value) : null)}
                inputProps={{ min: 0 }}
                size="small"
                fullWidth
              />
            </Grid>
            
            {/* Max Runs */}
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Max Runs"
                type="number"
                value={filters.max_runs || ''}
                onChange={(e) => handleFilterChange('max_runs', e.target.value ? parseInt(e.target.value) : null)}
                inputProps={{ min: 0 }}
                size="small"
                fullWidth
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
      
      {/* Left-Right Analysis Filters */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">🏏 Left-Right Analysis</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Autocomplete
                multiple
                value={filters.crease_combo || []}
                onChange={(e, value) => handleFilterChange('crease_combo', value)}
                options={availableColumns.crease_combo_options || []}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Crease Combo" size="small" />
                )}
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Autocomplete
                multiple
                value={filters.ball_direction || []}
                onChange={(e, value) => handleFilterChange('ball_direction', value)}
                options={availableColumns.ball_direction_options || []}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Ball Direction" size="small" />
                )}
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <FormControl size="small" fullWidth>
                <InputLabel>Striker Type</InputLabel>
                <Select
                  value={filters.striker_batter_type || ''}
                  onChange={(e) => handleFilterChange('striker_batter_type', e.target.value || null)}
                  label="Striker Type"
                >
                  <MenuItem value="">All</MenuItem>
                  {availableColumns.batter_type_options?.map(option => (
                    <MenuItem key={option} value={option}>{option}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <FormControl size="small" fullWidth>
                <InputLabel>Non-Striker Type</InputLabel>
                <Select
                  value={filters.non_striker_batter_type || ''}
                  onChange={(e) => handleFilterChange('non_striker_batter_type', e.target.value || null)}
                  label="Non-Striker Type"
                >
                  <MenuItem value="">All</MenuItem>
                  {availableColumns.batter_type_options?.map(option => (
                    <MenuItem key={option} value={option}>{option}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
      
      {/* Cricket Specific Filters */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">🎯 Cricket Specific</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Autocomplete
                multiple
                value={filters.bowler_type || []}
                onChange={(e, value) => handleFilterChange('bowler_type', value)}
                options={availableColumns.common_bowler_types || []}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Bowler Type" size="small" />
                )}
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <FormControl size="small" fullWidth>
                <InputLabel>Innings</InputLabel>
                <Select
                  value={filters.innings || ''}
                  onChange={(e) => handleFilterChange('innings', e.target.value || null)}
                  label="Innings"
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value={1}>1st Innings</MenuItem>
                  <MenuItem value={2}>2nd Innings</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Over Min"
                type="number"
                value={filters.over_min || ''}
                onChange={(e) => handleFilterChange('over_min', e.target.value ? parseInt(e.target.value) : null)}
                inputProps={{ min: 0, max: 19 }}
                size="small"
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                label="Over Max"
                type="number"
                value={filters.over_max || ''}
                onChange={(e) => handleFilterChange('over_max', e.target.value ? parseInt(e.target.value) : null)}
                inputProps={{ min: 0, max: 19 }}
                size="small"
                fullWidth
              />
            </Grid>
            
            <Grid item xs={12} sm={6} md={4}>
              <Autocomplete
                multiple
                value={filters.wicket_type || []}
                onChange={(e, value) => handleFilterChange('wicket_type', value)}
                options={availableColumns.wicket_type_options || []}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                  ))
                }
                renderInput={(params) => (
                  <TextField {...params} label="Wicket Type" size="small" />
                )}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
      
      {/* Grouping */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">📊 Grouping & Aggregation</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Autocomplete
                multiple
                value={groupBy}
                onChange={handleGroupByChange}
                options={availableColumns.group_by_columns || []}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip 
                      variant="outlined" 
                      label={option} 
                      size="small" 
                      color="primary"
                      {...getTagProps({ index })} 
                    />
                  ))
                }
                renderInput={(params) => (
                  <TextField 
                    {...params} 
                    label="Group By Columns" 
                    helperText="Select columns to group results by. Leave empty for individual delivery records."
                    size="small"
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Alert severity="info" sx={{ mt: 1 }}>
                <Typography variant="body2">
                  <strong>Grouping Options:</strong>
                  <br />• <strong>No grouping</strong>: Returns individual delivery records
                  <br />• <strong>Single grouping</strong>: Aggregates data by one column (e.g., crease_combo)  
                  <br />• <strong>Multiple grouping</strong>: Cross-analysis (e.g., venue + ball_direction)
                  <br />• <strong>Phase grouping</strong>: Powerplay/Middle/Death analysis using "phase" column
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>
      
      {/* Query Settings */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">⚙️ Query Settings</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography gutterBottom>Result Limit: {filters.limit}</Typography>
              <Slider
                value={filters.limit}
                onChange={(e, value) => handleFilterChange('limit', value)}
                min={100}
                max={10000}
                step={100}
                marks={[
                  { value: 100, label: '100' },
                  { value: 1000, label: '1K' },
                  { value: 5000, label: '5K' },
                  { value: 10000, label: '10K' }
                ]}
                valueLabelDisplay="auto"
              />
            </Grid>
            
            {filters.include_international && (
              <Grid item xs={12} sm={6}>
                <Typography gutterBottom>Top Teams: {filters.top_teams}</Typography>
                <Slider
                  value={filters.top_teams}
                  onChange={(e, value) => handleFilterChange('top_teams', value)}
                  min={5}
                  max={20}
                  step={1}
                  marks={[
                    { value: 5, label: '5' },
                    { value: 10, label: '10' },
                    { value: 15, label: '15' },
                    { value: 20, label: '20' }
                  ]}
                  valueLabelDisplay="auto"
                />
              </Grid>
            )}
          </Grid>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default QueryFilters;
