import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, Skeleton, TextField } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import config from '../config';
import { rememberEntity } from '../utils/recentEntities';
import { colors, fonts } from '../theme/hindsightDark';
import VerdictScreen, { windowQuery } from './playerProfile/verdict/VerdictScreen';
import PlaysLikeCard from './playerProfile/cards/PlaysLikeCard';
import ProfileFilters from './playerProfile/cards/ProfileFilters';
import { RoleCardSet } from './playerProfile/cards/RoleCards';
import AuctionCard from './playerProfile/cards/AuctionCard';

// The player profile, simplified (PROFILE_SIMPLIFY_PLAN.md, agreed 3 Nov 2026): the verdict, who he plays like, then
// four cards for his role (both sets for an all-rounder, main role first, with a switch). One window and scope for
// the whole page, set by the verdict's pills and the filters icon and kept in the address bar, so a shared link opens
// the same view. Each card fits one phone screenshot and shares on its own; the data credit sits once at the foot.
// Every other section of the old page was removed: the query builder and the connector still reach that data.

const DEFAULT_WINDOW = { fmt: 'T20', period: 'recent', scope: 'strong', start: null, end: null };

const readWindow = (search) => {
  const q = new URLSearchParams(search);
  const fmt = q.get('format') === 'ODI' ? 'ODI' : 'T20';
  const start = q.get('start_date'); const end = q.get('end_date');
  const period = start ? 'custom' : q.get('period') === 'career' ? 'career' : 'recent';
  return { fmt, period, scope: q.get('scope') === 'all' ? 'all' : 'strong', start: start || null, end: end || null };
};

const writeSearch = (name, w) => {
  const q = new URLSearchParams({ name });
  if (w.fmt !== 'T20') q.set('format', w.fmt);
  if (w.period === 'career') q.set('period', 'career');
  if (w.period === 'custom') {
    if (w.start) q.set('start_date', w.start);
    if (w.end) q.set('end_date', w.end);
  }
  if (w.scope !== 'strong') q.set('scope', w.scope);
  return `?${q.toString()}`;
};

/** The role cards' numbers for the page's window (GET /player/{name}/cards); a busy server is retried twice. */
const useCards = (player, win) => {
  const query = windowQuery(win);
  const [state, setState] = useState({ status: 'loading', data: null });
  useEffect(() => {
    if (!player) return undefined;
    let cancelled = false;
    let timer = null;
    setState({ status: 'loading', data: null });
    const load = (attempt) => {
      fetch(`${config.API_URL}/player/${encodeURIComponent(player)}/cards?${query}`)
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
        .catch((e) => {
          if (cancelled) return;
          if (e === 503 && attempt < 2) timer = setTimeout(() => load(attempt + 1), 8000);
          else setState({ status: e === 404 ? 'empty' : 'error', data: null });
        });
    };
    load(0);
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [player, query]);
  return state;
};

const RoleSwitch = ({ order, value, onChange }) => (
  <Box role="tablist" aria-label="Cards first" sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
    {order.map((r) => (
      <Box key={r} component="button" type="button" role="tab" aria-selected={r === value} onClick={() => onChange(r)}
        sx={{
          all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 700, fontSize: 14, px: 1.75, minHeight: 32, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', borderRadius: '999px',
          bgcolor: r === value ? colors.accent : 'transparent', color: r === value ? colors.bg : colors.textMed,
          '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
        }}>
        {r === 'bat' ? 'Batting' : 'Bowling'}
      </Box>
    ))}
  </Box>
);

const PlayerPicker = () => {
  const navigate = useNavigate();
  const [players, setPlayers] = useState([]);
  useEffect(() => {
    fetch(`${config.API_URL}/players`).then((r) => r.json()).then(setPlayers).catch(() => setPlayers([]));
  }, []);
  return (
    <Box sx={{ px: 2, pt: 3, display: 'flex', flexDirection: 'column', gap: 1.5, maxWidth: 520, mx: 'auto', color: colors.textHi }}>
      <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 28 }}>Player profile</Box>
      <Box sx={{ color: colors.textLo, fontSize: 14 }}>Is the hype fair? Pick a player.</Box>
      <Autocomplete options={players} onChange={(_, v) => v && navigate(`/player?name=${encodeURIComponent(v)}`)}
        renderInput={(params) => <TextField {...params} label="Player" autoFocus />} />
    </Box>
  );
};

const UnifiedPlayerProfile = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const name = new URLSearchParams(location.search).get('name');
  const [win, setWin] = useState(() => readWindow(location.search));
  const [summary, setSummary] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [first, setFirst] = useState(null);

  // A new player (search, a twin's link) starts from the address bar's window.
  useEffect(() => { setWin(readWindow(location.search)); setSummary(null); setFirst(null); }, [name]); // eslint-disable-line react-hooks/exhaustive-deps

  const changeWindow = useCallback((patch) => {
    setWin((w) => {
      const next = { ...w, ...patch };
      if (patch.period && patch.period !== 'custom') { next.start = null; next.end = null; }
      navigate({ search: writeSearch(name, next), hash: '' }, { replace: true });
      return next;
    });
  }, [name, navigate]);

  useEffect(() => { if (name) { document.title = `${name} · Hindsight`; rememberEntity('player', name); } }, [name]);

  const cards = useCards(name, win);
  const onSummary = useCallback((s) => setSummary(s), []);

  // The roles the verdict shows: the main one, plus the other for an all-rounder.
  const order = useMemo(() => {
    if (!summary) return [];
    const roles = Object.keys(summary.roles || {});
    const main = summary.primary_role;
    const other = roles.find((r) => r !== main);
    return summary.allrounder && other ? [main, other] : [main];
  }, [summary]);
  const lead = first && order.includes(first) ? first : order[0];
  const shown = lead ? [lead, ...order.filter((r) => r !== lead)] : [];

  // A shared card link (#pitch, #start...) scrolls to its card once the cards are drawn.
  useEffect(() => {
    if (cards.status !== 'ready' || !location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: 'start' });
  }, [cards.status, location.hash]);

  if (!name) return <PlayerPicker />;

  const qb = `/query?batters=${encodeURIComponent(name)}`;
  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', pb: 3, color: colors.textHi }}>
      <VerdictScreen key={name} player={name} win={win} onWindow={changeWindow} onFilters={() => setFiltersOpen(true)} onSummary={onSummary} />

      <Box sx={{ px: 2, display: 'flex', flexDirection: 'column', gap: 1.75 }}>
        {win.fmt === 'T20' && <PlaysLikeCard player={name} unit={win.period === 'career' ? 'career' : 'window'} />}

        {shown.length > 1 && <RoleSwitch order={order} value={lead} onChange={setFirst} />}
        {cards.status === 'loading' && summary && (
          <>
            <Skeleton variant="rounded" height={240} sx={{ bgcolor: colors.surface2, borderRadius: '18px' }} />
            <Skeleton variant="rounded" height={200} sx={{ bgcolor: colors.surface2, borderRadius: '18px' }} />
          </>
        )}
        {cards.status === 'ready' && shown.map((role) => (
          <RoleCardSet key={role} role={role} player={name} data={cards.data.roles[role]} hand={summary?.identity?.bat_hand} query={windowQuery(win)} />
        ))}
        <AuctionCard player={name} />
        {cards.status === 'error' && (
          <Box sx={{ color: colors.textLo, fontSize: 13.5 }}>The detailed cards couldn't load just now. Try again shortly.</Box>
        )}

        <Box component={Link} to={qb} sx={{ textAlign: 'center', color: colors.accent, fontSize: 14, textDecoration: 'none', pt: 1, whiteSpace: 'nowrap', minHeight: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          Dig deeper in the query builder →
        </Box>
        <Box sx={{ borderTop: `1px solid ${colors.border}`, pt: 1.5, textAlign: 'center', fontSize: 11.5, color: colors.textLo, lineHeight: 1.6 }}>
          <Box sx={{ whiteSpace: 'nowrap' }}>Data: Himanish Ganjoo &amp; TechRadar, Cricsheet</Box>
          <Box sx={{ whiteSpace: 'nowrap' }}>Metrics: Himanish Ganjoo&apos;s T20 Primer</Box>
        </Box>
      </Box>

      <ProfileFilters open={filtersOpen} onClose={() => setFiltersOpen(false)} value={win} onApply={(w) => changeWindow(w)} />
    </Box>
  );
};

export default UnifiedPlayerProfile;
