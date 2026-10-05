// A readable message from a failed API call. FastAPI sends `detail` as a string for HTTP errors but
// as a list of {loc, msg, ...} objects for validation errors (422); rendering that list as a React
// child throws and blanks the page, so every error shown to people goes through here. Pass a null
// fallback to chain: `apiErrorText(err, null) || err.message || 'Failed'`.
export function apiErrorText(error, fallback = 'Something went wrong') {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => {
      if (typeof d === 'string') return d;
      const field = Array.isArray(d?.loc) ? d.loc.filter((p) => p !== 'query' && p !== 'body').join('.') : '';
      return [field, d?.msg].filter(Boolean).join(': ');
    }).filter(Boolean).join('; ') || fallback;
  }
  if (detail && typeof detail === 'object') return detail.message || detail.msg || fallback;
  return fallback;
}
