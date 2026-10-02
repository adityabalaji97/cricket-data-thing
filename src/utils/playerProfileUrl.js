/**
 * Profile URL for a search pick. Search suggestions carry the legacy key (`name`, "V Kohli") and
 * the full spelling (`details_name` / `display_name`, "Virat Kohli"); the profile's player list
 * holds canonical full names, so the full spelling is the one that matches it.
 */
const playerProfileUrl = (item, { startDate, endDate } = {}) => {
  const params = new URLSearchParams();
  params.set('name', item.details_name || item.display_name || item.name);
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  params.set('autoload', 'true');
  return `/player?${params.toString()}`;
};

export default playerProfileUrl;
