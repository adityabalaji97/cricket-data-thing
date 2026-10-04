import React from 'react';
import { Box, Typography } from '@mui/material';
import { WinningPhases } from '../ExpectStrip';
import { TeamFormCard, TeamSplitHeader, VenueRecentMatches } from '../MatchHistory';
import { ScoresBarChart, WinPercentagesPie } from '../venue/VenueResultCharts';
import DivergingBars from '../charts/DivergingBars';
import { KIND_COLORS, SERIES } from '../../theme/chartDefaults';
import { colors, fonts } from '../../theme/hindsightDark';
import { useStoryNav } from './StoryNav';

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
            color: 'inherit', px: 1.25, py: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 0.25, overflow: 'hidden',
            cursor: openCard ? 'pointer' : 'default', font: 'inherit', minHeight: 0,
            '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
          }}
        >
          <Typography noWrap sx={{ fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo }}>
            {t.label}
          </Typography>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 30, lineHeight: 1.05, color: colors.textHi, fontVariantNumeric: 'tabular-nums' }}>
            {t.value}
          </Typography>
          <Typography noWrap sx={{ fontSize: 13, color: colors.textMed, lineHeight: 1.25 }}>{t.sub}</Typography>
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
export const toStoryCard = (card, { isMobile }) => {
  const Visual = VISUALS[card.visual];
  if (!Visual) return null;
  return {
    id: card.id,
    title: card.title,
    help: card.help,
    sample: card.sample,
    smallSample: card.small_sample,
    queryUrl: card.query_url,
    info: card.info ? <InfoBody info={card.info} /> : null,
    render: () => <Visual payload={card.payload} isMobile={isMobile} />,
  };
};

export const toStoryChapters = (manifest, opts) => (manifest?.chapters || [])
  .map((chapter) => ({ ...chapter, cards: chapter.cards.map((c) => toStoryCard(c, opts)).filter(Boolean) }))
  .filter((chapter) => chapter.cards.length);
