import React, { useMemo } from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../theme/hindsightDark';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import { ScoringWheel } from '../playerProfile/cards/RoleCards';
import { signed } from '../playerProfile/verdict/verdictFormat';
import { Eyebrow } from '../pageKit/pageKit';

// Batter v bowler on the Compare page, from /matchup: the head-to-head and its Impact, the head-to-head against each
// player's usual, where the bowler pitched it, where the batter scored, year by year. One colour per side on every
// card: lime is the batter's side of things (his dot, cells and slices he scored faster in), blue the bowler's.

const mono = { fontFamily: fonts.mono, fontVariantNumeric: 'tabular-nums' };
const LINES = ['WIDE_OUTSIDE_OFFSTUMP', 'OUTSIDE_OFFSTUMP', 'ON_THE_STUMPS', 'DOWN_LEG'];
const LINE_NAMES = ['Wide off', 'Off', 'Stumps', 'Leg'];
const LENGTHS = ['YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT'];
const LENGTH_NAMES = { YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };
const CELL_MIN = 6;

const surname = (n) => (n || '').split(' ').slice(-1)[0];
// What to call him in a sentence: the surname, or the first name where the surname is shared by many (Rohit, Rashid).
const COMMON = new Set(['Sharma', 'Singh', 'Khan', 'Kumar', 'Patel', 'Ali', 'Ahmed', 'Yadav', 'Iyer', 'Malik', 'Shah', 'Hussain', 'Smith', 'Williams', 'Jones', 'Mohammad', 'Rahman', 'Islam', 'Hasan']);
const first = (n) => { const w = (n || '').split(' '); return w.length > 1 && !/^[A-Z]{1,3}$/.test(w[0]) ? w[0] : surname(n); };
const call = (n) => (COMMON.has(surname(n)) ? first(n) : surname(n));

const Legend = ({ items }) => (
  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '4px 14px' }}>
    {items.map(([label, colour, ring]) => (
      <Box key={label} component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75, fontSize: 12, color: colors.textMed }}>
        <Box component="span" sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: ring ? 'transparent' : colour, border: ring ? `2px solid ${colour}` : 'none' }} />
        {label}
      </Box>
    ))}
  </Box>
);

/** The head-to-head, its sentence against the batter's usual, and the three measures that rate it (T20). */
const HeadCard = ({ d, A, B }) => {
  const o = d.overall; const u = d.batter_usual;
  const claim = useMemo(() => {
    if (!u || !o.strike_rate || !u.strike_rate) return null;
    const diff = o.strike_rate - u.strike_rate;
    const pace = Math.abs(diff) < 8 ? 'at about his usual rate' : diff > 0 ? 'faster than usual' : 'slower than usual';
    const outs = o.balls_per_dismissal && u.balls_per_dismissal
      ? `, and is out ${o.balls_per_dismissal < u.balls_per_dismissal ? 'more' : 'less'} often (every ${Math.round(o.balls_per_dismissal)} balls v ${Math.round(u.balls_per_dismissal)})`
      : '';
    return `${call(d.batter)} scores ${pace} against ${u.against} off ${call(d.bowler)} (${Math.round(o.strike_rate)} v ${Math.round(u.strike_rate)})${outs}.`;
  }, [d, o, u]);
  const rated = [['Above par', o.raa, 1, o.raa_per_100 != null ? `${signed(o.raa_per_100, 1)} per 100 balls` : null],
    ['Impact', o.impact, 1, null], ['Wins added', o.wpa, 2, null]].filter(([, v]) => v !== null && v !== undefined);
  return (
    <ProfileCard id="matchup" title={`${call(d.batter)} v ${call(d.bowler)}`} player={`${d.batter} v ${d.bowler}`}
      note={null}>
      <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 30, lineHeight: 1.1 }}>
        {o.runs}
        <Box component="span" sx={{ fontSize: 17, fontWeight: 500, color: colors.textMed }}>{` off ${o.balls} balls · `}</Box>
        {o.wickets}
        <Box component="span" sx={{ fontSize: 17, fontWeight: 500, color: colors.textMed }}>{o.wickets === 1 ? ' out' : ' outs'}</Box>
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '2px 14px', ...mono, fontSize: 12.5, color: colors.textMed }}>
        <span>{`SR ${Math.round(o.strike_rate)}`}</span>
        <span>{`${Math.round(o.dot_percentage)}% dots`}</span>
        <span>{`${o.fours} fours · ${o.sixes} sixes`}</span>
        <span>{`${o.innings} innings`}</span>
      </Box>
      {claim && <Box sx={{ fontSize: 14.5, lineHeight: 1.45, color: colors.textHi }}>{claim}</Box>}
      {rated.length > 0 && (
        <>
          <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${rated.length}, minmax(0, 1fr))`, gap: 1 }}>
            {rated.map(([label, v, dp, sub]) => (
              <Box key={label} sx={{ border: `1px solid ${colors.borderStrong}`, borderRadius: '12px', px: 1.25, py: 1, minWidth: 0 }}>
                <Box sx={{ ...mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</Box>
                <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, color: v > 0 ? A : v < 0 ? B : colors.textHi }}>{signed(v, dp)}</Box>
                {sub && <Box sx={{ fontSize: 10.5, color: colors.textLo, whiteSpace: 'nowrap' }}>{sub}</Box>}
              </Box>
            ))}
          </Box>
          <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{`For ${call(d.batter)}: lime is in his favour, blue in ${call(d.bowler)}'s.`}</Box>
        </>
      )}
    </ProfileCard>
  );
};

// Measures read from the batter's side: is higher good for him?
const TUG = [
  ['strike_rate', 'Strike rate', true, (v) => Math.round(v)],
  ['dot_percentage', 'Dot %', false, (v) => `${Math.round(v)}%`],
  ['boundary_percentage', 'Boundary %', true, (v) => `${Math.round(v)}%`],
  ['false_shot_percentage', 'False shots', false, (v) => `${Math.round(v)}%`],
  ['balls_per_dismissal', 'Balls per out', true, (v) => Math.round(v)],
];

/** Each measure: the batter's usual (lime dot), the bowler's usual (blue dot) and the head-to-head (ring) on one scale. */
const UsualCard = ({ d, A, B }) => {
  const o = d.overall; const bu = d.batter_usual; const wu = d.bowler_usual;
  if (!bu || !wu) return null;
  const rows = TUG.filter(([k]) => [o[k], bu[k], wu[k]].every((v) => v !== null && v !== undefined));
  if (!rows.length) return null;
  const W = 343; const H = 18;
  return (
    <ProfileCard id="usual" title="Against their usual" player={`${d.batter} v ${d.bowler}`}>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 58px 58px 58px', columnGap: 0.75, fontSize: 11.5, fontWeight: 700, textAlign: 'right' }}>
        <span />
        <Box component="span" sx={{ color: colors.textHi }}>H2H</Box>
        <Box component="span" sx={{ color: A, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{first(d.batter)}</Box>
        <Box component="span" sx={{ color: B, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{first(d.bowler)}</Box>
      </Box>
      {rows.map(([k, label, up, fmt]) => {
        const vals = [o[k], bu[k], wu[k]];
        const lo = Math.min(...vals); const hi = Math.max(...vals); const pad = (hi - lo) * 0.15 || 1;
        // The batter's good side on the right, every row.
        const x = (v) => { const t = (v - (lo - pad)) / (hi - lo + 2 * pad); return 8 + (up ? t : 1 - t) * (W - 16); };
        const nearer = Math.abs(o[k] - bu[k]) <= Math.abs(o[k] - wu[k]) ? A : B;
        return (
          <Box key={k} sx={{ display: 'flex', flexDirection: 'column', gap: '2px', py: 0.25 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 58px 58px 58px', columnGap: 0.75, alignItems: 'baseline', textAlign: 'right' }}>
              <Box component="span" sx={{ textAlign: 'left', color: colors.textMed, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</Box>
              <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 15, color: nearer }}>{fmt(o[k])}</Box>
              <Box component="span" sx={{ ...mono, fontSize: 12.5, color: colors.textMed }}>{fmt(bu[k])}</Box>
              <Box component="span" sx={{ ...mono, fontSize: 12.5, color: colors.textMed }}>{fmt(wu[k])}</Box>
            </Box>
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" aria-hidden="true">
              <rect x="0" y="8" width={W} height="2" rx="1" fill={colors.surface2} />
              <line x1={x(bu[k])} x2={x(wu[k])} y1="9" y2="9" stroke={colors.textGhost} strokeWidth="2" />
              <circle cx={x(bu[k])} cy="9" r="5" fill={A} stroke={colors.bg} strokeWidth="2" />
              <circle cx={x(wu[k])} cy="9" r="5" fill={B} stroke={colors.bg} strokeWidth="2" />
              <circle cx={x(o[k])} cy="9" r="6.5" fill="none" stroke={colors.textHi} strokeWidth="2" />
            </svg>
          </Box>
        );
      })}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 9.5, color: colors.textFaint }}>
        <span>{`← ${call(d.bowler)}'s way`}</span><span>{`${call(d.batter)}'s way →`}</span>
      </Box>
      <Legend items={[['Head to head', colors.textHi, true], [`${call(d.batter)} v all ${bu.against}`, A], [`${call(d.bowler)} v all ${wu.against}`, B]]} />
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>
        {`H2H is every ball between them, since ${d.since}; it takes the colour of the player whose usual it sits nearer.`}
      </Box>
    </ProfileCard>
  );
};

/** Where the bowler pitched it to him: balls, and his strike rate, in each line and length; outs as dots. */
const PitchMapCard = ({ d, A, B }) => {
  const by = useMemo(() => Object.fromEntries((d.cells || []).map((c) => [`${c.line}|${c.length}`, c])), [d.cells]);
  const lengths = LENGTHS.filter((l) => LINES.some((ln) => by[`${ln}|${l}`]));
  const tagged = (d.cells || []).reduce((t, c) => t + c.balls, 0);
  if (!lengths.length || tagged < 20) return null;
  const sr = d.overall.strike_rate;
  const cw = 62; const ch = 50; const L = 92; const W = L + cw * 4 + 4; const H = 24 + ch * lengths.length + 20;
  return (
    <ProfileCard id="pitch" title={`Where ${call(d.bowler)} bowled to him`} player={`${d.batter} v ${d.bowler}`}
      note={null}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={(d.cells || []).map((c) => `${LENGTH_NAMES[c.length] || c.length} ${c.line}: ${c.runs} off ${c.balls}`).join('; ')}>
        {lengths.map((l, i) => (
          <text key={l} x={L - 8} y={24 + i * ch + ch / 2 + 2} textAnchor="end" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{LENGTH_NAMES[l]}</text>
        ))}
        {lengths.map((l, i) => LINES.map((ln, j) => {
          const c = by[`${ln}|${l}`];
          const x = L + j * cw; const y = 20 + i * ch;
          if (!c) return <rect key={`${l}${ln}`} x={x + 2} y={y + 2} width={cw - 4} height={ch - 4} rx="6" fill="none" stroke={colors.border} />;
          const enough = c.balls >= CELL_MIN;
          const faster = (c.strike_rate ?? 0) >= sr;
          const op = enough ? Math.min(0.85, 0.2 + Math.abs((c.strike_rate ?? 0) - sr) / 150) : 0;
          const ink = enough && op > 0.6 && faster ? colors.bg : colors.textHi;
          return (
            <g key={`${l}${ln}`}>
              <rect x={x + 2} y={y + 2} width={cw - 4} height={ch - 4} rx="6" fill={faster ? A : B} fillOpacity={op}
                stroke={enough ? 'none' : colors.borderStrong}>
                <title>{`${LENGTH_NAMES[l]}, ${LINE_NAMES[j]}: ${c.runs} off ${c.balls}${c.wickets ? `, ${c.wickets} out` : ''}`}</title>
              </rect>
              <text x={x + cw / 2} y={y + ch / 2 - 1} textAnchor="middle" style={{ ...mono, fontSize: 12.5, fontWeight: 600, fill: enough ? ink : colors.textLo }}>{`${c.runs}/${c.balls}`}</text>
              <text x={x + cw / 2} y={y + ch / 2 + 12} textAnchor="middle" style={{ ...mono, fontSize: 9, fill: enough ? ink : colors.textLo, opacity: 0.85 }}>
                {enough ? `SR ${Math.round(c.strike_rate)}` : 'few balls'}
              </text>
              {Array.from({ length: c.wickets }).map((_, w) => (
                <circle key={w} cx={x + cw - 9 - w * 8} cy={y + 9} r="3" fill={colors.red} stroke={colors.bg} strokeWidth="1" />
              ))}
            </g>
          );
        }))}
        {LINE_NAMES.map((name, j) => (
          <text key={name} x={L + j * cw + cw / 2} y={H - 4} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{name}</text>
        ))}
      </Box>
      <Legend items={[[`Faster than his ${Math.round(sr)}`, A], ['Slower', B], ['Out', colors.red]]} />
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{`Runs/balls in each cell · ${tagged} of ${d.overall.balls} balls tracked · faded under ${CELL_MIN} balls`}</Box>
    </ProfileCard>
  );
};

/** Where he scored off him: the profile's scoring wheel, in the matchup's colours. */
const WheelCard = ({ d, A, B }) => {
  if ((d.zones || []).reduce((t, z) => t + z.runs, 0) < 20) return null;
  return (
    <ProfileCard id="scoring" title={`Where he scores off ${call(d.bowler)}`} player={`${d.batter} v ${d.bowler}`}>
      <ScoringWheel zones={d.zones} hand={d.hand} strikeRate={d.overall.strike_rate} faster={A} slower={B} />
      <Box sx={{ fontSize: 11.5, color: colors.textLo }}>{`Share of runs by area (${d.hand === 'LHB' ? 'left' : 'right'}-handed)`}</Box>
    </ProfileCard>
  );
};

/** Runs each year as columns, outs as dots on top; every year from the first meeting, gaps included. */
const YearsCard = ({ d, A, B }) => {
  const years = d.years || [];
  if (years.length < 2) return null;
  const by = Object.fromEntries(years.map((y) => [y.year, y]));
  const all = []; for (let y = years[0].year; y <= years[years.length - 1].year; y += 1) all.push(y);
  const max = Math.max(...years.map((y) => y.runs), 1);
  const W = 343; const top = 30; const base = 120; const H = base + 30; const step = W / all.length; const bw = Math.min(18, step - 6);
  const sr = d.overall.strike_rate;
  const outs = (d.dismissals || []).map((o) => `${o.how} ${o.count}`).join(' · ');
  return (
    <ProfileCard id="years" title="Year by year" player={`${d.batter} v ${d.bowler}`}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={years.map((y) => `${y.year}: ${y.runs} off ${y.balls}, ${y.wickets} out`).join('; ')}>
        <line x1="0" x2={W} y1={base} y2={base} stroke={colors.border} />
        {all.map((yr, i) => {
          const y = by[yr]; const cx = i * step + step / 2;
          const label = <text x={cx} y={base + 14} textAnchor="middle" style={{ ...mono, fontSize: 9.5, fill: colors.textLo }}>{`'${String(yr).slice(2)}`}</text>;
          if (!y) return <g key={yr}>{label}</g>;
          const h = Math.max(2, (y.runs / max) * (base - top));
          return (
            <g key={yr}>
              <rect x={cx - bw / 2} y={base - h} width={bw} height={h} rx="3" fill={(y.strike_rate ?? 0) >= sr ? A : B} fillOpacity="0.85">
                <title>{`${yr}: ${y.runs} off ${y.balls}${y.wickets ? `, ${y.wickets} out` : ''}`}</title>
              </rect>
              <text x={cx} y={base - h - 4 - y.wickets * 8} textAnchor="middle" style={{ ...mono, fontSize: 10, fill: colors.textHi }}>{y.runs}</text>
              {Array.from({ length: y.wickets }).map((_, w) => (
                <circle key={w} cx={cx} cy={base - h - 5 - w * 8} r="3" fill={colors.red} stroke={colors.bg} strokeWidth="1" />
              ))}
              <text x={cx} y={base + 25} textAnchor="middle" style={{ ...mono, fontSize: 8.5, fill: colors.textFaint }}>{`${y.balls}b`}</text>
              {label}
            </g>
          );
        })}
      </Box>
      <Legend items={[[`Faster than his ${Math.round(sr)}`, A], ['Slower', B], ['Out', colors.red]]} />
      {outs && <Box sx={{ fontSize: 12.5, color: colors.textMed }}><Eyebrow>How he got out</Eyebrow>{outs}</Box>}
    </ProfileCard>
  );
};

export const matchupQuery = (bat, bowl) => `/query?batters=${encodeURIComponent(bat)}&bowlers=${encodeURIComponent(bowl)}&group_by=line&group_by=length`;

const MatchupView = ({ d, A, B }) => (
  <>
    <HeadCard d={d} A={A} B={B} />
    <UsualCard d={d} A={A} B={B} />
    <PitchMapCard d={d} A={A} B={B} />
    <WheelCard d={d} A={A} B={B} />
    <YearsCard d={d} A={A} B={B} />
  </>
);

export default MatchupView;
