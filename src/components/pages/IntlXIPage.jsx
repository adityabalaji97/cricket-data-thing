import React, { useEffect, useState } from 'react';
import { Box, Drawer } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { colors, fonts } from '../../theme/hindsightDark';
import { PageFooter, PageSkeleton, usePageData } from '../pageKit/pageKit';
import PlayerLink from '../common/PlayerLink';

// Pick your XI for the top 10 T20I sides (XI_BUILDER_PLAN.md stage 3a; the India opener mockup, signed off 13 Nov 2026):
// the side's last T20I XI as eleven slots. Each slot: who has had it lately, what moved last match, the contenders ranked
// (batting by strike rate, bowling by economy) with four measures, and a case for and against each. Data:
// GET /intl-xi (services/intl_xi.py), built in the background when cold. /pick-xi?team=India&slot=2.

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const oneLine = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' };
const FLAG = '#f0b429';
// Names open the profile on the window the measures use: all T20s since Jan 2025, all opposition.
const XI_WINDOW = { start: '2025-01-01', scope: 'all' };
const GRID = '16px minmax(0, 1fr) 34px 36px 34px 34px';
const COLS = {
  bat: [['sr', 'SR', (v) => v.toFixed(0)], ['bnd', 'Bnd%', (v) => v.toFixed(1)], ['ctl', 'Ctrl%', (v) => v.toFixed(0)], ['bpd', 'BpD', (v) => v.toFixed(1)]],
  bowl: [['econ', 'Econ', (v) => v.toFixed(2)], ['dot', 'Dot%', (v) => v.toFixed(0)], ['false', 'False%', (v) => v.toFixed(0)], ['bpw', 'BpW', (v) => v.toFixed(1)]],
};
const BEST = { sr: 'max', bnd: 'max', ctl: 'max', bpd: 'max', econ: 'min', dot: 'max', false: 'max', bpw: 'min' };
const VERB = { openers: 'Opened', top: 'Batted at 3-4', middle: 'Batted at 5-7', 'powerplay|pace': 'Bowled in the powerplay',
  'middle|spin': 'Bowled in the middle overs', 'death|pace': 'Bowled at the death' };
const ROLE_HEAD = { openers: 'As an opener', top: 'At 3-4', middle: 'At 5-7' };
const head = (slot) => (slot.kind === 'bat' ? ROLE_HEAD[slot.role] : slot.label);

const Case = ({ c }) => (
  <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.6, py: 1.2, display: 'flex', flexDirection: 'column', gap: 0.6 }}>
    <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18, display: 'flex', alignItems: 'center', gap: 0.75 }}>
      <PlayerLink name={c.name} win={XI_WINDOW} />
      {c.holder && <Box component="span" sx={{ ...mono, fontSize: 10, border: `1px solid ${colors.accent}`, color: colors.accent, borderRadius: '4px', px: '4px' }}>In XI</Box>}
    </Box>
    <Box sx={{ fontSize: 13.5, color: colors.textMed }}><Box component="strong" sx={{ color: colors.textHi }}>For:</Box> {c.for}.</Box>
    <Box sx={{ fontSize: 13.5, color: colors.textMed }}><Box component="strong" sx={{ color: colors.textHi }}>Against:</Box> {c.against}.</Box>
  </Box>
);

const Slot = ({ data, slot }) => {
  const [open, setOpen] = useState(null);
  useEffect(() => { setOpen(null); }, [slot.n]);
  const cols = COLS[slot.kind] || [];
  const rows = slot.contenders || [];
  const best = Object.fromEntries(cols.map(([k]) => {
    const vals = rows.map((r) => r.m[k]).filter((v) => v != null);
    return [k, vals.length ? (BEST[k] === 'max' ? Math.max(...vals) : Math.min(...vals)) : null];
  }));
  const mine = (slot.had || []).find((h) => h.name === slot.holder);
  const sub = mine ? `${VERB[slot.role]} in ${mine.times} of the last ${data.recent} T20Is` : 'In the last XI';
  const shown = open ? rows.filter((r) => r.name === open) : rows.filter((r) => r.holder).concat(rows.filter((r) => !r.holder).slice(0, 2));
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.4 }}>
      <Box>
        <Box sx={{ ...mono, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.accent }}>{`Slot ${slot.n} · ${slot.label}`}</Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 24, lineHeight: 1.15, mt: 0.25 }}><PlayerLink name={slot.holder} win={XI_WINDOW} /></Box>
        <Box sx={{ fontSize: 13, color: colors.textMed, ...oneLine }}>{sub}</Box>
      </Box>
      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.5, py: 1.1 }}>
        <Box sx={{ fontSize: 11, color: colors.textLo, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          {`What moved · ${data.as_of ? new Date(data.as_of).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''} v ${data.last_opponent || ''}`}
        </Box>
        <Box sx={{ fontSize: 13.5, mt: 0.25, ...oneLine }}>{`${slot.holder}: ${slot.moved}`}</Box>
      </Box>

      {rows.length > 0 && (
        <Box role="table" aria-label="Contenders" sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.5, py: 0.5 }}>
          <Box role="row" sx={{ display: 'grid', gridTemplateColumns: GRID, gap: 0.75, fontSize: 11, color: colors.textLo, py: 0.75 }}>
            <span />
            <span>{head(slot)}</span>
            {cols.map(([, l]) => <Box component="span" key={l} sx={{ textAlign: 'right' }}>{l}</Box>)}
          </Box>
          {rows.map((r, i) => (
            <Box key={r.name} role="row" component="button" type="button" onClick={() => setOpen(open === r.name ? null : r.name)}
              sx={{ all: 'unset', boxSizing: 'border-box', cursor: 'pointer', width: '100%', display: 'grid', gridTemplateColumns: GRID,
                gap: 0.75, alignItems: 'center', py: 0.9, minHeight: 44, borderTop: `1px solid ${colors.border}`,
                bgcolor: open === r.name ? colors.surface2 : 'transparent', '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
              <Box sx={{ ...mono, fontSize: 11, color: colors.textLo }}>{i + 1}</Box>
              <Box sx={{ minWidth: 0 }}>
                <Box sx={{ fontSize: 13.5, fontWeight: 500, ...oneLine }}>{r.name}</Box>
                <Box sx={{ fontSize: 11, color: colors.textLo, ...oneLine }}>
                  {r.holder && <Box component="span" sx={{ color: colors.accent, fontWeight: 600 }}>In XI · </Box>}
                  {`${r.balls.toLocaleString()} balls`}
                  {r.small && <Box component="span" sx={{ color: FLAG }}> · small</Box>}
                  {!r.capped && ` · ${(data.home_leagues || [])[0] || 'league'}`}
                </Box>
              </Box>
              {cols.map(([k, , f]) => (
                <Box key={k} sx={{ ...mono, fontSize: 12.5, textAlign: 'right', color: r.m[k] != null && r.m[k] === best[k] ? colors.accent : colors.textHi }}>
                  {r.m[k] == null ? '–' : f(r.m[k])}
                </Box>
              ))}
            </Box>
          ))}
        </Box>
      )}
      {rows.length === 0 && <Box sx={{ fontSize: 13.5, color: colors.textLo }}>No contenders with 150+ balls in this role since 2025.</Box>}
      {shown.filter((c) => c.for).map((c) => <Case key={c.name} c={c} />)}
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
        {`In the role, all T20s since Jan 2025: T20Is and every league. Ranked by ${slot.kind === 'bat' ? 'strike rate' : 'economy'}; the best in each column in green. Tap a name for his case.`}
      </Box>
    </Box>
  );
};

// Short role labels for the XI list (a 390px row: role, name, his number).
const SHORT = { openers: 'Opener', top: 'No. 3-4', middle: 'No. 5-7', 'powerplay|pace': 'PP pace', 'middle|spin': 'Spin', 'death|pace': 'Death' };
const KEY = { bat: ['sr', 'SR', (v) => v.toFixed(0)], bowl: ['econ', 'Econ', (v) => v.toFixed(2)] };

// The XI first, as eleven rows (role, player, his number in the role, what he did last match); tap a row for its sheet:
// who else fits and the case, as picking a slot in 19-0 (user, 13 Nov 2026). ?slot=N opens that sheet (a shareable link).
const IntlXIPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const q = new URLSearchParams(location.search);
  const team = q.get('team') || 'India';
  const { status, data } = usePageData('/intl-xi', `team=${encodeURIComponent(team)}`);
  useEffect(() => { document.title = `${team} XI · Hindsight`; }, [team]);
  const slots = data?.slots || [];
  const n = Number(q.get('slot')) || null;
  const open = slots.find((s) => s.n === n) || null;
  const setSlot = (k) => {
    const p = new URLSearchParams(location.search);
    if (k) p.set('slot', String(k)); else p.delete('slot');
    navigate({ search: `?${p.toString()}` }, { replace: true });
  };
  const when = data?.as_of ? new Date(data.as_of).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '';

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 4, color: colors.textHi, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box>
        <Box component={Link} to={`/team?team=${encodeURIComponent(team)}`} sx={{ color: colors.textLo, fontSize: 13, textDecoration: 'none' }}>← {team}</Box>
        <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26, mt: 0.5 }}>{`Pick ${team}'s XI`}</Box>
        <Box sx={{ color: colors.textMed, fontSize: 13.5, ...oneLine }}>Tap a player to see who else fits, and the case.</Box>
      </Box>
      {(status === 'loading' || status === 'building') && <PageSkeleton note={status === 'building' ? 'Building this XI. It takes under a minute the first time.' : null} />}
      {status === 'empty' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>Pick your XI covers the top 10 T20I sides.</Box>}
      {status === 'error' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>This XI couldn't load just now. Try again shortly.</Box>}
      {status === 'ready' && slots.length > 0 && (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <Box sx={{ ...mono, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo }}>The last XI</Box>
            <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{`${when} v ${data.last_opponent || ''}`}</Box>
          </Box>
          <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.25, py: 0.5 }}>
            {slots.map((s, i) => {
              const key = KEY[s.kind];
              const me = (s.contenders || []).find((c) => c.holder);
              const better = key && me ? (s.contenders || []).filter((c) => !c.holder && (s.kind === 'bat' ? c.m[key[0]] > me.m[key[0]] : c.m[key[0]] < me.m[key[0]])).length : 0;
              return (
                <Box key={s.n} component="button" type="button" onClick={() => setSlot(s.n)} disabled={s.kind === 'lower'}
                  sx={{ all: 'unset', boxSizing: 'border-box', cursor: s.kind === 'lower' ? 'default' : 'pointer', width: '100%', display: 'grid',
                    gridTemplateColumns: '58px minmax(0, 1fr) auto', alignItems: 'center', columnGap: 1, py: 0.8, minHeight: 48,
                    borderTop: i ? `1px solid ${colors.border}` : 'none', '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
                  <Box sx={{ fontSize: 11.5, color: colors.textLo, whiteSpace: 'nowrap' }}>{SHORT[s.role] || s.label}</Box>
                  <Box sx={{ minWidth: 0 }}>
                    <Box sx={{ fontSize: 14.5, fontWeight: 500, ...oneLine }}>{s.holder}</Box>
                    <Box sx={{ fontSize: 11.5, color: colors.textLo, ...oneLine }}>{s.moved}</Box>
                  </Box>
                  <Box sx={{ textAlign: 'right' }}>
                    {key && me && me.m[key[0]] != null && <Box sx={{ ...mono, fontSize: 13.5 }}>{`${key[2](me.m[key[0]])}`}<Box component="span" sx={{ fontSize: 11, color: colors.textLo }}>{` ${key[1]}`}</Box></Box>}
                    {key && s.contenders?.length > 0 && (
                      <Box sx={{ fontSize: 11, color: better ? colors.textMed : colors.accent, whiteSpace: 'nowrap' }}>{better ? `${better} ahead ›` : 'best of these ›'}</Box>
                    )}
                  </Box>
                </Box>
              );
            })}
          </Box>
          <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
            In the role, all T20s since Jan 2025. "Ahead": contenders with a better strike rate (batting) or economy (bowling).
          </Box>
          <Drawer anchor="bottom" open={!!open} onClose={() => setSlot(null)}
            PaperProps={{ sx: { bgcolor: colors.bg, color: colors.textHi, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '88vh' } }}>
            {open && (
              <Box sx={{ maxWidth: 560, mx: 'auto', width: '100%', boxSizing: 'border-box', p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))' }}>
                <Slot data={data} slot={open} />
              </Box>
            )}
          </Drawer>
        </>
      )}
      <PageFooter />
    </Box>
  );
};

export default IntlXIPage;
