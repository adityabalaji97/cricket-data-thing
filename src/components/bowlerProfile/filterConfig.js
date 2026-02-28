import { DEFAULT_START_DATE, TODAY } from '../../utils/dateDefaults';

export { DEFAULT_START_DATE, TODAY };

export const buildBowlerProfileFilters = ({ players, venues, playerSearch = {} }) => [
  {
    key: 'player',
    label: 'Select Player',
    type: 'autocomplete',
    options: players,
    defaultValue: null,
    required: true,
    ...playerSearch,
  },
  {
    key: 'startDate',
    label: 'Start Date',
    type: 'date',
    defaultValue: DEFAULT_START_DATE,
    group: 'dateRange',
  },
  {
    key: 'endDate',
    label: 'End Date',
    type: 'date',
    defaultValue: TODAY,
    group: 'dateRange',
  },
  {
    key: 'venue',
    label: 'Select Venue',
    type: 'autocomplete',
    options: venues,
    defaultValue: 'All Venues',
  },
];
