/**
 * The selected cricket format, and everything the UI needs to know about it.
 *
 * Formats are fetched from `GET /formats` rather than duplicated here, so phase boundaries,
 * over caps and innings counts have exactly one definition — format_config.py on the backend.
 * A small static fallback covers first paint and the case where the request fails.
 *
 * The backend reports `available: false` for a format whose data has not been loaded, so the
 * switcher can show what is coming without a separate feature flag.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import config from '../config';
import { clearAnalyticsCache, setActiveFormatParams } from '../utils/analyticsApi';

const STORAGE_KEY = 'hindsight.format';
const URL_PARAM = 'fmt';

// Enough to render the shell before /formats resolves. Men's T20 only, because that is the one
// format guaranteed to have data.
const FALLBACK_FORMATS = [
  {
    format: 'T20',
    gender: 'male',
    slug: 'mens-t20',
    label: "Men's T20",
    innings_count: 2,
    balls_per_innings: 120,
    chase_innings: 2,
    over_max: 19,
    has_fixed_over_cap: true,
    phases: [
      { key: 'powerplay', label: 'Powerplay', start_over: 0, end_over: 5, display_overs: '1-6' },
      { key: 'middle', label: 'Middle', start_over: 6, end_over: 14, display_overs: '7-15' },
      { key: 'death', label: 'Death', start_over: 15, end_over: 19, display_overs: '16-20' },
    ],
    phases_4: [],
    available: true,
  },
];

const FormatContext = createContext(null);

const readInitialSlug = () => {
  // A ?fmt= in the URL wins, so a shared link lands on the format it was shared from.
  try {
    const fromUrl = new URLSearchParams(window.location.search).get(URL_PARAM);
    if (fromUrl) return fromUrl;
    return window.localStorage.getItem(STORAGE_KEY) || 'mens-t20';
  } catch {
    return 'mens-t20';
  }
};

export const FormatProvider = ({ children }) => {
  const [formats, setFormats] = useState(FALLBACK_FORMATS);
  const [slug, setSlug] = useState(readInitialSlug);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${config.API_URL}/formats`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((data) => {
        if (cancelled || !data?.formats?.length) return;
        setFormats(data.formats);
      })
      .catch(() => {
        // Keep the fallback. A failed lookup should not stop the app rendering men's T20.
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Never leave the app pointed at a format that does not exist or has no data — a stale
  // localStorage value or a hand-edited URL would otherwise produce empty pages.
  const active = useMemo(() => {
    const requested = formats.find((f) => f.slug === slug);
    if (requested?.available) return requested;
    return formats.find((f) => f.available) || formats[0];
  }, [formats, slug]);

  const selectFormat = useCallback((nextSlug) => {
    setSlug(nextSlug);
    try {
      window.localStorage.setItem(STORAGE_KEY, nextSlug);
    } catch {
      // Private browsing: the choice just will not persist.
    }
    try {
      const url = new URL(window.location.href);
      url.searchParams.set(URL_PARAM, nextSlug);
      window.history.replaceState({}, '', url);
    } catch {
      // Non-fatal; the in-memory selection still applies.
    }
  }, []);

  // Keep the API client in step with the selection, and drop cached responses for the previous
  // format so a switch cannot serve the old format's numbers from cache.
  useEffect(() => {
    if (!active) return;
    setActiveFormatParams({ format: active.format, gender: active.gender });
    clearAnalyticsCache();
  }, [active]);

  const value = useMemo(
    () => ({
      formats,
      loading,
      active,
      selectFormat,
      // Ready to spread into a request: `{ ...formatParams }`.
      formatParams: { format: active?.format || 'T20', gender: active?.gender || 'male' },
      isDefaultFormat: (active?.format || 'T20') === 'T20' && (active?.gender || 'male') === 'male',
      phaseLabel: (key) => active?.phases?.find((p) => p.key === key)?.label || key,
      phaseOvers: (key) => active?.phases?.find((p) => p.key === key)?.display_overs || '',
    }),
    [formats, loading, active, selectFormat],
  );

  return <FormatContext.Provider value={value}>{children}</FormatContext.Provider>;
};

export const useFormat = () => {
  const ctx = useContext(FormatContext);
  if (!ctx) throw new Error('useFormat must be used inside a FormatProvider');
  return ctx;
};

export default FormatContext;
