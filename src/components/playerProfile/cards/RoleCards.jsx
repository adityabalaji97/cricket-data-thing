import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { colors, fonts } from '../../../theme/hindsightDark';
import ProfileCard from './ProfileCard';
import config from '../../../config';

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
            {r.detail && <Box sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap' }}>{r.detail}</Box>}
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
            <text x={L - 4} y={sy(v) + 3} textAnchor="end" style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{v}</text>
          </g>
        ))}
        <path d={path('sr_ball')} fill="none" stroke={SLATE} strokeWidth="1.5" />
        <path d={path('sr_cum')} fill="none" stroke={LIME} strokeWidth="2.4" />
        <line x1={sx(n)} x2={sx(n)} y1={T} y2={B} stroke={colors.textHi} strokeWidth="1" />
        <circle cx={sx(n)} cy={sy(p.sr_cum)} r="4" fill={LIME} stroke={colors.bg} strokeWidth="1.5" />
        {[1, 10, 20, 30].filter((t) => t <= pts.length).map((t) => (
          <text key={t} x={sx(t)} y={H - 4} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: colors.textLo }}>{t}</text>
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
 * strike rate and red where slower (or the colours given). zones: [{zone 1-8, runs, strike_rate}]. Shared by the
 * profile's card and the query builder's answer for a by-scoring-zone question.
 */
export const ScoringWheel = ({ zones, hand, strikeRate, faster = BLUE, slower = RED, catches, outline, labels }) => {
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
          const fill = (a.sr ?? 0) >= strikeRate ? faster : slower;
          const lx = c + (R + 26) * Math.cos(rad); const ly = c + (R + 26) * Math.sin(rad);
          return (
            <g key={a.label}>
              <path d={`M${c},${c} L${c + r * Math.cos(a1)},${c + r * Math.sin(a1)} A${r},${r} 0 0 1 ${c + r * Math.cos(a2)},${c + r * Math.sin(a2)} Z`}
                fill={fill} fillOpacity={0.85}>
                <title>{`${a.label}: ${Math.round(a.share * 100)}% of runs, strike rate ${Math.round(a.sr ?? 0)}`}</title>
              </path>
              <text x={lx} y={ly} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{a.label}</text>
              <text x={lx} y={ly + 13} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: colors.textHi }}>{`${Math.round(a.share * 100)}%`}</text>
            </g>
          );
        })}
        {/* The zone the scouting line points to (the fielder who matters), outlined on the wheel itself. */}
        {outline && (() => {
          const lab = ZONES_RHB[left ? MIRROR[outline] : outline];
          const deg = left ? ANGLE_LHB[lab] : (360 - ANGLE_LHB[lab]) % 360;
          const rad = ((deg - 90) * Math.PI) / 180; const r = R + 6;
          const a1 = rad - (22.5 * Math.PI) / 180; const a2 = rad + (22.5 * Math.PI) / 180;
          return <path d={`M${c},${c} L${c + r * Math.cos(a1)},${c + r * Math.sin(a1)} A${r},${r} 0 0 1 ${c + r * Math.cos(a2)},${c + r * Math.sin(a2)} Z`}
            fill="none" stroke={colors.textHi} strokeWidth="2" strokeDasharray="4 3" />;
        })()}
        {/* Catches: where he was caught (or, for a bowler, where his catches were taken), on the feed's 0-363 grid, a
            fixed view of the ground as the wheel draws it; the boundary is about 181 from the middle. */}
        {(catches?.points || []).map((p, i) => {
          const k = (R + 6) / 181;
          const dx = (p.x - 181) * k; const dy = (p.y - 181) * k;
          const d = Math.hypot(dx, dy); const lim = R + 4;
          const s = d > lim ? lim / d : 1;
          return <circle key={i} cx={c + dx * s} cy={c + dy * s} r={2.6 + Math.min(2, (p.n - 1) * 0.8)} fill="#ffffff"
            fillOpacity="0.9" stroke={colors.bg} strokeWidth="1" />;
        })}
        <rect x={c - 3} y={c - 9} width="6" height="18" rx="2" fill="#c9b27c" />
      </Box>
      <Legend items={[[labels?.[0] || `Faster than his ${Math.round(strikeRate)}`, faster], [labels?.[1] || 'Slower', slower],
        ...(catches?.points?.length ? [[`Caught · ${catches.plotted}/${catches.total}`, '#ffffff']] : [])]} />
    </>
  );
};

/** Where he scores: the scoring wheel on the profile. */
// ---- the wheel's own filters (a gear on the card: phase, pace or spin, a bowling type) ----------------------------

const PHASE_OPTS = [['', 'All overs'], ['powerplay', 'Powerplay'], ['middle', 'Middle'], ['death', 'Death']];
const BOWL_OPTS = [['', 'All bowling'], ['kind:pace', 'Pace'], ['kind:spin', 'Spin'],
  ...['Right-arm pace', 'Left-arm pace', 'Off-spin', 'Leg-spin', 'Left-arm orthodox', 'Left-arm wrist spin'].map((f) => [`family:${f}`, f])];
const PHASE_WORDS = { powerplay: 'powerplay', middle: 'middle overs', death: 'death overs' };
const HAND_OPTS = [['', 'All batters'], ['RHB', 'Right-handers'], ['LHB', 'Left-handers']];
const HAND_WORDS = { RHB: 'right-handers', LHB: 'left-handers' };

/** The filter's words for the card's note, so a screenshot says what it shows ("Spin · death overs"). */
const filterWords = (f) => [f.bowl ? f.bowl.split(':')[1] : null, f.hand ? HAND_WORDS[f.hand] : null,
  f.phase ? PHASE_WORDS[f.phase] : null].filter(Boolean)
  .map((w, i) => (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w)).join(' · ');

const Pill = ({ on, onClick, children }) => (
  <Box component="button" type="button" onClick={onClick} aria-pressed={on}
    sx={{ all: 'unset', cursor: 'pointer', fontSize: 12.5, px: 1.1, minHeight: 32, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', borderRadius: '999px', whiteSpace: 'nowrap',
      border: `1px solid ${on ? colors.accent : colors.borderStrong}`, bgcolor: on ? colors.accent : 'transparent',
      color: on ? colors.bg : colors.textMed, '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
    {children}
  </Box>
);

/** The filter's icon, beside the card's share icon: horizontal sliders; lime with a dot when a filter is on. */
const FilterIcon = ({ open, active, onClick }) => (
  <Box component="button" type="button" onClick={onClick} aria-expanded={open} aria-label="Filter this card"
    sx={{ all: 'unset', cursor: 'pointer', position: 'relative', display: 'inline-flex', p: 0.75, borderRadius: '8px',
      color: active || open ? colors.accent : colors.textMed, '&:focus-visible': { outline: `2px solid ${colors.accent}` } }}>
    <Box component="svg" viewBox="0 0 24 24" sx={{ width: 22, height: 22 }} aria-hidden="true">
      <path fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M4 7h10M18 7h2M4 17h4M12 17h8" />
      <circle cx="16" cy="7" r="2" fill="none" stroke="currentColor" strokeWidth="2" />
      <circle cx="10" cy="17" r="2" fill="none" stroke="currentColor" strokeWidth="2" />
    </Box>
    {active && <Box component="span" sx={{ position: 'absolute', top: 4, right: 4, width: 7, height: 7, borderRadius: '50%', bgcolor: colors.accent }} />}
  </Box>
);

/** The panel the icon opens: phase always; bowling for a batter's card, the batter's hand for a bowler's. "All ..." clears. */
const FilterPanel = ({ filter, setFilter, bowling, hands, bowlOpts }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, p: 1, borderRadius: '12px', bgcolor: colors.surface2 }}>
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
      {PHASE_OPTS.map(([v, l]) => <Pill key={l} on={filter.phase === v} onClick={() => setFilter({ ...filter, phase: v })}>{l}</Pill>)}
    </Box>
    {hands && (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {HAND_OPTS.map(([v, l]) => <Pill key={l} on={(filter.hand || '') === v} onClick={() => setFilter({ ...filter, hand: v })}>{l}</Pill>)}
      </Box>
    )}
    {(bowling || bowlOpts) && (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {(bowlOpts || BOWL_OPTS).map(([v, l]) => <Pill key={l} on={(filter.bowl || '') === v} onClick={() => setFilter({ ...filter, bowl: v })}>{l}</Pill>)}
      </Box>
    )}
  </Box>
);

/** A card's filter state: the choices, whether the panel is open, and the icon for the card's header. */
const useCardFilter = () => {
  const [filter, setFilter] = useState({ phase: '', bowl: '', hand: '' });
  const [open, setOpen] = useState(false);
  const active = !!(filter.phase || filter.bowl || filter.hand);
  return { filter, setFilter, open, active, icon: <FilterIcon open={open} active={active} onClick={() => setOpen((o) => !o)} /> };
};

/** A card's numbers under its own filter (GET /player/{name}/slice), only when a filter is on; null otherwise.
 * `fixedHand`: a hand the card itself sets (the bowler's wheel switch), sent with the filter. */
const useSlice = (player, card, query, filter, fixedHand) => {
  const [state, setState] = useState({ key: null, data: null, loading: false });
  const on = !!(filter.phase || filter.bowl || filter.hand);
  const params = new URLSearchParams(query || '');
  params.set('card', card);
  if (filter.phase) params.set('phase', filter.phase);
  if (filter.bowl) { const [k, v] = filter.bowl.split(':'); params.set(k === 'kind' ? 'kind' : 'family', v); }
  const hand = filter.hand || fixedHand;
  if (hand) params.set('hand', hand);
  const key = on ? params.toString() : null;
  useEffect(() => {
    if (!key) return undefined;
    let cancelled = false;
    setState((st) => ({ ...st, loading: true }));
    fetch(`${config.API_URL}/player/${encodeURIComponent(player)}/slice?${key}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => { if (!cancelled) setState({ key, data, loading: false }); })
      .catch(() => { if (!cancelled) setState({ key, data: null, loading: false }); });
    return () => { cancelled = true; };
  }, [key, player]);
  return on ? { data: state.key === key ? state.data : null, loading: state.loading } : { data: null, loading: false };
};

export const ScoringAreasCard = ({ player, zones, hand, strikeRate, boundary, catches, query }) => {
  const cf = useCardFilter();
  const { filter } = cf;
  const f = useSlice(player, 'wheel_bat', query, filter);
  if (!zones.reduce((a, z) => a + z.runs, 0)) return null;
  const left = hand === 'LHB';
  const on = !!(filter.phase || filter.bowl);
  const d = on && f.data ? f.data : { zones, strike_rate: strikeRate, catches };
  const key = boundary ? ZONES_RHB[left ? MIRROR[boundary.key_zone] : boundary.key_zone].toLowerCase() : null;
  // Descriptive, not advice: we don't know where the fielders stood, so where his boundaries go isn't where to put one.
  const note = on ? `${filterWords(filter)} · ${d.zones ? d.zones.reduce((a, z) => a + z.balls, 0) : 0} balls`
    : boundary ? `Outlined: most of his boundaries off pace, ${key} · ${boundary.key_share}%` : `Share of runs by area (${left ? 'left' : 'right'}-handed)`;
  const empty = on && f.data && !f.data.zones?.length;
  return (
    <ProfileCard id="scoring" title="Where he scores" player={player} note={note} action={cf.icon}>
      {cf.open && <FilterPanel filter={filter} setFilter={cf.setFilter} bowling />}
      <Box sx={{ opacity: on && f.loading ? 0.45 : 1, transition: 'opacity 150ms' }}>
        {empty ? <Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>Too few balls for this filter.</Box>
          : <ScoringWheel zones={d.zones || zones} hand={hand} strikeRate={d.strike_rate || strikeRate} catches={d.catches} outline={on ? null : boundary?.key_zone} />}
      </Box>
    </ProfileCard>
  );
};

/** Who to bowl to him: strike rate against each of six bowling families, and against his own; fastest in lime,
 * slowest in red. The bowler's type, not the variation (we don't have slower balls or googlies). */
export const FamiliesCard = ({ player, families, strikeRate }) => {
  if (!families?.length) return null;
  const best = families.reduce((a, b) => (b.strike_rate > a.strike_rate ? b : a));
  const worst = families.reduce((a, b) => (b.strike_rate < a.strike_rate ? b : a));
  return (
    <ProfileCard id="bowling-types" title="Who to bowl to him" player={player}
      note="Strike rate · bowler's type, not variation · 40+ balls">
      <BarRows format={(v) => Math.round(v)}
        rows={families.map((f) => ({ label: f.family, value: f.strike_rate,
          detail: `${f.balls} balls · ${f.outs} out${f.vs_own != null ? ` · ${sign(f.vs_own, 0)}% v his` : ''}`,
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

// ---- how a bowler takes wickets (services/wicket_style.py) ---------------------------------------------------------

const HOW_PARTS = [['bowled', 'Bowled', LIME, colors.bg], ['lbw', 'LBW', '#7fa833', colors.bg],
  ['caught', 'Caught', SLATE, colors.textHi], ['stumped', 'Stumped', '#363d4b', colors.textMed]];

/** One 100% bar of wickets by type, each share written inside its segment when there's room. */
const SplitBar = ({ shares }) => (
  <Box sx={{ display: 'flex', height: 24, gap: '2px' }}>
    {HOW_PARTS.filter(([k]) => shares[k] > 0).map(([k, , bg, ink], i, arr) => (
      <Box key={k} sx={{ flex: shares[k], minWidth: 0, bgcolor: bg, color: ink, display: 'flex', alignItems: 'center', justifyContent: 'center',
        ...mono, fontSize: 11.5, overflow: 'hidden', whiteSpace: 'nowrap',
        borderRadius: `${i === 0 ? 5 : 0}px ${i === arr.length - 1 ? 5 : 0}px ${i === arr.length - 1 ? 5 : 0}px ${i === 0 ? 5 : 0}px` }}>
        {shares[k] >= 10 ? `${Math.round(shares[k])}%` : ''}
      </Box>
    ))}
  </Box>
);

/** How he takes wickets: his wickets by type against a typical bowler of his type where he bowled (the competitions and
 * years, weighted by his wickets), and how often he attacks the stumps. A style, not a rating. `bat`: the batter's
 * "How he gets out", against a typical batter out to the same kinds of bowling where he batted (no stumps line). */
const WicketsView = ({ player, style, bat, action, panel, filtered, noteOverride }) => {
  const shell = (body, note) => (
    <ProfileCard id={bat ? 'dismissals' : 'wickets'} title={bat ? 'How he gets out' : 'How he takes wickets'} player={player}
      action={action} note={noteOverride || note}>{panel}{body}</ProfileCard>
  );
  if (!style?.wickets) {
    return filtered ? shell(<Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>{`Too few ${bat ? 'dismissals' : 'wickets'} for this filter.`}</Box>) : null;
  }
  const mine = Object.fromEntries(HOW_PARTS.map(([k]) => [k, (100 * style.split[k]) / style.wickets]));
  const kind = style.kind === 'spin' ? 'spinner' : 'pace bowler';
  const a = style.attack;
  const scale = a ? Math.max(50, Math.ceil((Math.max(a.share, a.typical) + 5) / 10) * 10) : 50;
  const row = (label, body) => (
    <Box sx={{ display: 'grid', gridTemplateColumns: '58px 1fr', alignItems: 'center', gap: 1 }}>
      <Box sx={{ fontSize: 12.5, color: colors.textMed, whiteSpace: 'nowrap' }}>{label}</Box>{body}
    </Box>
  );
  return shell(
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.1 }}>
      {row('Him', <SplitBar shares={mine} />)}
      {style.typical && row('Typical', <SplitBar shares={style.typical} />)}
      <Legend items={HOW_PARTS.map(([, label, bg]) => [label, bg])} />
      {a && (
        <Box sx={{ display: 'grid', gridTemplateColumns: '108px 1fr auto', alignItems: 'center', gap: 1, pt: 1, borderTop: `1px solid ${colors.border}` }}>
          <Box sx={{ fontSize: 12.5, color: colors.textMed, whiteSpace: 'nowrap' }}>Attacks the stumps</Box>
          <Box sx={{ position: 'relative', height: 6, bgcolor: 'rgba(255,255,255,0.06)', borderRadius: '3px' }}>
            <Box sx={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(100 * a.share) / scale}%`, bgcolor: LIME, borderRadius: '3px' }} />
            <Box sx={{ position: 'absolute', top: -5, height: 16, width: '2px', left: `${(100 * a.typical) / scale}%`, bgcolor: colors.textHi }} />
          </Box>
          <Box sx={{ ...mono, fontSize: 12.5, whiteSpace: 'nowrap' }}>{`${Math.round(a.share)}% v ${Math.round(a.typical)}%`}</Box>
        </Box>
      )}
    </Box>,
    bat ? (style.typical ? `${style.wickets} outs · typical: same bowling where he batted` : `${style.wickets} outs · too few to compare`)
      : style.typical ? `${style.wickets} wkts · typical: a ${kind} where he bowled` : `${style.wickets} wkts · too few to compare`,
  );
};

/** The card with its filter: a bowler's by phase and the batter's hand, a batter's by phase and the bowling. */
export const WicketsCard = ({ player, style, rows, query, bat }) => {
  const cf = useCardFilter();
  const f = useSlice(player, bat ? 'dismissals' : 'wickets', query, cf.filter);
  if (!style) return <OutsCard player={player} rows={rows} bowling={!bat} />;
  const d = cf.active && f.data ? f.data.wicket_style : style;
  return (
    <Filtered on={cf.active} loading={f.loading}>
      <WicketsView player={player} style={d} bat={bat} action={cf.icon} filtered={cf.active}
        panel={cf.open && <FilterPanel filter={cf.filter} setFilter={cf.setFilter} hands={!bat} bowling={bat} />}
        noteOverride={cf.active && d?.wickets ? `${filterWords(cf.filter)} · ${d.wickets} ${bat ? 'outs' : 'wkts'}${d.typical ? '' : ' · too few to compare'}` : null} />
    </Filtered>
  );
};

/** A group heading between cards: "How to bowl to him", "How to bat against him" (PROFILE_SCOUTING_PLAN.md). */
const GroupHead = ({ children }) => (
  <Box sx={{ ...mono, fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: colors.accent, mt: 1, mb: -0.25 }}>
    {children}
  </Box>
);

const PACE_LINES = ['WIDE_OUTSIDE_OFFSTUMP', 'OUTSIDE_OFFSTUMP', 'ON_THE_STUMPS', 'DOWN_LEG'];
const PACE_LINE_NAMES = ['Wide off', 'Off', 'Stumps', 'Leg'];
const PACE_LENGTHS = ['YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT'];
const PACE_LENGTH_NAMES = { YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };

/** Enough of a map to draw: two or more lengths with balls in two or more lines. */
const mapLengths = (cells) => {
  const by = new Set((cells || []).map((c) => `${c.line}|${c.length}`));
  return PACE_LENGTHS.filter((l) => PACE_LINES.filter((ln) => by.has(`${ln}|${l}`)).length > 1);
};

/** Where to bowl to him: his strike rate in each line and length against his strike rate against that kind of bowling
 * (pace or spin, a switch; one bowling type behind the filter); lime where he scores faster, red slower; the slowest
 * cell with 40+ balls outlined. */
const PaceMapView = ({ player, cells, paceSr, kindWord = 'pace', switcher, action, panel, filtered, noteOverride }) => {
  const by = useMemo(() => Object.fromEntries((cells || []).map((c) => [`${c.line}|${c.length}`, c])), [cells]);
  const lengths = mapLengths(cells);
  if (!paceSr || lengths.length < 2) {
    return filtered ? <ProfileCard id="pace-map" title="Where to bowl to him" player={player} action={action} note={noteOverride}>{switcher}{panel}<Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>Too few balls for this filter.</Box></ProfileCard> : null;
  }
  const shown = (cells || []).filter((c) => lengths.includes(c.length));
  const tight = shown.filter((c) => c.balls >= 40).reduce((a, b) => (!a || b.strike_rate < a.strike_rate ? b : a), null);
  const cw = 58; const ch = 44; const L = 92; const W = L + cw * 4 + 4; const H = 24 + ch * lengths.length + 20;
  return (
    <ProfileCard id="pace-map" title="Where to bowl to him" player={player} action={action}
      note={noteOverride || `Strike rate, against his ${Math.round(paceSr)} v ${kindWord} · 20+ balls a cell`}>
      {switcher}
      {panel}
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" sx={{ width: '100%' }}
        aria-label={shown.map((c) => `${PACE_LENGTH_NAMES[c.length]} ${c.line}: strike rate ${c.strike_rate}`).join('; ')}>
        {lengths.map((l, i) => (
          <text key={l} x={L - 8} y={24 + i * ch + ch / 2 + 2} textAnchor="end" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{PACE_LENGTH_NAMES[l]}</text>
        ))}
        {lengths.map((l, i) => PACE_LINES.map((ln, j) => {
          const cell = by[`${ln}|${l}`];
          const x = L + j * cw; const y = 20 + i * ch;
          if (!cell) return <rect key={`${l}${ln}`} x={x + 2} y={y + 2} width={cw - 4} height={ch - 4} rx="6" fill="none" stroke={colors.border} />;
          const diff = cell.strike_rate - paceSr;
          const op = Math.min(0.9, 0.18 + Math.abs(diff) / 120);
          const ink = diff > 0 && op > 0.6 ? colors.bg : colors.textHi;
          return (
            <g key={`${l}${ln}`}>
              <rect x={x + 2} y={y + 2} width={cw - 4} height={ch - 4} rx="6" fill={diff > 0 ? LIME : RED} fillOpacity={op}
                stroke={cell === tight ? colors.textHi : 'none'} strokeWidth="2">
                <title>{`${PACE_LENGTH_NAMES[l]}, ${PACE_LINE_NAMES[j]}: strike rate ${Math.round(cell.strike_rate)} (${cell.balls} balls, ${cell.outs} out)`}</title>
              </rect>
              <text x={x + cw / 2} y={y + ch / 2 + 2} textAnchor="middle" style={{ ...mono, fontSize: 13, fontWeight: 600, fill: ink }}>{Math.round(cell.strike_rate)}</text>
              <text x={x + cw / 2} y={y + ch / 2 + 14} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: ink, opacity: 0.8 }}>{`${cell.balls}b`}</text>
            </g>
          );
        }))}
        {PACE_LINE_NAMES.map((name, j) => (
          <text key={name} x={L + j * cw + cw / 2} y={H - 4} textAnchor="middle" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>{name}</text>
        ))}
      </Box>
      <Legend items={[[`Faster than his ${Math.round(paceSr)}`, LIME], ['Slower', RED]]} />
    </ProfileCard>
  );
};

const SHOT_NAMES = { DRIVE: 'Drives', FLICK_GLANCE: 'Flicks and glances', PULL_HOOK: 'Pulls and hooks', WORK_PUSH: 'Works and pushes',
  CUT: 'Cuts', SLOG: 'Slogs', SWEEP: 'Sweeps', RAMP_SCOOP: 'Ramps and scoops', REVERSE: 'Reverse sweeps' };

/** How he scores: his main scoring shots' share of his runs, against the average batter of his hand. */
const ShotMixView = ({ player, mix, hand, action, panel, filtered, noteOverride }) => {
  if (!mix?.rows?.length) {
    return filtered ? <ShotMixShell player={player} action={action} note={noteOverride}>{panel}<Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>Too few balls for this filter.</Box></ShotMixShell> : null;
  }
  const max = Math.max(...mix.rows.flatMap((r) => [r.share, r.average]), 1);
  return (
    <ProfileCard id="shot-mix" title="How he scores" player={player} action={action}
      note={noteOverride || `Share of his runs, v the average ${hand === 'LHB' ? 'left' : 'right'}-hander`}>
      {panel}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.8 }}>
        {mix.rows.map((r) => (
          <Box key={r.family} sx={{ display: 'grid', gridTemplateColumns: '128px 1fr 74px', alignItems: 'center', gap: 1 }}>
            <Box sx={{ fontSize: 13.5, whiteSpace: 'nowrap' }}>{SHOT_NAMES[r.family] || r.family}</Box>
            <Box sx={{ position: 'relative', height: 12 }}>
              <Box sx={{ position: 'absolute', left: 0, right: 0, top: 5, height: 2, bgcolor: colors.border }} />
              <Box sx={{ position: 'absolute', left: `${(100 * r.average) / max}%`, top: 1, width: 10, height: 10, ml: '-5px', borderRadius: '50%', bgcolor: SLATE }} />
              <Box sx={{ position: 'absolute', left: `${(100 * r.share) / max}%`, top: 1, width: 10, height: 10, ml: '-5px', borderRadius: '50%', bgcolor: LIME }} />
            </Box>
            <Box sx={{ ...mono, fontSize: 12, textAlign: 'right', whiteSpace: 'nowrap' }}>
              <Box component="span" sx={{ color: colors.textHi }}>{`${Math.round(r.share)}%`}</Box>
              <Box component="span" sx={{ color: colors.textLo }}>{` v ${Math.round(r.average)}%`}</Box>
            </Box>
          </Box>
        ))}
      </Box>
      <Legend items={[['Him', LIME], ['Average batter', SLATE]]} />
    </ProfileCard>
  );
};

// ---- bowlers ------------------------------------------------------------------------------------------------------

const LINES = ['WIDE_OUTSIDE_OFFSTUMP', 'OUTSIDE_OFFSTUMP', 'ON_THE_STUMPS', 'DOWN_LEG'];
const LINE_NAMES = ['Wide off', 'Off', 'Stumps', 'Leg'];
const LENGTHS = ['YORKER', 'FULL', 'GOOD_LENGTH', 'SHORT_OF_A_GOOD_LENGTH', 'SHORT'];
const LENGTH_NAMES = { YORKER: 'Yorker', FULL: 'Full', GOOD_LENGTH: 'Good', SHORT_OF_A_GOOD_LENGTH: 'Back of length', SHORT: 'Short' };

/** Economy by line and length (to all batters), against his own economy: cheaper in lime, dearer in red. */
const PitchView = ({ player, cells, economy, action, panel, filtered, noteOverride }) => {
  const by = useMemo(() => Object.fromEntries((cells || []).map((c) => [`${c.line}|${c.length}`, c])), [cells]);
  const lengths = LENGTHS.filter((l) => LINES.some((ln) => by[`${ln}|${l}`]));
  if (!lengths.length) {
    return filtered ? <ProfileCard id="pitch" title="Where he bowls" player={player} action={action} note={noteOverride}>{panel}<Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>Too few balls for this filter.</Box></ProfileCard> : null;
  }
  const cheapest = (cells || []).filter((c) => c.balls >= 40).reduce((a, b) => (!a || b.economy < a.economy ? b : a), null);
  const cw = 58; const ch = 44; const L = 92; const W = L + cw * 4 + 4; const H = 24 + ch * lengths.length + 20;
  return (
    <ProfileCard id="pitch" title="Where he bowls" player={player} action={action} note={noteOverride || 'Runs an over · 15+ balls a cell'}>
      {panel}
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
              <text x={x + cw / 2} y={y + ch / 2 + 14} textAnchor="middle" style={{ ...mono, fontSize: 11, fill: ink, opacity: 0.8 }}>{`${cell.balls}b`}</text>
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
            <Box sx={{ ...mono, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: colors.textLo }}>{PHASE_NAMES[p.phase] || p.phase}</Box>
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

/** Where batters score off him, one hand at a time (a switch), with his catches on the same wheel: wedge size the
 * share of runs, colour faster or slower than batters of that hand go off him, dots where the catches were taken. */
export const BowlerWheelCard = ({ player, byHand, catchesByHand, query }) => {
  const hands = ['RHB', 'LHB'].filter((h) => byHand?.[h]);
  const [pick, setPick] = useState(null);
  const cf = useCardFilter();
  const { filter } = cf;
  const h = hands.includes(pick) ? pick : hands[0];
  const f = useSlice(player, 'wheel_bowl', query, filter, h);
  if (!hands.length) return null;
  const on = !!filter.phase;
  const base = byHand[h];
  const d = on && f.data ? f.data : { ...base, catches: catchesByHand?.[h] };
  const empty = on && f.data && !f.data.zones?.length;
  return (
    <ProfileCard id="scoring-against" title="Where batters score off him" player={player}
      note={`${h === 'LHB' ? 'Left' : 'Right'}-handers${on ? ` · ${PHASE_WORDS[filter.phase]}` : ''} · share of runs by area`} action={cf.icon}>
      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', alignItems: 'center' }}>
        {hands.length > 1 && (
          <Box role="tablist" aria-label="Batter's hand" sx={{ display: 'inline-flex', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
            {hands.map((x) => (
              <Box key={x} component="button" type="button" role="tab" aria-selected={x === h} onClick={() => setPick(x)}
                sx={{ all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13.5, px: 1.5, minHeight: 32, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', borderRadius: '999px',
                  bgcolor: x === h ? colors.accent : 'transparent', color: x === h ? colors.bg : colors.textMed }}>
                {x === 'RHB' ? 'Right-handers' : 'Left-handers'}
              </Box>
            ))}
          </Box>
        )}
      </Box>
      {cf.open && <FilterPanel filter={filter} setFilter={cf.setFilter} />}
      <Box sx={{ opacity: on && f.loading ? 0.45 : 1, transition: 'opacity 150ms' }}>
        {empty ? <Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>Too few balls for this filter.</Box>
          : <ScoringWheel zones={d.zones || base.zones} hand={h} strikeRate={d.strike_rate || base.strike_rate} catches={d.catches}
            labels={[`Faster than ${Math.round(d.strike_rate || base.strike_rate)} off him`, 'Slower']} />}
      </Box>
    </ProfileCard>
  );
};

/** What works against him: batters' strike rate with each shot against him, against their strike rate off him, with
 * balls per wicket beside it (a shot that scores fast and gets you out every 8 balls isn't simply "working"). */
const ShotsAgainstView = ({ player, rows, srAgainst, action, panel, filtered, noteOverride }) => {
  if (!rows?.length || srAgainst == null) {
    return filtered ? <ProfileCard id="shots-against" title="What works against him" player={player} action={action} note={noteOverride}>{panel}<Box sx={{ color: colors.textLo, fontSize: 13.5, py: 4, textAlign: 'center' }}>Too few balls for this filter.</Box></ProfileCard> : null;
  }
  const top = rows.slice(0, 7);
  const max = Math.max(...top.map((r) => Math.abs(r.vs_all)), 1);
  return (
    <ProfileCard id="shots-against" title="What works against him" player={player} action={action}
      note={noteOverride || `Batters' strike rate by shot, v ${Math.round(srAgainst)} off him`}>
      {panel}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.9 }}>
        {top.map((r, i) => (
          <Box key={r.family} sx={{ display: 'grid', gridTemplateColumns: '136px 1fr 40px', alignItems: 'center', gap: 1 }}>
            <Box sx={{ minWidth: 0, lineHeight: 1.15 }}>
              <Box sx={{ fontSize: 13.5, whiteSpace: 'nowrap' }}>{SHOT_NAMES[r.family] || r.family}</Box>
              <Box sx={{ fontSize: 11, color: colors.textLo, whiteSpace: 'nowrap' }}>
                {`SR ${Math.round(r.strike_rate)} · ${r.wickets ? `${Math.round(r.balls / r.wickets)} balls per wicket` : `${r.balls} balls, no wicket`}`}
              </Box>
            </Box>
            <Box sx={{ position: 'relative', height: 12 }}>
              <Box sx={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '1px', bgcolor: colors.borderStrong }} />
              <Box sx={{ position: 'absolute', top: 0, height: '100%', borderRadius: '4px',
                left: r.vs_all >= 0 ? '50%' : `${50 - (50 * Math.abs(r.vs_all)) / max}%`, width: `${(50 * Math.abs(r.vs_all)) / max}%`,
                bgcolor: i === 0 ? LIME : r.vs_all >= 0 ? SLATE : RED }} />
            </Box>
            <Box sx={{ ...mono, fontSize: 13, textAlign: 'right' }}>{sign(r.vs_all, 0)}</Box>
          </Box>
        ))}
      </Box>
    </ProfileCard>
  );
};

const ShotMixShell = ({ player, action, note, children }) => (
  <ProfileCard id="shot-mix" title="How he scores" player={player} action={action} note={note}>{children}</ProfileCard>
);

/** A card wrapper: its filter (icon and panel), the filtered numbers when it's on, the card's own view drawing them. */
const Filtered = ({ on, loading, children }) => <Box sx={{ opacity: on && loading ? 0.5 : 1, transition: 'opacity 150ms' }}>{children}</Box>;

const KIND_FAMILIES = {
  pace: ['Right-arm pace', 'Left-arm pace'],
  spin: ['Off-spin', 'Leg-spin', 'Left-arm orthodox', 'Left-arm wrist spin'],
};

/** A two-way switch in a card (pace or spin here; the bowler's wheel has its own for the batter's hand). */
const Switch = ({ label, options, value, onChange }) => (
  <Box role="tablist" aria-label={label} sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
    {options.map(([v, text]) => (
      <Box key={v} component="button" type="button" role="tab" aria-selected={v === value} onClick={() => onChange(v)}
        sx={{ all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 13.5, px: 1.5, minHeight: 32, boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', borderRadius: '999px',
          bgcolor: v === value ? colors.accent : 'transparent', color: v === value ? colors.bg : colors.textMed,
          '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
        {text}
      </Box>
    ))}
  </Box>
);

/** Where to bowl to him: pace or spin (the switch, shown when both have a map), each against his own strike rate
 * against that kind; the filter adds a phase and one bowling type of the chosen kind. */
export const PaceMapCard = ({ player, cells, paceSr, spinCells, spinSr, query }) => {
  const kinds = [['pace', cells, paceSr], ['spin', spinCells, spinSr]].filter(([, c, sr]) => sr && mapLengths(c).length >= 2);
  const [pick, setPick] = useState(null);
  const kind = kinds.some(([k]) => k === pick) ? pick : kinds[0]?.[0] || 'pace';
  const cf = useCardFilter();
  // The slice always says which kind (a filter on spin must stay on spin); a bowling type narrows it further.
  const eff = cf.active ? { ...cf.filter, bowl: cf.filter.bowl || `kind:${kind}` } : cf.filter;
  const f = useSlice(player, 'pace_map', query, eff);
  if (!kinds.length && !cf.active) return null;
  const base = kind === 'spin' ? { cells: spinCells, sr: spinSr } : { cells, sr: paceSr };
  const d = cf.active && f.data ? { cells: f.data.pace_cells, sr: f.data.pace_sr } : base;
  const family = cf.filter.bowl?.startsWith('family:') ? cf.filter.bowl.slice(7) : null;
  const word = family || kind;
  const switcher = kinds.length > 1 && (
    <Switch label="Pace or spin" value={kind} options={[['pace', 'Pace'], ['spin', 'Spin']]}
      onChange={(k) => { setPick(k); if (family) cf.setFilter({ ...cf.filter, bowl: '' }); }} />
  );
  const bowlOpts = [['', `All ${kind}`], ...KIND_FAMILIES[kind].map((x) => [`family:${x}`, x])];
  return (
    <Filtered on={cf.active} loading={f.loading}>
      <PaceMapView player={player} cells={d.cells} paceSr={d.sr} kindWord={word.toLowerCase()} switcher={switcher}
        action={cf.icon} filtered={cf.active}
        panel={cf.open && <FilterPanel filter={cf.filter} setFilter={cf.setFilter} bowlOpts={bowlOpts} />}
        noteOverride={cf.active ? `${[family, cf.filter.phase ? PHASE_WORDS[cf.filter.phase] : null].filter(Boolean).join(' · ').replace(/^./, (c) => c.toUpperCase())} · v his ${d.sr ? Math.round(d.sr) : '–'} v ${family ? 'it' : kind}` : null} />
    </Filtered>
  );
};

export const ShotMixCard = ({ player, mix, hand, query }) => {
  const cf = useCardFilter();
  const f = useSlice(player, 'shot_mix', query, cf.filter);
  const m = cf.active && f.data ? f.data.shot_mix : mix;
  if (!cf.active && !mix?.rows?.length) return null;
  return (
    <Filtered on={cf.active} loading={f.loading}>
      <ShotMixView player={player} mix={m} hand={hand} action={cf.icon} filtered={cf.active}
        panel={cf.open && <FilterPanel filter={cf.filter} setFilter={cf.setFilter} bowling />}
        noteOverride={cf.active ? `${filterWords(cf.filter)} · v the average ${hand === 'LHB' ? 'left' : 'right'}-hander` : null} />
    </Filtered>
  );
};

export const PitchCard = ({ player, cells, economy, query }) => {
  const cf = useCardFilter();
  const f = useSlice(player, 'pitch', query, cf.filter);
  const d = cf.active && f.data ? { cells: f.data.cells, econ: f.data.economy } : { cells, econ: economy };
  return (
    <Filtered on={cf.active} loading={f.loading}>
      <PitchView player={player} cells={d.cells} economy={d.econ ?? economy} action={cf.icon} filtered={cf.active}
        panel={cf.open && <FilterPanel filter={cf.filter} setFilter={cf.setFilter} hands />}
        noteOverride={cf.active ? `${filterWords(cf.filter)} · runs an over, his ${d.econ != null ? d.econ.toFixed(1) : '–'}` : null} />
    </Filtered>
  );
};

export const ShotsAgainstCard = ({ player, rows, srAgainst, query }) => {
  const cf = useCardFilter();
  const f = useSlice(player, 'shots_against', query, cf.filter);
  const d = cf.active && f.data ? { rows: f.data.shots_against, sr: f.data.strike_rate_against } : { rows, sr: srAgainst };
  if (!cf.active && (!rows?.length || srAgainst == null)) return null;
  return (
    <Filtered on={cf.active} loading={f.loading}>
      <ShotsAgainstView player={player} rows={d.rows} srAgainst={d.sr} action={cf.icon} filtered={cf.active}
        panel={cf.open && <FilterPanel filter={cf.filter} setFilter={cf.setFilter} hands />}
        noteOverride={cf.active ? `${filterWords(cf.filter)} · v ${d.sr != null ? Math.round(d.sr) : '–'} off him` : null} />
    </Filtered>
  );
};

/** The batter's or bowler's four cards. */
export const RoleCardSet = ({ role, player, data, hand, query }) => {
  if (!data) return null;
  if (role === 'bat') {
    const h = data.hand || hand;
    return (
      <>
        {data.start?.points?.length > 1 && <StartCard player={player} start={data.start} />}
        <GroupHead>How to bowl to him</GroupHead>
        <FamiliesCard player={player} families={data.families} strikeRate={data.strike_rate} />
        <PaceMapCard player={player} cells={data.pace_cells} paceSr={data.pace_sr} spinCells={data.spin_cells} spinSr={data.spin_sr} query={query} />
        {data.zones?.length > 0 && <ScoringAreasCard player={player} zones={data.zones} hand={h} strikeRate={data.strike_rate} boundary={data.boundary} catches={data.catches} query={query} />}
        <ShotMixCard player={player} mix={data.shot_mix} hand={h} query={query} />
        <WicketsCard player={player} style={data.out_style} rows={data.dismissals} query={query} bat />
      </>
    );
  }
  return (
    <>
      <GroupHead>How to bat against him</GroupHead>
      <PitchCard player={player} cells={data.cells} economy={data.economy} query={query} />
      <BowlerWheelCard player={player} byHand={data.zones_by_hand} catchesByHand={data.catches_by_hand} query={query} />
      <ShotsAgainstCard player={player} rows={data.shots_against} srAgainst={data.strike_rate_against} query={query} />
      <PhaseCard player={player} phases={data.phases} />
      <HandsCard player={player} hands={data.hands} />
      <WicketsCard player={player} style={data.wicket_style} rows={data.wickets} query={query} />
    </>
  );
};
