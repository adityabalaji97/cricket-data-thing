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
  Alert,
  Tooltip,
  IconButton
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';
import axios from 'axios';
import config from '../config';

// Info tooltip component
const InfoTooltip = ({ tooltip }) => (
  <Tooltip title={tooltip} placement="top">
    <IconButton size="small" sx={{ p: 0.5 }}>
      <InfoIcon fontSize="small" color="action" />
    </IconButton>
  </Tooltip>
);

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
      {/* Compact filters without section titles */}
      <Grid container spacing={2}>
        {/* Row 1: Date Range & Venue */}
        <Grid item xs={12} sm={4} md={3}>
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
        
        <Grid item xs={12} sm={4} md={3}>
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
        
        <Grid item xs={12} sm={4} md={3}>
          <Autocomplete
            value={filters.venue}
            onChange={(e, value) => handleFilterChange('venue', value)}
            options={venues}
            renderInput={(params) => (
              <TextField {...params} label="Venue" size="small" />
            )}
          />
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
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
        
        {/* Row 2: Teams */}
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.batting_teams || []}
              onChange={(e, value) => handleFilterChange('batting_teams', value)}
              options={teams.map(t => t.full_name)}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" color="primary" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Batting Teams" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Teams when batting" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.bowling_teams || []}
              onChange={(e, value) => handleFilterChange('bowling_teams', value)}
              options={teams.map(t => t.full_name)}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" color="secondary" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Bowling Teams" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Teams when bowling" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.teams || []}
              onChange={(e, value) => handleFilterChange('teams', value)}
              options={teams.map(t => t.full_name)}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Teams (Any Role)" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Teams in either batting or bowling role" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={filters.include_international}
                  onChange={(e) => handleFilterChange('include_international', e.target.checked)}
                  size="small"
                />
              }
              label="International"
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Include international matches in analysis" />
          </Box>
        </Grid>
        
        {/* Row 3: Players */}
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
        
        {/* Row 4: Match Context */}
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
        
        <Grid item xs={12} sm={6} md={3}>
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
        
        {/* Row 5: Cricket Specific */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="RF=Right Fast, RM=Right Medium, LO=Left Orthodox, etc." />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              value={filters.crease_combo}
              onChange={(e, value) => handleFilterChange('crease_combo', value)}
              options={availableColumns.crease_combo_options || []}
              renderInput={(params) => (
                <TextField {...params} label="Crease Combo" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Left/Right hand batting combinations (striker_nonstriker)" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              value={filters.ball_direction}
              onChange={(e, value) => handleFilterChange('ball_direction', value)}
              options={availableColumns.ball_direction_options || []}
              renderInput={(params) => (
                <TextField {...params} label="Ball Direction" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Ball direction relative to batter's stance" />
          </Box>
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
        
        {/* Row 6: Grouping */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
                  size="small"
                />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Leave empty for individual deliveries. Group for aggregated stats." />
          </Box>
        </Grid>
        
        {/* Row 7: Result Filtering */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TextField
              label="Min Balls"
              type="number"
              value={filters.min_balls || ''}
              onChange={(e) => handleFilterChange('min_balls', e.target.value ? parseInt(e.target.value) : null)}
              inputProps={{ min: 0 }}
              size="small"
              fullWidth
            />
            <InfoTooltip tooltip="Minimum balls for grouped results (removes small samples)" />
          </Box>
        </Grid>
        
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
        
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TextField
              label="Min Runs"
              type="number"
              value={filters.min_runs || ''}
              onChange={(e) => handleFilterChange('min_runs', e.target.value ? parseInt(e.target.value) : null)}
              inputProps={{ min: 0 }}
              size="small"
              fullWidth
            />
            <InfoTooltip tooltip="Minimum runs for grouped results" />
          </Box>
        </Grid>
        
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
        
        {/* Row 8: Query Settings */}
        <Grid item xs={12} sm={6}>
          <Box>
            <Typography variant="body2" gutterBottom>Result Limit: {filters.limit}</Typography>
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
              size="small"
            />
          </Box>
        </Grid>
        
        {filters.include_international && (
          <Grid item xs={12} sm={6}>
            <Box>
              <Typography variant="body2" gutterBottom>Top Teams: {filters.top_teams}</Typography>
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
                size="small"
              />
            </Box>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default QueryFilters;
