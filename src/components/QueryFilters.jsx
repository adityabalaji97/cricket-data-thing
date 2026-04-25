import React from 'react';
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
  FormControlLabel,
  Switch,
  Slider,
  Tooltip,
  IconButton
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import WarningIcon from '@mui/icons-material/Warning';


// Info tooltip component
const InfoTooltip = ({ tooltip }) => (
  <Tooltip title={tooltip} placement="top">
    <IconButton size="small" sx={{ p: 0.5 }}>
      <InfoIcon fontSize="small" color="action" />
    </IconButton>
  </Tooltip>
);

// Coverage warning component
const CoverageWarning = ({ coverage, columnName }) => {
  if (coverage >= 80) return null;
  
  const color = coverage < 50 ? 'warning.main' : 'info.main';
  
  return (
    <Tooltip title={`${columnName} data is available for ${coverage}% of deliveries. Filtering may reduce results significantly.`}>
      <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', ml: 0.5 }}>
        <WarningIcon sx={{ fontSize: 16, color }} />
      </Box>
    </Tooltip>
  );
};

const QueryFilters = ({ filters, setFilters, groupBy, setGroupBy, availableColumns, isMobile }) => {
  // All dropdown data now comes from availableColumns (fetched from delivery_details)
  
  const handleFilterChange = (key, value) => {
    setFilters(prev => {
      const next = {
        ...prev,
        [key]: value
      };

      // Keep chase-outcome filters consistent with API rules.
      if (key === 'is_chase' && value === false) {
        next.chase_outcome = [];
      }
      if (key === 'innings' && value !== 2) {
        next.chase_outcome = [];
      }

      return next;
    });
  };
  
  const handleGroupByChange = (event, newValue) => {
    setGroupBy(newValue || []);
  };
  
  if (!availableColumns) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography>Loading filter options...</Typography>
      </Box>
    );
  }

  const chaseOutcomeDisabled = filters.is_chase === false || filters.innings === 1;

  return (
    <Box>
      <Grid container spacing={isMobile ? 1.5 : 2}>
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
            options={availableColumns?.venues || []}
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
            options={availableColumns?.competitions || []}
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
              options={availableColumns?.batting_teams || []}
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
              options={availableColumns?.bowling_teams || []}
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
          <FormControlLabel
            control={
              <Switch
                checked={filters.include_international}
                onChange={(e) => handleFilterChange('include_international', e.target.checked)}
                size="small"
              />
            }
            label="Include T20I"
          />
        </Grid>
        
        {/* Row 3: Players */}
        <Grid item xs={12} sm={6}>
          <Autocomplete
            multiple
            value={filters.batters || []}
            onChange={(e, value) => handleFilterChange('batters', value)}
            options={availableColumns?.batters || []}
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
            options={availableColumns?.bowlers || []}
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
        <Grid item xs={12} sm={4} md={3}>
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
        
        <Grid item xs={12} sm={4} md={3}>
          <TextField
            label="Over Min"
            type="number"
            value={filters.over_min ?? ''}
            onChange={(e) => handleFilterChange('over_min', e.target.value ? parseInt(e.target.value) : null)}
            inputProps={{ min: 0, max: 19 }}
            size="small"
            fullWidth
          />
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <TextField
            label="Over Max"
            type="number"
            value={filters.over_max ?? ''}
            onChange={(e) => handleFilterChange('over_max', e.target.value ? parseInt(e.target.value) : null)}
            inputProps={{ min: 0, max: 19 }}
            size="small"
            fullWidth
          />
        </Grid>

        {/* Row 5: Advanced Match Context */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, mt: 1 }}>
            Advanced Match Context
          </Typography>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Autocomplete
            multiple
            value={filters.match_outcome || []}
            onChange={(e, value) => handleFilterChange('match_outcome', value)}
            options={availableColumns?.match_outcome_options || ['win', 'loss', 'tie', 'no_result']}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
              ))
            }
            renderInput={(params) => (
              <TextField {...params} label="Match Outcome" size="small" />
            )}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <FormControl size="small" fullWidth>
            <InputLabel>Is Chase</InputLabel>
            <Select
              value={filters.is_chase === null || filters.is_chase === undefined ? '' : String(filters.is_chase)}
              onChange={(e) => {
                const raw = e.target.value;
                if (raw === '') {
                  handleFilterChange('is_chase', null);
                } else {
                  handleFilterChange('is_chase', raw === 'true');
                }
              }}
              label="Is Chase"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="true">Yes (2nd innings)</MenuItem>
              <MenuItem value="false">No (1st innings)</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Autocomplete
            multiple
            disabled={chaseOutcomeDisabled}
            value={filters.chase_outcome || []}
            onChange={(e, value) => handleFilterChange('chase_outcome', value)}
            options={availableColumns?.chase_outcome_options || ['win', 'loss', 'tie', 'no_result']}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
              ))
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Chase Outcome"
                size="small"
                helperText={chaseOutcomeDisabled ? 'Requires chase innings' : ''}
              />
            )}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Autocomplete
            multiple
            value={filters.toss_decision || []}
            onChange={(e, value) => handleFilterChange('toss_decision', value)}
            options={availableColumns?.toss_decision_options || ['bat', 'field']}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
              ))
            }
            renderInput={(params) => (
              <TextField {...params} label="Toss Decision" size="small" />
            )}
          />
        </Grid>
        
        {/* Row 6: Batter/Bowler Attributes */}
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel>Bat Hand</InputLabel>
              <Select
                value={filters.bat_hand || ''}
                onChange={(e) => handleFilterChange('bat_hand', e.target.value || null)}
                label="Bat Hand"
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="RHB">Right Hand (RHB)</MenuItem>
                <MenuItem value="LHB">Left Hand (LHB)</MenuItem>
              </Select>
            </FormControl>
            <CoverageWarning coverage={availableColumns?.bat_hand_coverage} columnName="Bat hand" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.bowl_style || []}
              onChange={(e, value) => handleFilterChange('bowl_style', value)}
              options={availableColumns?.bowl_style_options || []}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Bowl Style" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="RF=Right Fast, RM=Right Medium, SLA=Slow Left Arm, OB=Off Break, LB=Leg Break" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.bowl_kind || []}
              onChange={(e, value) => handleFilterChange('bowl_kind', value)}
              options={availableColumns?.bowl_kind_options || []}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Bowl Kind" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Pace bowler, Spin bowler, or Mixture/Unknown" />
          </Box>
        </Grid>
        
        {/* Row 7: Delivery Details - NEW */}
        <Grid item xs={12}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, mt: 1 }}>
            Delivery Analysis Filters
          </Typography>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.line || []}
              onChange={(e, value) => handleFilterChange('line', value)}
              options={availableColumns?.line_options || []}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Line" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <CoverageWarning coverage={availableColumns?.line_coverage} columnName="Line" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.length || []}
              onChange={(e, value) => handleFilterChange('length', value)}
              options={availableColumns?.length_options || []}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Length" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <CoverageWarning coverage={availableColumns?.length_coverage} columnName="Length" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.shot || []}
              onChange={(e, value) => handleFilterChange('shot', value)}
              options={availableColumns?.shot_options || []}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Shot Type" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <CoverageWarning coverage={availableColumns?.shot_coverage} columnName="Shot" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel>Shot Control</InputLabel>
              <Select
                value={filters.control ?? ''}
                onChange={(e) => handleFilterChange('control', e.target.value === '' ? null : parseInt(e.target.value))}
                label="Shot Control"
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value={1}>Controlled</MenuItem>
                <MenuItem value={0}>Uncontrolled</MenuItem>
              </Select>
            </FormControl>
            <CoverageWarning coverage={availableColumns?.control_coverage} columnName="Control" />
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={4} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Autocomplete
              multiple
              value={filters.wagon_zone || []}
              onChange={(e, value) => handleFilterChange('wagon_zone', value)}
              options={availableColumns?.wagon_zone_options || [0, 1, 2, 3, 4, 5, 6, 7, 8]}
              getOptionLabel={(option) => `Zone ${option}`}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip variant="outlined" label={`Z${option}`} size="small" {...getTagProps({ index })} />
                ))
              }
              renderInput={(params) => (
                <TextField {...params} label="Wagon Zone" size="small" />
              )}
              sx={{ flexGrow: 1 }}
            />
            <InfoTooltip tooltip="Wagon wheel zones 0-8. Zone 0=No shot, 1-8=Direction of shot" />
          </Box>
        </Grid>
        
        {/* Row 8: Grouping - KEY FEATURE */}
        <Grid item xs={12}>
          <Box sx={{ 
            mt: isMobile ? 1.5 : 2, 
            p: isMobile ? 1.5 : 2, 
            borderRadius: 2, 
            border: '2px solid',
            borderColor: 'primary.main',
            backgroundColor: 'primary.50',
            position: 'relative'
          }}>
            {/* Key insight badge */}
            <Box sx={{ 
              display: isMobile ? 'none' : 'flex',
              position: 'absolute', 
              top: -12, 
              left: 16, 
              backgroundColor: 'primary.main', 
              color: 'white',
              px: 1.5,
              py: 0.25,
              borderRadius: 1,
              fontSize: '0.7rem',
              fontWeight: 'bold',
              alignItems: 'center',
              gap: 0.5
            }}>
              🔑 KEY INSIGHT
            </Box>
            
            <Typography variant="subtitle2" color="primary.dark" sx={{ mb: 0.75, mt: isMobile ? 0 : 0.5, fontWeight: 'bold' }}>
              {isMobile ? 'Group By (Insight Mode)' : 'Group By — This changes everything!'}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: isMobile ? 1 : 1.5 }}>
              {isMobile
                ? 'Pick dimensions like batter, phase, competition, or match_outcome.'
                : 'Choose how to slice your data. Try "batter + phase" or "bowl_style + length" for powerful insights.'}
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Autocomplete
                multiple
                value={groupBy}
                onChange={handleGroupByChange}
                options={availableColumns?.group_by_columns || []}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip 
                      variant="filled" 
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
                    placeholder="Select dimensions to analyze..."
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        backgroundColor: 'white',
                      }
                    }}
                  />
                )}
                sx={{ flexGrow: 1 }}
              />
              <InfoTooltip tooltip="Leave empty for individual deliveries. Group for aggregated stats with charts." />
            </Box>
          </Box>
        </Grid>
        
        {/* Summary Rows Toggle */}
        {groupBy && groupBy.length > 1 && (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, pl: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={filters.show_summary_rows || false}
                    onChange={(e) => handleFilterChange('show_summary_rows', e.target.checked)}
                    size="small"
                    color="primary"
                  />
                }
                label="Show Summary Rows"
              />
              <InfoTooltip tooltip="Add summary rows for each group level with % calculations" />
            </Box>
          </Grid>
        )}
        
        {/* Row 9: Result Filtering */}
        <Grid item xs={12} sm={6} md={3}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TextField
              label="Min Balls"
              type="number"
              value={filters.min_balls ?? ''}
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
            value={filters.max_balls ?? ''}
            onChange={(e) => handleFilterChange('max_balls', e.target.value ? parseInt(e.target.value) : null)}
            inputProps={{ min: 0 }}
            size="small"
            fullWidth
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <TextField
            label="Min Runs"
            type="number"
            value={filters.min_runs ?? ''}
            onChange={(e) => handleFilterChange('min_runs', e.target.value ? parseInt(e.target.value) : null)}
            inputProps={{ min: 0 }}
            size="small"
            fullWidth
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <TextField
            label="Max Runs"
            type="number"
            value={filters.max_runs ?? ''}
            onChange={(e) => handleFilterChange('max_runs', e.target.value ? parseInt(e.target.value) : null)}
            inputProps={{ min: 0 }}
            size="small"
            fullWidth
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <TextField
            label="Min Wickets"
            type="number"
            value={filters.min_wickets ?? ''}
            onChange={(e) => handleFilterChange('min_wickets', e.target.value ? parseInt(e.target.value, 10) : null)}
            inputProps={{ min: 0 }}
            size="small"
            fullWidth
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <TextField
            label="Max Wickets"
            type="number"
            value={filters.max_wickets ?? ''}
            onChange={(e) => handleFilterChange('max_wickets', e.target.value ? parseInt(e.target.value, 10) : null)}
            inputProps={{ min: 0 }}
            size="small"
            fullWidth
          />
        </Grid>
        
        {/* Row 10: Query Settings */}
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
        
        {/* Data coverage info */}
        {availableColumns?.total_deliveries && (
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary">
              Total deliveries in database: {availableColumns.total_deliveries.toLocaleString()}
            </Typography>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default QueryFilters;
