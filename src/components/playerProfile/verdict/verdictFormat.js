// Number formats shared by the verdict screen's pieces.

export const ordinal = (n) => {
  const v = n % 100;
  const s = ['th', 'st', 'nd', 'rd'];
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
};

export const signed = (v, dp = 2) => {
  if (v === null || v === undefined) return '–';
  const text = Math.abs(v).toFixed(dp);
  if (Number(text) === 0) return text;
  return `${v > 0 ? '+' : '−'}${text}`;
};

export const formatMetric = (key, v) => {
  if (v === null || v === undefined) return '–';
  if (key === 'wpa') return signed(v, 2);
  if (key === 'economy') return v.toFixed(2);
  if (key === 'dot_percentage') return `${v.toFixed(1)}%`;
  return v.toFixed(1);
};

export const ROLE_COLOURS = { bowl: '#5b8def', bat: '#c4850f' }; // validated on surface #101319 (dataviz checks)
export const ROLE_NAMES = { bowl: 'Bowling', bat: 'Batting' };
