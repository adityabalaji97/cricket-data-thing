import React from 'react';
import { Box, Typography } from '@mui/material';
import { WinningPhases } from '../ExpectStrip';
import { TeamFormCard, TeamSplitHeader, VenueRecentMatches } from '../MatchHistory';
import { ScoresBarChart, WinPercentagesPie } from '../venue/VenueResultCharts';
import DivergingBars from '../charts/DivergingBars';
import { DIVERGING, KIND_COLORS, SERIES } from '../../theme/chartDefaults';
import { colors, fonts } from '../../theme/hindsightDark';
import { useStoryNav } from './StoryNav';
import { getTeamColor, readableOnDark } from '../../utils/teamColors';
import { POST_VISUALS } from './postVisuals';

/**
 * Renderers for the `visual` each card declares (services/preview_cards). A card's payload is
 * exactly what its renderer draws; reused components run in `bare` mode, since the story card
 * supplies the title and frame.
 */
const Stat = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 96, lineHeight: 1, color: colors.accent }}>
      {payload.value}
    </Typography>
    {payload.caption && (
      <Typography sx={{ mt: 1.5, fontSize: 16, color: colors.textMed }}>{payload.caption}</Typography>
    )}
  </Box>
);

const svgText = { fontFamily: fonts.mono, fontSize: 12 };

/** Par: the number, its trend in words, and par season by season (a line: no zero baseline needed). */
const Par = ({ payload }) => {
  const series = payload.series || [];
  const W = 300; const H = 120; const padX = 22; const top = 26; const bottom = 96;
  const values = series.map((r) => r.value);
  const lo = Math.min(...values) - 6; const hi = Math.max(...values) + 6;
  const x = (i) => (series.length < 2 ? W / 2 : padX + (i * (W - 2 * padX)) / (series.length - 1));
  const y = (v) => bottom - ((v - lo) / Math.max(1, hi - lo)) * (bottom - top);
  const last = series.length - 1;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 96, lineHeight: 1, color: colors.accent }}>
        {payload.value}
      </Typography>
      {payload.caption && <Typography sx={{ fontSize: 16, color: colors.textMed }}>{payload.caption}</Typography>}
      {series.length > 1 && (
        <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Par by season: ${series.map((r) => `${r.year} ${r.value}`).join(', ')}`} sx={{ width: '100%', mt: 1 }}>
          <polyline
            points={series.map((r, i) => `${x(i)},${y(r.value)}`).join(' ')}
            fill="none" stroke={colors.textFaint} strokeWidth="2" strokeLinejoin="round"
          />
          {series.map((r, i) => (
            <g key={r.year}>
              <circle cx={x(i)} cy={y(r.value)} r={i === last ? 6 : 4.5} fill={i === last ? colors.accent : colors.textLo} stroke={colors.surface1} strokeWidth="2">
                <title>{`${r.year}: par ${r.value} (${r.n} ${r.n === 1 ? 'match' : 'matches'})`}</title>
              </circle>
              <text x={x(i)} y={y(r.value) - 11} textAnchor="middle" style={{ ...svgText, fill: i === last ? colors.textHi : colors.textLo }}>{r.value}</text>
              <text x={x(i)} y={H - 4} textAnchor="middle" style={{ ...svgText, fill: colors.textFaint }}>{`'${String(r.year).slice(2)}`}</text>
            </g>
          ))}
        </Box>
      )}
    </Box>
  );
};

/** Chase record with its likely range against an even split (MATCH_PREVIEW_VIZ_PLAN.md, B4). */
const ChaseBand = ({ payload }) => {
  const W = 300; const x = (pct) => 10 + (pct * (W - 20)) / 100;
  const pct = Math.round((100 * payload.chase_wins) / Math.max(1, payload.decided));
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 2 }}>
      <Box component="svg" viewBox={`0 0 ${W} 112`} role="img" aria-label={`${pct}% of chases won; likely range ${payload.lo} to ${payload.hi}%`} sx={{ width: '100%' }}>
        <line x1="10" x2={W - 10} y1="50" y2="50" stroke={colors.borderStrong} strokeWidth="10" strokeLinecap="round" />
        <rect x={x(payload.lo)} y="40" width={Math.max(4, x(payload.hi) - x(payload.lo))} height="20" rx="10" fill={colors.blue} fillOpacity="0.35">
          <title>{`Likely range ${payload.lo}–${payload.hi}%`}</title>
        </rect>
        <line x1={x(50)} x2={x(50)} y1="28" y2="72" stroke={colors.textLo} strokeDasharray="3 3" />
        <text x={x(50)} y="20" textAnchor="middle" style={{ ...svgText, fill: colors.textLo }}>Even</text>
        <circle cx={x(pct)} cy="50" r="7" fill={colors.blue} stroke={colors.surface1} strokeWidth="2" />
        <text x={Math.min(W - 75, Math.max(75, x(pct)))} y="104" textAnchor="middle" style={{ ...svgText, fontSize: 14, fill: colors.textHi }}>{`${pct}% of chases won`}</text>
        <text x="10" y="80" style={{ ...svgText, fill: colors.textFaint }}>0%</text>
        <text x={W - 10} y="80" textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>100%</text>
      </Box>
      <Typography sx={{ fontSize: 14, color: colors.textMed }}>
        <Box component="span" sx={{ px: 1, py: 0.25, mr: 1, borderRadius: 1, bgcolor: colors.surface2, color: payload.within_noise ? colors.textMed : colors.accent, fontWeight: 600 }}>
          {payload.within_noise ? 'Within noise' : 'A real edge'}
        </Box>
        {payload.within_noise
          ? `The likely range, ${payload.lo}–${payload.hi}%, includes an even split.`
          : `The likely range, ${payload.lo}–${payload.hi}%, stays clear of an even split.`}
      </Typography>
      {(payload.notes || []).map((note) => (
        <Typography key={note} sx={{ fontSize: 14, color: colors.textLo }}>{note}</Typography>
      ))}
    </Box>
  );
};

const PHASE_LABEL = { powerplay: 'Powerplay', middle: 'Middle overs', death: 'Death overs' };
const Legend = ({ items }) => (
  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mt: 1 }}>
    {items.map(([label, color]) => (
      <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
        <Box sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: color }} />
        <Typography sx={{ fontSize: 13, color: colors.textMed }}>{label}</Typography>
      </Box>
    ))}
  </Box>
);

/** A1: the story's headline numbers; each tile opens its card. */
const Tiles = ({ payload }) => {
  const { openCard } = useStoryNav();
  return (
    <Box sx={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: '1fr 1fr', gridAutoRows: 'minmax(0, 1fr)', gap: 1 }}>
      {payload.tiles.map((t) => (
        <Box
          key={`${t.card}-${t.label}`}
          component="button"
          type="button"
          data-story-noswipe
          onClick={(e) => { e.stopPropagation(); if (openCard) openCard(t.card); }}
          aria-label={`${t.label}: ${t.value}, ${t.sub}. Open the card`}
          sx={{
            textAlign: 'left', border: `1px solid ${colors.border}`, borderRadius: '14px', bgcolor: colors.surface2,
            color: 'inherit', px: 1.25, py: { xs: 0.5, sm: 1 }, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.25, overflow: 'hidden',
            cursor: openCard ? 'pointer' : 'default', font: 'inherit', minHeight: 0,
            '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
          }}
        >
          <Typography noWrap sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo }}>
            {t.label}
          </Typography>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 26, sm: 30 }, lineHeight: 1.05, color: colors.textHi, fontVariantNumeric: 'tabular-nums' }}>
            {t.value}
          </Typography>
          <Typography noWrap sx={{ fontSize: { xs: 12, sm: 13 }, color: colors.textMed, lineHeight: 1.25 }}>{t.sub}</Typography>
        </Box>
      ))}
    </Box>
  );
};

/** B1: every first innings by season, defended or chased down, against a line near par. */
const TotalsScatter = ({ payload }) => {
  const W = 300; const H = 220; const left = 34; const right = 8; const top = 10; const bottom = 196;
  const totals = payload.points.map((p) => p.total);
  const lo = Math.floor((Math.min(...totals, payload.line) - 10) / 20) * 20;
  const hi = Math.ceil((Math.max(...totals, payload.line) + 10) / 20) * 20;
  const [y0, y1] = payload.years;
  const x = (yr, i) => left + ((yr - y0 + 0.5 + (((i * 37) % 11) - 5) * 0.06) / (y1 - y0 + 1)) * (W - left - right);
  const y = (v) => bottom - ((v - lo) / (hi - lo)) * (bottom - top);
  const ticks = []; for (let v = lo; v <= hi; v += (hi - lo > 120 ? 50 : 20)) ticks.push(v);
  const years = []; for (let yr = y0; yr <= y1; yr += 1) years.push(yr);
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`First-innings totals by season; line at ${payload.line}`} sx={{ width: '100%' }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={left} x2={W - right} y1={y(v)} y2={y(v)} stroke={colors.border} />
            <text x={left - 6} y={y(v) + 4} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{v}</text>
          </g>
        ))}
        <line x1={left} x2={W - right} y1={y(payload.line)} y2={y(payload.line)} stroke={colors.textMed} strokeDasharray="4 4" />
        <text x={W - right} y={y(payload.line) - 5} textAnchor="end" style={{ ...svgText, fill: colors.textMed }}>{payload.line}</text>
        {payload.points.map((p, i) => (
          <circle key={i} cx={x(p.year, i)} cy={y(p.total)} r="4.5" fill={p.won ? SERIES[0] : SERIES[1]}
            fillOpacity={p.recent ? 0.95 : 0.3} stroke={colors.surface1} strokeWidth="1.5">
            <title>{`${p.year}: ${p.total}, ${p.won ? 'defended' : 'chased down'}`}</title>
          </circle>
        ))}
        {years.map((yr) => (
          <text key={yr} x={x(yr, 5)} y={H - 6} textAnchor="middle" style={{ ...svgText, fill: colors.textFaint }}>{`'${String(yr).slice(2)}`}</text>
        ))}
      </Box>
      <Legend items={[['Defended', SERIES[0]], ['Chased down', SERIES[1]]]} />
      {payload.faded_label && <Typography sx={{ fontSize: 13, color: colors.textLo, mt: 0.5 }}>{`Faded: ${payload.faded_label}`}</Typography>}
    </Box>
  );
};

/** B2: average score at the end of each over, here and across the competition. */
const Worm = ({ payload }) => {
  const W = 300; const H = 210; const left = 30; const right = 8; const top = 22; const bottom = 186;
  const n = payload.overs.length;
  const max = Math.ceil(Math.max(...payload.here, ...payload.all) / 50) * 50;
  const x = (i) => left + (i / Math.max(1, n - 1)) * (W - left - right);
  const y = (v) => bottom - (v / max) * (bottom - top);
  const path = (vals) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ');
  const ticks = []; for (let v = 50; v <= max; v += 50) ticks.push(v);
  const lastHere = payload.here[n - 1]; const lastAll = payload.all[n - 1];
  const hereAbove = lastHere >= lastAll;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Average score by over: ${payload.here_label} ${Math.round(lastHere)}, ${payload.all_label} ${Math.round(lastAll)} after ${payload.overs[n - 1]} overs`} sx={{ width: '100%' }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={left} x2={W - right} y1={y(v)} y2={y(v)} stroke={colors.border} />
            <text x={left - 6} y={y(v) + 4} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{v}</text>
          </g>
        ))}
        <path d={path(payload.all)} fill="none" stroke={colors.textLo} strokeWidth="2" strokeDasharray="5 4" />
        <path d={path(payload.here)} fill="none" stroke={SERIES[0]} strokeWidth="2" />
        <circle cx={x(n - 1)} cy={y(lastHere)} r="4.5" fill={SERIES[0]} />
        <text x={x(n - 1)} y={y(lastHere) + (hereAbove ? -9 : 17)} textAnchor="end" style={{ ...svgText, fill: colors.textHi }}>{Math.round(lastHere)}</text>
        <text x={x(n - 1)} y={y(lastAll) + (hereAbove ? 17 : -9)} textAnchor="end" style={{ ...svgText, fill: colors.textLo }}>{Math.round(lastAll)}</text>
        {[[0, 'start'], [Math.floor((n - 1) / 2), 'middle'], [n - 1, 'end']].map(([i, anchor]) => (
          <text key={i} x={x(i)} y={H - 4} textAnchor={anchor} style={{ ...svgText, fill: colors.textFaint }}>{`Over ${payload.overs[i]}`}</text>
        ))}
      </Box>
      <Legend items={[[payload.here_label, SERIES[0]], [payload.all_label, colors.textLo]]} />
    </Box>
  );
};

/** B3: run rate by phase here minus the competition's. */
const PhaseDiverging = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
    <DivergingBars
      span={3}
      labelWidth={150}
      ariaLabel={`Runs per over by phase, here minus the ${payload.comparison} average`}
      rows={payload.rows.map((r) => ({
        key: r.phase, label: `${PHASE_LABEL[r.phase]} · ${r.here.toFixed(1)} v ${r.all.toFixed(1)}`, value: r.diff,
      }))}
    />
    <Typography sx={{ fontSize: 13, color: colors.textLo }}>
      {`Runs per over here v every ${payload.comparison} ground.`}
    </Typography>
  </Box>
);

/** B5: share of balls by spin and pace in each phase, with the competition's spin share as a tick. */
const PaceSpin = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 2 }}>
    {payload.rows.map((r) => (
      <Box key={r.phase}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography sx={{ fontSize: 14, color: colors.textHi }}>{PHASE_LABEL[r.phase]}</Typography>
          <Typography sx={{ fontSize: 14, color: colors.textHi, fontFamily: fonts.mono }}>{`spin ${r.spin_pct}%`}</Typography>
        </Box>
        <Box component="svg" viewBox="0 0 300 26" role="img" aria-label={`${PHASE_LABEL[r.phase]}: spin ${r.spin_pct}% of balls, ${r.spin_pct_all}% across the ${payload.comparison}`} sx={{ width: '100%', display: 'block' }}>
          <rect x="0" y="2" width={Math.max(0, 3 * r.spin_pct - 1)} height="20" rx="4" fill={KIND_COLORS.spin}>
            <title>{`Spin: ${r.spin_balls} balls, ${r.spin_wickets} wickets, ${r.spin_econ ?? '–'} an over`}</title>
          </rect>
          <rect x={3 * r.spin_pct + 1} y="2" width={Math.max(0, 300 - 3 * r.spin_pct - 1)} height="20" rx="4" fill={KIND_COLORS.pace}>
            <title>{`Pace: ${r.pace_balls} balls, ${r.pace_wickets} wickets, ${r.pace_econ ?? '–'} an over`}</title>
          </rect>
          <line x1={3 * r.spin_pct_all} x2={3 * r.spin_pct_all} y1="0" y2="26" stroke={colors.textHi} strokeWidth="2" />
        </Box>
        <Typography sx={{ fontSize: 13, color: colors.textLo, mt: 0.25 }}>
          {`spin ${r.spin_econ ?? '–'} an over · pace ${r.pace_econ ?? '–'} an over`}
        </Typography>
      </Box>
    ))}
    <Legend items={[['Spin', KIND_COLORS.spin], ['Pace', KIND_COLORS.pace], [`Tick: spin share across the ${payload.comparison}`, colors.textHi]]} />
  </Box>
);

/** B6: share of boundaries to each zone; behind the batter at the top, leg side on the right. */
const BoundaryZones = ({ payload }) => {
  const cx = 150; const cy = 120; const R = 104;
  const order = [8, 1, 2, 3, 4, 5, 6, 7]; // third man top-left, fine leg top-right, round to point
  const max = Math.max(...payload.zones.map((z) => z.pct));
  const rad = (deg) => (deg * Math.PI) / 180;
  const centre = (i) => -112.5 + i * 45;
  const wedge = (i) => {
    const a0 = rad(centre(i) - 22.5); const a1 = rad(centre(i) + 22.5);
    return `M${cx},${cy} L${cx + R * Math.cos(a0)},${cy + R * Math.sin(a0)} A${R},${R} 0 0 1 ${cx + R * Math.cos(a1)},${cy + R * Math.sin(a1)} Z`;
  };
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox="0 0 300 240" role="img" aria-label={payload.zones.map((z) => `${z.name} ${z.pct}%`).join(', ')} sx={{ width: '100%' }}>
        {order.map((zn, i) => {
          const z = payload.zones.find((q) => q.zone === zn);
          const a = rad(centre(i)); const lx = cx + R * 0.64 * Math.cos(a); const ly = cy + R * 0.64 * Math.sin(a);
          const isTop = zn === payload.top;
          return (
            <g key={zn}>
              <path d={wedge(i)} fill={SERIES[0]} fillOpacity={0.12 + (0.7 * z.pct) / max} stroke={isTop ? colors.accent : colors.surface1} strokeWidth={isTop ? 2.5 : 2}>
                <title>{`${z.name}: ${z.pct}% of boundaries (usually ${z.usual_pct}%)`}</title>
              </path>
              <text x={lx} y={ly - 3} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textHi }}>{z.name}</text>
              <text x={lx} y={ly + 11} textAnchor="middle" style={{ ...svgText, fill: colors.textHi }}>{`${z.pct.toFixed(0)}%`}</text>
            </g>
          );
        })}
        <rect x={cx - 4} y={cy - 12} width="8" height="24" rx="2" fill="#c8b48a" />
      </Box>
      <Typography sx={{ fontSize: 13, color: colors.textLo }}>
        {`Behind the batter at the top, leg side on the right. ${payload.leg_side_pct}% go to the leg side.`}
      </Typography>
    </Box>
  );
};

/** B8: how batters get out here (≤4 slices), with the usual share beside each. */
const Dismissals = ({ payload }) => {
  const total = payload.rows.reduce((a, r) => a + r.n, 0);
  const cols = [SERIES[0], SERIES[1], SERIES[2], '#5b6170'];
  const cx = 70; const cy = 100; const R = 66; const r0 = 42;
  let a = -Math.PI / 2;
  const segs = payload.rows.map((d, i) => {
    const a1 = a + (2 * Math.PI * d.n) / Math.max(1, total); const big = a1 - a > Math.PI ? 1 : 0;
    const p = `M${cx + R * Math.cos(a)},${cy + R * Math.sin(a)} A${R},${R} 0 ${big} 1 ${cx + R * Math.cos(a1)},${cy + R * Math.sin(a1)} L${cx + r0 * Math.cos(a1)},${cy + r0 * Math.sin(a1)} A${r0},${r0} 0 ${big} 0 ${cx + r0 * Math.cos(a)},${cy + r0 * Math.sin(a)} Z`;
    a = a1;
    return <path key={d.kind} d={p} fill={cols[i]} stroke={colors.surface1} strokeWidth="2"><title>{`${d.label}: ${d.n} (${d.pct}%, usually ${d.usual_pct}%)`}</title></path>;
  });
  const top = payload.rows.find((r) => r.kind === payload.top);
  return (
    <Box sx={{ flex: 1, display: 'flex', alignItems: 'center' }}>
      <Box component="svg" viewBox="0 0 300 200" role="img" aria-label={payload.rows.map((r) => `${r.label} ${r.pct}%`).join(', ')} sx={{ width: '100%' }}>
        {segs}
        <text x={cx} y={cy + 4} textAnchor="middle" style={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 24, fill: colors.textHi }}>{`${top.pct}%`}</text>
        <text x={cx} y={cy + 22} textAnchor="middle" style={{ ...svgText, fontSize: 11, fill: colors.textLo }}>{top.label.toLowerCase()}</text>
        {payload.rows.map((d, i) => (
          <g key={d.kind} transform={`translate(152 ${46 + i * 34})`}>
            <rect width="10" height="10" y="-9" rx="2" fill={cols[i]} />
            <text x="16" y="0" style={{ fontFamily: fonts.body, fontSize: 13, fill: colors.textHi }}>{d.label === 'Stumped and other' ? 'Stumped/other' : d.label}</text>
            <text x="16" y="15" style={{ ...svgText, fontSize: 11, fill: colors.textLo }}>{`${d.pct}% · usually ${d.usual_pct}%`}</text>
          </g>
        ))}
      </Box>
    </Box>
  );
};

/**
 * Colours for the two sides: their own colours when both are known, readable on the dark card and
 * clearly apart; otherwise the validated blue/orange pair. Text never takes these colours.
 */
const hexDistance = (a, b) => {
  const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [rgb(a), rgb(b)];
  return Math.sqrt(x.reduce((acc, v, i) => acc + (v - y[i]) ** 2, 0));
};
export const pairColors = (team1, team2) => {
  const a = getTeamColor(team1); const b = getTeamColor(team2);
  const ok = (c) => typeof c === 'string' && /^#[0-9a-f]{6}$/i.test(c);
  if (ok(a) && ok(b)) {
    const ra = readableOnDark(a); const rb = readableOnDark(b);
    if (ok(ra) && ok(rb) && hexDistance(ra, rb) > 120) return [ra, rb];
  }
  return [SERIES[0], SERIES[1]];
};
const signed = (v, digits = 0) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(digits)}`;

/** C1: each side against the competition average, per phase, bat and ball. */
const Dumbbell = ({ payload }) => {
  const [c1, c2] = pairColors(payload.team1, payload.team2);
  const span = Math.max(10, Math.ceil(Math.max(...payload.rows.flatMap((r) => [Math.abs(r.team1), Math.abs(r.team2)])) / 5) * 5);
  const W = 300; const left = 84; const right = 66; const rowH = 22;
  const x = (v) => left + ((v + span) / (2 * span)) * (W - left - right);
  const groups = ['Batting', 'Bowling'];
  let y = 0;
  const marks = [];
  groups.forEach((g) => {
    y += 14;
    marks.push(<text key={`${g}-h`} x="0" y={y} style={{ ...svgText, fontSize: 11, fill: colors.textLo, letterSpacing: '0.08em' }}>{g.toUpperCase()}</text>);
    payload.rows.filter((r) => r.group === g).forEach((r) => {
      y += rowH;
      const a = x(r.team1); const b = x(r.team2);
      marks.push(
        <g key={`${g}-${r.phase}`}>
          <text x="0" y={y + 4} style={{ fontFamily: fonts.body, fontSize: 13, fill: colors.textHi }}>{PHASE_LABEL[r.phase].replace(' overs', '')}</text>
          <line x1={Math.min(a, b)} x2={Math.max(a, b)} y1={y} y2={y} stroke={colors.borderStrong} strokeWidth="3" />
          <circle cx={a} cy={y} r="7" fill={c1} stroke={colors.surface1} strokeWidth="2"><title>{`${payload.team1} ${g.toLowerCase()}, ${PHASE_LABEL[r.phase].toLowerCase()}: ${signed(r.team1, 1)} per 100 balls`}</title></circle>
          <circle cx={b} cy={y} r="7" fill={c2} stroke={colors.surface1} strokeWidth="2"><title>{`${payload.team2} ${g.toLowerCase()}, ${PHASE_LABEL[r.phase].toLowerCase()}: ${signed(r.team2, 1)} per 100 balls`}</title></circle>
          <text x={W} y={y + 4} textAnchor="end" style={{ ...svgText, fill: colors.textMed }}>{`${signed(r.team1)} · ${signed(r.team2)}`}</text>
        </g>,
      );
    });
    y += 4;
  });
  const H = y + 20;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Runs per 100 balls against the ${payload.comparison} average, ${payload.team1} and ${payload.team2}`} sx={{ width: '100%' }}>
        <line x1={x(0)} x2={x(0)} y1="22" y2={H - 18} stroke={colors.textFaint} />
        {marks}
        <text x={x(-span)} y={H - 2} style={{ ...svgText, fill: colors.textFaint }}>{signed(-span)}</text>
        <text x={x(0)} y={H - 2} textAnchor="middle" style={{ ...svgText, fill: colors.textFaint }}>avg</text>
        <text x={x(span)} y={H - 2} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{signed(span)}</text>
      </Box>
      <Legend items={[[payload.team1, c1], [payload.team2, c2]]} />
    </Box>
  );
};

/** C2: rank among the competition's sides, per phase; a full bar is first. */
const RankBars = ({ payload }) => {
  const [c1, c2] = pairColors(payload.team1, payload.team2);
  const groups = ['batting', 'bowling'];
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.75 }}>
      {groups.map((g) => (
        <Box key={g}>
          <Typography sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.08em', color: colors.textLo, textTransform: 'uppercase', mb: 0.5 }}>{g}</Typography>
          {payload.rows.filter((r) => r.group === g).map((r) => {
            const len = (rank) => Math.max(0.04, (r.of - rank + 1) / r.of);
            return (
              <Box key={r.phase} sx={{ display: 'grid', gridTemplateColumns: '70px 1fr 54px', gap: 1, alignItems: 'center', mb: 0.75 }}>
                <Typography sx={{ fontSize: 13, color: colors.textHi }}>{PHASE_LABEL[r.phase].replace(' overs', '')}</Typography>
                <Box component="svg" viewBox="0 0 200 20" role="img" aria-label={`${payload.team1} ${r.team1} of ${r.of}, ${payload.team2} ${r.team2} of ${r.of}`} sx={{ width: '100%', display: 'block' }}>
                  <rect x="0" y="1" width={200 * len(r.team1)} height="7" rx="3.5" fill={c1}><title>{`${payload.team1}: ${r.team1} of ${r.of}`}</title></rect>
                  <rect x="0" y="12" width={200 * len(r.team2)} height="7" rx="3.5" fill={c2}><title>{`${payload.team2}: ${r.team2} of ${r.of}`}</title></rect>
                </Box>
                <Typography sx={{ fontSize: 13, color: colors.textMed, fontFamily: fonts.mono, textAlign: 'right' }}>{`${r.team1} · ${r.team2}`}</Typography>
              </Box>
            );
          })}
        </Box>
      ))}
      <Legend items={[[payload.team1, c1], [payload.team2, c2]]} />
      <Typography sx={{ fontSize: 13, color: colors.textLo }}>{`Rank of ${payload.rows[0]?.of} (1 = best)`}</Typography>
    </Box>
  );
};

/** C3: each side's Elo before every match over the last year. */
const EloLines = ({ payload }) => {
  const teams = payload.series.map((s) => s.team);
  const cols = pairColors(teams[0], teams[1]);
  const all = payload.series.flatMap((s) => s.points);
  const t = (d) => new Date(d).getTime();
  const t0 = Math.min(...all.map((p) => t(p.date))); const t1 = Math.max(...all.map((p) => t(p.date)));
  const lo = Math.floor((Math.min(...all.map((p) => p.elo)) - 15) / 25) * 25;
  const hi = Math.ceil((Math.max(...all.map((p) => p.elo)) + 15) / 25) * 25;
  const W = 300; const H = 200; const left = 38; const right = 40; const top = 10; const bottom = 176;
  const x = (d) => left + ((t(d) - t0) / Math.max(1, t1 - t0)) * (W - left - right);
  const y = (v) => bottom - ((v - lo) / Math.max(1, hi - lo)) * (bottom - top);
  const ticks = []; for (let v = lo; v <= hi; v += (hi - lo > 150 ? 50 : 25)) ticks.push(v);
  const month = (d) => new Date(d).toLocaleString('en-GB', { month: 'short', year: '2-digit' });
  // End labels: when the two ratings sit close, push the higher one up and the lower one down.
  const ends = payload.series.map((s) => s.points[s.points.length - 1].elo);
  const close = Math.abs(y(ends[0]) - y(ends[1])) < 14;
  const labelNudge = (i) => (close ? (ends[i] >= ends[1 - i] ? -7 : 7) : 0);
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={payload.series.map((s) => `${s.team} ${s.points[s.points.length - 1].elo}`).join(', ')} sx={{ width: '100%' }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={left} x2={W - right} y1={y(v)} y2={y(v)} stroke={colors.border} />
            <text x={left - 6} y={y(v) + 4} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{v}</text>
          </g>
        ))}
        {payload.series.map((s, i) => {
          const last = s.points[s.points.length - 1];
          return (
            <g key={s.team}>
              <path d={s.points.map((p, k) => `${k ? 'L' : 'M'}${x(p.date)},${y(p.elo)}`).join(' ')} fill="none" stroke={cols[i]} strokeWidth="2" />
              {s.points.map((p) => (
                <circle key={p.date} cx={x(p.date)} cy={y(p.elo)} r="3" fill={cols[i]}><title>{`${s.team}, ${p.date}: ${p.elo}${p.won ? ' (won)' : ''}`}</title></circle>
              ))}
              <text x={W - right + 6} y={y(last.elo) + 4 + labelNudge(i)} style={{ ...svgText, fill: colors.textHi }}>{last.elo}</text>
            </g>
          );
        })}
        <text x={left} y={H - 4} style={{ ...svgText, fill: colors.textFaint }}>{month(t0)}</text>
        <text x={W - right} y={H - 4} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{month(t1)}</text>
      </Box>
      <Legend items={teams.map((tm, i) => [tm, cols[i]])} />
    </Box>
  );
};

/** C4: team1's chance of winning after every ball of the last meeting, and both scores. */
const LastMeeting = ({ payload }) => {
  const [c1, c2] = pairColors(payload.team1, payload.team2);
  const path = payload.path || [];
  const W = 300; const H = 170; const left = 34; const right = 6; const top = 10; const bottom = 150;
  const x = (i) => left + (i / Math.max(1, path.length - 1)) * (W - left - right);
  const y = (wp) => bottom - wp * (bottom - top);
  const brk = path.findIndex((p) => p.innings === 2);
  const chaser = payload.innings[1]?.side;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
      {path.length > 1 && (
        <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${payload.team1}'s chance of winning, ball by ball`} sx={{ width: '100%' }}>
          {[0, 0.5, 1].map((v) => (
            <g key={v}>
              <line x1={left} x2={W - right} y1={y(v)} y2={y(v)} stroke={v === 0.5 ? colors.textFaint : colors.border} strokeDasharray={v === 0.5 ? '4 4' : undefined} />
              <text x={left - 6} y={y(v) + 4} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{`${v * 100}%`}</text>
            </g>
          ))}
          {brk > 0 && (
            <g>
              <line x1={x(brk)} x2={x(brk)} y1={top} y2={bottom} stroke={colors.textFaint} />
              <text x={x(brk) + 4} y={top + 10} style={{ ...svgText, fontSize: 11, fill: colors.textLo }}>{`${chaser} chase`}</text>
            </g>
          )}
          <path d={path.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.wp)}`).join(' ')} fill="none" stroke={c1} strokeWidth="2" />
        </Box>
      )}
      <Box sx={{ display: 'grid', gap: 0.75 }}>
        {payload.innings.map((inn) => (
          <Box key={inn.innings} sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: inn.side === payload.team1 ? c1 : c2, flexShrink: 0 }} />
            <Typography sx={{ fontSize: 15, color: colors.textHi, minWidth: 64 }}>{inn.side || '—'}</Typography>
            <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 24, color: colors.textHi, fontVariantNumeric: 'tabular-nums' }}>
              {`${inn.runs}/${inn.wickets}`}
            </Typography>
            <Typography sx={{ fontSize: 13, color: colors.textLo }}>{`${Math.floor(inn.balls / 6)}.${inn.balls % 6} overs`}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

/** C6: each side's last XI in batting order. */
const Xis = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, alignContent: 'center' }}>
    {payload.sides.map((s) => (
      <Box key={s.team} sx={{ minWidth: 0 }}>
        <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, letterSpacing: '0.08em', color: colors.accent, textTransform: 'uppercase' }}>{s.team}</Typography>
        <Typography sx={{ fontSize: 12, color: colors.textLo, mb: 0.75 }} noWrap>
          {`v ${s.opponent}, ${new Date(s.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}`}
        </Typography>
        {s.players.map((p, i) => (
          <Typography key={p} noWrap sx={{ fontSize: 14, lineHeight: 1.6, color: colors.textMed }}>
            <Box component="span" sx={{ display: 'inline-block', width: 20, fontFamily: fonts.mono, fontSize: 11, color: colors.textFaint }}>{i + 1}</Box>
            {p}
          </Typography>
        ))}
      </Box>
    ))}
  </Box>
);

const surname = (name) => name.split(' ').slice(-1)[0];
const sideColor = (side, team1, team2) => {
  const [c1, c2] = pairColors(team1, team2);
  return side === team1 ? c1 : c2;
};

/** D1: likely edge per batter-bowler pair (bar either side of the middle); the scoreline is what happened. */
const Battles = ({ payload }) => {
  const span = Math.max(20, ...payload.rows.map((r) => Math.abs(r.edge)));
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.25 }}>
      {payload.rows.map((r) => {
        const w = (50 * Math.abs(r.edge)) / span;
        return (
          <Box key={`${r.batter}-${r.bowler}`} sx={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 1, alignItems: 'center' }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography noWrap sx={{ fontSize: 14, color: colors.textHi }}>{`${r.batter} v ${r.bowler}`}</Typography>
              <Typography noWrap sx={{ fontSize: 12, color: colors.textLo, fontFamily: fonts.mono }}>
                {`${r.runs} off ${r.balls}${r.outs ? `, out ${r.outs}` : ', not out'}`}
              </Typography>
            </Box>
            <Box component="svg" viewBox="0 0 120 22" role="img" aria-label={`Likely edge ${signed(r.edge)} runs per 100 balls`} sx={{ width: '100%', display: 'block' }}>
              <line x1="60" x2="60" y1="0" y2="22" stroke={colors.textFaint} />
              <rect x={r.edge >= 0 ? 60 : 60 - (120 * w) / 100} y="6" width={Math.max(2, (120 * w) / 100)} height="10" rx="3"
                fill={r.edge >= 0 ? DIVERGING.positive : DIVERGING.negative} />
              <text x={r.edge >= 0 ? 4 : 116} y="15" textAnchor={r.edge >= 0 ? 'start' : 'end'} style={{ ...svgText, fill: colors.textMed }}>{signed(r.edge)}</text>
            </Box>
          </Box>
        );
      })}
      <Typography sx={{ fontSize: 12, color: colors.textLo }}>Likely edge, runs per 100 balls · blue: batter ahead · red: bowler ahead</Typography>
    </Box>
  );
};

/** D2: ranked bars for players from both XIs, coloured by side. */
const PlayerBars = ({ payload, teams }) => {
  const rows = payload.rows;
  const max = Math.max(...rows.map((r) => Math.abs(r.value)), 1);
  const sides = [...new Set(rows.map((r) => r.side))];
  const [t1, t2] = teams || sides;
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: payload.extra === 'detail' ? 0.4 : 0.75 }}>
      {rows.map((r) => (
        <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: '112px 1fr 44px', gap: 1, alignItems: 'center' }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography noWrap sx={{ fontSize: 13, color: colors.textHi }}>{r.name}</Typography>
            {payload.extra === 'detail' && r.detail && (
              <Typography noWrap sx={{ fontSize: 11, lineHeight: 1.3, color: colors.textLo }}>{r.detail}</Typography>
            )}
          </Box>
          <Box sx={{ position: 'relative', height: 14 }}>
            <Box sx={{ position: 'absolute', left: 0, top: 2, height: 10, borderRadius: '0 4px 4px 0', width: `${Math.max(3, (100 * Math.max(0, r.value)) / max)}%`, bgcolor: sideColor(r.side, t1, t2), opacity: r.value > 0 ? 1 : 0.35 }} />
          </Box>
          <Typography sx={{ fontSize: 13, color: colors.textMed, fontFamily: fonts.mono, textAlign: 'right' }}>
            {`${payload.signed ? signed(r.value, payload.decimals || 0) : r.value.toFixed(payload.decimals || 0)}${payload.unit || ''}`}
          </Typography>
        </Box>
      ))}
      {payload.extra !== 'detail' && (
        <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 0.5 }}>
          {rows.map((r) => `${surname(r.name)} ${payload.extra === 'sr' ? `SR ${r.sr}` : `${r.econ} an over`}`).join(' · ')}
        </Typography>
      )}
      <Legend items={[[t1, sideColor(t1, t1, t2)], [t2, sideColor(t2, t1, t2)]].filter(([t]) => t)} />
    </Box>
  );
};

/** D3: runs in each of the last ten innings, oldest first; 50+ in the accent colour. */
const FormStrips = ({ payload, teams }) => {
  const [t1, t2] = teams || [];
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1 }}>
      {payload.strips.map((f) => (
        <Box key={f.name} sx={{ display: 'grid', gridTemplateColumns: '104px 1fr', gap: 1, alignItems: 'end' }}>
          <Typography sx={{ fontSize: 13, color: colors.textHi, lineHeight: 1.2 }}>{f.name}</Typography>
          <Box component="svg" viewBox="0 0 200 36" role="img" aria-label={`${f.name}: ${f.innings.map((i) => i.runs).join(', ')}`} sx={{ width: '100%', display: 'block' }}>
            {f.innings.map((i, k) => {
              const h = Math.max(2, Math.min(34, (34 * i.runs) / 100));
              const fifty = i.runs >= 50;
              return (
                <rect key={k} x={k * 20 + 2} y={36 - h} width="15" height={h} rx="2"
                  fill={fifty ? colors.textHi : sideColor(f.side, t1, t2)} fillOpacity={fifty ? 1 : 0.6}>
                  <title>{`${i.date}: ${i.runs}${i.out ? '' : '*'} off ${i.balls}`}</title>
                </rect>
              );
            })}
          </Box>
        </Box>
      ))}
      <Legend items={[['50 or more', colors.textHi], ...(t1 ? [[t1, sideColor(t1, t1, t2)], [t2, sideColor(t2, t1, t2)]] : [])]} />
    </Box>
  );
};

/** D4: record here against elsewhere; above the diagonal is better here. */
const SuitsScatter = ({ payload, teams }) => {
  const [t1, t2] = teams || [];
  const vals = payload.rows.flatMap((r) => [r.here, r.elsewhere]);
  const span = Math.max(20, Math.ceil(Math.max(...vals.map(Math.abs)) / 10) * 10);
  const W = 300; const H = 186; const left = 10; const right = 10; const top = 16; const bottom = 154;
  const x = (v) => left + ((v + span) / (2 * span)) * (W - left - right);
  const y = (v) => bottom - ((v + span) / (2 * span)) * (bottom - top);
  const gaps = payload.rows.map((r) => Math.abs(r.here - r.elsewhere)).sort((a, b) => b - a);
  const labelled = new Set(payload.rows.filter((r) => Math.abs(r.here - r.elsewhere) >= (gaps[2] ?? 0)).map((r) => r.name));
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Runs above average per 100 balls at ${payload.ground} against elsewhere`} sx={{ width: '100%' }}>
        <line x1={x(-span)} y1={y(-span)} x2={x(span)} y2={y(span)} stroke={colors.textFaint} strokeDasharray="4 4" />
        <line x1={x(0)} x2={x(0)} y1={top} y2={bottom} stroke={colors.border} />
        <line x1={left} x2={W - right} y1={y(0)} y2={y(0)} stroke={colors.border} />
        {payload.rows.map((r) => (
          <g key={r.name}>
            <circle cx={x(r.elsewhere)} cy={y(r.here)} r="5" fill={sideColor(r.side, t1, t2)} stroke={colors.surface1} strokeWidth="1.5">
              <title>{`${r.name}: ${signed(r.here)} here (${r.balls_here} balls), ${signed(r.elsewhere)} elsewhere`}</title>
            </circle>
            {labelled.has(r.name) && (
              <text x={x(r.elsewhere) + 8} y={y(r.here) + 4} style={{ fontFamily: fonts.body, fontSize: 12, fill: colors.textHi }}>{surname(r.name)}</text>
            )}
          </g>
        ))}
        <text x={x(-span)} y={H - 18} style={{ ...svgText, fill: colors.textFaint }}>{signed(-span)}</text>
        <text x={x(span)} y={H - 18} textAnchor="end" style={{ ...svgText, fill: colors.textFaint }}>{signed(span)}</text>
        <text x={(left + W - right) / 2} y={H - 2} textAnchor="middle" style={{ ...svgText, fill: colors.textLo }}>Elsewhere</text>
        <text x="4" y={top + 8} style={{ ...svgText, fill: colors.textLo }}>{`At ${payload.ground}`}</text>
      </Box>
      {t1 && <Legend items={[[t1, sideColor(t1, t1, t2)], [t2, sideColor(t2, t1, t2)]]} />}
    </Box>
  );
};

/** D5: milestones within reach, one line each. */
const Milestones = ({ payload, teams }) => {
  const [t1, t2] = teams || [];
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.25 }}>
      {payload.rows.map((m) => (
        <Box key={`${m.player}-${m.stat}`} sx={{ display: 'flex', gap: 1, alignItems: 'baseline' }}>
          <Box sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: sideColor(m.side, t1, t2), flexShrink: 0, transform: 'translateY(-1px)' }} />
          <Typography sx={{ fontSize: 15, color: colors.textHi, lineHeight: 1.35 }}>
            <Box component="span" sx={{ fontWeight: 600 }}>{m.player}</Box>
            {` ${m.text}`}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

/** D6: the bowler's share of balls by line and length; a dot marks 1.5× the usual share or more. */
const LENGTH_LABEL = { FULL_TOSS: 'Full toss', YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };
const LINE_LABEL = { DOWN_LEG: 'Leg', ON_THE_STUMPS: 'Stumps', OUTSIDE_OFFSTUMP: 'Off', WIDE_OUTSIDE_OFFSTUMP: 'Wide' };
const PitchUsage = ({ payload }) => {
  const cw = 50; const ch = 30; const x0 = 98; const y0 = 20;
  const max = Math.max(...payload.grid.map((g) => g.pct), 1);
  const cell = (line, length) => payload.grid.find((g) => g.line === line && g.length === length);
  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Box component="svg" viewBox={`0 0 300 ${y0 + payload.lengths.length * ch + 4}`} role="img" aria-label={`Where ${payload.bowler} pitches the ball`} sx={{ width: '100%' }}>
        {payload.lines.map((l, j) => (
          <text key={l} x={x0 + j * cw + cw / 2} y="12" textAnchor="middle" style={{ ...svgText, fill: colors.textLo }}>{LINE_LABEL[l]}</text>
        ))}
        {payload.lengths.map((len, i) => (
          <g key={len}>
            <text x={x0 - 8} y={y0 + i * ch + ch / 2 + 4} textAnchor="end" style={{ fontFamily: fonts.body, fontSize: 12, fill: colors.textHi }}>{LENGTH_LABEL[len]}</text>
            {payload.lines.map((l, j) => {
              const c = cell(l, len);
              const standout = c.usual_pct > 0 && c.pct >= 2 && c.pct / c.usual_pct >= 1.5;
              return (
                <g key={l}>
                  <rect x={x0 + j * cw + 1} y={y0 + i * ch + 1} width={cw - 2} height={ch - 2} rx="5" fill={SERIES[0]} fillOpacity={0.08 + (0.8 * c.pct) / max}>
                    <title>{`${LENGTH_LABEL[len]}, ${LINE_LABEL[l]}: ${c.pct}% of balls (usually ${c.usual_pct}%)`}</title>
                  </rect>
                  <text x={x0 + j * cw + cw / 2} y={y0 + i * ch + ch / 2 + 4} textAnchor="middle" style={{ ...svgText, fontSize: 11, fill: colors.textHi }}>{c.pct >= 1 ? `${Math.round(c.pct)}` : ''}</text>
                  {standout && <circle cx={x0 + j * cw + cw - 7} cy={y0 + i * ch + 7} r="3" fill={colors.accent} />}
                </g>
              );
            })}
          </g>
        ))}
      </Box>
      <Typography sx={{ fontSize: 12, color: colors.textLo }}>% of the bowler&apos;s balls · dot: 1.5× usual or more</Typography>
    </Box>
  );
};

/** F2: captain and vice-captain as two tiles. */
const Captaincy = ({ payload, teams }) => {
  const [t1, t2] = teams || [];
  return (
    <Box sx={{ flex: 1, display: 'grid', gap: 1.5, alignContent: 'center' }}>
      {payload.picks.map((p) => (
        <Box key={p.role} sx={{ border: `1px solid ${colors.border}`, borderRadius: '14px', bgcolor: colors.surface2, p: 2, display: 'grid', gap: 0.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo }}>{p.role}</Typography>
            <Typography sx={{ fontFamily: fonts.mono, fontSize: 13, color: colors.textMed }}>{`${p.multiplier} points`}</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: sideColor(p.side, t1, t2), flexShrink: 0 }} />
            <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 28, lineHeight: 1.1, color: colors.textHi }}>{p.name}</Typography>
          </Box>
          <Typography sx={{ fontSize: 14, color: colors.textMed }}>{`${p.side} · ${p.reason}`}</Typography>
        </Box>
      ))}
    </Box>
  );
};

/** E2: one-tap links to the query behind a card. */
const Links = ({ payload }) => (
  <Box sx={{ flex: 1, display: 'grid', gap: 1.25, alignContent: 'center' }}>
    {payload.links.map((l) => (
      <Box
        key={l.card}
        component="a"
        href={l.url}
        data-story-noswipe
        sx={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, p: 2, minHeight: 56,
          borderRadius: '14px', border: `1px solid ${colors.border}`, bgcolor: colors.surface2, color: colors.textHi,
          textDecoration: 'none', fontSize: 16, '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
        }}
      >
        <span>{l.label}</span>
        <Box component="span" aria-hidden sx={{ color: colors.accent, fontFamily: fonts.mono }}>→</Box>
      </Box>
    ))}
  </Box>
);

export const VISUALS = {
  stat: Stat,
  par: Par,
  chase_band: ChaseBand,
  tiles: Tiles,
  totals_scatter: TotalsScatter,
  worm: Worm,
  phase_diverging: PhaseDiverging,
  pace_spin: PaceSpin,
  boundary_zones: BoundaryZones,
  dismissals: Dismissals,
  dumbbell: Dumbbell,
  rank_bars: RankBars,
  elo_lines: EloLines,
  last_meeting: LastMeeting,
  xis: Xis,
  battles: Battles,
  player_bars: PlayerBars,
  form_strips: FormStrips,
  suits_scatter: SuitsScatter,
  milestones: Milestones,
  pitch_usage: PitchUsage,
  captaincy: Captaincy,
  links: Links,
  phase_bars: ({ payload }) => <WinningPhases phases={payload.phases} bare />,
  results_split: ({ payload }) => <WinPercentagesPie data={payload} bare />,
  benchmarks: ({ payload }) => <ScoresBarChart data={payload} bare />,
  recent_results: ({ payload, isMobile }) => <VenueRecentMatches matches={payload.matches} isMobile={isMobile} bare />,
  h2h: ({ payload, isMobile }) => <TeamSplitHeader team1={payload.team1} team2={payload.team2} stats={payload.stats} isMobile={isMobile} bare />,
  form: ({ payload, isMobile }) => (
    <TeamFormCard
      team1={payload.team1}
      team2={payload.team2}
      team1Matches={payload.team1_matches}
      team2Matches={payload.team2_matches}
      isMobile={isMobile}
      bare
    />
  ),
};

/** The info sheet's body: what the chart shows, how to read it, definitions, method. */
export const InfoBody = ({ info }) => (
  <Box sx={{ display: 'grid', gap: 1.25 }}>
    <Typography sx={{ fontSize: 15, color: colors.textHi }}>{info.what}</Typography>
    {info.how_to_read && <Typography sx={{ fontSize: 14, color: colors.textMed }}>{info.how_to_read}</Typography>}
    {(info.definitions || []).length > 0 && (
      <Box component="dl" sx={{ m: 0, display: 'grid', gap: 0.75 }}>
        {info.definitions.map((d) => (
          <Box key={d.term}>
            <Typography component="dt" sx={{ fontSize: 13, fontWeight: 600, color: colors.textHi }}>{d.term}</Typography>
            <Typography component="dd" sx={{ m: 0, fontSize: 13, color: colors.textMed }}>{d.meaning}</Typography>
          </Box>
        ))}
      </Box>
    )}
    {info.method && <Typography sx={{ fontSize: 13, color: colors.textLo }}>{info.method}</Typography>}
  </Box>
);

/** A manifest card (JSON from /match-preview/.../cards) as a StoryViewer card. Unknown visuals are dropped. */
export const toStoryCard = (card, { isMobile, teams, params }) => {
  // POST_VISUALS: the Instagram post cards' visuals (services/ig_posts), kept in their own module.
  const Visual = VISUALS[card.visual] || POST_VISUALS[card.visual];
  if (!Visual) return null;
  return {
    id: card.id,
    title: card.title,
    help: card.help,
    sample: card.sample,
    smallSample: card.small_sample,
    queryUrl: card.query_url,
    info: card.info ? <InfoBody info={card.info} /> : null,
    render: () => <Visual payload={card.payload} isMobile={isMobile} teams={teams} />,
    // The share image and embed are rebuilt server-side from the story's own parameters.
    graphic: params ? { kind: 'preview_card', params: { ...params, card: card.id } } : null,
  };
};

export const toStoryChapters = (manifest, opts) => {
  // The fixture's two sides, so player cards colour each player by side.
  const teams = manifest?.fixture ? [manifest.fixture.team1, manifest.fixture.team2] : undefined;
  const params = manifest?.fixture?.params;
  return (manifest?.chapters || [])
    .map((chapter) => ({ ...chapter, cards: chapter.cards.map((c) => toStoryCard(c, { ...opts, teams, params })).filter(Boolean) }))
    .filter((chapter) => chapter.cards.length);
};
