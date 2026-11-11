import React, { useEffect, useState } from 'react';
import { Box, IconButton, Skeleton, Tooltip } from '@mui/material';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import { Link } from 'react-router-dom';
import config from '../../config';
import PlayerLink from '../common/PlayerLink';
import { colors, fonts } from '../../theme/hindsightDark';
import ShareButton from '../ui/ShareButton';

// The pieces the simplified pages share (TEAM_VENUE_PLAN.md S1): the player profile set the pattern, the venue and
// team pages follow it. One window per page kept in the address bar, a header with the filters and share icons and the
// format/period pills, a summary of rank | description rows, cards (playerProfile/cards/ProfileCard), and the data
// credit once at the foot. Every line fits one line at 390px.

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const FORMATS = ['T20', 'ODI'];
const PERIOD_TABS = [['recent', 'Recent'], ['career', 'Career']];

// ---- the window --------------------------------------------------------------------------------------------------

export const readWindow = (search) => {
  const q = new URLSearchParams(search);
  const fmt = q.get('format') === 'ODI' ? 'ODI' : 'T20';
  const start = q.get('start_date'); const end = q.get('end_date');
  const period = start ? 'custom' : q.get('period') === 'career' ? 'career' : 'recent';
  return { fmt, period, start: start || null, end: end || null };
};

/** The page's search string: its subject (e.g. {venue: 'Wankhede Stadium'}) plus the window, defaults left out. */
export const writeSearch = (subject, w) => {
  const q = new URLSearchParams(subject);
  if (w.fmt !== 'T20') q.set('format', w.fmt);
  if (w.period === 'career') q.set('period', 'career');
  if (w.period === 'custom') {
    if (w.start) q.set('start_date', w.start);
    if (w.end) q.set('end_date', w.end);
  }
  return `?${q.toString()}`;
};

export const windowQuery = (w) => {
  const q = new URLSearchParams({ format: w.fmt });
  if (w.period === 'custom') {
    if (w.start) q.set('start_date', w.start);
    if (w.end) q.set('end_date', w.end);
  } else {
    q.set('period', w.period);
  }
  return q.toString();
};

export const windowChip = (win, extra) => {
  const month = (iso) => { const d = new Date(`${iso}T00:00:00`); return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`; };
  if (!win?.start_date) return extra || '';
  const end = win.end_date ? new Date(`${win.end_date}T00:00:00`) : null;
  const now = new Date();
  const ended = end && (end.getFullYear() < now.getFullYear() || (end.getFullYear() === now.getFullYear() && end.getMonth() < now.getMonth()));
  const span = ended ? `${month(win.start_date)} to ${month(win.end_date)}` : `Since ${month(win.start_date)}`;
  return [span, extra].filter(Boolean).join(' · ');
};

// ---- data --------------------------------------------------------------------------------------------------------

/**
 * GET a page's one call. A cold page is built in the background and the API answers 503 meanwhile, so it asks again
 * every few seconds, for up to a minute and a half, before giving up.
 */
export const usePageData = (path, query) => {
  const [state, setState] = useState({ status: 'loading', data: null });
  useEffect(() => {
    if (!path) return undefined;
    let cancelled = false;
    let timer = null;
    setState({ status: 'loading', data: null });
    const load = (attempt) => {
      fetch(`${config.API_URL}${path}?${query}`)
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
        .catch((e) => {
          if (cancelled) return;
          if (e === 503 && attempt < 18) {
            setState({ status: 'building', data: null });
            timer = setTimeout(() => load(attempt + 1), 5000);
          } else {
            setState({ status: e === 404 ? 'empty' : 'error', data: null });
          }
        });
    };
    load(0);
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [path, query]);
  return state;
};

// ---- header ------------------------------------------------------------------------------------------------------

const Pills = ({ label, items, value, onChange, light }) => (
  <Box role="tablist" aria-label={label} sx={{ display: 'inline-flex', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
    {items.map(([key, name]) => (
      <Box key={key} component="button" role="tab" aria-selected={key === value} onClick={() => onChange(key)}
        sx={{
          all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13, letterSpacing: '0.04em',
          px: 1.5, minHeight: 32, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', borderRadius: '999px',
          bgcolor: key === value ? (light ? colors.textHi : colors.accent) : 'transparent', color: key === value ? colors.bg : colors.textLo,
          '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
        }}>
        {name}
      </Box>
    ))}
  </Box>
);

export const PageHeader = ({ name, meta, win, onWindow, onFilters, chip, shareKind, shareTitle }) => (
  <>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1.5 }}>
      <Box sx={{ minWidth: 0 }}>
        <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 27, lineHeight: 1.05,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</Box>
        {meta && <Box sx={{ color: colors.textLo, fontSize: 13.5, mt: 0.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{meta}</Box>}
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0, mt: '-2px' }}>
        <Tooltip title="Filters">
          <IconButton aria-label="Filters: format and period" onClick={onFilters} sx={{ color: colors.textHi }}>
            <TuneRoundedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <ShareButton variant="icon" kind={shareKind} title={shareTitle} sx={{ color: colors.textHi }} />
      </Box>
    </Box>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexWrap: 'wrap' }}>
      <Pills label="Format" items={FORMATS.map((f) => [f, f])} value={win.fmt} onChange={(fmt) => onWindow({ fmt })} />
      <Pills label="Period" light items={PERIOD_TABS} value={win.period} onChange={(period) => onWindow({ period })} />
      {chip && <Box component="span" sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap' }}>{chip}</Box>}
    </Box>
  </>
);

/** rank | description, one per line; the first row leads. rows: [{rank, what, lead?}] */
export const SummaryRows = ({ rows, label = 'Summary' }) => (
  <Box component="ul" aria-label={label} sx={{ listStyle: 'none', m: 0, p: 0 }}>
    {rows.map((r, i) => (
      <Box component="li" key={`${r.rank}-${r.what}-${i}`}
        sx={{ display: 'grid', gridTemplateColumns: '92px minmax(0, 1fr)', alignItems: 'baseline', columnGap: 1.25, py: 0.6,
          borderBottom: `1px solid ${colors.border}`, whiteSpace: 'nowrap' }}>
        <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: r.lead ? 22 : 17, color: r.lead ? colors.textHi : colors.accent }}>{r.rank}</Box>
        <Box component="span" sx={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis',
          ...(r.lead ? { fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: colors.textHi } : { fontWeight: 500, fontSize: 15, color: colors.textMed }) }}>
          {r.what}
        </Box>
      </Box>
    ))}
  </Box>
);

export const Eyebrow = ({ children, right }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
    <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.textLo }}>
      {children}
    </Box>
    {right}
  </Box>
);

export const PageSkeleton = ({ note }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
    {note && <Box sx={{ color: colors.textLo, fontSize: 13.5 }}>{note}</Box>}
    <Skeleton variant="rounded" height={120} sx={{ bgcolor: colors.surface2 }} />
    <Skeleton variant="rounded" height={260} sx={{ bgcolor: colors.surface2, borderRadius: '18px' }} />
    <Skeleton variant="rounded" height={220} sx={{ bgcolor: colors.surface2, borderRadius: '18px' }} />
  </Box>
);

/** A short list inside a card: name, a detail, a value on the right. rows: [{name, detail, value, tone}] */
export const ValueList = ({ rows, label }) => (
  <Box component="ul" aria-label={label} sx={{ listStyle: 'none', m: 0, p: 0 }}>
    {rows.map((r) => (
      <Box component="li" key={r.key || r.player || r.name}
        sx={{ display: 'grid', gridTemplateColumns: r.lead ? '18px minmax(0, 1fr) auto 48px' : 'minmax(0, 1fr) auto 48px', alignItems: 'baseline',
          columnGap: 1, py: 0.75, borderBottom: `1px solid ${colors.border}`, whiteSpace: 'nowrap' }}>
        {r.lead && <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo }}>{r.lead}</Box>}
        <Box component="span" sx={{ fontWeight: 600, fontSize: 14, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {r.player ? <PlayerLink name={r.player} win={r.win} /> : r.name}
        </Box>
        <Box component="span" sx={{ fontSize: 12, color: colors.textLo }}>{r.detail}</Box>
        <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 13, textAlign: 'right',
          color: r.tone === 'pos' ? colors.accent : r.tone === 'neg' ? colors.red : colors.textHi }}>{r.value}</Box>
      </Box>
    ))}
  </Box>
);

export const PageFooter = ({ queryLink }) => (
  <>
    {queryLink && (
      <Box component={Link} to={queryLink} sx={{ textAlign: 'center', color: colors.accent, fontSize: 14, textDecoration: 'none', pt: 1, whiteSpace: 'nowrap', minHeight: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Dig deeper in the query builder →
      </Box>
    )}
    <Box sx={{ borderTop: `1px solid ${colors.border}`, pt: 1.5, textAlign: 'center', fontSize: 11.5, color: colors.textLo, lineHeight: 1.6 }}>
      <Box sx={{ whiteSpace: 'nowrap' }}>Data: Himanish Ganjoo &amp; TechRadar, Cricsheet</Box>
      <Box sx={{ whiteSpace: 'nowrap' }}>Metrics: Himanish Ganjoo&apos;s T20 Primer</Box>
    </Box>
  </>
);

export const ordinal = (n) => `${n}${(n % 100 >= 11 && n % 100 <= 13) ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th')}`;
export const signed = (v, d = 0) => {
  const r = Number(v).toFixed(d);
  if (Number(r) === 0) return (0).toFixed(d);
  return `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(d)}`;
};
