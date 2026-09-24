const formatDate = (value) => value.toISOString().split('T')[0];

export const getSeasonStartDate = (referenceDate = new Date(), yearsBack = 1) => (
  `${referenceDate.getFullYear() - yearsBack}-01-01`
);

export const DEFAULT_START_DATE = getSeasonStartDate();
export const TODAY = formatDate(new Date());

/**
 * Match preview history window, by format: from 1 January, 8 years back for ODIs (they are sparse)
 * and 4 years back for T20s -- enough matches at most grounds for the numbers to mean something.
 * Keep in step with PREVIEW_WINDOW_YEARS in mcp_server/server.py (the connector's preview_match).
 */
export const PREVIEW_WINDOW_YEARS = { ODI: 8, T20: 4 };

export const getPreviewStartDate = (format = 'T20', referenceDate = new Date()) => (
  getSeasonStartDate(referenceDate, PREVIEW_WINDOW_YEARS[format] || PREVIEW_WINDOW_YEARS.T20)
);
