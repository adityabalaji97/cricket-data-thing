const formatDate = (value) => value.toISOString().split('T')[0];

export const getSeasonStartDate = (referenceDate = new Date(), yearsBack = 1) => (
  `${referenceDate.getFullYear() - yearsBack}-01-01`
);

export const DEFAULT_START_DATE = getSeasonStartDate();
export const TODAY = formatDate(new Date());
