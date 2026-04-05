import config from '../config';

const analyticsCache = new Map();

const isPresent = (value) => value !== null && value !== undefined && value !== '';

const stableEntries = (params = {}) => {
  const keys = Object.keys(params || {}).sort();
  const entries = [];
  keys.forEach((key) => {
    const value = params[key];
    if (Array.isArray(value)) {
      [...value]
        .filter(isPresent)
        .map((item) => String(item))
        .sort()
        .forEach((item) => entries.push([key, item]));
      return;
    }
    if (isPresent(value)) {
      entries.push([key, String(value)]);
    }
  });
  return entries;
};

export const buildAnalyticsQuery = (params = {}) => {
  const query = new URLSearchParams(stableEntries(params));
  return query.toString();
};

export const buildAnalyticsUrl = (path, params = {}) => {
  const query = buildAnalyticsQuery(params);
  return `${config.API_URL}${path}${query ? `?${query}` : ''}`;
};

export const fetchAnalyticsJson = (path, params = {}, options = {}) => {
  const { force = false } = options;
  const url = buildAnalyticsUrl(path, params);

  if (force) {
    analyticsCache.delete(url);
  }

  if (analyticsCache.has(url)) {
    return analyticsCache.get(url);
  }

  const request = fetch(url).then(async (response) => {
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Analytics request failed (${response.status}): ${detail}`);
    }
    return response.json();
  }).catch((error) => {
    analyticsCache.delete(url);
    throw error;
  });

  analyticsCache.set(url, request);
  return request;
};

export const clearAnalyticsCache = () => {
  analyticsCache.clear();
};

export const normalizeAnalyticsName = (name) => (
  String(name || '').trim().toLowerCase().replace(/\s+/g, ' ')
);

export const getFormFlagMeta = (flag) => {
  const normalized = String(flag || 'neutral').toLowerCase();
  if (normalized === 'hot') {
    return { label: 'HOT', color: 'success' };
  }
  if (normalized === 'cold') {
    return { label: 'COLD', color: 'error' };
  }
  return { label: 'NEUTRAL', color: 'default' };
};
