import React from 'react';
import { Box, Button, TextField, Autocomplete } from '@mui/material';
import CompetitionFilter from '../CompetitionFilter';
import { borderRadius, colors, spacing, typography } from '../../theme/designSystem';

const FilterBar = ({
  filters,
  values,
  onChange,
  onSubmit,
  loading,
  competitionFilters,
  onCompetitionChange,
}) => {
  const dateFilters = filters.filter((filter) => filter.group === 'dateRange');

  const inputStyles = {
    '& .MuiInputBase-root': {
      minHeight: 44,
      borderRadius: `${borderRadius.base}px`,
      backgroundColor: colors.neutral[0],
    },
    '& .MuiOutlinedInput-notchedOutline': {
      borderColor: colors.neutral[300],
    },
    '&:hover .MuiOutlinedInput-notchedOutline': {
      borderColor: colors.primary[400],
    },
    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
      borderColor: colors.primary[600],
      borderWidth: 2,
    },
  };

  const renderFilterField = (filter) => {
    if (filter.type === 'autocomplete') {
      return (
        <Autocomplete
          key={filter.key}
          value={values[filter.key]}
          onChange={(_, newValue) => onChange(filter.key, newValue)}
          options={filter.options}
          fullWidth
          size="small"
          getOptionLabel={(option) => {
            if (typeof option === 'string') {
              return option;
            }
            return option || '';
          }}
          isOptionEqualToValue={(option, value) => {
            if (typeof value === 'string') {
              return option === value;
            }
            return option === value;
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label={filter.label}
              required={filter.required}
              variant="outlined"
              sx={inputStyles}
            />
          )}
        />
      );
    }

    return (
      <TextField
        key={filter.key}
        label={filter.label}
        type="date"
        value={values[filter.key]}
        onChange={(event) => onChange(filter.key, event.target.value)}
        InputLabelProps={{ shrink: true }}
        size="small"
        sx={inputStyles}
      />
    );
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.base}px` }}>
      {filters.reduce(
        (acc, filter) => {
          if (filter.group === 'dateRange') {
            if (!acc.hasDateRange) {
              acc.items.push(
                <Box
                  key="date-range"
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                    gap: `${spacing.sm}px`,
                  }}
                >
                  {dateFilters.map((dateFilter) => renderFilterField(dateFilter))}
                </Box>
              );
              acc.hasDateRange = true;
            }
            return acc;
          }

          acc.items.push(renderFilterField(filter));
          return acc;
        },
        { items: [], hasDateRange: false }
      ).items}

      <Button
        variant="contained"
        onClick={onSubmit}
        disabled={!values.player || loading}
        id="go-button"
        fullWidth
        size="medium"
        sx={{
          minHeight: 44,
          borderRadius: `${borderRadius.base}px`,
          textTransform: 'none',
          fontWeight: typography.fontWeight.semibold,
          '&:focus-visible': {
            outline: `2px solid ${colors.primary[600]}`,
            outlineOffset: 2,
          },
        }}
      >
        GO
      </Button>

      <CompetitionFilter
        onFilterChange={onCompetitionChange}
        isMobile={false}
        value={competitionFilters}
      />
    </Box>
  );
};

export default FilterBar;
