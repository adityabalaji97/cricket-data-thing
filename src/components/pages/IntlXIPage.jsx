import React, { useEffect, useState } from 'react';
import { Box } from '@mui/material';
import { Navigate, useLocation } from 'react-router-dom';
import { colors, fonts } from '../../theme/hindsightDark';
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

export const Slot = ({ data, slot }) => {
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

// /pick-xi is now the team page's The XI card (13 Nov 2026): old links land there, on the last XI, with the slot's sheet up.
const IntlXIPage = () => {
  const location = useLocation();
  const q = new URLSearchParams(location.search);
  const t = new URLSearchParams({ team: q.get('team') || 'India', xi: 'last' });
  if (q.get('slot')) t.set('slot', q.get('slot'));
  return <Navigate to={`/team?${t.toString()}`} replace />;
};

export default IntlXIPage;
