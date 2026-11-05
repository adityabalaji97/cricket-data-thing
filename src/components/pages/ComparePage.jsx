import React, { useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, TextField } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import { ordinal, signed } from '../playerProfile/verdict/verdictFormat';
import { Eyebrow, PageFooter, PageSkeleton, usePageData } from '../pageKit/pageKit';

// Compare (the menu overhaul, 5 Nov 2026): one page in place of Batter Comparison, Matchups, Team Comparison and the
// Doppelgangers leaderboard. Two players side by side on every ranked measure from /player-compare (overall, by phase,
// by opponent; same pool, same window, so both dots sit on one spread), or a batter against a bowler from the query builder.

const A_COL = colors.accent;
const B_COL = '#5b9bf0';
const ROLE_NAMES = { bat: 'Batting', bowl: 'Bowling' };
// "Sharma" alone could be anyone: an initial and the surname.
const shortName = (n) => { const w = (n || '').split(' '); return w.length > 1 ? `${w[0][0]} ${w[w.length - 1]}` : n; };
// Column heads for a pair: first names ("Jasprit", "Arshdeep"), unless a name starts with initials or the two clash.
const pairNames = (a, b) => {
  const first = (n) => { const w = (n || '').split(' '); return w.length > 1 && !/^[A-Z]{1,3}$/.test(w[0]) ? w[0] : null; };
  const fa = first(a); const fb = first(b);
  return fa && fb && fa !== fb ? [fa, fb] : [shortName(a), shortName(b)];
};

const usePlayers = () => {
  const [players, setPlayers] = useState([]);
  useEffect(() => {
    fetch(`${config.API_URL}/players`).then((r) => r.json()).then((d) => setPlayers(Array.isArray(d) ? d : [])).catch(() => setPlayers([]));
  }, []);
  return players;
};

const Pills = ({ items, value, onChange, label }) => (
  <Box role="tablist" aria-label={label} sx={{ display: 'inline-flex', alignSelf: 'flex-start', border: `1px solid ${colors.borderStrong}`, borderRadius: '999px', p: '2px' }}>
    {items.map(([key, name]) => (
      <Box key={key} component="button" type="button" role="tab" aria-selected={key === value} onClick={() => onChange(key)}
        sx={{
          all: 'unset', cursor: 'pointer', fontFamily: fonts.display, fontWeight: 600, fontSize: 14, px: 1.75, py: '4px', borderRadius: '999px',
          bgcolor: key === value ? colors.accent : 'transparent', color: key === value ? colors.bg : colors.textMed,
          '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 },
        }}>
        {name}
      </Box>
    ))}
  </Box>
);

const Picker = ({ label, value, onChange, options, colour }) => (
  <Autocomplete size="small" options={options} value={value || null} onChange={(_, v) => onChange(v)}
    renderInput={(params) => (
      <TextField {...params} label={label}
        sx={{ '& .MuiOutlinedInput-notchedOutline': { borderColor: colour }, '& label': { color: colour } }} />
    )}
    sx={{ flex: 1, minWidth: 0 }} />
);

// Each measure arrives with its own format from /player-compare.
const FORMATS = {
  signed2: (v) => signed(v, 2), signed1: (v) => signed(v, 1), int: (v) => String(Math.round(v)),
  dec1: (v) => v.toFixed(1), dec2: (v) => v.toFixed(2), pct: (v) => `${v.toFixed(1)}%`,
};
const show = (m, v) => (v === null || v === undefined ? '–' : (FORMATS[m.format] || FORMATS.dec1)(v));

/** One measure, both players: their values and ranks, two dots on the pool's spread (better to the right). */
const PairStrip = ({ m }) => {
  const W = 343; const H = 16;
  const q = m.quantiles || [];
  const va = m.a.value; const vb = m.b.value;
  const at = (f) => q[Math.min(q.length - 1, Math.max(0, Math.round(f * (q.length - 1))))];
  const lo = Math.min(at(0.02), va, vb);
  const hi = Math.max(at(0.98), va, vb);
  const span = hi - lo || 1;
  const x = (v) => {
    const t = (Math.min(hi, Math.max(lo, v)) - lo) / span;
    return 6 + (m.lower_is_better ? 1 - t : t) * (W - 12);
  };
  const aBetter = m.a.rank < m.b.rank;
  const cell = (p, col, better) => (
    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75, justifyContent: 'flex-end', minWidth: 0, whiteSpace: 'nowrap' }}>
      <Box component="span" sx={{ fontFamily: fonts.display, fontWeight: better ? 700 : 500, fontSize: 15, color: better ? col : colors.textMed }}>
        {show(m, p.value)}
      </Box>
      <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 10, color: colors.textLo }}>{ordinal(p.rank)}</Box>
    </Box>
  );
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: '3px', py: 0.5 }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 86px 86px', columnGap: 1, alignItems: 'baseline' }}>
        <Box component="span" sx={{ color: colors.textMed, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.label}</Box>
        {cell(m.a, A_COL, aBetter)}
        {cell(m.b, B_COL, !aBetter && m.a.rank !== m.b.rank)}
      </Box>
      {q.length > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" aria-hidden="true">
          <rect x="0" y="7" width={W} height="2" rx="1" fill={colors.surface2} />
          {q.map((v, i) => <rect key={i} x={x(v) - 0.5} y="4" width="1" height="8" fill={colors.textGhost} opacity="0.8" />)}
          <rect x={x(m.median) - 0.75} y="0" width="1.5" height={H} fill={colors.textLo} />
          <circle cx={x(vb)} cy="8" r="5" fill={B_COL} stroke={colors.bg} strokeWidth="2" />
          <circle cx={x(va)} cy="8" r="5" fill={A_COL} stroke={colors.bg} strokeWidth="2" />
        </svg>
      )}
    </Box>
  );
};

const PlayersTab = ({ a, b, fmt, setParams, players }) => {
  const c = usePageData(a && b ? '/player-compare' : null, `a=${encodeURIComponent(a || '')}&b=${encodeURIComponent(b || '')}&format=${fmt}`);
  const roles = c.status === 'ready' ? c.data.roles || {} : {};
  const shared = ['bat', 'bowl'].filter((r) => roles[r]);
  const [role, setRole] = useState(null);
  const [section, setSection] = useState('Overall');
  const shown = shared.includes(role) ? role : shared[0];
  const sections = shown ? roles[shown].sections : [];
  const sec = sections.find((s) => s.title === section) || sections[0];
  const [na, nb] = shown ? pairNames(roles[shown].a, roles[shown].b) : [a, b];

  return (
    <>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Picker label="Player 1" value={a} onChange={(v) => setParams({ a: v || '' })} options={players} colour={A_COL} />
        <Picker label="Player 2" value={b} onChange={(v) => setParams({ b: v || '' })} options={players} colour={B_COL} />
      </Box>
      {(!a || !b) && <Box sx={{ color: colors.textLo, fontSize: 14 }}>Pick two players to put them side by side.</Box>}
      {a && b && c.status !== 'ready' && (
        c.status === 'empty' || c.status === 'error'
          ? <Box sx={{ color: colors.textLo, fontSize: 14 }}>This couldn't load just now. Try again shortly.</Box>
          : <PageSkeleton />
      )}
      {c.status === 'ready' && (
        !shown ? (
          <Box sx={{ color: colors.textLo, fontSize: 14 }}>
            {`They don't share a role with enough ${fmt}s against strong sides since Jan ${c.data.window?.start_date?.slice(0, 4)}. If one bats and the other bowls, try the batter v bowler tab.`}
          </Box>
        ) : (
          <ProfileCard id="compare" title={`${ROLE_NAMES[shown]}, side by side`} player={`${a} v ${b}`}
            note={`Ranked among ${roles[shown].pool} players since Jan ${c.data.window.start_date.slice(0, 4)} · ${c.data.scope_label}`}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {shared.length > 1 && <Pills label="Role" items={shared.map((r) => [r, ROLE_NAMES[r]])} value={shown} onChange={setRole} />}
              {sections.length > 1 && <Pills label="Measures" items={sections.map((s) => [s.title, s.title])} value={sec.title} onChange={setSection} />}
            </Box>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 86px 86px', columnGap: 1, fontSize: 12.5, fontWeight: 700 }}>
              <span />
              <Box component={Link} to={`/player?name=${encodeURIComponent(a)}`} sx={{ color: A_COL, textAlign: 'right', textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{na}</Box>
              <Box component={Link} to={`/player?name=${encodeURIComponent(b)}`} sx={{ color: B_COL, textAlign: 'right', textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{nb}</Box>
            </Box>
            {sec.groups.map((g) => (
              <Box key={g.label || 'all'} sx={{ display: 'flex', flexDirection: 'column' }}>
                {g.label && <Box sx={{ mt: 0.75 }}><Eyebrow>{g.label}</Eyebrow></Box>}
                {g.metrics.map((m) => <PairStrip key={m.key} m={m} />)}
              </Box>
            ))}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', fontFamily: fonts.mono, fontSize: 9.5, color: colors.textFaint }}>
              <span>← worse</span><span>│ median</span><span>better →</span>
            </Box>
            {sec.title !== 'Overall' && (
              <Box sx={{ fontSize: 11.5, color: colors.textLo }}>Phases and opponents need 60 balls each; a missing row means one of them has fewer there.</Box>
            )}
          </ProfileCard>
        )
      )}
    </>
  );
};

const Stat = ({ label, value }) => (
  <Box sx={{ border: `1px solid ${colors.borderStrong}`, borderRadius: '12px', px: 1.25, py: 1, minWidth: 0 }}>
    <Box sx={{ fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textLo, whiteSpace: 'nowrap' }}>{label}</Box>
    <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 21 }}>{value}</Box>
  </Box>
);

const MatchupTab = ({ bat, bowl, fmt, setParams, players }) => {
  const [state, setState] = useState({ status: 'idle', data: null });
  useEffect(() => {
    if (!bat || !bowl) { setState({ status: 'idle', data: null }); return undefined; }
    let cancelled = false;
    setState({ status: 'loading', data: null });
    const q = new URLSearchParams({ format: fmt, batters: bat, bowlers: bowl });
    const one = fetch(`${config.API_URL}/query/deliveries?${q}&group_by=batter`).then((r) => r.json());
    const years = fetch(`${config.API_URL}/query/deliveries?${q}&group_by=year`).then((r) => r.json());
    Promise.all([one, years]).then(([o, y]) => {
      if (cancelled) return;
      const row = (o.data || [])[0];
      setState(row ? { status: 'ready', data: { row, years: (y.data || []).sort((p, r) => p.year - r.year) } } : { status: 'empty', data: null });
    }).catch(() => { if (!cancelled) setState({ status: 'error', data: null }); });
    return () => { cancelled = true; };
  }, [bat, bowl, fmt]);
  const qb = bat && bowl ? `/query?batters=${encodeURIComponent(bat)}&bowlers=${encodeURIComponent(bowl)}&group_by=line&group_by=length` : null;
  const r = state.data?.row;
  return (
    <>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Picker label="Batter" value={bat} onChange={(v) => setParams({ bat: v || '' })} options={players} colour={A_COL} />
        <Picker label="Bowler" value={bowl} onChange={(v) => setParams({ bowl: v || '' })} options={players} colour={B_COL} />
      </Box>
      {state.status === 'idle' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>Pick a batter and a bowler: every ball between them.</Box>}
      {state.status === 'loading' && <PageSkeleton />}
      {state.status === 'empty' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>{`They haven't met in a ${fmt} in the data.`}</Box>}
      {state.status === 'error' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>This couldn't load just now. Try again shortly.</Box>}
      {state.status === 'ready' && (
        <ProfileCard id="matchup" title={`${shortName(bat)} v ${shortName(bowl)}`} player={`${bat} v ${bowl}`}
          note={`${fmt}s, every ball they've met`}>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 1 }}>
            <Stat label="Runs (balls)" value={`${r.runs} (${r.balls})`} />
            <Stat label="Outs" value={r.wickets} />
            <Stat label="Strike rate" value={Math.round(r.strike_rate)} />
            <Stat label="Dots" value={`${Math.round(r.dot_percentage)}%`} />
            <Stat label="Boundaries" value={`${Math.round(r.boundary_percentage)}%`} />
            <Stat label="False shots" value={r.control_percentage != null ? `${Math.round(100 - r.control_percentage)}%` : '–'} />
          </Box>
          {state.data.years.length > 1 && (
            <Box sx={{ mt: 0.5 }}>
              <Eyebrow>By year · runs (balls), outs</Eyebrow>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '4px 12px', mt: 0.5, fontSize: 12.5, color: colors.textMed }}>
                {state.data.years.map((y) => (
                  <Box key={y.year} component="span" sx={{ whiteSpace: 'nowrap' }}>
                    <Box component="span" sx={{ fontFamily: fonts.mono, color: colors.textLo }}>{`'${String(y.year).slice(2)} `}</Box>
                    {`${y.runs} (${y.balls})${y.wickets ? `, ${y.wickets} out` : ''}`}
                  </Box>
                ))}
              </Box>
            </Box>
          )}
          <Box component={Link} to={qb} sx={{ color: colors.accent, fontSize: 13.5, textDecoration: 'none', mt: 0.5 }}>By line and length in the query builder →</Box>
        </ProfileCard>
      )}
    </>
  );
};

const ComparePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const q = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const tab = q.get('tab') === 'matchup' ? 'matchup' : 'players';
  const fmt = q.get('format') === 'ODI' ? 'ODI' : 'T20';
  const players = usePlayers();
  const setParams = (patch) => {
    const next = new URLSearchParams(location.search);
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    navigate({ search: `?${next.toString()}` }, { replace: true });
  };
  useEffect(() => { document.title = 'Compare · Hindsight'; }, []);

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', px: 2, pt: 1.5, pb: 3, display: 'flex', flexDirection: 'column', gap: 1.5, color: colors.textHi }}>
      <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 27 }}>Compare</Box>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Pills label="Compare" items={[['players', 'Two players'], ['matchup', 'Batter v bowler']]} value={tab} onChange={(t) => setParams({ tab: t === 'players' ? '' : t })} />
        <Pills label="Format" items={[['T20', 'T20'], ['ODI', 'ODI']]} value={fmt} onChange={(f) => setParams({ format: f === 'T20' ? '' : f })} />
      </Box>
      {tab === 'players'
        ? <PlayersTab a={q.get('a')} b={q.get('b')} fmt={fmt} setParams={setParams} players={players} />
        : <MatchupTab bat={q.get('bat')} bowl={q.get('bowl')} fmt={fmt} setParams={setParams} players={players} />}
      <PageFooter queryLink="/query" />
    </Box>
  );
};

export default ComparePage;
