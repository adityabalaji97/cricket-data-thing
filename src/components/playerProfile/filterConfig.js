export const DEFAULT_START_DATE = '2020-01-01';
export const TODAY = new Date().toISOString().split('T')[0];

export const buildPlayerProfileFilters = ({ players, venues }) => [
  {
    key: 'player',
    label: 'Select Player',
    type: 'autocomplete',
    options: players,
    defaultValue: null,
    required: true,
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
