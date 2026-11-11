import React from 'react';
import { Box, Drawer } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { colors, fonts } from '../../theme/hindsightDark';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import PlayerLink from '../common/PlayerLink';
import { usePageData } from '../pageKit/pageKit';
import { Slot } from './IntlXIPage';

// The XI (13 Nov 2026, replacing "Who bats where" and "Who bowls when"; mockup https://claude.ai/artifact/8ngGBcW7Vw6ZkfVs63jVFr):
// the side's XI in batting order, each player with the 20 overs he's in the game: blue where he's at the crease (his
// share of the over's balls faced), lime where he bowls (his share of the over's balls bowled); an all-rounder has both,
// batting on top. Two views (URL ?xi=last): Regulars, each spot's regular in the page's window, then the busiest other
// bowlers; Last XI (the ten T20I sides), with each player's number in his role and how many contenders rate higher.
// Tapping a player (T20I sides) opens "who else fits" in a sheet (?slot=N), as picking a slot in 19-0. IPL sides: the
// names link to profiles and the header action is Fix my team.

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const oneLine = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' };
const BAT = '91,155,240';
const BOWL = '182,242,74';
const SEP = [6, 15];  // a gap after the powerplay and after the middle overs
const sum = (a) => (a || []).reduce((x, y) => x + y, 0);
const KEY = { bat: ['sr', 'SR', (v) => v.toFixed(0)], bowl: ['econ', 'econ', (v) => v.toFixed(2)] };
const SHORT = { openers: 'Opener', top: 'No. 3-4', middle: 'No. 5-7', 'powerplay|pace': 'PP pace', 'middle|spin': 'Spin', 'death|pace': 'Death' };
const COLS = 'repeat(6, 1fr) 3px repeat(9, 1fr) 3px repeat(5, 1fr)';

const Cells = ({ shares, rgb, k, half }) => (
  <Box sx={{ display: 'grid', gridTemplateColumns: COLS, gap: '1px', height: half ? 8 : 16 }}>
    {Array.from({ length: 20 }, (_, i) => {
      const v = shares ? shares[i] || 0 : 0;
      return (
        <React.Fragment key={i}>
          {SEP.includes(i) && <span />}
          <Box component="span" sx={{ borderRadius: '2px', bgcolor: v > 0.004 ? `rgba(${rgb},${Math.min(1, 0.06 + v * k).toFixed(2)})` : 'rgba(255,255,255,.04)' }} />
        </React.Fragment>
      );
    })}
  </Box>
);

// Only a real part earns a strip: a tailender's one ball faced isn't batting (summed shares of the 20 overs).
const Strip = ({ bat, bowl, batter }) => {
  // A batting-order regular always shows his batting, however little he faces (Prashant Veer at 7).
  const b = batter ? sum(bat) > 0 : sum(bat) > 0.2; const w = sum(bowl) > 0.2;
  if (b && w) return <Box sx={{ display: 'flex', flexDirection: 'column', gap: '2px' }}><Cells shares={bat} rgb={BAT} k={4.2} half /><Cells shares={bowl} rgb={BOWL} k={1.4} half /></Box>;
  if (b) return <Cells shares={bat} rgb={BAT} k={4.2} />;
  if (w) return <Cells shares={bowl} rgb={BOWL} k={1.4} />;
  return <Cells />;
};

const Axis = () => (
  <Box sx={{ display: 'grid', gridTemplateColumns: '16px minmax(0, 1fr) 150px', columnGap: 1, ...mono, fontSize: 11, color: colors.textLo, pt: 0.5 }}>
    <span /><span>Bats</span>
    <Box sx={{ display: 'grid', gridTemplateColumns: COLS, gap: '1px' }}>
      {Array.from({ length: 20 }, (_, i) => (
        <React.Fragment key={i}>
          {SEP.includes(i) && <span />}
          <Box component="span" sx={{ textAlign: 'center' }}>{[1, 6, 7, 15, 16, 20].includes(i + 1) ? i + 1 : ''}</Box>
        </React.Fragment>
      ))}
    </Box>
  </Box>
);

const signedPar = (v) => (v == null ? null : `${v > 0 ? '+' : ''}${Math.round(v)} v par`);

const XICard = ({ team, win, order, bowlGrid, batGrid, intl, ipl }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const q = new URLSearchParams(location.search);
  const view = intl && q.get('xi') === 'last' ? 'last' : 'reg';
  const xi = usePageData(intl ? '/intl-xi' : null, `team=${encodeURIComponent(team)}`);
  const slots = xi.data?.slots || [];
  const open = slots.find((s) => s.n === Number(q.get('slot'))) || null;
  const setQ = (patch) => {
    const p = new URLSearchParams(location.search);
    Object.entries(patch).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)));
    navigate({ search: `?${p.toString()}` }, { replace: true });
  };
  const bat = Object.fromEntries((batGrid?.batters || []).map((b) => [b.name, b.shares]));
  const bowl = Object.fromEntries((bowlGrid?.bowlers || []).map((b) => [b.name, b.shares]));
  if (!order?.length && !bowlGrid?.bowlers?.length) return null;

  // Regulars: each batting spot's regular, then the busiest bowlers not already in, to eleven.
  const reg = (order || []).map((o) => ({ n: o.position, name: o.batter, batter: true,
    sub: [signedPar(o.raa_per_100), `${o.share}% of inns`].filter(Boolean).join(' · ') }));
  (bowlGrid?.bowlers || []).slice().sort((a, b) => b.balls - a.balls).forEach((b) => {
    if (reg.length < 11 && !reg.some((r) => r.name === b.name)) reg.push({ n: reg.length + 1, name: b.name, sub: 'bowls' });
  });
  // A regular's sheet: his slot in the last XI, else the slot at his batting position.
  const slotFor = (r) => (slots.find((s) => s.holder === r.name) || slots.find((s) => s.n === r.n))?.n;
  const tap = intl && slots.length > 0;

  const action = intl ? (
    <Box component="button" type="button" onClick={() => setQ({ xi: 'last' })}
      sx={{ all: 'unset', cursor: 'pointer', fontSize: 13.5, color: colors.accent, minHeight: 32, display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap',
        '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>Pick your XI ›</Box>
  ) : ipl ? (
    <Box component={Link} to={`/team-builder?team=${encodeURIComponent(team)}`}
      sx={{ fontSize: 13.5, color: colors.accent, minHeight: 32, display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap', textDecoration: 'none' }}>Fix my team ›</Box>
  ) : null;

  const rowSx = (i) => ({ all: 'unset', boxSizing: 'border-box', width: '100%', display: 'grid', alignItems: 'center', columnGap: 1, py: 0.8, minHeight: 46,
    borderTop: i ? `1px solid ${colors.border}` : 'none', cursor: tap ? 'pointer' : 'default', '&:focus-visible': { outline: `2px solid ${colors.accent}` } });
  const Row = ({ i, onClick, children, cols }) => (tap
    ? <Box component="button" type="button" onClick={onClick} sx={{ ...rowSx(i), gridTemplateColumns: cols }}>{children}</Box>
    : <Box sx={{ ...rowSx(i), gridTemplateColumns: cols }}>{children}</Box>);

  return (
    <ProfileCard id="the-xi" title="The XI" player={team} action={action}
      note={view === 'reg' ? 'Brighter: more of the over · v par: runs per 100 balls'
        : 'In his role, all T20s since 2025 · ahead: rate higher'}>
      {intl && (
        <Box role="tablist" aria-label="Which XI" sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
          {[['reg', 'Regulars'], ['last', 'Last XI']].map(([k, l]) => (
            <Box key={k} component="button" type="button" role="tab" aria-selected={view === k} onClick={() => setQ({ xi: k === 'last' ? 'last' : null, slot: null })}
              sx={{ all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13, px: 1.5, minHeight: 32, boxSizing: 'border-box',
                display: 'inline-flex', alignItems: 'center', borderRadius: '999px', bgcolor: view === k ? colors.textHi : 'transparent',
                color: view === k ? colors.bg : colors.textLo, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>{l}</Box>
          ))}
        </Box>
      )}
      {view === 'reg' && (
        <Box>
          <Box sx={{ fontSize: 12, color: colors.textLo, ...oneLine }}>{`Each spot’s regular · when he’s in the game${tap ? ' · tap a player' : ''}`}</Box>
          <Box sx={{ display: 'flex', gap: 1.5, fontSize: 11.5, color: colors.textLo, mt: 0.5 }}>
            <span><Box component="i" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '2px', bgcolor: `rgb(${BAT})`, mr: 0.5, verticalAlign: '-1px' }} />at the crease</span>
            <span><Box component="i" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '2px', bgcolor: `rgb(${BOWL})`, mr: 0.5, verticalAlign: '-1px' }} />bowling</span>
          </Box>
          <Axis />
          {reg.map((r, i) => (
            <Row key={r.name} i={i} cols="16px minmax(0, 1fr) 150px" onClick={() => setQ({ slot: String(slotFor(r) || '') })}>
              <Box sx={{ ...mono, fontSize: 11, color: colors.textLo }}>{r.n}</Box>
              <Box sx={{ minWidth: 0 }}>
                <Box sx={{ fontSize: 14, fontWeight: 500, ...oneLine }}>{tap ? r.name : <PlayerLink name={r.name} win={win} />}</Box>
                <Box sx={{ fontSize: 11, color: colors.textLo, ...oneLine }}>{r.sub}</Box>
              </Box>
              <Strip bat={bat[r.name]} bowl={bowl[r.name]} batter={r.batter} />
            </Row>
          ))}
        </Box>
      )}
      {view === 'last' && (
        <Box>
          {xi.status !== 'ready' && <Box sx={{ fontSize: 13, color: colors.textLo, py: 1 }}>{xi.status === 'error' ? "The last XI couldn't load just now." : 'Loading the last XI…'}</Box>}
          {xi.status === 'ready' && (
            <>
              <Box sx={{ fontSize: 12, color: colors.textLo, ...oneLine }}>
                {`v ${xi.data.last_opponent}, ${new Date(xi.data.as_of).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} · tap a player for who else fits`}
              </Box>
              {slots.map((s, i) => {
                const key = KEY[s.kind];
                const me = (s.contenders || []).find((c) => c.holder);
                const ahead = key && me ? (s.contenders || []).filter((c) => !c.holder && c.m[key[0]] != null
                  && (s.kind === 'bat' ? c.m[key[0]] > me.m[key[0]] : c.m[key[0]] < me.m[key[0]])).length : 0;
                return (
                  <Row key={s.n} i={i} cols="16px minmax(0, 1fr) auto" onClick={() => s.contenders?.length && setQ({ slot: String(s.n) })}>
                    <Box sx={{ ...mono, fontSize: 11, color: colors.textLo }}>{s.n}</Box>
                    <Box sx={{ minWidth: 0 }}>
                      <Box sx={{ fontSize: 14, fontWeight: 500, ...oneLine }}>{s.holder}<Box component="span" sx={{ fontSize: 11, color: colors.textLo, fontWeight: 400 }}>{` · ${SHORT[s.role] || s.label}`}</Box></Box>
                      <Box sx={{ fontSize: 11, color: colors.textLo, ...oneLine }}>{s.moved}</Box>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      {key && me?.m[key[0]] != null && <Box sx={{ ...mono, fontSize: 12.5 }}>{key[2](me.m[key[0]])}<Box component="span" sx={{ fontSize: 11, color: colors.textLo }}>{` ${key[1]}`}</Box></Box>}
                      {key && s.contenders?.length > 0 && (
                        <Box sx={{ fontSize: 11, whiteSpace: 'nowrap', color: ahead ? colors.textMed : colors.accent }}>{ahead ? `${ahead} ahead ›` : 'best of these ›'}</Box>
                      )}
                    </Box>
                  </Row>
                );
              })}
            </>
          )}
        </Box>
      )}
      <Drawer anchor="bottom" open={!!open} onClose={() => setQ({ slot: null })}
        PaperProps={{ sx: { bgcolor: colors.bg, color: colors.textHi, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '88vh' } }}>
        {open && (
          <Box sx={{ maxWidth: 560, mx: 'auto', width: '100%', boxSizing: 'border-box', p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))' }}>
            <Slot data={xi.data} slot={open} />
          </Box>
        )}
      </Drawer>
    </ProfileCard>
  );
};

export default XICard;
