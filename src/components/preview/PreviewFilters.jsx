/**
 * Match preview filters — venue, date range, time slice, competitions and the two teams.
 *
 * Extracted verbatim from the inline JSX in the `/venue` route in App.js (chunk A6). The
 * behaviour is deliberately unchanged: same handlers, same state, same conditional rendering,
 * so a T20 preview produces identical results before and after. Only the skin moved, from
 * light-theme MUI defaults to the dark design system in src/theme/hindsightDark.js.
 *
 * Kept as a presentational component with state owned by App.js. The preview's data fetching
 * is bound up with that state and moving both at once would make "did the numbers change?"
 * impossible to answer, which is the one thing A6 has to guarantee.
 */

import React from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Collapse,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';

import CompetitionFilter from '../CompetitionFilter';
import { buttonSx, cardSx, colors, fonts } from '../../theme/hindsightDark';

// MUI's outlined inputs default to light-theme greys, so each surface needs restating.
// Defined once here rather than per-field: five inputs drifting apart is exactly the kind of
// inconsistency the design-system consolidation was meant to end.
const inputSx = {
  '& .MuiOutlinedInput-root': {
    bgcolor: colors.input,
    color: colors.textHi,
    borderRadius: '10px',
    fontFamily: fonts.body,
    '& fieldset': { borderColor: colors.border },
    '&:hover fieldset': { borderColor: colors.borderStrong },
    '&.Mui-focused fieldset': { borderColor: colors.accent },
  },
  '& .MuiInputLabel-root': {
    color: colors.textLo,
    fontFamily: fonts.body,
    '&.Mui-focused': { color: colors.accent },
  },
  // Keeps the native date picker indicator visible on a dark field.
  '& input[type="date"]::-webkit-calendar-picker-indicator': {
    filter: 'invert(0.7)',
    cursor: 'pointer',
  },
};

const toggleSx = {
  '& .MuiToggleButton-root': {
    color: colors.textLo,
    borderColor: colors.border,
    fontFamily: fonts.mono,
    fontSize: 11,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    px: 1.5,
    '&.Mui-selected': {
      bgcolor: colors.accentSoft,
      color: colors.accent,
      borderColor: 'rgba(182,242,74,0.4)',
      '&:hover': { bgcolor: colors.accentSoft },
    },
  },
};

const labelSx = {
  fontFamily: fonts.mono,
  color: colors.accent,
  fontSize: 10,
  letterSpacing: '0.16em',
  textTransform: 'uppercase',
  mb: 0.75,
};

const PreviewFilters = ({
  error,
  loading,
  isMobile,
  filtersExpanded,
  showVisualizations,
  setShowVisualizations,
  hasFetchedRef,
  // Venue
  venues,
  selectedVenue,
  setSelectedVenue,
  // Dates
  startDate,
  endDate,
  handleDateChange,
  today,
  // Time slice
  dayNightFilter,
  handleDayNightChange,
  // Competitions
  competitions,
  handleFilterChange,
  // Teams
  teams,
  selectedTeam1,
  setSelectedTeam1,
  selectedTeam2,
  setSelectedTeam2,
}) => (
  <>
    {error && (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    )}

    <Collapse in={filtersExpanded || !showVisualizations}>
      <Box
        sx={{
          ...cardSx,
          mb: 2,
          p: { xs: 1.75, md: 2.25 },
          // Once results are showing the filters are secondary, so the card recedes rather
          // than competing with them. Mirrors the original boxShadow/transparent switch.
          ...(showVisualizations
            ? { bgcolor: 'transparent', border: `1px solid ${colors.border}` }
            : {}),
        }}
      >
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            gap: 2,
            mb: 2,
          }}
        >
          <Autocomplete
            value={selectedVenue}
            onChange={(event, newValue) => {
              setSelectedVenue(newValue || 'All Venues');
              setShowVisualizations(false);
            }}
            options={venues}
            sx={{ width: '100%', ...inputSx }}
            loading={loading}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Select Venue"
                required
                fullWidth
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {loading ? <CircularProgress color="inherit" size={20} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
          />

          <TextField
            label="Start Date"
            type="date"
            value={startDate}
            onChange={(e) => handleDateChange(e.target.value, true)}
            InputLabelProps={{ shrink: true }}
            inputProps={{ max: endDate }}
            required
            fullWidth
            sx={inputSx}
          />

          <TextField
            label="End Date"
            type="date"
            value={endDate}
            onChange={(e) => handleDateChange(e.target.value, false)}
            InputLabelProps={{ shrink: true }}
            inputProps={{ max: today }}
            required
            fullWidth
            sx={inputSx}
          />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography sx={labelSx}>Match Time Slice</Typography>
          <ToggleButtonGroup
            size="small"
            value={dayNightFilter}
            exclusive
            onChange={handleDayNightChange}
            sx={toggleSx}
          >
            <ToggleButton value="all">All</ToggleButton>
            <ToggleButton value="day">Day</ToggleButton>
            <ToggleButton value="night">Night</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        <CompetitionFilter
          onFilterChange={handleFilterChange}
          isMobile={isMobile}
          value={competitions}
        />

        {startDate && endDate && !error && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: { xs: 'column', md: 'row' },
              gap: 2,
              mb: 0,
              mt: 2,
            }}
          >
            <Autocomplete
              value={selectedTeam1}
              onChange={(event, newValue) => {
                setSelectedTeam1(newValue);
                setShowVisualizations(false);
              }}
              options={teams}
              sx={{ width: '100%', ...inputSx }}
              getOptionLabel={(option) => option?.abbreviated_name || ''}
              renderOption={(props, option) => (
                <li {...props}>
                  <Typography sx={{ fontFamily: fonts.body }}>
                    {option.abbreviated_name} - {option.full_name}
                  </Typography>
                </li>
              )}
              renderInput={(params) => <TextField {...params} label="Team 1" fullWidth />}
              isOptionEqualToValue={(option, value) => option?.full_name === value?.full_name}
            />

            <Autocomplete
              value={selectedTeam2}
              onChange={(event, newValue) => {
                setSelectedTeam2(newValue);
                setShowVisualizations(false);
              }}
              options={teams.filter((team) => team?.full_name !== selectedTeam1?.full_name)}
              sx={{ width: '100%', ...inputSx }}
              getOptionLabel={(option) => option?.abbreviated_name || ''}
              renderOption={(props, option) => (
                <li {...props}>
                  <Typography sx={{ fontFamily: fonts.body }}>
                    {option.abbreviated_name} - {option.full_name}
                  </Typography>
                </li>
              )}
              renderInput={(params) => <TextField {...params} label="Team 2" fullWidth />}
              isOptionEqualToValue={(option, value) => option?.full_name === value?.full_name}
            />

            <Button
              variant="contained"
              onClick={() => {
                hasFetchedRef.current = false;
                setShowVisualizations(true);
              }}
              disabled={loading || error}
              sx={{
                ...buttonSx,
                mt: { xs: 1, md: 0 },
                width: { xs: '100%', md: 'auto' },
                height: { xs: 'auto', md: '56px' },
                px: 3,
              }}
            >
              Go
            </Button>
          </Box>
        )}
      </Box>
    </Collapse>
  </>
);

export default PreviewFilters;
