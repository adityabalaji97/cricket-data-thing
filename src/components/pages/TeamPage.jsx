import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, TextField } from '@mui/material';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { rememberEntity } from '../../utils/recentEntities';
import { colors, fonts } from '../../theme/hindsightDark';
import { getTeamAbbr } from '../../utils/teamAbbreviations';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import ProfileFilters from '../playerProfile/cards/ProfileFilters';
import TeamSquad from './TeamSquad';
import {
  Eyebrow, PageFooter, PageHeader, PageSkeleton, SummaryRows, ValueList, ordinal, readWindow, signed, usePageData, windowChip,
  windowQuery, writeSearch,
} from '../pageKit/pageKit';
// The sides with Pick your XI (services/intl_xi.py TEAMS): the top 10 T20I sides.
const PICK_XI = ['India', 'Australia', 'England', 'South Africa', 'New Zealand', 'Pakistan', 'West Indies', 'Sri Lanka', 'Afghanistan', 'Bangladesh'];

// The team page (TEAM_VENUE_PLAN.md T3): a summary ranked against the sides of its competition (its league, or the
// top 12 for an international side), the last 8, then seven cards: rating, by phase, who bats where, who bowls when,
// top players, where they win, against each side. One cached call (GET /team-page) for the page's window.

const PHASES = [['powerplay', 'Powerplay'], ['middle', 'Middle'], ['death', 'Death']];

const summaryRows = (p) => {
  const rows = [];
  if (p.rating) rows.push({ rank: `${ordinal(p.rating.rank)} of ${p.rating.of}`, what: `Rating · ${p.rating.now}`, lead: true });
  const items = [];
  PHASES.forEach(([k, n]) => {
    const ph = p.phases?.[k];
    if (!ph) return;
    items.push({ rank: ph.bat.rank, of: ph.bat.of,
      what: ph.bat.measure === 'strike_rate' ? `${n} batting · SR ${ph.bat.strike_rate}` : `${n} batting · ${signed(ph.bat.raa_per_100)} v par` });
    items.push({ rank: ph.bowl.rank, of: ph.bowl.of, what: `${n} bowling · ${ph.bowl.economy.toFixed(2)}` });
  });
  if (items.length) {
    const sorted = [...items].sort((a, b) => a.rank / a.of - b.rank / b.of);
    const best = sorted[0]; const worst = sorted[sorted.length - 1];
    rows.push({ rank: `${ordinal(best.rank)} of ${best.of}`, what: best.what });
    if (worst !== best) rows.push({ rank: `${ordinal(worst.rank)} of ${worst.of}`, what: worst.what });
  }
  rows.push({ rank: `${p.won}–${p.lost}`, what: `Won–lost · ${p.played} matches` });
  return rows;
};

const LastGames = ({ games }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
    <Eyebrow>{`Last ${games.length}`}</Eyebrow>
    <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(games.length, 1)}, minmax(0, 1fr))`, gap: 0.5 }}>
      {games.map((g) => {
        const tone = g.result === 'won' ? colors.accent : g.result === 'lost' ? colors.red : colors.textLo;
        return (
          <Box key={`${g.date}-${g.opp}`} title={`${g.date}: v ${g.opp}, ${g.result || 'no result'} · scorecard`}
            {...(g.match_id ? { component: Link, to: `/scorecard/${g.match_id}` } : {})}
            sx={{ border: `1px solid ${g.result ? tone : colors.borderStrong}`, borderRadius: '8px', textAlign: 'center', py: 0.5, minWidth: 0,
              textDecoration: 'none', color: 'inherit', '&:hover, &:focus-visible': { bgcolor: colors.surface2, outline: 'none' } }}>
            <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 16, color: tone }}>{g.result === 'won' ? 'W' : g.result === 'lost' ? 'L' : '–'}</Box>
            <Box sx={{ fontFamily: fonts.mono, fontSize: 11, color: colors.textLo, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.opp_short}</Box>
          </Box>
        );
      })}
    </Box>
  </Box>
);

const RatingCard = ({ team, rating }) => {
  const pts = rating.series;
  const W = 340; const H = 160; const L = 36; const R = 12; const T = 16; const B = 136;
  const lo = Math.min(...pts.map((p) => p.elo)) - 20; const hi = Math.max(...pts.map((p) => p.elo)) + 20;
  const sx = (i) => L + (i / Math.max(1, pts.length - 1)) * (W - L - R);
  const sy = (v) => B - ((v - lo) / (hi - lo)) * (B - T);
  const ticks = [0, 1, 2, 3].map((k) => Math.round((lo + ((hi - lo) * k) / 3) / 10) * 10);
  const years = [];
  pts.forEach((p, i) => { const y = p.date.slice(0, 4); if (!years.find((x) => x.y === y)) years.push({ y, i }); });
  const end = pts[pts.length - 1];
  const path = pts.map((p, i) => `${i ? 'L' : 'M'}${sx(i).toFixed(1)},${sy(p.elo).toFixed(1)}`).join(' ');
  return (
    <ProfileCard id="rating" title="Rating" player={team} note={`Elo after each match · ${ordinal(rating.rank)} of ${rating.of} now`}>
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Rating, ${pts[0].elo} to ${end.elo}`} sx={{ width: '100%', display: 'block' }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke={colors.border} />
            <text x={L - 5} y={sy(v) + 3} textAnchor="end" style={{ fontFamily: fonts.mono, fontSize: 11, fill: colors.textLo }}>{v}</text>
          </g>
        ))}
        {years.map(({ y, i }) => (
          <text key={y} x={sx(i)} y={H - 6} style={{ fontFamily: fonts.mono, fontSize: 11, fill: colors.textLo }}>{y}</text>
        ))}
        <path d={path} fill="none" stroke={colors.accent} strokeWidth="2" />
        <circle cx={sx(pts.length - 1)} cy={sy(end.elo)} r="4" fill={colors.accent} />
        <text x={sx(pts.length - 1) - 7} y={sy(end.elo) - 8} textAnchor="end"
          style={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, fill: colors.textHi, paintOrder: 'stroke', stroke: colors.surface1, strokeWidth: 3 }}>{end.elo}</text>
      </Box>
    </ProfileCard>
  );
};

const PhaseCard = ({ team, phases }) => {
  const rows = [];
  PHASES.forEach(([k, n]) => {
    const ph = phases[k];
    if (!ph) return;
    rows.push({ key: `${k}-bat`, label: `${n} batting`,
      value: ph.bat.measure === 'strike_rate' ? `${ph.bat.strike_rate}` : signed(ph.bat.raa_per_100, 1), ...ph.bat });
    rows.push({ key: `${k}-bowl`, label: `${n} bowling`, value: ph.bowl.economy.toFixed(2), ...ph.bowl });
  });
  if (!rows.length) return null;
  return (
    <ProfileCard id="phases" title="By phase" player={team}
      note={rows[0]?.measure === 'strike_rate' ? 'Batting: strike rate · bowling: runs an over' : 'Batting: runs v par per 100 balls · bowling: runs an over'}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', fontFamily: fonts.mono, fontSize: 11, color: colors.textLo }}>
        <span>← worst</span><span>best →</span>
      </Box>
      {rows.map((r) => {
        const left = r.of > 1 ? (100 * (r.of - r.rank)) / (r.of - 1) : 50;
        const top = r.rank <= Math.max(1, Math.round(r.of / 4));
        return (
          <Box key={r.key} sx={{ mt: 0.75 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto 72px', columnGap: 1.25, alignItems: 'baseline', whiteSpace: 'nowrap' }}>
              <Box component="span" sx={{ fontSize: 13.5, overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.label}</Box>
              <Box component="span" sx={{ fontFamily: fonts.mono, fontWeight: 600, fontSize: 14 }}>{r.value}</Box>
              <Box component="span" sx={{ fontFamily: fonts.mono, fontSize: 11.5, textAlign: 'right', color: top ? colors.accent : colors.textLo }}>{`${ordinal(r.rank)} of ${r.of}`}</Box>
            </Box>
            <Box sx={{ position: 'relative', height: 10, mt: 0.5, borderBottom: `1px solid ${colors.borderStrong}` }}>
              <Box sx={{ position: 'absolute', left: '50%', top: 0, height: 10, width: '1.5px', bgcolor: colors.textLo }} />
              <Box sx={{ position: 'absolute', top: 2, left: `${left}%`, width: 10, height: 10, ml: '-5px', borderRadius: '50%', bgcolor: top ? colors.accent : colors.textMed }} />
            </Box>
          </Box>
        );
      })}
    </ProfileCard>
  );
};

const OrderCard = ({ team, order, win }) => {
  if (!order?.length) return null;
  const par = order.some((o) => o.raa_per_100 != null);  // ODIs have no par yet: strike rate instead
  const rows = order.map((o) => ({
    key: `${o.position}`, lead: o.position, name: o.batter, player: o.batter, win, detail: `${o.share}% of inns`,
    value: par ? (o.raa_per_100 == null ? '–' : signed(o.raa_per_100)) : `${o.strike_rate}`,
    tone: par ? (o.raa_per_100 > 0 ? 'pos' : o.raa_per_100 < 0 ? 'neg' : null) : null,
  }));
  return (
    <ProfileCard id="batting-order" title="Who bats where" player={team}
      note={par ? "Each spot's regular · runs v par per 100 balls" : "Each spot's regular · strike rate"}>
      <ValueList rows={rows} label="Batting order" />
    </ProfileCard>
  );
};

const OversCard = ({ team, grid }) => {
  if (!grid?.bowlers?.length) return null;
  const { overs, bowlers } = grid;
  const W = 340; const L = 84; const T = 16; const ch = 18;
  const cw = (W - L - 2) / Math.max(20, overs.length);
  const H = T + ch * bowlers.length + 4;
  const marks = overs.length >= 20 ? [1, 6, 7, 15, 16, 20] : [overs[0], overs[overs.length - 1]];
  return (
    <ProfileCard id="bowling-overs" title="Who bowls when" player={team} note="Share of each over's balls · brighter is more">
      <Box component="svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Who bowls which over" sx={{ width: '100%', display: 'block' }}>
        {marks.map((o) => (
          <text key={o} x={L + (o - 0.5) * cw} y={10} textAnchor="middle" style={{ fontFamily: fonts.mono, fontSize: 11, fill: colors.textLo }}>{o}</text>
        ))}
        {bowlers.map((b, j) => (
          <g key={b.name}>
            <text x={L - 6} y={T + j * ch + 12.5} textAnchor="end" style={{ fontFamily: fonts.body, fontSize: 11, fill: colors.textMed }}>
              {b.name.split(' ').length > 1 ? `${b.name[0]} ${b.name.split(' ').slice(-1)[0]}` : b.name}
            </text>
            {overs.map((o, i) => (b.shares[i] > 0.02 ? (
              <rect key={o} x={L + (o - 1) * cw} y={T + j * ch} width={cw - 1.5} height={ch - 2.5} rx="2"
                fill={colors.accent} fillOpacity={Math.min(1, 0.15 + b.shares[i] * 1.6)}>
                <title>{`${b.name}, over ${o}: ${Math.round(b.shares[i] * 100)}% of its balls`}</title>
              </rect>
            ) : null))}
          </g>
        ))}
      </Box>
    </ProfileCard>
  );
};

const TopCard = ({ team, top, win }) => {
  const par = (top?.bat || []).some((r) => r.raa != null);
  const bat = (top?.bat || []).slice(0, 3).map((r) => (par
    ? { name: r.name, player: r.name, win, detail: `${r.runs} runs · SR ${r.strike_rate}`, value: signed(r.raa), tone: r.raa > 0 ? 'pos' : r.raa < 0 ? 'neg' : null }
    : { name: r.name, player: r.name, win, detail: `${r.balls} balls · SR ${r.strike_rate}`, value: `${r.runs}` }));
  const bowl = (top?.bowl || []).slice(0, 3).map((r) => ({
    name: r.name, player: r.name, win, detail: `${r.wickets} wkts · ${r.dot_percentage}% dots`, value: r.economy.toFixed(2),
  }));
  if (!bat.length && !bowl.length) return null;
  return (
    <ProfileCard id="top" title="Top players" player={team} note={`${top.min_balls.bat}+ balls faced, ${top.min_balls.bowl}+ bowled`}>
      {bat.length > 0 && <><Eyebrow>{par ? 'Batting · runs above par' : 'Batting · runs'}</Eyebrow><ValueList rows={bat} label="Batters" /></>}
      {bowl.length > 0 && <Box sx={{ mt: 1 }}><Eyebrow>Bowling · runs an over</Eyebrow><ValueList rows={bowl} label="Bowlers" /></Box>}
    </ProfileCard>
  );
};

const Bar = ({ label, won, of }) => {
  const pct = of ? (100 * won) / of : 0;
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: '120px minmax(0, 1fr) 44px', columnGap: 1, alignItems: 'center', my: 0.75 }}>
      <Box sx={{ fontSize: 13.5, lineHeight: 1.2, whiteSpace: 'nowrap' }}>{label}
        <Box component="small" sx={{ display: 'block', color: colors.textLo, fontSize: 11 }}>{`won ${won} of ${of}`}</Box>
      </Box>
      <Box sx={{ height: 12, bgcolor: 'rgba(255,255,255,.05)', borderRadius: '4px', overflow: 'hidden' }}>
        <Box sx={{ width: `${pct}%`, height: '100%', bgcolor: colors.accent, borderRadius: '4px' }} />
      </Box>
      <Box sx={{ fontFamily: fonts.mono, fontSize: 13, textAlign: 'right' }}>{`${Math.round(pct)}%`}</Box>
    </Box>
  );
};

const WhereCard = ({ team, res }) => (
  <ProfileCard id="where-they-win" title="Where they win" player={team}>
    <Bar label="Batting first" won={res.batting_first.won} of={res.batting_first.of} />
    <Bar label="Chasing" won={res.chasing.won} of={res.chasing.of} />
  </ProfileCard>
);

const AgainstCard = ({ team, against }) => {
  const rows = (against || []).slice(0, 7);
  if (!rows.length) return null;
  const most = Math.max(...rows.map((r) => r.won + r.lost));
  return (
    <ProfileCard id="against" title="Against each side" player={team} note="Most-played opponents · won–lost">
      {rows.map((r) => (
        <Box key={r.team} sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 96px 40px', columnGap: 1, alignItems: 'center', py: 0.6,
          borderBottom: `1px solid ${colors.border}`, whiteSpace: 'nowrap' }}>
          <Box sx={{ fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.team.length > 22 ? (getTeamAbbr(r.team) || r.team) : r.team}</Box>
          <Box sx={{ display: 'flex', gap: '2px' }}>
            <Box sx={{ height: 10, width: `${(96 * r.won) / most}px`, bgcolor: colors.accent, borderRadius: '3px' }} />
            <Box sx={{ height: 10, width: `${(96 * r.lost) / most}px`, bgcolor: colors.red, borderRadius: '3px' }} />
          </Box>
          <Box sx={{ fontFamily: fonts.mono, fontSize: 13, textAlign: 'right' }}>{`${r.won}–${r.lost}`}</Box>
        </Box>
      ))}
    </ProfileCard>
  );
};

export const TeamPicker = () => {
  const navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  useEffect(() => {
    fetch(`${config.API_URL}/teams/`).then((r) => r.json())
      .then((d) => setTeams((Array.isArray(d) ? d : []).sort((a, b) => a.full_name.localeCompare(b.full_name))))
      .catch(() => setTeams([]));
  }, []);
  return (
    <Box sx={{ px: 2, pt: 3, display: 'flex', flexDirection: 'column', gap: 1.5, maxWidth: 520, mx: 'auto', color: colors.textHi }}>
      <Box component="h1" sx={{ m: 0, fontFamily: fonts.display, fontWeight: 700, fontSize: 28 }}>Teams</Box>
      <Box sx={{ color: colors.textLo, fontSize: 14 }}>How good is a side, phase by phase? Pick one.</Box>
      <Autocomplete options={teams} getOptionLabel={(t) => t.full_name}
        onChange={(_, v) => v && navigate(`/team?team=${encodeURIComponent(v.full_name)}`)}
        renderInput={(params) => <TextField {...params} label="Team" autoFocus />} />
    </Box>
  );
};

const TeamPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const team = new URLSearchParams(location.search).get('team');
  const win = useMemo(() => readWindow(location.search), [location.search]);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const changeWindow = useCallback((patch) => {
    const next = { ...win, ...patch };
    if (patch.period && patch.period !== 'custom') { next.start = null; next.end = null; }
    navigate({ search: writeSearch({ team }, next), hash: '' }, { replace: true });
  }, [win, team, navigate]);

  useEffect(() => { if (team) document.title = `${team} · Hindsight`; }, [team]);
  // The page names the side as the data does ("CSK" in a link opens Chennai Super Kings).
  const { status, data } = usePageData(team ? '/team-page' : null, `team=${encodeURIComponent(team || '')}&${windowQuery(win)}`);
  useEffect(() => { if (data?.team) rememberEntity('team', data.team); }, [data?.team]);

  useEffect(() => {
    if (status !== 'ready' || !location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: 'start' });
  }, [status, location.hash]);

  if (!team) return <TeamPicker />;
  const meta = data?.scope ? (data.scope.kind === 'international' ? `${data.scope.competition} v the ${data.scope.label}` : data.scope.competition) : null;
  const chip = data ? windowChip(data.window, `${data.played} matches`) : null;
  const qb = `/query?batting_teams=${encodeURIComponent(team)}`;

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', pb: 3, color: colors.textHi }}>
      <Box sx={{ px: 2, pt: 1.5, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <PageHeader name={data?.team || team} meta={meta} win={win} onWindow={changeWindow} onFilters={() => setFiltersOpen(true)} chip={chip}
          shareKind="team" shareTitle={`${team} on Hindsight`} />
        {status === 'ready' && (
          <>
            <Eyebrow>{`Ranked among ${data.scope.label}`}</Eyebrow>
            <SummaryRows rows={summaryRows(data)} label="How the side stands" />
            {data.results?.last?.length > 0 && <LastGames games={data.results.last} />}
          </>
        )}
      </Box>
      <Box sx={{ px: 2, pt: 1.75, display: 'flex', flexDirection: 'column', gap: 1.75 }}>
        {(status === 'loading' || status === 'building') && (
          <PageSkeleton note={status === 'building' ? 'Building this side’s page. It takes about half a minute the first time.' : null} />
        )}
        {status === 'empty' && (
          <Box sx={{ color: colors.textLo, fontSize: 14 }}>
            No {win.fmt} matches for {team} in this window.{win.period === 'recent' && <> Try <Box component="button" type="button" onClick={() => changeWindow({ period: 'career' })} sx={{ all: 'unset', cursor: 'pointer', color: colors.accent }}>Career</Box>.</>}
          </Box>
        )}
        {status === 'error' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>This page couldn't load just now. Try again shortly.</Box>}
        {status === 'ready' && (
          <>
            {data.rating && <RatingCard team={team} rating={data.rating} />}
            {data.phases && <PhaseCard team={team} phases={data.phases} />}
            <OrderCard team={team} order={data.batting_order} win={win} />
            <OversCard team={team} grid={data.bowling_overs} />
            <TopCard team={team} top={data.top} win={win} />
            {data.results && <WhereCard team={team} res={data.results} />}
            <AgainstCard team={team} against={data.results?.against} />
            {PICK_XI.includes(data.team || team) && (
              <Box component={Link} to={`/pick-xi?team=${encodeURIComponent(data.team || team)}`}
                sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: colors.surface1, border: `1px solid ${colors.border}`,
                  borderRadius: '14px', px: 2, py: 1.5, textDecoration: 'none', color: colors.textHi, '&:hover': { borderColor: colors.accent } }}>
                <Box>
                  <Box sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 18 }}>{`Pick ${data.team || team}'s XI`}</Box>
                  <Box sx={{ fontSize: 13, color: colors.textMed }}>Slot by slot: who else fits, and the case for each.</Box>
                </Box>
                <Box sx={{ color: colors.accent, fontFamily: fonts.mono, fontSize: 13 }}>Open →</Box>
              </Box>
            )}
            <TeamSquad team={data.team || team} />
          </>
        )}
        <PageFooter queryLink={qb} />
      </Box>
      <ProfileFilters open={filtersOpen} onClose={() => setFiltersOpen(false)} value={{ ...win, scope: 'strong' }}
        onApply={({ fmt, period, start, end }) => changeWindow({ fmt, period, start, end })} showScope={false} />
    </Box>
  );
};

export default TeamPage;
