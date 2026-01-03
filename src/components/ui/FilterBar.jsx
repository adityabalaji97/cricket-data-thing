/**
 * FilterBar Component - Consistent filter UI for desktop and mobile
 */
import React from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Drawer,
  Button,
  Typography,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import CloseIcon from '@mui/icons-material/Close';
import { colors, spacing, borderRadius, typography, transitions } from '../../theme/designSystem';

const FilterItem = ({ label, value, options, onChange, isMobile, fullWidth = false }) => {
  return (
    <FormControl
      size="small"
      sx={{
        minWidth: isMobile ? (fullWidth ? '100%' : 120) : 140,
        flex: fullWidth ? 1 : 'none',
      }}
    >
      <InputLabel
        sx={{
          fontSize: isMobile ? typography.fontSize.sm : typography.fontSize.base,
          color: colors.neutral[600],
        }}
      >
        {label}
      </InputLabel>
      <Select
        value={value}
        label={label}
        onChange={onChange}
        sx={{
          fontSize: isMobile ? typography.fontSize.sm : typography.fontSize.base,
          borderRadius: `${borderRadius.base}px`,
          backgroundColor: colors.neutral[0],
          transition: `all ${transitions.base}`,
          '&:hover': {
            backgroundColor: colors.neutral[50],
          },
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: colors.neutral[300],
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: colors.primary[400],
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: colors.primary[600],
          },
        }}
      >
        {options.map((option) => (
          <MenuItem
            key={option.value}
            value={option.value}
            sx={{
              fontSize: isMobile ? typography.fontSize.sm : typography.fontSize.base,
            }}
          >
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

const FilterBar = ({
  filters,
  activeFilters = {},
  onFilterChange,
  isMobile = false,
  showActiveCount = true,
}) => {
  const [mobileDrawerOpen, setMobileDrawerOpen] = React.useState(false);

  const activeCount = Object.values(activeFilters).filter(
    (value) => value !== 'all' && value !== 'overall' && value !== null
  ).length;

  const handleFilterChange = (filterKey) => (event) => {
    onFilterChange(filterKey, event.target.value);
  };

  const renderFilters = () => (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: `${spacing.md}px`,
        alignItems: 'center',
      }}
    >
      {filters.map((filter) => (
        <FilterItem
          key={filter.key}
          label={filter.label}
          value={activeFilters[filter.key] || filter.defaultValue || 'all'}
          options={filter.options}
          onChange={handleFilterChange(filter.key)}
          isMobile={isMobile}
          fullWidth={filter.fullWidth}
        />
      ))}
    </Box>
  );

  if (isMobile) {
    return (
      <>
        {/* Mobile Filter Button */}
        <Box sx={{ display: 'flex', gap: `${spacing.sm}px`, alignItems: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<FilterListIcon />}
            onClick={() => setMobileDrawerOpen(true)}
            sx={{
              borderRadius: `${borderRadius.base}px`,
              borderColor: colors.neutral[300],
              color: colors.neutral[700],
              fontSize: typography.fontSize.sm,
              textTransform: 'none',
              fontWeight: typography.fontWeight.medium,
              '&:hover': {
                borderColor: colors.primary[400],
                backgroundColor: colors.primary[50],
              },
            }}
          >
            Filters
            {showActiveCount && activeCount > 0 && (
              <Chip
                label={activeCount}
                size="small"
                sx={{
                  ml: `${spacing.sm}px`,
                  height: 20,
                  minWidth: 20,
                  fontSize: typography.fontSize.xs,
                  backgroundColor: colors.primary[600],
                  color: colors.neutral[0],
                }}
              />
            )}
          </Button>
        </Box>

        {/* Mobile Filter Drawer (Bottom Sheet) */}
        <Drawer
          anchor="bottom"
          open={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          sx={{
            '& .MuiDrawer-paper': {
              borderTopLeftRadius: `${borderRadius.lg}px`,
              borderTopRightRadius: `${borderRadius.lg}px`,
              maxHeight: '80vh',
            },
          }}
        >
          <Box sx={{ p: `${spacing.lg}px` }}>
            {/* Header */}
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: `${spacing.lg}px`,
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: typography.fontWeight.semibold }}>
                Filters
              </Typography>
              <IconButton onClick={() => setMobileDrawerOpen(false)} size="small">
                <CloseIcon />
              </IconButton>
            </Box>

            {/* Filters */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${spacing.base}px` }}>
              {renderFilters()}
            </Box>

            {/* Apply Button */}
            <Button
              fullWidth
              variant="contained"
              onClick={() => setMobileDrawerOpen(false)}
              sx={{
                mt: `${spacing.lg}px`,
                borderRadius: `${borderRadius.base}px`,
                textTransform: 'none',
                fontWeight: typography.fontWeight.semibold,
              }}
            >
              Apply Filters
            </Button>
          </Box>
        </Drawer>
      </>
    );
  }

  // Desktop Filters
  return (
    <Box
      sx={{
        display: 'flex',
        gap: `${spacing.base}px`,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}
    >
      {renderFilters()}
      {showActiveCount && activeCount > 0 && (
        <Chip
          label={`${activeCount} active`}
          size="small"
          variant="outlined"
          sx={{
            borderColor: colors.primary[300],
            color: colors.primary[700],
            fontSize: typography.fontSize.xs,
          }}
        />
      )}
    </Box>
  );
};

export default FilterBar;
export { FilterItem };
