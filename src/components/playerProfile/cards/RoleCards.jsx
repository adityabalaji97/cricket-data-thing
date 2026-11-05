import React, { useMemo, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import ProfileCard from './ProfileCard';

// The role cards below the verdict and "plays like" (PROFILE_SIMPLIFY_PLAN.md P3-P5), drawn from GET
// /player/{name}/cards for the verdict's window. Batters: his start, where he scores, against each bowling type, how
// he gets out. Bowlers: where he bowls, by phase, right- v left-handers, how he takes wickets.

const LIME = colors.accent;
const RED = colors.red;
const SLATE = '#5b6b85';
const BLUE = '#5b9bf0';
const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const sign = (v, d = 1) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}`;

const Legend = ({ items }) => (
  <Box sx={{ display: 'flex', gap: 1.5, fontSize: 12, color: colors.textMed, whiteSpace: 'nowrap', flexWrap: 'nowrap', overflow: 'hidden' }}>
    {items.map(([label, colour]) => (
      <Box key={label} component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.6 }}>
        <Box component="i" sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: colour, display: 'inline-block' }} />
        {label}
      </Box>
    ))}
  </Box>
);

// A label (with an optional detail line under it), a bar and its value: the families, wickets and hands cards.
const BarRows = ({ rows, format = (v) => v }) => {
  const max = Math.max(...rows.map((r) => r.value), 1e-9);
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.9 }}>
      {rows.map((r) => (
        <Box key={r.label} sx={{ display: 'grid', gridTemplateColumns: '136px 1fr 40px', alignItems: 'center', gap: 1 }}>
          <Box sx={{ minWidth: 0, lineHeight: 1.15 }}>
            <Box sx={{ fontSize: 13.5, whiteSpace: 'nowrap' }}>{r.label}</Box>
            {r.detail && <Box sx={{ fontSize: 10.5, color: colors.textLo, whiteSpace: 'nowrap' }}>{r.detail}</Box>}
          </Box>
          <Box sx={{ height: 12, bgcolor: 'rgba(255,255,255,0.04)', borderRadius: '4px', overflow: 'hidden' }}>
            <Box sx={{ height: '100%', width: `${(100 * r.value) / max}%`, bgcolor: r.colour || SLATE, borderRadius: '4px' }} />
          </Box>
          <Box sx={{ ...mono, fontSize: 13, textAlign: 'right' }}>{format(r.value)}</Box>
        </Box>
      ))}
    </Box>
  );
};

// ---- batters ------------------------------------------------------------------------------------------------------

/** Strike rate by ball of the innings; drag (or hover) across to read each ball. */
export const StartCard = ({ player, start }) => {
  const pts = start.points;
  const W = 330; const H = 170; const L = 30; const R = 8; const T = 12; const B = 148;
  const ymax = Math.max(260, ...pts.map((p) => p.sr_ball + 20));
  const sx = (n) => L + ((n - 1) / Math.max(1, pts.length - 1)) * (W - L - R);
  const sy = (v) => B - (v / ymax) * (B - T);
  const path = (k) => pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.n).toFixed(1)},${sy(p[k]).toFixed(1)}`).join(' ');
  const [n, setN] = useState(Math.min(10, pts.length));
  const svg = useRef(null);
  const at = (evt) => {
    const box = svg.current.getBoundingClientRect();
    const x = ((evt.clientX - box.left) / box.width) * W;
    setN(Math.min(pts.length, Math.max(1, Math.round(((x - L) / (W - L - R)) * (pts.length - 1)) + 1)));
  };
  const p = pts[n - 1];
  const read = [
    [Math.round(p.sr_cum), 'strike rate so far'],
    [Math.round(p.sr_ball), `on ball ${n}`],
    [sign(p.par), 'runs v par, typical innings', p.par >= 0 ? LIME : RED],
    [p.alive, 'innings still going'],
  ];
  return (
    <ProfileCard id="start" title="His start" player={player} note={`${start.innings} innings · runs v par include the wicket's cost`}>
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 1.5, rowGap: 0.5 }}>
        <Box sx={{ gridColumn: '1 / -1', ...mono, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: LIME }}>Ball {n}</Box>
        {read.map(([v, label, c]) => (
          <Box key={label} sx={{ lineHeight: 1.2 }}>
            <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 20, color: c || colors.textHi }}>{v}</Box>
            <Box sx={{ fontSize: 12, color: colors.textLo, whiteSpace: 'nowrap' }}>{label}</Box>
          </Box>
        ))}
      </Box>
      <Box component="svg" ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" onPointerMove={at}
        onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); at(e); }}
        aria-label={`Strike rate by ball of the innings, 1 to ${pts.length}; drag across to read each ball`}
        sx={{ width: '100%', touchAction: 'pan-y', cursor: 'crosshair' }}>
        {[0, 100, 200].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke={colors.border} />
            <text x={L - 4} y={sy(v) + 3} textAnchor="end" style={{ ...mono, fontSize: 9, fill: colors.textLo }}>{v}</text>
          </g>
        ))}
        <path d={path('sr_ball')} fill="none" stroke={SLATE} strokeWidth="1.5" />
        <path d={path('sr_cum')} fill="none" stroke={LIME} strokeWidth="2.4" />
        <line x1={sx(n)} x2={sx(n)} y1={T} y2={B} stroke={colors.textHi} strokeWidth="1" />
        <circle cx={sx(n)} cy={sy(p.sr_cum)} r="4" fill={LIME} stroke={colors.bg} strokeWidth="1.5" />
        {[1, 10, 20, 30].filter((t) => t <= pts.length).map((t) => (
          <text key={t} x={sx(t)} y={H - 4} textAnchor="middle" style={{ ...mono, fontSize: 9, fill: colors.textLo }}>{t}</text>
        ))}
      </Box>
      <Legend items={[['Strike rate so far', LIME], ['On that ball', SLATE]]} />
    </ProfileCard>
  );
};

const ZONES_RHB = { 1: 'Fine leg', 2: 'Square leg', 3: 'Midwicket', 4: 'Long on', 5: 'Long off', 6: 'Cover', 7: 'Point', 8: 'Behind' };
const MIRROR = { 1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 8 };
// Clockwise from the top for a left-hander (off side on the right); a right-hander's field is its mirror image.
const ANGLE_LHB = { Behind: 0, Point: 45, Cover: 90, 'Long off': 135, 'Long on': 180, Midwicket: 225, 'Square leg': 270, 'Fine leg': 315 };

/**
 * The scoring wheel: share of runs by area, wedge length is the share; every wedge blue where faster than his overall
 * strike rate and red where slower. zones: [{zone 1-8, runs, strike_rate}]. Shared by the
 * profile's card and the query builder's answer for a by-scoring-zone question.
 */
export const ScoringWheel = ({ zones, hand, strikeRate }) => {
  const total = zones.reduce((a, z) => a + z.runs, 0);
  if (!total) return null;
  const left = hand === 'LHB';
  const areas = zones.map((z) => ({ label: ZONES_RHB[left ? MIRROR[z.zone] : z.zone], share: z.runs / total, sr: z.strike_rate }));
  const top = areas.reduce((a, b) => (b.share > a.share ? b : a));
  const max = top.share;
  const c = 150; const R = 104;
  return (
    <>
      <Box component="svg" viewBox="-24 0 348 300" role="img" sx={{ width: '100%' }}
        aria-label={areas.map((a) => `${a.label} ${Math.round(a.share * 100)}%`).join(', ')}>
        <circle cx={c} cy={c} r={R + 6} fill="#12301c" stroke="rgba(255,255,255,0.22)" />
        {areas.map((a) => {
          const deg = left ? ANGLE_LHB[a.label] : (360 - ANGLE_LHB[a.label]) % 360;
          const rad = ((deg - 90) * Math.PI) / 180;
          const r = 22 + (a.share / max) * (R - 22);
          const a1 = rad - (20 * Math.PI) / 180; const a2 = rad + (20 * Math.PI) / 180;
          // Colour is strike rate only, every slice: the slice's length already shows its share of runs (user,
          // 5 Nov 2026), so the biggest isn't singled out.
          const fill = (a.sr ?? 0) >= strikeRate ? BLUE : RED;
          const lx = c + (R + 26) * Math.cos(rad); const ly = c + (R + 26) * Math.sin(rad);
          return (
            <g key={a.label}>
              <path d={`M${c},${c} L${c + r * Math.cos(a1)},${c + r * Math.sin(a1)} A${r},${r} 0 0 1 ${c + r * Math.cos(a2)},${c + r * Math.sin(a2)} Z`}
                fill={fill} fillOpacity={0.85}>
                <title>{`${a.label}: ${Math.round(a.share * 100)}% of runs, strike rate ${Math.round(a.sr ?? 0)}`}</title>
              </path>
              <text x={lx} y={ly} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{a.label}</text>
              <text x={lx} y={ly + 13} textAnchor="middle" style={{ ...mono, fontSize: 10.5, fill: colors.textHi }}>{`${Math.round(a.share * 100)}%`}</text>
            </g>
          );
        })}
        <rect x={c - 3} y={c - 9} width="6" height="18" rx="2" fill="#c9b27c" />
      </Box>
      <Legend items={[[`Faster than his ${Math.round(strikeRate)}`, BLUE], ['Slower', RED]]} />
    </>
  );
};

/** Where he scores: the scoring wheel on the profile. */
export const ScoringAreasCard = ({ player, zones, hand, strikeRate }) => {
  if (!zones.reduce((a, z) => a + z.runs, 0)) return null;
  return (
    <ProfileCard id="scoring" title="Where he scores" player={player} note={`Share of runs by area (${hand === 'LHB' ? 'left' : 'right'}-handed)`}>
      <ScoringWheel zones={zones} hand={hand} strikeRate={strikeRate} />
    </ProfileCard>
  );
};

/** Strike rate against each of six bowling families; fastest in lime, slowest in red. */
export const FamiliesCard = ({ player, families }) => {
  if (!families?.length) return null;
  const best = families.reduce((a, b) => (b.strike_rate > a.strike_rate ? b : a));
  const worst = families.reduce((a, b) => (b.strike_rate < a.strike_rate ? b : a));
  return (
    <ProfileCard id="bowling-types" title="Against each bowling type" player={player} note="Strike rate · 40+ balls">
      <BarRows format={(v) => Math.round(v)}
        rows={families.map((f) => ({ label: f.family, detail: `${f.balls} balls · ${f.outs} out`, value: f.strike_rate,
          colour: f === best ? LIME : f === worst && families.length > 1 ? RED : SLATE }))} />
    </ProfileCard>
  );
};

const HOW = { 'leg before wicket': 'LBW', 'caught and bowled': 'Caught and bowled', 'hit wicket': 'Hit wicket' };
const howName = (h) => HOW[h] || h.charAt(0).toUpperCase() + h.slice(1);

/** How a batter gets out, or how a bowler takes wickets. */
export const OutsCard = ({ player, rows, bowling }) => {
  if (!rows?.length) return null;
  const top = rows.slice(0, 5);
  return (
    <ProfileCard id={bowling ? 'wickets' : 'dismissals'} title={bowling ? 'How he takes wickets' : 'How he gets out'} player={player}
      note={bowling ? 'Run-outs not counted' : null}>
      <BarRows rows={top.map((r, i) => ({ label: howName(r.how), value: r.count, colour: i === 0 ? LIME : SLATE }))} />
    </ProfileCard>
  );
};

// ---- bowlers ------------------------------------------------------------------------------------------------------

const LINES = ['WIDE_OUTSIDE_OFFSTUMP', 'OUTSIDE_OFFSTUMP', 'ON_THE_STUMPS', 'DOWN_LEG'];
const LINE_NAMES = ['Wide off', 'Off', 'Stumps', 'Leg'];
const LENGTHS = ['YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT'];
const LENGTH_NAMES = { YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };

/** Economy by line and length (to all batters), against his own economy: cheaper in lime, dearer in red. */
export const PitchCard = ({ player, cells, economy }) => {
  const by = useMemo(() => Object.fromEntries((cells || []).map((c) => [`${c.line}|${c.length}`, c])), [cells]);
  const lengths = LENGTHS.filter((l) => LINES.some((ln) => by[`${ln}|${l}`]));
  if (!lengths.length) return null;
  const cheapest = (cells || []).filter((c) => c.balls >= 40).reduce((a, b) => (!a || b.economy < a.economy ? b : a), null);
  const cw = 58; const ch = 44; const L = 92; const W = L + cw * 4 + 4; const H = 24 + ch * lengths.length + 20;
  return (
    <ProfileCard id="pitch" title="Where he bowls" player={player} note="Runs an over · 15+ balls a cell">
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={(cells || []).map((c) => `${LENGTH_NAMES[c.length] || c.length} ${c.line}: ${c.economy}`).join('; ')}>
        {lengths.map((l, i) => (
          <text key={l} x={L - 8} y={24 + i * ch + ch / 2 + 2} textAnchor="end" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{LENGTH_NAMES[l]}</text>
        ))}
        {lengths.map((l, i) => LINES.map((ln, j) => {
          const cell = by[`${ln}|${l}`];
          const x = L + j * cw; const y = 20 + i * ch;
          if (!cell) return <rect key={`${l}${ln}`} x={x + 2} y={y + 2} width={cw - 4} height={ch - 4} rx="6" fill="none" stroke={colors.border} />;
          const diff = cell.economy - economy;
          const op = Math.min(0.9, 0.18 + Math.abs(diff) / 4);
          const ink = diff < 0 && op > 0.6 ? colors.bg : colors.textHi;
          return (
            <g key={`${l}${ln}`}>
              <rect x={x + 2} y={y + 2} width={cw - 4} height={ch - 4} rx="6" fill={diff < 0 ? LIME : RED} fillOpacity={op}
                stroke={cell === cheapest ? colors.textHi : 'none'} strokeWidth="2">
                <title>{`${LENGTH_NAMES[l]}, ${LINE_NAMES[j]}: ${cell.economy} an over (${cell.balls} balls)`}</title>
              </rect>
              <text x={x + cw / 2} y={y + ch / 2 + 2} textAnchor="middle" style={{ ...mono, fontSize: 13, fontWeight: 600, fill: ink }}>{cell.economy.toFixed(1)}</text>
              <text x={x + cw / 2} y={y + ch / 2 + 14} textAnchor="middle" style={{ ...mono, fontSize: 8.5, fill: ink, opacity: 0.8 }}>{`${cell.balls}b`}</text>
            </g>
          );
        }))}
        {LINE_NAMES.map((name, j) => (
          <text key={name} x={L + j * cw + cw / 2} y={H - 4} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{name}</text>
        ))}
      </Box>
      <Legend items={[[`Cheaper than his ${economy.toFixed(1)}`, LIME], ['Dearer', RED]]} />
    </ProfileCard>
  );
};

const PHASE_NAMES = { powerplay: 'Powerplay', middle: 'Middle', death: 'Death' };

/** Economy, dots and false shots forced in each phase; the phase with the most false shots outlined. */
export const PhaseCard = ({ player, phases }) => {
  if (!phases?.length) return null;
  const withFs = phases.filter((p) => p.false_shots !== null && p.false_shots !== undefined);
  const best = withFs.length ? withFs.reduce((a, b) => (b.false_shots > a.false_shots ? b : a)) : null;
  return (
    <ProfileCard id="phases" title="By phase" player={player} note={withFs.length ? 'False shots: edges, misses, mistimed' : null}>
      <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${phases.length}, minmax(0, 1fr))`, gap: 1 }}>
        {phases.map((p) => (
          <Box key={p.phase} sx={{ border: `1px solid ${p === best ? LIME : colors.borderStrong}`, borderRadius: '14px', p: 1.25 }}>
            <Box sx={{ ...mono, fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: colors.textLo }}>{PHASE_NAMES[p.phase] || p.phase}</Box>
            <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26, lineHeight: 1.1 }}>{p.economy.toFixed(1)}</Box>
            <Box sx={{ fontSize: 11.5, color: colors.textLo, lineHeight: 1.35, whiteSpace: 'nowrap' }}>{`${Math.round(p.dot_percentage)}% dots`}</Box>
            {p.false_shots !== null && p.false_shots !== undefined && (
              <Box sx={{ fontSize: 11.5, color: colors.textLo, lineHeight: 1.35, whiteSpace: 'nowrap' }}>{`${Math.round(p.false_shots)}% false shots`}</Box>
            )}
          </Box>
        ))}
      </Box>
    </ProfileCard>
  );
};

/** Economy to right- and left-handers. */
export const HandsCard = ({ player, hands }) => {
  if (!hands || hands.length < 2) return null;
  const better = hands.reduce((a, b) => (b.economy < a.economy ? b : a));
  const names = { RHB: 'Right-handers', LHB: 'Left-handers' };
  return (
    <ProfileCard id="hands" title="Right- v left-handers" player={player} note="Runs an over">
      <BarRows format={(v) => v.toFixed(1)}
        rows={['RHB', 'LHB'].map((h) => hands.find((x) => x.hand === h)).filter(Boolean).map((h) => ({
          label: names[h.hand], detail: `${h.balls} balls · ${h.wickets} wkts · ${Math.round(h.dot_percentage)}% dots`,
          value: h.economy, colour: h === better ? LIME : SLATE }))} />
    </ProfileCard>
  );
};

/** The batter's or bowler's four cards. */
export const RoleCardSet = ({ role, player, data, hand }) => {
  if (!data) return null;
  if (role === 'bat') {
    return (
      <>
        {data.start?.points?.length > 1 && <StartCard player={player} start={data.start} />}
        {data.zones?.length > 0 && <ScoringAreasCard player={player} zones={data.zones} hand={hand} strikeRate={data.strike_rate} />}
        <FamiliesCard player={player} families={data.families} />
        <OutsCard player={player} rows={data.dismissals} />
      </>
    );
  }
  return (
    <>
      <PitchCard player={player} cells={data.cells} economy={data.economy} />
      <PhaseCard player={player} phases={data.phases} />
      <HandsCard player={player} hands={data.hands} />
      <OutsCard player={player} rows={data.wickets} bowling />
    </>
  );
};
