import React, { useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import FilterDrawer from './FilterDrawer';

/**
 * A page's filter form, folded into one line on phones once there are results to look at.
 *
 * Filter forms (player, dates, venue, leagues...) used to fill the whole first phone screen above
 * the results, on every visit. With `collapsed` set, this shows a summary card instead
 * ("V Kohli · Jan 2025 - today · All leagues  [Edit]") and opens the unchanged form in a bottom
 * sheet. Anything in the form marked `data-filter-submit` (the page's GO / Compare button)
 * closes the sheet when pressed. Not collapsed (desktop, or nothing chosen yet): the form renders
 * inline exactly as before.
 *
 * Moving the form between inline and the sheet remounts it, so inputs must be controlled by the
 * page (pass `value` to CompetitionFilter).
 */
const FilterSummary = ({ collapsed, title, summary, sheetTitle = 'Filters', children }) => {
  const [open, setOpen] = useState(false);

  if (!collapsed) return children;

  return (
    <>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 1.75,
          py: 1.25,
          border: 1,
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {title && (
            <Typography sx={{ fontWeight: 700, fontSize: 15 }} noWrap>
              {title}
            </Typography>
          )}
          {summary && (
            <Typography variant="body2" color="text.secondary" noWrap>
              {summary}
            </Typography>
          )}
        </Box>
        <Button
          size="small"
          variant="outlined"
          startIcon={<TuneRoundedIcon />}
          onClick={() => setOpen(true)}
          sx={{ flexShrink: 0, minHeight: 36 }}
        >
          Edit
        </Button>
      </Box>
      <FilterDrawer open={open} onClose={() => setOpen(false)} title={sheetTitle}>
        <Box
          onClickCapture={(event) => {
            if (event.target.closest && event.target.closest('[data-filter-submit]')) {
              // Let the page's own handler run first, then get out of the way of the results.
              setTimeout(() => setOpen(false), 0);
            }
          }}
          sx={{ pb: 'env(safe-area-inset-bottom, 0px)' }}
        >
          {children}
        </Box>
      </FilterDrawer>
    </>
  );
};

const MONTH_YEAR = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric' });

const parseIsoDate = (value) => {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
};

/** "Jan 2025 - today", "Mar 2019 - Dec 2023". An end within the last few days reads as today. */
export const summarizeDateRange = (start, end) => {
  const startDate = parseIsoDate(start);
  const endDate = parseIsoDate(end);
  const startLabel = startDate ? MONTH_YEAR.format(startDate) : 'Start';
  const recent = !endDate || (Date.now() - endDate.getTime()) < 4 * 24 * 3600 * 1000;
  return `${startLabel} - ${recent ? 'today' : MONTH_YEAR.format(endDate)}`;
};

/** "All leagues", "IPL, BBL", "4 leagues", plus "+ top 10 intl" when internationals are in. */
export const summarizeCompetitions = (filters) => {
  if (!filters) return '';
  const leagues = Array.isArray(filters.leagues) ? filters.leagues : [];
  let label = 'All leagues';
  if (leagues.length === 1 || leagues.length === 2) label = leagues.join(', ');
  else if (leagues.length > 2) label = `${leagues.length} leagues`;
  if (filters.international) {
    label += filters.topTeams ? ` + top ${filters.topTeams} intl` : ' + intl';
  }
  return label;
};

export const joinSummary = (...parts) => parts.filter(Boolean).join(' · ');

export default FilterSummary;
