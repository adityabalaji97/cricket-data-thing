import React, { useEffect, useMemo, useState } from 'react';
import { Box, Drawer } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import OverseasMark from '../common/OverseasMark';
import OutsideIplTag from '../common/OutsideIplTag';
import { limitsState, score } from '../../utils/xiEngine';
import { Eyebrow } from '../pageKit/pageKit';
import XITab from './XITab';

// Fix my team (XI_BUILDER_PLAN.md X6): an IPL squad against the winners' template, role by role. Tap a role to see
// who holds it and who in the auction pool could; add a player or put him in "instead of" a holder (a pin); drop
// players. Scored in the browser (src/utils/xiEngine.js, the server's rules). Over the purse or a limit it still scores,
// but Save stays off (the agreed rule). Description, not prediction: "roles at playoff level".

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const STATUS = { 'playoff level': { label: 'Playoff level', c: colors.accent }, short: { label: 'Short', c: '#f0b429' },
  gap: { label: 'Gap', c: colors.red } };
const FMT = { average: (v) => v.toFixed(1), strike_rate: (v) => v.toFixed(0), wickets_per_24: (v) => v.toFixed(2),
  economy: (v) => v.toFixed(2), regular_bowlers: (v) => v.toFixed(0) };
const UNIT = { average: 'avg', strike_rate: 'SR', wickets_per_24: 'wkts / 4 ov', economy: 'an over', regular_bowlers: 'bowlers' };
const crore = (v) => (v >= 1 ? `₹${v.toFixed(2).replace(/\.00$/, '')} cr` : `₹${Math.round(v * 100)} L`);

const enc = (names) => names.map(encodeURIComponent).join('~');
const dec = (s) => (s ? s.split('~').map(decodeURIComponent).filter(Boolean) : []);

const Pill = ({ status }) => (
  <Box component="span" sx={{ ...mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: STATUS[status].c }}>
    {STATUS[status].label}
  </Box>
);

const XIBuilderPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const q = new URLSearchParams(location.search);
  const team = q.get('team');
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState(null);  // role key whose sheet is open
  // The reader's changes live in the URL, so a built squad is a link: added, dropped, and pins (role:name).
  const added = useMemo(() => dec(q.get('add')), [location.search]); // eslint-disable-line react-hooks/exhaustive-deps
  const dropped = useMemo(() => dec(q.get('drop')), [location.search]); // eslint-disable-line react-hooks/exhaustive-deps
  const pins = useMemo(() => dec(q.get('pin')).reduce((o, s) => {
    const [k, n] = s.split(':'); (o[k] = o[k] || []).push(n); return o;
  }, {}), [location.search]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!team) return undefined;
    let cancelled = false;
    fetch(`${config.API_URL}/xi-builder?team=${encodeURIComponent(team)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [team]);

  // Every other parameter (the tab, the XI) is kept when the squad changes.
  const setParams = (obj) => {
    const p = new URLSearchParams(location.search);
    Object.entries(obj).forEach(([k, v]) => { if (v) p.set(k, v); else p.delete(k); });
    navigate({ search: `?${p.toString()}` }, { replace: true });
  };
  const set = (patch) => {
    const next = { add: added, drop: dropped, pin: Object.entries(pins).flatMap(([k, ns]) => ns.map((n) => `${k}:${n}`)), ...patch };
    setParams({ add: next.add.length ? enc(next.add) : '', drop: next.drop.length ? enc(next.drop) : '',
      pin: next.pin.length ? enc(next.pin) : '' });
  };
  const tab = q.get('tab') === 'xi' ? 'xi' : 'squad';

  const squad = useMemo(() => {
    if (!data) return [];
    const byName = Object.fromEntries([...data.squad, ...data.pool].map((p) => [p.name, p]));
    return [...data.squad.filter((p) => !dropped.includes(p.name)), ...added.map((n) => byName[n]).filter(Boolean)];
  }, [data, added, dropped]);
  const base = useMemo(() => (data ? score(data.squad, data.roles, data.bench) : null), [data]);
  const now = useMemo(() => (data ? score(squad, data.roles, data.bench, pins) : null), [data, squad, pins]);
  const lim = useMemo(() => (data ? limitsState(squad, data.limits) : null), [data, squad]);

  if (!team) return <Box sx={{ p: 2, color: colors.textLo }}>Pick a team from its page: "Fix my team".</Box>;
  if (error) return <Box sx={{ p: 2, color: colors.textLo }}>This builder couldn't load just now. Try again shortly.</Box>;
  if (!data) return <Box sx={{ p: 2, color: colors.textLo }}>Loading the squad…</Box>;

  const role = open && data.roles.find((r) => r.key === open);
  const row = open && now.roles.find((r) => r.key === open);
  const inSquad = new Set(squad.map((p) => p.name));
  const changed = added.length + dropped.length + Object.keys(pins).length > 0;
  // The XI tab shares the XI (its own card, api/og.mjs xiTabCard): shareable once there's an XI in the link (or the
  // squad changed), and not with more than four overseas in the twelve.
  const xiNames = dec(q.get('xi'));
  const xiOverseas = xiNames.filter((n) => squad.find((p) => p.name === n)?.overseas).length;
  const share = tab === 'xi'
    ? { ok: lim?.can_save && xiOverseas <= 4 && (changed || xiNames.length === 12),
      label: !lim?.can_save ? lim?.problems[0] : xiOverseas > 4 ? 'More than four overseas in the XI' : 'Share this XI',
      title: `${data?.team}'s XI` }
    : { ok: lim?.can_save && changed, label: lim?.can_save ? 'Share this squad' : lim?.problems[0], title: `${data?.team}, rebuilt` };
  const fmt = (r, v) => (v == null ? '–' : FMT[r.measure](v));

  const addPlayer = (name, instead) => {
    const add = added.includes(name) || inSquad.has(name) ? added : [...added, name];
    const pinList = Object.entries(pins).flatMap(([k, ns]) => ns.map((n) => `${k}:${n}`)).filter((s) => !s.startsWith(`${open}:`) || !instead);
    const pin = instead ? [...pinList, `${open}:${name}`, ...(row.holders.filter((h) => h !== instead).map((h) => `${open}:${h}`))] : pinList;
    set({ add, pin });
  };
  const dropPlayer = (name) => (added.includes(name) ? set({ add: added.filter((n) => n !== name) }) : set({ drop: [...dropped, name] }));

  // Who could hold the open role: the squad's other players with balls in it, then the auction pool.
  const cands = open && role.side !== 'depth'
    ? [...squad, ...data.pool.filter((p) => !inSquad.has(p.name))]
      .filter((p) => p.roles[open] && p.roles[open].balls >= 60 && !row.holders.includes(p.name))
      .map((p) => {
        const t = p.roles[open];
        const v = role.measure === 'average' ? (t.wickets ? t.runs / t.wickets : null) : role.measure === 'strike_rate'
          ? (100 * t.runs) / t.balls : role.measure === 'wickets_per_24' ? (24 * t.wickets) / t.balls : (6 * t.runs) / t.balls;
        return { ...p, v, inSquad: inSquad.has(p.name) };
      })
      .filter((p) => p.v != null)
      .sort((a, b) => (role.lower ? a.v - b.v : b.v - a.v))
      .slice(0, 12)
    : [];

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pb: 12, pt: 1.5, color: colors.textHi, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box>
        <Box component={Link} to={`/team?team=${encodeURIComponent(data.team)}`} sx={{ color: colors.textLo, fontSize: 13, textDecoration: 'none' }}>← {data.team}</Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26, mt: 0.5 }}>Fix my team</Box>
        <Box sx={{ color: colors.textMed, fontSize: 13.5 }}>Swap players in and watch each role against what IPL playoff sides had.</Box>
      </Box>

      {tab === 'squad' && <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {[[`${now.at_level} of ${now.of}`, 'roles at playoff level', base.at_level !== now.at_level ? `was ${base.at_level}` : null],
          [crore(Math.abs(lim.left)), lim.left >= 0 ? 'left in the purse' : 'over the purse', null],
          [`${lim.overseas}/${data.limits.overseas_max}`, 'overseas', null], [`${lim.size}`, 'players', null]].map(([v, l, was]) => {
          const bad = (l === 'over the purse') || (l === 'overseas' && lim.overseas > data.limits.overseas_max)
            || (l === 'players' && (lim.size > data.limits.squad_max || lim.size < data.limits.squad_min));
          return (
          <Box key={l} sx={{ flex: '1 1 40%', bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.5, py: 1 }}>
            <Box sx={{ ...mono, fontSize: 20, color: bad ? colors.red : colors.textHi }}>{v}</Box>
            <Box sx={{ fontSize: 11.5, color: colors.textLo, whiteSpace: 'nowrap' }}>{l.startsWith('overseas') ? <OverseasMark size={11} sx={{ ml: 0, mr: 0.4, color: colors.textLo, verticalAlign: '-1px' }} /> : null}{l}{was ? ` · ${was}` : ''}</Box>
          </Box>
          );
        })}
      </Box>}

      <Box role="tablist" aria-label="View" sx={{ display: 'flex', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '3px' }}>
        {[['squad', 'Squad'], ['xi', 'XI']].map(([k, l]) => (
          <Box key={k} component="button" type="button" role="tab" aria-selected={tab === k} onClick={() => setParams({ tab: k === 'xi' ? 'xi' : '' })}
            sx={{ all: 'unset', cursor: 'pointer', flex: 1, textAlign: 'center', py: 0.6, borderRadius: '999px', fontFamily: fonts.display, fontWeight: 600,
              bgcolor: tab === k ? colors.accent : 'transparent', color: tab === k ? colors.bg : colors.textMed }}>{l}</Box>
        ))}
      </Box>

      {tab === 'xi' && <XITab data={data} squad={squad} q={q} setParams={setParams} RoleRows={({ rows }) => rows.map((r) => {
        const rr = data.roles.find((x) => x.key === r.key);
        return (
          <Box key={r.key} sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.75, py: 1.1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
              <Box sx={{ fontWeight: 600, fontSize: 15, whiteSpace: 'nowrap' }}>{r.label}</Box>
              <Pill status={r.status} />
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, mt: 0.25 }}>
              <Box sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {r.holders.length ? r.holders.join(', ') : 'nobody in the XI does it'}
              </Box>
              <Box sx={{ ...mono, fontSize: 12.5, whiteSpace: 'nowrap', color: colors.textMed }}>{`${fmt(rr, r.value)} · playoff ${fmt(rr, r.playoff)}`}</Box>
            </Box>
          </Box>
        );
      })} />}

      {tab === 'squad' && <Eyebrow>Tap a role</Eyebrow>}
      {tab === 'squad' && now.roles.map((r) => {
        const rr = data.roles.find((x) => x.key === r.key);
        const before = base.roles.find((x) => x.key === r.key);
        return (
          <Box key={r.key} component="button" type="button" onClick={() => setOpen(r.key)}
            sx={{ all: 'unset', cursor: 'pointer', display: 'block', bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.75, py: 1.25 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 1 }}>
              <Box sx={{ fontWeight: 600, fontSize: 15, whiteSpace: 'nowrap' }}>{r.label}</Box>
              <Pill status={r.status} />
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, mt: 0.25 }}>
              <Box sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {r.holders.length ? r.holders.join(', ') : 'nobody in the squad has done it'}
              </Box>
              <Box sx={{ ...mono, fontSize: 12.5, whiteSpace: 'nowrap', color: colors.textMed }}>
                {`${fmt(rr, r.value)} · playoff ${fmt(rr, r.playoff)}`}
                {before.status !== r.status && <Box component="span" sx={{ color: colors.accent }}> ●</Box>}
              </Box>
            </Box>
          </Box>
        );
      })}

      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
        Players' IPL 2024-26 at any side · prices before the auction are last or base prices · a description, not a forecast
      </Box>

      <Box sx={{ position: 'fixed', left: 0, right: 0, bottom: 'calc(64px + env(safe-area-inset-bottom, 0px))', display: 'flex', justifyContent: 'center', px: 2, pointerEvents: 'none' }}>
        <Box sx={{ maxWidth: 560, width: '100%', display: 'flex', gap: 1, pointerEvents: 'auto', bgcolor: colors.bg, py: 1 }}>
          <Box component="button" type="button" disabled={!changed} onClick={() => set({ add: [], drop: [], pin: [] })}
            sx={{ all: 'unset', cursor: changed ? 'pointer' : 'default', flex: 1, textAlign: 'center', py: 1.1, borderRadius: '12px', border: `1px solid ${colors.borderStrong}`, color: changed ? colors.textHi : colors.textLo }}>
            Reset
          </Box>
          <Box component="button" type="button" disabled={!share.ok}
            onClick={() => {
              // The phone's share sheet where there is one; the link unfurls as this squad's or this XI's card (api/og.mjs).
              const url = window.location.href;
              if (navigator.share) navigator.share({ title: share.title, url }).catch(() => {});
              else navigator.clipboard?.writeText(url);
            }}
            sx={{ all: 'unset', cursor: share.ok ? 'pointer' : 'default', flex: 2, textAlign: 'center', py: 1.1, borderRadius: '12px',
              bgcolor: share.ok ? colors.accent : colors.surface2, color: share.ok ? colors.bg : colors.textLo, fontWeight: 600 }}>
            {share.label}
          </Box>
        </Box>
      </Box>

      <Drawer anchor="bottom" open={!!open} onClose={() => setOpen(null)}
        PaperProps={{ sx: { bgcolor: colors.bg, color: colors.textHi, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '80vh' } }}>
        {open && (
          <Box sx={{ maxWidth: 560, mx: 'auto', width: '100%', p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20 }}>{row.label}</Box>
              <Pill status={row.status} />
            </Box>
            <Box sx={{ ...mono, fontSize: 12.5, color: colors.textMed, mb: 1.5 }}>
              {`${fmt(role, row.value)} ${UNIT[role.measure]} · playoff sides ${fmt(role, row.playoff)}`}
            </Box>
            <Eyebrow>{role.side === 'depth' ? 'Regular bowlers' : 'Holding it'}</Eyebrow>
            {row.holders.map((h) => (
              <Box key={h} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.75 }}>
                <Box sx={{ fontSize: 14.5 }}>{h}</Box>
                <Box component="button" type="button" onClick={() => dropPlayer(h)}
                  sx={{ all: 'unset', cursor: 'pointer', fontSize: 12.5, color: colors.textLo }}>Drop from squad</Box>
              </Box>
            ))}
            {role.side !== 'depth' && (
              <>
                <Box sx={{ mt: 1.5 }}><Eyebrow>Could hold it</Eyebrow></Box>
                {cands.length === 0 && <Box sx={{ fontSize: 13.5, color: colors.textLo, py: 1 }}>Nobody else with 60+ balls in this role.</Box>}
                {cands.map((p) => (
                  <Box key={p.name} sx={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 1, alignItems: 'center', py: 0.75, borderTop: `1px solid ${colors.border}` }}>
                    <Box sx={{ minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                        <Box sx={{ fontSize: 14.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.name}</Box>
                        {p.overseas && <OverseasMark />}{p.outside && <OutsideIplTag />}
                      </Box>
                      <Box sx={{ fontSize: 11.5, color: colors.textLo, whiteSpace: 'nowrap' }}>
                        {`${FMT[role.measure](p.v)} ${UNIT[role.measure]} · ${p.roles[open].balls} balls · ${p.inSquad ? 'in the squad' : `auction pool · ${crore(p.price)}`}`}
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.75 }}>
                      {row.holders.length >= role.n ? (
                        <Box component="button" type="button" onClick={() => addPlayer(p.name, row.holders[row.holders.length - 1])}
                          sx={{ all: 'unset', cursor: 'pointer', fontSize: 12.5, px: 1.1, py: 0.5, borderRadius: '999px', border: `1px solid ${colors.accent}`, color: colors.accent, whiteSpace: 'nowrap' }}>
                          {`In for ${row.holders[row.holders.length - 1].split(' ').slice(-1)[0]}`}
                        </Box>
                      ) : (
                        <Box component="button" type="button" onClick={() => addPlayer(p.name, null)}
                          sx={{ all: 'unset', cursor: 'pointer', fontSize: 12.5, px: 1.1, py: 0.5, borderRadius: '999px', border: `1px solid ${colors.accent}`, color: colors.accent }}>
                          Add
                        </Box>
                      )}
                    </Box>
                  </Box>
                ))}
              </>
            )}
          </Box>
        )}
      </Drawer>
    </Box>
  );
};

export default XIBuilderPage;
