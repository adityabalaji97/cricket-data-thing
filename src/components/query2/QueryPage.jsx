import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Box, CircularProgress } from '@mui/material';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { useFormat } from '../../context/FormatContext';
import { parseUrlParams } from '../../utils/urlParamParser';
import { track } from '../../utils/analytics';
import { PageFooter } from '../pageKit/pageKit';
import AnswerCard from './AnswerCard';
import FilterSheet from './FilterSheet';
import { ASKABLE, shapeAnswer } from './answerShape';
import { GROUP_CHIPS, queryChips, queryInWords, removeChip } from './qbWords';

// The query builder, rebuilt for the phone (QUERY_BUILDER_PLAN.md, signed off 5 Nov 2026). The question is the way in:
// a plain-English bar, then the answer (a sentence, the chart that fits, the rows), the query as editable chips,
// group-by chips and a follow-up box that refines the current query. Filters live in a bottom sheet. The query itself,
// its API (/query/deliveries) and its shareable URL are the old page's, so old links still open.

const SKIP_DEFAULTS = { limit: 1000, offset: 0, include_international: false, show_summary_rows: false, query_mode: 'delivery' };
const RECENT_KEY = 'hindsight.qb.recent';

/** The URL for a query: its filters (defaults left out), group-by and the question that made it. */
const toSearch = (filters, groupBy, q, m, fmtSlug = null) => {
  const p = new URLSearchParams();
  Object.entries(filters || {}).forEach(([k, v]) => {
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) return;
    if (k in SKIP_DEFAULTS && v === SKIP_DEFAULTS[k]) return;
    if (Array.isArray(v)) v.forEach((x) => p.append(k, x)); else p.append(k, v);
  });
  (groupBy || []).forEach((g) => p.append('group_by', g));
  if (q) p.set('q', q);
  if (m) p.set('m', m);
  // ODI links carry their format (App.js applies ?fmt=), so a shared ODI answer opens in ODIs.
  if (fmtSlug && fmtSlug !== 'mens-t20') p.set('fmt', fmtSlug);
  return `?${p.toString()}`;
};

const hasQuery = (filters, groupBy) => (groupBy || []).length > 0 || Object.entries(filters || {}).some(([k, v]) => (
  !(k in SKIP_DEFAULTS) && k !== 'top_teams' && v != null && v !== '' && v !== false && !(Array.isArray(v) && !v.length)));

const readRecent = () => { try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch { return []; } };
const saveRecent = (q, search) => {
  try {
    const list = [{ q, search, at: Date.now() }, ...readRecent().filter((r) => r.q !== q)].slice(0, 6);
    localStorage.setItem(RECENT_KEY, JSON.stringify(list));
  } catch { /* storage off */ }
};
const ago = (t) => {
  const d = Math.floor((Date.now() - t) / 86400000);
  return d <= 0 ? 'today' : d === 1 ? 'yesterday' : `${d} days ago`;
};

const Chip = ({ children, onClick, onRemove, tone = 'set' }) => (
  <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, borderRadius: '999px', fontSize: 13.5,
    border: `1px ${tone === 'add' ? 'dashed' : 'solid'} ${tone === 'suggest' ? 'rgba(182,242,74,0.45)' : tone === 'add' ? colors.accent : colors.borderStrong}`,
    bgcolor: tone === 'set' ? colors.surface2 : 'transparent', color: tone === 'set' ? colors.textHi : colors.accent }}>
    <Box component="button" type="button" onClick={onClick}
      sx={{ all: 'unset', cursor: 'pointer', pl: 1.25, pr: onRemove ? 0.25 : 1.25, py: 0.5, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
      {children}
    </Box>
    {onRemove && (
      <Box component="button" type="button" aria-label={`Remove ${children}`} onClick={onRemove}
        sx={{ all: 'unset', cursor: 'pointer', display: 'inline-flex', pr: 0.75, color: colors.textLo, '&:hover': { color: colors.textHi } }}>
        <CloseRoundedIcon sx={{ fontSize: 15 }} />
      </Box>
    )}
  </Box>
);

const Eyebrow = ({ children }) => (
  <Box sx={{ fontFamily: fonts.mono, fontSize: 10.5, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.textLo }}>{children}</Box>
);

const QueryPage = ({ isMobile }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { formats, active, selectFormat, formatParams } = useFormat();
  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const filters = useMemo(() => parseUrlParams(location.search), [location.search]);
  const groupBy = useMemo(() => params.getAll('group_by'), [params]);
  const question = params.get('q') || '';
  const measure = params.get('m');
  const live = hasQuery(filters, groupBy);

  const [text, setText] = useState(question);
  const [follow, setFollow] = useState('');
  const [parsing, setParsing] = useState(null);   // 'ask' | 'follow'
  const [parseError, setParseError] = useState(null);
  const [run, setRun] = useState({ status: 'idle', data: null, qs: '' });
  const [options, setOptions] = useState(null);
  const [sheet, setSheet] = useState({ open: false, focus: null });
  const [suggest, setSuggest] = useState([]);
  const [recent, setRecent] = useState(readRecent);
  const nlRef = useRef(null);
  useEffect(() => { setText(question); }, [question]);
  useEffect(() => { document.title = 'Query · Hindsight'; }, []);

  // One format at a time: "All formats" mixes T20s and ODIs and reads wrong, so the page pins T20 unless ODI is chosen.
  const fmt = formatParams.format === 'ODI' ? 'ODI' : 'T20';
  useEffect(() => {
    if (formatParams.format !== 'T20' && formatParams.format !== 'ODI') selectFormat('mens-t20');
  }, [formatParams.format, selectFormat]);
  const slugFor = (f) => (formats || []).find((x) => x.format === f && (x.gender || 'male') === 'male')?.slug || (f === 'ODI' ? 'mens-odi' : 'mens-t20');
  const setFmt = (f) => {
    const slug = slugFor(f);
    if (slug !== active?.slug) selectFormat(slug);
  };

  // The filter sheet's options (players, teams, venues, lines, lengths...).
  useEffect(() => {
    let cancelled = false;
    fetch(`${config.API_URL}/query/deliveries/columns?format=${fmt}`).then((r) => r.json())
      .then((d) => { if (!cancelled) setOptions(d); }).catch(() => {});
    return () => { cancelled = true; };
  }, [fmt]);

  // Suggestions about the next fixture, in its format and our data's names (GET /query-suggestions).
  useEffect(() => {
    fetch(`${config.API_URL}/query-suggestions`).then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.items?.length) setSuggest(d); }).catch(() => {});
  }, []);

  // Run the query whenever the URL holds one.
  useEffect(() => {
    if (!live) { setRun({ status: 'idle', data: null, qs: '' }); return undefined; }
    let cancelled = false;
    const p = new URLSearchParams({ format: fmt, gender: 'male' });
    Object.entries(filters).forEach(([k, v]) => {
      if (v == null || v === '' || (Array.isArray(v) && !v.length)) return;
      if (k === 'query_mode' && v === 'delivery') return;
      if (fmt === 'ODI' && (k === 'include_international' || k === 'top_teams')) return;
      if (k === 'top_teams' && !filters.include_international) return;
      if (Array.isArray(v)) v.forEach((x) => p.append(k, x)); else p.append(k, v);
    });
    groupBy.forEach((g) => p.append('group_by', g));
    if (nlRef.current) p.set('nl_ref', nlRef.current);
    const qs = p.toString();
    setRun({ status: 'loading', data: null, qs });
    track('query_run', { group_by: groupBy.join(',') });
    axios.get(`${config.API_URL}/query/deliveries?${qs}`)
      .then((r) => { if (!cancelled) setRun({ status: 'ready', data: r.data, qs }); })
      .catch((e) => {
        if (cancelled) return;
        const d = e.response?.data?.detail;
        setRun({ status: 'error', data: null, qs, error: typeof d === 'string' ? d : 'The query could not run. Try removing a filter.' });
      });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, fmt]);

  const go = useCallback((f, g, q, m = null, f2 = null) => {
    const search = toSearch(f, g, q, m, slugFor(f2 || fmt));
    navigate({ search }, { replace: false });
    if (q) { saveRecent(q, search); setRecent(readRecent()); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate, fmt, formats]);

  // Plain English to a query; a follow-up sends the current query along as its context.
  const ask = async (q, mode = 'ask', fmtOverride = null) => {
    const t = (q || '').trim();
    if (!t || parsing) return;
    setParsing(mode);
    setParseError(null);
    track('nl_search', { follow_up: mode === 'follow' });
    try {
      const body = { query: t, format: fmtOverride || fmt };
      if (mode === 'follow') body.context = [question, queryInWords(filters, groupBy)].filter(Boolean).join(' — ');
      const { data } = await axios.post(`${config.API_URL}/nl2query/parse`, body);
      if (!data.success) { setParseError(data.error || "That question didn't parse. Try rephrasing it."); return; }
      if (data.format === 'ODI' || data.format === 'T20') setFmt(data.format);
      nlRef.current = data.log_ref || null;
      const merged = { ...parseUrlParams(''), ...data.filters };
      const label = mode === 'follow' ? `${question || queryInWords(filters, groupBy)} … ${t}` : t;
      setFollow('');
      // The measure the question asks about, when it names one ("most wickets"); otherwise the page's default.
      const yAxis = data.recommended_chart?.y_axis;
      const runFmt = data.format === 'ODI' || data.format === 'T20' ? data.format : (fmtOverride || fmt);
      go(merged, data.group_by || [], label, ASKABLE.includes(yAxis) ? yAxis : null, runFmt);
    } catch (e) {
      const d = e.response?.data?.detail;
      setParseError(typeof d === 'string' ? d : "That question didn't parse. Try again in a moment.");
    } finally {
      setParsing(null);
    }
  };

  // /query?nl=… (site search, the home page): ask that question straight away.
  const nlParam = params.get('nl');
  const askedNl = useRef(null);
  useEffect(() => {
    if (nlParam && askedNl.current !== nlParam) {
      askedNl.current = nlParam;
      setText(nlParam);
      ask(nlParam);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nlParam]);

  const chips = queryChips(filters, groupBy);
  // A scoring wheel needs the batter's hand to draw the field the right way round: for one named batter, ask the
  // query builder (one row by batting hand).
  const [hand, setHand] = useState(null);
  const oneBatter = (filters.batters || []).length === 1 ? filters.batters[0] : null;
  const wantsHand = groupBy.includes('wagon_zone') && oneBatter;
  useEffect(() => {
    setHand(null);
    if (!wantsHand) return;
    const p = new URLSearchParams({ format: fmt, batters: oneBatter, group_by: 'bat_hand' });
    axios.get(`${config.API_URL}/query/deliveries?${p}`)
      .then((r) => {
        const rows = (r.data?.data || []).filter((x) => x.bat_hand === 'LHB' || x.bat_hand === 'RHB').sort((a, b) => b.balls - a.balls);
        if (rows[0]) setHand(rows[0].bat_hand);
      }).catch(() => {});
  }, [wantsHand, oneBatter, fmt]);
  const answer = useMemo(() => (run.status === 'ready' ? shapeAnswer(run.data?.data, filters, groupBy, measure, hand) : null), [run, filters, groupBy, measure, hand]);
  const groupKey = groupBy.join(',');

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto', px: 2, pt: 1.5, pb: 3, display: 'flex', flexDirection: 'column', gap: 1.5, color: colors.textHi }}>
      {!live && <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 27, lineHeight: 1.1 }}>Ask the ball-by-ball data</Box>}

      <Box component="form" onSubmit={(e) => { e.preventDefault(); ask(text); }}
        sx={{ display: 'flex', alignItems: 'center', gap: 1, border: `1.5px solid ${colors.accent}`, borderRadius: '16px', bgcolor: colors.surface1, pl: 1.5, pr: 1, py: 0.75 }}>
        {parsing === 'ask' ? <CircularProgress size={18} sx={{ color: colors.accent }} /> : <SearchRoundedIcon sx={{ color: colors.accent }} />}
        <Box component="input" value={text} onChange={(e) => setText(e.target.value)} aria-label="Ask a question"
          placeholder="Ask anything about any ball"
          sx={{ all: 'unset', flex: 1, minWidth: 0, fontSize: 15.5, py: 0.75, color: colors.textHi, '&::placeholder': { color: colors.textLo } }} />
        <Box role="tablist" aria-label="Format" sx={{ display: 'inline-flex', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px', flexShrink: 0 }}>
          {['T20', 'ODI'].map((f) => (
            <Box key={f} component="button" type="button" role="tab" aria-selected={f === fmt} onClick={() => setFmt(f)}
              sx={{ all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 12.5, px: 1.1, py: '2px', borderRadius: '999px',
                bgcolor: f === fmt ? colors.accent : 'transparent', color: f === fmt ? colors.bg : colors.textLo }}>{f}</Box>
          ))}
        </Box>
      </Box>
      {parseError && <Box sx={{ color: colors.red, fontSize: 13.5 }}>{parseError}</Box>}

      {live && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
          {chips.map((c) => (
            <Chip key={`${c.key}-${c.value ?? ''}`} onClick={() => setSheet({ open: true, focus: c.key === 'dates' ? 'dates' : c.key })}
              onRemove={() => { const n = removeChip(filters, groupBy, c); go(n.filters, n.groupBy, question, measure); }}>
              {c.label}
            </Chip>
          ))}
          <Chip tone="add" onClick={() => setSheet({ open: true, focus: null })}>+ Add filter</Chip>
        </Box>
      )}

      {!live && (
        <>
          {suggest.items?.length > 0 && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
              <Eyebrow>{suggest.label}</Eyebrow>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                {suggest.items.map((s) => <Chip key={s} tone="suggest" onClick={() => { if (suggest.format) setFmt(suggest.format); setText(s); ask(s, 'ask', suggest.format); }}>{s}</Chip>)}
              </Box>
            </Box>
          )}
          {recent.length > 0 && (
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
              <Eyebrow>Your recent</Eyebrow>
              {recent.map((r) => (
                <Box key={r.q} component="button" type="button" onClick={() => navigate({ search: r.search })}
                  sx={{ all: 'unset', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', gap: 1, py: 1, borderBottom: `1px solid ${colors.border}`, fontSize: 14.5 }}>
                  <Box component="span" sx={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.q}</Box>
                  <Box component="span" sx={{ color: colors.textLo, fontSize: 12, whiteSpace: 'nowrap' }}>{ago(r.at)}</Box>
                </Box>
              ))}
            </Box>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            <Eyebrow>Or build one</Eyebrow>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              <Chip tone="add" onClick={() => setSheet({ open: true, focus: 'batters' })}>+ Add filter</Chip>
            </Box>
          </Box>
        </>
      )}

      {live && run.status === 'loading' && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, color: colors.textLo, fontSize: 14, py: 3, justifyContent: 'center' }}>
          <CircularProgress size={20} sx={{ color: colors.accent }} /> Counting every ball…
        </Box>
      )}
      {live && run.status === 'error' && <Box sx={{ color: colors.red, fontSize: 14 }}>{run.error}</Box>}
      {live && answer && (
        <AnswerCard answer={answer} results={run.data} filters={filters} groupBy={groupBy} isMobile={isMobile}
          apiQueryString={run.qs} autoGraphic={params.get('graphic') === '1'} />
      )}

      {live && run.status === 'ready' && (
        <>
          <Box component="form" onSubmit={(e) => { e.preventDefault(); ask(follow, 'follow'); }}
            sx={{ display: 'flex', alignItems: 'center', gap: 1, border: `1px dashed ${colors.borderStrong}`, borderRadius: '14px', px: 1.5, py: 0.5 }}>
            <Box component="input" value={follow} onChange={(e) => setFollow(e.target.value)} aria-label="Refine this answer"
              placeholder="…and in the powerplay? only since 2024?"
              sx={{ all: 'unset', flex: 1, minWidth: 0, fontSize: 14.5, py: 0.9, color: colors.textHi, '&::placeholder': { color: colors.textLo } }} />
            <Box component="button" type="submit" disabled={!follow.trim() || Boolean(parsing)}
              sx={{ all: 'unset', cursor: 'pointer', color: follow.trim() ? colors.accent : colors.textLo, fontWeight: 600, fontSize: 14 }}>
              {parsing === 'follow' ? <CircularProgress size={16} sx={{ color: colors.accent }} /> : 'Ask'}
            </Box>
          </Box>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {GROUP_CHIPS.map(([label, g]) => {
              const on = g.join(',') === groupKey;
              return (
                <Box key={label} component="button" type="button" onClick={() => go(filters, on ? [] : g, question, measure)}
                  sx={{ all: 'unset', cursor: 'pointer', border: `1px solid ${on ? colors.accent : colors.borderStrong}`, color: on ? colors.accent : colors.textMed,
                    borderRadius: '10px', px: 1.25, py: 0.6, fontSize: 13, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>{label}</Box>
              );
            })}
          </Box>
        </>
      )}

      <PageFooter />
      <FilterSheet open={sheet.open} focus={sheet.focus} onClose={() => setSheet({ open: false, focus: null })}
        filters={filters} groupBy={groupBy} options={options} onApply={(f, g) => go(f, g, question, measure)} />
    </Box>
  );
};

export default QueryPage;
