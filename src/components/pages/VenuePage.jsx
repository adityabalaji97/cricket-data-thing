import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Autocomplete, Box, TextField } from '@mui/material';
import SportsCricketRoundedIcon from '@mui/icons-material/SportsCricketRounded';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import config from '../../config';
import { rememberEntity } from '../../utils/recentEntities';
import { colors } from '../../theme/hindsightDark';
import ProfileCard from '../playerProfile/cards/ProfileCard';
import ProfileFilters from '../playerProfile/cards/ProfileFilters';
import StoryCard from '../story/StoryCard';
import { toStoryChapters } from '../story/visuals';
import {
  Eyebrow, PageFooter, PageHeader, PageSkeleton, SummaryRows, ValueList, ordinal, readWindow, signed, usePageData, windowChip,
  windowQuery, writeSearch,
} from '../pageKit/pageKit';

// The venue page (TEAM_VENUE_PLAN.md G2): the match preview with no teams picked. A summary ranked against the grounds
// of its main competition, the preview's own ground cards for the page's window, and who does well here, from one
// cached call (GET /venue-page). Picking two teams opens the full preview (/venue?venue=…&team1=…&team2=…).

const norm = (s) => (s || '').toLowerCase().split(',')[0].replace(/[^a-z0-9 ]/g, '').trim();

/** The ground cards at the column's width, 4:5 as in the preview. */
const GroundCards = ({ cards }) => {
  const ref = useRef(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const measure = () => setWidth(Math.round(el.getBoundingClientRect().width));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <Box ref={ref} sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
      {width > 0 && cards.map((c) => (
        <Box key={c.id} id={c.id} sx={{ scrollMarginTop: '72px' }}>
          <StoryCard card={c} width={width} height={Math.round(width * 1.25)} onPage />
        </Box>
      ))}
    </Box>
  );
};

const TeamsPicker = ({ venue, onClose }) => {
  const navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [t1, setT1] = useState(null);
  const [t2, setT2] = useState(null);
  useEffect(() => {
    fetch(`${config.API_URL}/teams/`).then((r) => r.json())
      .then((d) => setTeams((Array.isArray(d) ? d : []).sort((a, b) => a.full_name.localeCompare(b.full_name))))
      .catch(() => setTeams([]));
  }, []);
  useEffect(() => {
    if (t1 && t2) {
      navigate(`/venue?venue=${encodeURIComponent(venue)}&team1=${encodeURIComponent(t1.abbreviated_name)}`
        + `&team2=${encodeURIComponent(t2.abbreviated_name)}&autoload=true`);
    }
  }, [t1, t2, venue, navigate]);
  const field = (label, value, set, other) => (
    <Autocomplete size="small" options={teams.filter((t) => t !== other)} value={value} onChange={(_, v) => set(v)}
      getOptionLabel={(t) => t.full_name} isOptionEqualToValue={(a, b) => a.full_name === b.full_name}
      renderInput={(params) => <TextField {...params} label={label} />} sx={{ flex: 1, minWidth: 0 }} />
  );
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, border: `1px solid ${colors.borderStrong}`, borderRadius: '14px', p: 1.25 }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        {field('Team 1', t1, setT1, t2)}
        {field('Team 2', t2, setT2, t1)}
      </Box>
      <Box component="button" type="button" onClick={onClose}
        sx={{ all: 'unset', cursor: 'pointer', alignSelf: 'flex-end', fontSize: 13, color: colors.textLo }}>Cancel</Box>
    </Box>
  );
};

const NextHere = ({ venue }) => {
  const [next, setNext] = useState(undefined);
  useEffect(() => {
    let cancelled = false;
    fetch(`${config.API_URL}/fixtures/upcoming?count=20`).then((r) => r.json())
      .then((list) => {
        if (cancelled) return;
        const v = norm(venue);
        setNext((Array.isArray(list) ? list : []).find((f) => {
          const fv = norm(f.venue);
          return fv && v && (fv === v || fv.includes(v) || v.includes(fv));
        }) || null);
      })
      .catch(() => { if (!cancelled) setNext(null); });
    return () => { cancelled = true; };
  }, [venue]);
  if (next === undefined) return null;
  if (!next) return <Box sx={{ color: colors.textLo, fontSize: 12.5, whiteSpace: 'nowrap' }}>Next here: none scheduled</Box>;
  const d = new Date(`${next.date}T00:00:00`);
  const to = `/venue?venue=${encodeURIComponent(venue)}&team1=${encodeURIComponent(next.team1_abbr || next.team1)}`
    + `&team2=${encodeURIComponent(next.team2_abbr || next.team2)}&autoload=true${next.match_id ? `&matchId=${next.match_id}` : ''}`;
  return (
    <Box component={Link} to={to} sx={{ color: colors.accent, fontSize: 13, textDecoration: 'none', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
      Next here: {next.team1_abbr || next.team1} v {next.team2_abbr || next.team2}, {d.getDate()} {d.toLocaleString('en', { month: 'short' })} · preview →
    </Box>
  );
};

const LeadersCard = ({ venue, leaders }) => {
  const par = (leaders?.bat || []).some((r) => r.raa != null);  // ODIs have no par yet: runs instead
  const bat = (leaders?.bat || []).slice(0, 4).map((r) => (par
    ? { name: r.name, detail: `${r.runs} runs · SR ${r.strike_rate}`, value: r.raa == null ? '–' : signed(r.raa), tone: r.raa > 0 ? 'pos' : r.raa < 0 ? 'neg' : null }
    : { name: r.name, detail: `${r.balls} balls · SR ${r.strike_rate}`, value: `${r.runs}` }));
  const bowl = (leaders?.bowl || []).slice(0, 4).map((r) => ({
    name: r.name, detail: `${r.wickets} wkts · ${r.dot_percentage}% dots`, value: r.economy?.toFixed(2),
  }));
  if (!bat.length && !bowl.length) return null;
  return (
    <ProfileCard id="leaders" title="Who does well here" player={venue}
      note={`${leaders.min_balls.bat}+ balls faced, ${leaders.min_balls.bowl}+ bowled`}>
      {bat.length > 0 && <><Eyebrow>{par ? 'Batting · runs above par' : 'Batting · runs'}</Eyebrow><ValueList rows={bat} label="Batters" /></>}
      {bowl.length > 0 && <Box sx={{ mt: 1 }}><Eyebrow>Bowling · runs an over</Eyebrow><ValueList rows={bowl} label="Bowlers" /></Box>}
    </ProfileCard>
  );
};

const summaryRows = (p) => {
  const rows = [];
  if (p.par?.value) rows.push({ rank: `${p.par.value}`, what: 'Par, first innings', lead: true });
  const r = p.ranks;
  if (r) {
    const of = (x) => `${ordinal(x.rank)} of ${x.of}`;
    if (r.rate) rows.push({ rank: of(r.rate), what: `Runs an over · ${r.rate.value.toFixed(2)}` });
    if (r.chase) rows.push({ rank: of(r.chase), what: `Chases won · ${r.chased} of ${r.decided}` });
    if (r.spin) rows.push({ rank: of(r.spin), what: `Spin's share of balls · ${Math.round(r.spin.value)}%` });
  }
  return rows;
};

const VenuePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const venue = new URLSearchParams(location.search).get('venue');
  const win = useMemo(() => readWindow(location.search), [location.search]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [picking, setPicking] = useState(false);

  const changeWindow = useCallback((patch) => {
    const next = { ...win, ...patch };
    if (patch.period && patch.period !== 'custom') { next.start = null; next.end = null; }
    navigate({ search: writeSearch({ venue }, next), hash: '' }, { replace: true });
  }, [win, venue, navigate]);

  useEffect(() => { if (venue) { document.title = `${venue} · Hindsight`; rememberEntity('venue', venue); } }, [venue]);
  const { status, data } = usePageData(venue ? '/venue-page' : null, `venue=${encodeURIComponent(venue || '')}&${windowQuery(win)}`);

  const cards = useMemo(() => {
    if (!data?.cards) return [];
    return toStoryChapters({ fixture: { params: {} }, chapters: [{ id: 'ground', title: 'The ground', cards: data.cards }] })
      .flatMap((ch) => ch.cards);
  }, [data]);

  // A shared card link (#totals, #leaders…) scrolls to its card once the page is drawn.
  useEffect(() => {
    if (status !== 'ready' || !location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: 'start' });
  }, [status, location.hash]);

  const meta = data ? [data.identity?.city, data.identity?.home && `home of ${data.identity.home}`].filter(Boolean).join(' · ') : null;
  const chip = data ? windowChip(data.window, `${data.matches} matches`) : null;
  const qb = `/query?venue=${encodeURIComponent(venue || '')}`;

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto', pb: 3, color: colors.textHi }}>
      <Box sx={{ px: 2, pt: 1.5, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <PageHeader name={venue} meta={meta} win={win} onWindow={changeWindow} onFilters={() => setFiltersOpen(true)} chip={chip}
          shareKind="venue" shareTitle={`${venue} on Hindsight`} />
        {status === 'ready' && (
          <>
            {data.ranks?.label && <Eyebrow>{`Ranked among ${data.ranks.label}`}</Eyebrow>}
            <SummaryRows rows={summaryRows(data)} label="How the ground plays" />
            {picking ? <TeamsPicker venue={venue} onClose={() => setPicking(false)} /> : (
              <Box component="button" type="button" onClick={() => setPicking(true)}
                sx={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 1, border: `1px solid ${colors.accent}`,
                  color: colors.accent, borderRadius: '999px', px: 1.75, py: 0.9, fontWeight: 600, fontSize: 14, whiteSpace: 'nowrap',
                  '&:focus-visible': { outline: `2px solid ${colors.accent}`, outlineOffset: 2 } }}>
                <SportsCricketRoundedIcon fontSize="small" />
                <Box component="span" sx={{ flex: 1 }}>Add two teams for a match preview</Box>
                <ChevronRightRoundedIcon fontSize="small" />
              </Box>
            )}
            <NextHere venue={venue} />
          </>
        )}
      </Box>

      <Box sx={{ px: 2, pt: 1.75, display: 'flex', flexDirection: 'column', gap: 1.75 }}>
        {(status === 'loading' || status === 'building') && (
          <PageSkeleton note={status === 'building' ? 'Building this ground’s page. It takes about half a minute the first time.' : null} />
        )}
        {status === 'empty' && (
          <Box sx={{ color: colors.textLo, fontSize: 14 }}>
            No {win.fmt} matches here in this window.{win.period === 'recent' && <> Try <Box component="button" type="button" onClick={() => changeWindow({ period: 'career' })} sx={{ all: 'unset', cursor: 'pointer', color: colors.accent }}>Career</Box>.</>}
          </Box>
        )}
        {status === 'error' && <Box sx={{ color: colors.textLo, fontSize: 14 }}>This page couldn't load just now. Try again shortly.</Box>}
        {status === 'ready' && (
          <>
            <GroundCards cards={cards} />
            <LeadersCard venue={venue} leaders={data.leaders} />
          </>
        )}
        <PageFooter queryLink={qb} />
      </Box>

      <ProfileFilters open={filtersOpen} onClose={() => setFiltersOpen(false)} value={{ ...win, scope: 'strong' }}
        onApply={({ fmt, period, start, end }) => changeWindow({ fmt, period, start, end })} showScope={false} />
    </Box>
  );
};

export default VenuePage;
