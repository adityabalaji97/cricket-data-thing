import React, { useEffect, useState } from 'react';
import { Box, Button, TextField, Autocomplete } from '@mui/material';
import CompetitionFilter from '../CompetitionFilter';
import FilterDrawer from '../ui/FilterDrawer';
import { borderRadius, colors, spacing, typography } from '../../theme/designSystem';

const touchTargetStyles = {
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

const FilterSheet = ({
  open,
  onClose,
  filters,
  values,
  competitionFilters,
  onApply,
  loading,
}) => {
  const [draftValues, setDraftValues] = useState(values);
  const [draftCompetitionFilters, setDraftCompetitionFilters] = useState(competitionFilters);

  useEffect(() => {
    if (open) {
      setDraftValues(values);
      setDraftCompetitionFilters(competitionFilters);
    }
  }, [open, values, competitionFilters]);

  const handleChange = (key, value) => {
    setDraftValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleApply = () => {
    onApply(draftValues, draftCompetitionFilters);
    onClose();
  };

  const dateFilters = filters.filter((filter) => filter.group === 'dateRange');

  const renderFilterField = (filter) => {
    if (filter.type === 'autocomplete') {
      const getOptionLabel = filter.getOptionLabel || ((option) => {
        if (typeof option === 'string') {
          return option;
        }
        return option?.display_name || option?.name || '';
      });
      const isOptionEqualToValue = filter.isOptionEqualToValue || ((option, value) => {
        if (!value) return false;
        if (typeof option === 'string' || typeof value === 'string') {
          return option === value;
        }
        return option?.name === value?.name;
      });
      return (
        <Autocomplete
          key={filter.key}
          value={draftValues[filter.key]}
          onChange={(_, newValue) => handleChange(filter.key, newValue)}
          options={filter.options}
          inputValue={filter.inputValue}
          onInputChange={filter.onInputChange}
          loading={filter.loading}
          filterOptions={filter.filterOptions}
          fullWidth
          size="medium"
          getOptionLabel={getOptionLabel}
          isOptionEqualToValue={isOptionEqualToValue}
          renderInput={(params) => (
            <TextField
              {...params}
              label={filter.label}
              required={filter.required}
              variant="outlined"
              sx={touchTargetStyles}
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
        value={draftValues[filter.key]}
        onChange={(event) => handleChange(filter.key, event.target.value)}
        InputLabelProps={{ shrink: true }}
        fullWidth
        size="medium"
        sx={touchTargetStyles}
      />
    );
  };

  return (
    <FilterDrawer
      open={open}
      onClose={onClose}
      title="Filters"
      footer={
        <Button
          fullWidth
          variant="contained"
          onClick={handleApply}
          disabled={!draftValues.player || loading}
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
          Apply Filters
        </Button>
      }
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.base}px` }}>
        {filters.reduce(
          (acc, filter) => {
            if (filter.group === 'dateRange') {
              if (!acc.hasDateRange) {
                acc.items.push(
                  <Box
                    key="date-range"
                    sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.base}px` }}
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

        <CompetitionFilter
          onFilterChange={setDraftCompetitionFilters}
          isMobile
          value={draftCompetitionFilters}
        />
      </Box>
    </FilterDrawer>
  );
};

export default FilterSheet;
