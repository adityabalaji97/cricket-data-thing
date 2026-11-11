import React, { useMemo, useState } from 'react';
import { Box, Drawer } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';
import OverseasMark from '../common/OverseasMark';
import OutsideIplTag from '../common/OutsideIplTag';
import { defaultXI, scoreXI } from '../../utils/xiEngine';
import { Eyebrow } from '../pageKit/pageKit';

// The XI tab (XI_BUILDER_PLAN.md stage 2b): twelve players from the squad, a batting order and an impact sub who comes
// in for a named player. Batting roles come from the order (1-2 openers, 3-4, 5-7); the 20 overs go to the bowling
// eleven by where each has bowled (tap a bowler to fix his phase). Scored in the browser (xiEngine.scoreXI). The XI
// lives in the URL (xi, sub, force) like the squad's changes, so it's a link.

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const SLOT = (i) => (i < 2 ? 'Opener' : i < 4 ? '3-4' : i < 7 ? '5-7' : 'Lower');
const PHASES = ['powerplay', 'middle', 'death'];
const enc = (names) => names.map(encodeURIComponent).join('~');
const dec = (s) => (s ? s.split('~').map(decodeURIComponent).filter(Boolean) : []);
const short = (n) => n.split(' ').slice(-1)[0];

const XITab = ({ data, squad, q, setParams, RoleRows }) => {
  const players = useMemo(() => Object.fromEntries(squad.map((p) => [p.name, p])), [squad]);
  const fromUrl = dec(q.get('xi')).filter((n) => players[n]);
  const subUrl = dec(q.get('sub'));
  const force = Object.fromEntries(dec(q.get('force')).map((s) => s.split(':')).filter(([n]) => players[n]));
  const xi = useMemo(() => {
    if (fromUrl.length === 12) {
      const [forName, bats] = subUrl;
      return { twelve: fromUrl, sub: forName ? { name: fromUrl[11], for: forName, bats: bats === 'bat' } : null, force };
    }
    return { ...defaultXI(squad, data.roles, data.bench), force };
  }, [q.toString(), squad]); // eslint-disable-line react-hooks/exhaustive-deps
  const s = useMemo(() => scoreXI(xi, players, data.roles, data.bench), [xi, players, data]);
  const [pickFor, setPickFor] = useState(null);  // index in the twelve being replaced

  const save = (next) => setParams({ xi: enc(next.twelve), sub: next.sub ? enc([next.sub.for, next.sub.bats ? 'bat' : 'bowl']) : '',
    force: enc(Object.entries(next.force || {}).map(([n, ph]) => `${n}:${ph}`)) });
  const order = s.order;
  const move = (name, d) => {
    const i = order.indexOf(name); const j = i + d;
    if (j < 0 || j >= order.length) return;
    const o = [...order]; [o[i], o[j]] = [o[j], o[i]];
    // The twelve keeps the batting order first; the one who doesn't bat (and the sub, last) after.
    const rest = xi.twelve.filter((n) => !o.includes(n));
    save({ ...xi, twelve: [...o, ...rest.filter((n) => n !== xi.sub?.name), ...(xi.sub && !o.includes(xi.sub.name) ? [xi.sub.name] : [])] });
  };
  const replace = (idx, name) => {
    const t = [...xi.twelve]; const old = t[idx]; t[idx] = name;
    const sub = xi.sub ? { ...xi.sub, name: idx === 11 ? name : xi.sub.name, for: xi.sub.for === old ? name : xi.sub.for } : xi.sub;
    const f = { ...xi.force }; delete f[old];
    save({ ...xi, twelve: t, sub, force: f });
    setPickFor(null);
  };
  const cycle = (name) => {
    const cur = xi.force[name]; const next = cur ? PHASES[PHASES.indexOf(cur) + 1] : PHASES[0];
    const f = { ...xi.force }; if (next) f[name] = next; else delete f[name];
    save({ ...xi, force: f });
  };
  const bench = squad.filter((p) => !xi.twelve.includes(p.name));
  const bowlers = Object.entries(s.overs).filter(([, o]) => o.powerplay + o.middle + o.death > 0);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        {[[`${s.at_level} of ${s.of}`, 'roles at playoff level', false], [`${s.overseas}/4`, 'overseas in the twelve', s.overseas > 4],
          [`${s.unassigned}`, 'overs with no bowler', s.unassigned > 0]].map(([v, l, bad]) => (
          <Box key={l} sx={{ flex: 1, bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '12px', px: 1.25, py: 1 }}>
            <Box sx={{ ...mono, fontSize: 19, color: bad ? colors.red : colors.textHi }}>{v}</Box>
            <Box sx={{ fontSize: 11, color: colors.textLo }}>{l.startsWith('overseas') ? <OverseasMark size={11} sx={{ ml: 0, mr: 0.4, color: colors.textLo, verticalAlign: '-1px' }} /> : null}{l}</Box>
          </Box>
        ))}
      </Box>

      <Eyebrow>Batting order</Eyebrow>
      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.25, py: 0.5 }}>
        {order.map((n, i) => (
          <Box key={n} sx={{ display: 'grid', gridTemplateColumns: '22px 1fr auto', alignItems: 'center', gap: 1, py: 0.6,
            borderTop: i ? `1px solid ${colors.border}` : 'none' }}>
            <Box sx={{ ...mono, fontSize: 13, color: colors.textLo }}>{i + 1}</Box>
            <Box component="button" type="button" onClick={() => setPickFor(xi.twelve.indexOf(n))}
              sx={{ all: 'unset', cursor: 'pointer', minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                <Box sx={{ fontSize: 14.5, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{n}</Box>
                {players[n]?.overseas && <OverseasMark />}{players[n]?.outside && <OutsideIplTag />}
              </Box>
              <Box sx={{ fontSize: 11, color: s.flags[n] ? '#f0b429' : colors.textLo, whiteSpace: 'nowrap' }}>
                {`${SLOT(i)}${s.flags[n] ? ` · ${s.flags[n]}` : ''}`}
              </Box>
            </Box>
            <Box sx={{ display: 'flex', gap: 0.25 }}>
              {[['↑', -1], ['↓', 1]].map(([t, d]) => (
                <Box key={t} component="button" type="button" aria-label={`Move ${n} ${d < 0 ? 'up' : 'down'}`} onClick={() => move(n, d)}
                  sx={{ all: 'unset', cursor: 'pointer', px: 1, py: 0.25, color: colors.textMed, fontSize: 16 }}>{t}</Box>
              ))}
            </Box>
          </Box>
        ))}
      </Box>

      {xi.sub && (
        <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.5, py: 1 }}>
          <Eyebrow>Impact sub</Eyebrow>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1, mt: 0.5 }}>
            <Box component="button" type="button" onClick={() => setPickFor(11)} sx={{ all: 'unset', cursor: 'pointer', fontSize: 14.5 }}>
              {`${xi.sub.name}, in for ${short(xi.sub.for)}`}
            </Box>
            <Box component="button" type="button" onClick={() => save({ ...xi, sub: { ...xi.sub, bats: !xi.sub.bats } })}
              sx={{ all: 'unset', cursor: 'pointer', fontSize: 12.5, px: 1.1, py: 0.4, borderRadius: '999px', border: `1px solid ${colors.borderStrong}`, whiteSpace: 'nowrap' }}>
              {xi.sub.bats ? 'Comes in to bat' : 'Comes in to bowl'}
            </Box>
          </Box>
          <Box sx={{ fontSize: 11.5, color: colors.textLo, mt: 0.5 }}>Tap the name to change him; the man he replaces is set from the batting order.</Box>
        </Box>
      )}

      <Eyebrow>Bowling · tap a bowler to fix his phase</Eyebrow>
      <Box sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`, borderRadius: '14px', px: 1.25, py: 0.75 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 44px 44px 44px', ...mono, fontSize: 10.5, color: colors.textLo, pb: 0.5 }}>
          <span /> <span style={{ textAlign: 'center' }}>PP</span><span style={{ textAlign: 'center' }}>MID</span><span style={{ textAlign: 'center' }}>DEATH</span>
        </Box>
        {bowlers.map(([n, o]) => (
          <Box key={n} component="button" type="button" onClick={() => cycle(n)}
            sx={{ all: 'unset', cursor: 'pointer', display: 'grid', gridTemplateColumns: '1fr 44px 44px 44px', alignItems: 'center', py: 0.5, width: '100%' }}>
            <Box sx={{ fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {n}{xi.force[n] ? <Box component="span" sx={{ color: colors.accent, fontSize: 11 }}>{` · ${xi.force[n]}`}</Box> : null}
            </Box>
            {PHASES.map((ph) => <Box key={ph} sx={{ ...mono, textAlign: 'center', fontSize: 14, color: o[ph] ? colors.textHi : colors.textLo }}>{o[ph] || '·'}</Box>)}
          </Box>
        ))}
      </Box>

      <Eyebrow>Against the winners' template</Eyebrow>
      <RoleRows rows={s.roles} />

      <Drawer anchor="bottom" open={pickFor != null} onClose={() => setPickFor(null)}
        PaperProps={{ sx: { bgcolor: colors.bg, color: colors.textHi, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '75vh' } }}>
        {pickFor != null && (
          <Box sx={{ maxWidth: 560, mx: 'auto', width: '100%', p: 2, pb: 'calc(16px + env(safe-area-inset-bottom, 0px))' }}>
            <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, mb: 1 }}>{`Replace ${xi.twelve[pickFor]}`}</Box>
            {bench.length === 0 && <Box sx={{ color: colors.textLo, fontSize: 13.5 }}>Everyone in the squad is in the twelve. Add players on the Squad tab.</Box>}
            {bench.map((p) => (
              <Box key={p.name} component="button" type="button" onClick={() => replace(pickFor, p.name)}
                sx={{ all: 'unset', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', width: '100%', py: 0.9, borderTop: `1px solid ${colors.border}` }}>
                <Box sx={{ display: 'flex', alignItems: 'center', fontSize: 14.5 }}>{p.name}{p.overseas && <OverseasMark />}{p.outside && <OutsideIplTag />}</Box>
                <Box sx={{ fontSize: 12, color: colors.textLo }}>{p.role}</Box>
              </Box>
            ))}
          </Box>
        )}
      </Drawer>
    </Box>
  );
};

export default XITab;
