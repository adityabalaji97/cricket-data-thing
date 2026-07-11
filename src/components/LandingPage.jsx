import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import SearchIcon from '@mui/icons-material/Search';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import ArrowBackIosNewIcon from '@mui/icons-material/ArrowBackIosNew';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import PersonIcon from '@mui/icons-material/Person';
import SportsCricketIcon from '@mui/icons-material/SportsCricket';
import StadiumIcon from '@mui/icons-material/Stadium';
import GroupsIcon from '@mui/icons-material/Groups';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import GitHubIcon from '@mui/icons-material/GitHub';
import XIcon from '@mui/icons-material/X';
import config from '../config';
import { fetchUpcomingMatches } from '../data/iplSchedule';
import MiniWagonWheel from './MiniWagonWheel';
import { getTeamColor } from '../utils/teamColors';

const C = {
  bg: '#0a0c11',
  surface: '#101319',
  raised: '#14171e',
  muted: '#0d1015',
  inset: '#070a0e',
  hairline: 'rgba(255,255,255,0.06)',
  hairlineStrong: 'rgba(255,255,255,0.12)',
  hi: '#f3f4f6',
  mid: '#c3c8d0',
  soft: '#9aa1ac',
  low: '#6b7280',
  faint: '#4b5563',
  lime: '#b6f24a',
  limeHover: '#c8f56f',
  gold: '#f0b429',
  red: '#e5484d',
};

const fonts = {
  body: '"Barlow", sans-serif',
  display: '"Barlow Semi Condensed", sans-serif',
  mono: '"IBM Plex Mono", monospace',
};

const DATE_OPTIONS = [
  { value: 'all', label: 'All time', mobileLabel: 'All' },
  { value: '7', label: 'Last 7 days', mobileLabel: '7 days' },
  { value: '30', label: 'Last 30 days', mobileLabel: '30 days' },
  { value: '90', label: 'Last 3 months', mobileLabel: '3 months' },
];

const ELO_RANGE_OPTIONS = [
  { value: 'all', label: 'All time' },
  { value: '24m', label: 'Last 24 months' },
  { value: '12m', label: 'Last 12 months' },
  { value: 'ytd', label: '2026 only' },
];

const EXPLORE_ITEMS = [
  { label: 'Batter Profiles', description: 'Batting form, scoring maps and matchups', route: '/player', icon: PersonIcon, color: '#c70d3a' },
  { label: 'Bowler Profiles', description: 'Wickets, phases, line and length patterns', route: '/bowler', icon: SportsCricketIcon, color: '#ff6f00' },
  { label: 'Batter Comparison', description: 'Compare players across roles and contexts', route: '/comparison', icon: CompareArrowsIcon, color: '#9c27b0' },
  { label: 'Query Builder', description: 'Ask custom questions of the ball-by-ball data', route: '/query', icon: QueryStatsIcon, color: '#5b8def' },
  { label: 'Venue Analysis', description: 'Preview venues, par scores and matchups', route: '/venue', icon: StadiumIcon, color: '#0057b7' },
  { label: 'Team Matchups', description: 'Head-to-head and tactical matchup history', route: '/matchups', icon: GroupsIcon, color: '#1cba2e' },
  { label: 'ELO Rankings', description: 'Current team strength ratings', route: '/rankings', icon: EmojiEventsIcon, color: '#f0b429' },
  { label: 'Credits', description: 'Sources, inspiration and project links', route: '/credits', icon: InfoOutlinedIcon, color: '#6b7280' },
];

const toDateLabel = (value) => {
  if (!value) return '';
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const dateInput = (date) => date.toISOString().slice(0, 10);

const routeTeam = (team) => `/team?team=${encodeURIComponent(team || '')}&autoload=true`;
const routePlayer = (player) => `/player?name=${encodeURIComponent(player || '')}&autoload=true`;
const routePreview = (match) => (
  `/venue?venue=${encodeURIComponent(match.venue || '')}` +
  `&team1=${encodeURIComponent(match.team1Abbr || match.team1 || '')}` +
  `&team2=${encodeURIComponent(match.team2Abbr || match.team2 || '')}` +
  `&includeInternational=true&topTeams=20&autoload=true` +
  `${match.matchId ? `&matchId=${encodeURIComponent(match.matchId)}` : ''}`
);

const textOn = (hex) => {
  const normalized = String(hex || '').replace('#', '');
  if (normalized.length !== 6) return '#fff';
  const r = parseInt(normalized.slice(0, 2), 16) / 255;
  const g = parseInt(normalized.slice(2, 4), 16) / 255;
  const b = parseInt(normalized.slice(4, 6), 16) / 255;
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum > 0.62 ? C.bg : '#fff';
};

const scrollTrack = (ref, direction) => {
  const node = ref.current;
  if (!node) return;
  node.scrollBy({
    left: direction * Math.min(node.clientWidth * 0.85, 640),
    behavior: 'smooth',
  });
};

const flattenRecentMatches = (data) => {
  if (!data) return [];
  if (Array.isArray(data.matches)) return data.matches;
  return (data.groups || []).flatMap((group) => group.matches || []);
};

const latestCompetition = (stats) => {
  const items = Object.values(stats || {}).filter((item) => item.competition || item.competition_key);
  const sorted = items.sort((a, b) => String(b.latest_date || '').localeCompare(String(a.latest_date || '')));
  return sorted[0]?.competition_key || sorted[0]?.competition || null;
};

const sectionTitleSx = {
  color: C.hi,
  fontFamily: fonts.display,
  fontWeight: 700,
  fontSize: { xs: 20, md: 25 },
  lineHeight: 1.05,
};

const Kicker = ({ children, color = C.lime }) => (
  <Typography
    sx={{
      color,
      fontFamily: fonts.mono,
      fontSize: 10,
      letterSpacing: '0.16em',
      textTransform: 'uppercase',
      fontWeight: 600,
      mb: 0.75,
    }}
  >
    {children}
  </Typography>
);

const SectionHeader = ({ kicker, kickerColor, title, subtitle, action }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 2, mb: 1.75 }}>
    <Box sx={{ minWidth: 0 }}>
      <Kicker color={kickerColor}>{kicker}</Kicker>
      <Typography sx={sectionTitleSx}>{title}</Typography>
      {subtitle && (
        <Typography sx={{ color: C.soft, mt: 0.6, fontFamily: fonts.body, fontSize: { xs: 13, md: 14 } }}>
          {subtitle}
        </Typography>
      )}
    </Box>
    {action}
  </Box>
);

const CarouselButtons = ({ trackRef, hide }) => {
  if (hide) return null;
  return (
    <Box sx={{ display: 'flex', gap: 0.75, flexShrink: 0 }}>
      <IconButton aria-label="Previous" onClick={() => scrollTrack(trackRef, -1)} sx={arrowButtonSx}>
        <ArrowBackIosNewIcon sx={{ fontSize: 15 }} />
      </IconButton>
      <IconButton aria-label="Next" onClick={() => scrollTrack(trackRef, 1)} sx={arrowButtonSx}>
        <ArrowForwardIosIcon sx={{ fontSize: 15 }} />
      </IconButton>
    </Box>
  );
};

const arrowButtonSx = {
  width: 38,
  height: 38,
  color: C.hi,
  border: `1px solid ${C.hairlineStrong}`,
  bgcolor: C.surface,
  '&:hover': { bgcolor: C.raised, borderColor: 'rgba(182,242,74,0.35)' },
};

const carouselSx = {
  display: 'flex',
  gap: { xs: 1.25, md: 1.5 },
  overflowX: 'auto',
  scrollSnapType: 'x mandatory',
  pb: 1,
  mx: { xs: -0.5, md: 0 },
  px: { xs: 0.5, md: 0 },
  '&::-webkit-scrollbar': { height: 5 },
  '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.12)', borderRadius: 999 },
};

const LandingDropdown = ({ id, label, value, options, onChange, openDropdown, setOpenDropdown, compact }) => {
  const selected = options.find((item) => item.value === value) || options[0];
  const display = compact ? (selected?.mobileLabel || selected?.label) : `${label} ${selected?.label || ''}`;
  const open = openDropdown === id;

  return (
    <Box sx={{ position: 'relative', minWidth: compact ? 0 : 154, flex: compact ? 1 : '0 0 auto' }}>
      <Button
        type="button"
        onClick={() => setOpenDropdown(open ? null : id)}
        endIcon={<KeyboardArrowDownIcon sx={{ fontSize: 17 }} />}
        sx={{
          justifyContent: 'space-between',
          width: '100%',
          minHeight: 42,
          px: compact ? 1 : 1.3,
          borderRadius: 2,
          color: C.mid,
          bgcolor: C.surface,
          border: `1px solid ${open ? 'rgba(182,242,74,0.45)' : C.hairlineStrong}`,
          fontFamily: fonts.mono,
          fontSize: 11,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          overflow: 'hidden',
          '& .MuiButton-endIcon': { ml: 0.5 },
          '&:hover': { bgcolor: C.raised, borderColor: 'rgba(182,242,74,0.35)' },
        }}
      >
        <Box component="span" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {display}
        </Box>
      </Button>
      {open && (
        <Box
          sx={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            minWidth: compact ? '100%' : 220,
            maxHeight: 300,
            overflowY: 'auto',
            zIndex: 45,
            p: 0.5,
            bgcolor: C.muted,
            border: `1px solid ${C.hairlineStrong}`,
            borderRadius: 2,
            boxShadow: '0 24px 60px rgba(0,0,0,0.45)',
          }}
        >
          {options.map((option) => (
            <Box
              key={option.value}
              component="button"
              type="button"
              onClick={() => {
                onChange(option.value);
                setOpenDropdown(null);
              }}
              sx={{
                width: '100%',
                display: 'block',
                textAlign: 'left',
                border: 0,
                borderRadius: 1.3,
                px: 1.1,
                py: 1,
                cursor: 'pointer',
                color: option.value === value ? C.lime : C.mid,
                bgcolor: option.value === value ? 'rgba(182,242,74,0.08)' : 'transparent',
                fontFamily: fonts.body,
                fontWeight: option.value === value ? 700 : 500,
                fontSize: 13,
                '&:hover': { bgcolor: C.raised },
              }}
            >
              {option.label}
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

const TopBar = ({ navOpen, setNavOpen, isMobile }) => {
  const navigate = useNavigate();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');

  const submit = (event) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    setSearchOpen(false);
  };

  const searchField = (
    <Box
      component="form"
      onSubmit={submit}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        width: '100%',
        maxWidth: { xs: 'none', md: 420 },
        ml: { md: 'auto' },
        px: 1.3,
        py: 0.7,
        minHeight: 42,
        bgcolor: C.surface,
        border: `1px solid ${C.hairlineStrong}`,
        borderRadius: 2.2,
      }}
    >
      <SearchIcon sx={{ color: C.low, fontSize: 19 }} />
      <Box
        component="input"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search players, teams, venues"
        sx={{
          width: '100%',
          bgcolor: 'transparent',
          border: 0,
          outline: 0,
          color: C.hi,
          fontFamily: fonts.body,
          fontSize: 14,
          '&::placeholder': { color: C.low },
        }}
      />
    </Box>
  );

  return (
    <Box sx={{ mb: { xs: 3, md: 4.2 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.4 }}>
        <Box component={Link} to="/" sx={{ display: 'flex', alignItems: 'center', gap: 1, textDecoration: 'none' }}>
          <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 32, height: 32 }} />
          <Typography sx={{ color: C.hi, fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 18, md: 20 } }}>
            Hindsight
          </Typography>
        </Box>
        {!isMobile && searchField}
        {isMobile && (
          <IconButton aria-label="Search" onClick={() => setSearchOpen((prev) => !prev)} sx={topIconSx}>
            <SearchIcon sx={{ fontSize: 20 }} />
          </IconButton>
        )}
        <Button
          type="button"
          onClick={() => setNavOpen(!navOpen)}
          startIcon={<MenuIcon />}
          sx={{
            ml: isMobile ? 0 : 0.5,
            minWidth: isMobile ? 42 : 116,
            width: isMobile ? 42 : 'auto',
            height: 42,
            px: isMobile ? 0 : 1.5,
            borderRadius: 2,
            color: C.bg,
            bgcolor: C.lime,
            fontFamily: fonts.mono,
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: '0.12em',
            '& .MuiButton-startIcon': { mr: isMobile ? 0 : 0.9 },
            '&:hover': { bgcolor: C.limeHover },
          }}
        >
          {isMobile ? '' : 'Explore'}
        </Button>
      </Box>
      {isMobile && searchOpen && <Box sx={{ mt: 1.3 }}>{searchField}</Box>}
    </Box>
  );
};

const topIconSx = {
  ml: 'auto',
  width: 42,
  height: 42,
  color: C.hi,
  bgcolor: C.surface,
  border: `1px solid ${C.hairlineStrong}`,
  borderRadius: 2,
  '&:hover': { bgcolor: C.raised },
};

const TodaySection = ({ matches, loading, isMobile }) => {
  const trackRef = useRef(null);
  const today = new Date().toLocaleDateString('en-CA');
  const todayMatches = matches.filter((match) => match.isLive || match.date === today);
  const displayMatches = todayMatches.length ? todayMatches : matches.slice(0, 6);
  const hasLive = displayMatches.some((match) => match.isLive);

  return (
    <Box component="section" sx={{ mb: { xs: 3.75, md: 5.5 } }}>
      <SectionHeader
        kicker={hasLive ? 'Live now' : '01 / Today'}
        kickerColor={hasLive ? C.red : C.lime}
        title="Today's Matches"
        subtitle={todayMatches.length ? 'Live and scheduled T20 cricket' : 'No match today, showing the next fixtures'}
        action={<CarouselButtons trackRef={trackRef} hide={isMobile || loading || displayMatches.length < 2} />}
      />
      {loading ? (
        <LoadingCard label="Loading fixtures..." />
      ) : (
        <Box ref={trackRef} sx={carouselSx}>
          {displayMatches.map((match) => (
            <TodayMatchCard key={`${match.matchId || match.matchNumber}-${match.date}`} match={match} />
          ))}
          {!displayMatches.length && <EmptyCard label="No live or upcoming fixtures found." />}
        </Box>
      )}
    </Box>
  );
};

const TodayMatchCard = ({ match }) => {
  const live = Boolean(match.isLive);
  const status = live ? (match.statusText || 'Live') : (match.time ? `Starts ${match.time} IST` : 'Scheduled');
  const team1Color = getTeamColor(match.team1Abbr || match.team1) || C.low;
  const team2Color = getTeamColor(match.team2Abbr || match.team2) || C.low;
  return (
    <Box
      sx={{
        scrollSnapAlign: 'start',
        flex: '0 0 auto',
        width: { xs: 290, md: 360 },
        minHeight: 236,
        p: 2,
        borderRadius: 3,
        bgcolor: C.surface,
        background: live ? 'linear-gradient(150deg,#16110f,#101319)' : C.surface,
        border: `1px solid ${live ? 'rgba(229,72,77,0.5)' : C.hairline}`,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1.2, mb: 2 }}>
        <Typography sx={chipSx}>{match.series || 'T20'}</Typography>
        <Typography sx={{ ...monoSx, color: live ? C.red : C.soft }}>{status}</Typography>
      </Box>
      <TeamFixtureRow color={team1Color} abbr={match.team1Abbr || match.team1} name={match.team1} />
      <Typography sx={{ color: C.faint, fontFamily: fonts.mono, fontSize: 11, textAlign: 'center', my: 1.3 }}>
        VS
      </Typography>
      <TeamFixtureRow color={team2Color} abbr={match.team2Abbr || match.team2} name={match.team2} />
      <Box sx={{ height: 1, bgcolor: C.hairline, my: 1.7 }} />
      <Typography sx={{ color: C.soft, fontFamily: fonts.body, fontSize: 13, minHeight: 36 }}>
        {match.venue || 'Venue TBA'}
      </Typography>
      <Button component={Link} to={routePreview(match)} fullWidth sx={limeButtonSx}>
        Match Preview
      </Button>
    </Box>
  );
};

const TeamFixtureRow = ({ color, abbr, name }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
    <Box sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: color, flexShrink: 0 }} />
    <Typography component={Link} to={routeTeam(abbr)} sx={teamLinkSx}>
      {abbr}
    </Typography>
    <Typography sx={{ color: C.soft, fontFamily: fonts.body, fontSize: 13, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {name}
    </Typography>
  </Box>
);

const chipSx = {
  color: C.mid,
  bgcolor: C.muted,
  px: 0.8,
  py: 0.45,
  borderRadius: 1,
  fontFamily: fonts.mono,
  fontSize: 10,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  maxWidth: '62%',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const monoSx = {
  fontFamily: fonts.mono,
  fontSize: 11,
  letterSpacing: '0.04em',
  whiteSpace: 'nowrap',
};

const teamLinkSx = {
  color: C.hi,
  fontFamily: fonts.display,
  fontWeight: 700,
  fontSize: 23,
  lineHeight: 1,
  textDecoration: 'none',
  '&:hover': { color: C.lime },
};

const limeButtonSx = {
  mt: 1.7,
  height: 42,
  borderRadius: 2,
  bgcolor: C.lime,
  color: C.bg,
  fontFamily: fonts.mono,
  fontWeight: 700,
  fontSize: 11,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  '&:hover': { bgcolor: C.limeHover },
};

const RecentMatchesSection = ({
  data,
  loading,
  activeCompetition,
  setActiveCompetition,
  teamFilter,
  setTeamFilter,
  dateFilter,
  setDateFilter,
  openDropdown,
  setOpenDropdown,
  isMobile,
}) => {
  const trackRef = useRef(null);
  const matches = useMemo(() => flattenRecentMatches(data), [data]);
  const competitionOptions = useMemo(() => {
    const source = data?.filter_options?.competitions || data?.filters || [];
    return source.map((item) => ({
      value: item.key,
      label: item.label,
      mobileLabel: item.label,
      latest_date: item.latest_date,
    }));
  }, [data]);
  const teamOptions = useMemo(() => {
    const source = data?.filter_options?.teams || data?.team_filters || [];
    const seen = new Set();
    return [
      { value: 'all', label: 'All teams', mobileLabel: 'All teams' },
      ...source
        .filter((item) => item.value && !seen.has(item.value) && seen.add(item.value))
        .map((item) => ({ value: item.value, label: item.label || item.value, mobileLabel: item.label || item.value })),
    ];
  }, [data]);
  const selectedCompetition = activeCompetition || competitionOptions[0]?.value || 'all';
  const narrowed = teamFilter !== 'all' || dateFilter !== 'all';

  return (
    <Box component="section" sx={{ mb: { xs: 3.75, md: 5.5 } }}>
      <SectionHeader
        kicker="02 / Browse"
        title="Recent Matches"
        subtitle={`${matches.length} matches - filter by team, competition & recency`}
        action={<CarouselButtons trackRef={trackRef} hide={isMobile || loading || matches.length < 2} />}
      />
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.7, flexWrap: isMobile ? 'nowrap' : 'wrap' }}>
        <LandingDropdown
          id="team"
          label="Team"
          value={teamFilter}
          options={teamOptions}
          onChange={setTeamFilter}
          openDropdown={openDropdown}
          setOpenDropdown={setOpenDropdown}
          compact={isMobile}
        />
        <LandingDropdown
          id="comp"
          label="Competition"
          value={selectedCompetition}
          options={competitionOptions.length ? competitionOptions : [{ value: 'all', label: 'All' }]}
          onChange={setActiveCompetition}
          openDropdown={openDropdown}
          setOpenDropdown={setOpenDropdown}
          compact={isMobile}
        />
        <LandingDropdown
          id="date"
          label="When"
          value={dateFilter}
          options={DATE_OPTIONS}
          onChange={setDateFilter}
          openDropdown={openDropdown}
          setOpenDropdown={setOpenDropdown}
          compact={isMobile}
        />
        {narrowed && !isMobile && (
          <Button
            type="button"
            onClick={() => {
              setTeamFilter('all');
              setDateFilter('all');
            }}
            sx={{
              color: C.lime,
              border: `1px solid rgba(182,242,74,0.35)`,
              borderRadius: 2,
              height: 38,
              px: 1.3,
              fontFamily: fonts.mono,
              fontSize: 11,
              textTransform: 'uppercase',
            }}
          >
            Clear filters
          </Button>
        )}
      </Box>
      {loading ? (
        <LoadingCard label="Loading recent matches..." />
      ) : matches.length ? (
        <Box ref={trackRef} sx={carouselSx}>
          {matches.map((match) => <RecentMatchTile key={match.match_id} match={match} />)}
        </Box>
      ) : (
        <EmptyCard
          label="No scorecards match these filters."
          actionLabel="Reset"
          onAction={() => {
            setTeamFilter('all');
            setDateFilter('all');
            setActiveCompetition('all');
          }}
        />
      )}
    </Box>
  );
};

const RecentMatchTile = ({ match }) => {
  const winner = match.winner || '';
  const winnerColor = getTeamColor(winner) || C.lime;
  const team1Won = winner && [match.team1, match.team1_full].some((team) => String(team || '').toLowerCase() === winner.toLowerCase());
  const team2Won = winner && [match.team2, match.team2_full].some((team) => String(team || '').toLowerCase() === winner.toLowerCase());

  return (
    <Box
      sx={{
        scrollSnapAlign: 'start',
        flex: '0 0 auto',
        width: { xs: 234, md: 252 },
        minHeight: 230,
        p: 1.45,
        borderRadius: 2.5,
        bgcolor: C.surface,
        border: `1px solid ${C.hairline}`,
        borderLeft: `4px solid ${winnerColor}`,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, mb: 1.4 }}>
        <Typography sx={{ ...chipSx, maxWidth: '58%' }}>{match.competition_abbr || match.competition_display || match.competition}</Typography>
        <Typography sx={{ ...monoSx, color: C.low }}>{toDateLabel(match.date)}</Typography>
      </Box>
      <ScoreRow team={match.team1} score={match.innings1_score || match.team1_score} winner={team1Won} />
      <ScoreRow team={match.team2} score={match.innings2_score || match.team2_score} winner={team2Won} />
      <Box sx={{ height: 1, bgcolor: C.hairline, my: 1.35 }} />
      <Typography
        component={Link}
        to={`/scorecard/${match.match_id}`}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          minHeight: 34,
          color: C.mid,
          fontFamily: fonts.body,
          fontSize: 13,
          lineHeight: 1.25,
          fontWeight: 600,
          textDecoration: 'none',
          '&:hover': { color: C.lime },
        }}
      >
        <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: winnerColor, flexShrink: 0 }} />
        {match.result_text || (winner ? `${winner} won` : 'Result unavailable')}
      </Typography>
      <Typography sx={{ color: C.low, fontFamily: fonts.body, fontSize: 12, lineHeight: 1.25, minHeight: 32, mt: 0.4 }}>
        {match.venue || 'Venue unavailable'}
      </Typography>
      <Button component={Link} to={`/scorecard/${match.match_id}`} fullWidth sx={limeButtonSx}>
        Scorecard
      </Button>
    </Box>
  );
};

const ScoreRow = ({ team, score, winner }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 0.75 }}>
    <Typography component={Link} to={routeTeam(team)} sx={{
      color: winner ? C.lime : C.mid,
      fontFamily: fonts.display,
      fontWeight: winner ? 700 : 600,
      fontSize: 16,
      lineHeight: 1,
      textDecoration: 'none',
      '&:hover': { color: C.lime },
    }}>
      {team}
    </Typography>
    <Typography sx={{
      color: winner ? C.lime : C.soft,
      fontFamily: fonts.display,
      fontWeight: winner ? 700 : 600,
      fontSize: 14,
      fontVariantNumeric: 'tabular-nums',
      whiteSpace: 'nowrap',
    }}>
      {score || '-'}
    </Typography>
  </Box>
);

const FeaturedInningsSection = ({ innings, loading, isMobile }) => {
  const trackRef = useRef(null);
  return (
    <Box component="section" sx={{ mb: { xs: 3.75, md: 5.5 } }}>
      <SectionHeader
        kicker="03 / Form"
        title="Recent Standout Innings"
        subtitle="Top hitting from the last 30 days - tap a name for the full profile"
        action={<CarouselButtons trackRef={trackRef} hide={isMobile || loading || innings.length < 2} />}
      />
      {loading ? (
        <LoadingCard label="Loading standout innings..." />
      ) : (
        <Box ref={trackRef} sx={carouselSx}>
          {innings.map((item, index) => (
            <Box
              key={`${item.batter}-${item.date}-${index}`}
              component={Link}
              to={routePlayer(item.batter)}
              sx={{
                scrollSnapAlign: 'start',
                flex: '0 0 auto',
                width: { xs: 280, md: 310 },
                minHeight: 154,
                p: 1.45,
                display: 'flex',
                gap: 1.4,
                alignItems: 'center',
                textDecoration: 'none',
                bgcolor: C.surface,
                border: `1px solid ${C.hairline}`,
                borderRadius: 2.5,
                '&:hover': { bgcolor: C.raised, borderColor: 'rgba(182,242,74,0.25)' },
              }}
            >
              <MiniWagonWheel deliveries={item.deliveries || []} size={isMobile ? 96 : 108} variant="dark" />
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography sx={{ color: C.lime, fontFamily: fonts.display, fontWeight: 700, fontSize: 17, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.batter}
                </Typography>
                <Typography sx={{ color: C.hi, fontFamily: fonts.display, fontWeight: 700, fontSize: 26, lineHeight: 1, fontVariantNumeric: 'tabular-nums', mt: 0.4 }}>
                  {item.runs} <Box component="span" sx={{ color: C.soft, fontSize: 16 }}>({item.balls})</Box>
                </Typography>
                <Typography sx={{ color: C.mid, fontFamily: fonts.mono, fontSize: 11, mt: 0.8 }}>
                  SR {item.strike_rate} - {item.fours}x4 - {item.sixes}x6
                </Typography>
                <Typography sx={{ color: C.soft, fontFamily: fonts.body, fontSize: 12.5, mt: 0.7, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.team} v {item.opponent}
                </Typography>
                <Typography sx={{ color: C.low, fontFamily: fonts.body, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.venue} - {item.date}
                </Typography>
              </Box>
            </Box>
          ))}
          {!innings.length && <EmptyCard label="No standout innings available." />}
        </Box>
      )}
    </Box>
  );
};

const EloSection = ({ isMobile, openDropdown, setOpenDropdown }) => {
  const [eloComp, setEloComp] = useState('international');
  const [eloRange, setEloRange] = useState('all');
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchRankings = async () => {
      setLoading(true);
      const params = new URLSearchParams();
      if (eloComp === 'international') {
        params.set('include_international', 'true');
        params.set('top_teams', '10');
      } else {
        params.set('include_international', 'false');
        params.set('league', 'Indian Premier League');
      }
      const now = new Date();
      if (eloRange === '24m') {
        const start = new Date(now);
        start.setMonth(start.getMonth() - 24);
        params.set('start_date', dateInput(start));
        params.set('end_date', dateInput(now));
      } else if (eloRange === '12m') {
        const start = new Date(now);
        start.setMonth(start.getMonth() - 12);
        params.set('start_date', dateInput(start));
        params.set('end_date', dateInput(now));
      } else if (eloRange === 'ytd') {
        params.set('start_date', `${now.getFullYear()}-01-01`);
        params.set('end_date', dateInput(now));
      }
      try {
        const response = await fetch(`${config.API_URL}/teams/elo-rankings?${params.toString()}`);
        const payload = await response.json();
        if (!cancelled) setRankings(payload.rankings || []);
      } catch (error) {
        console.error('Error fetching ELO rankings:', error);
        if (!cancelled) setRankings([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchRankings();
    return () => { cancelled = true; };
  }, [eloComp, eloRange]);

  return (
    <Box component="section" sx={{ mb: { xs: 3.75, md: 5.5 } }}>
      <SectionHeader kicker="04 / Rank" kickerColor={C.gold} title="ELO Team Rankings" />
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.7, flexWrap: 'wrap' }}>
        <LandingDropdown
          id="elo"
          label="Competition"
          value={eloComp}
          options={[
            { value: 'international', label: 'International Teams' },
            { value: 'ipl', label: 'IPL Teams' },
          ]}
          onChange={setEloComp}
          openDropdown={openDropdown}
          setOpenDropdown={setOpenDropdown}
          compact={isMobile}
        />
        <LandingDropdown
          id="eloRange"
          label="Range"
          value={eloRange}
          options={ELO_RANGE_OPTIONS}
          onChange={setEloRange}
          openDropdown={openDropdown}
          setOpenDropdown={setOpenDropdown}
          compact={isMobile}
        />
        <Typography sx={{ ml: { md: 'auto' }, color: C.low, fontFamily: fonts.mono, fontSize: 11, letterSpacing: '0.08em' }}>
          K-FACTOR 32 - TOP 10
        </Typography>
      </Box>
      {loading ? (
        <LoadingCard label="Loading ELO rankings..." />
      ) : (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' }, gap: 1.15 }}>
          {rankings.slice(0, 10).map((team) => <EloRow key={team.team_name} team={team} />)}
        </Box>
      )}
    </Box>
  );
};

const EloRow = ({ team }) => {
  const color = getTeamColor(team.team_abbreviation || team.team_name) || C.low;
  const rank = Number(team.rank || 0);
  const medal = rank === 1 ? C.gold : rank === 2 ? '#c0c0c0' : rank === 3 ? '#cd7f32' : 'transparent';
  const winPct = Number(team.win_percentage || 0);
  const winColor = winPct >= 60 ? C.lime : winPct >= 45 ? C.gold : C.red;

  return (
    <Box
      component={Link}
      to={routeTeam(team.team_abbreviation || team.team_name)}
      sx={{
        display: 'grid',
        gridTemplateColumns: '42px minmax(0,1fr) auto',
        alignItems: 'center',
        gap: 1.2,
        p: 1.25,
        minHeight: 70,
        bgcolor: C.surface,
        border: `1px solid ${C.hairline}`,
        borderRadius: 2.2,
        textDecoration: 'none',
        '&:hover': { bgcolor: C.raised, borderColor: 'rgba(182,242,74,0.25)' },
      }}
    >
      <Box sx={{
        width: 34,
        height: 34,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        bgcolor: color,
        color: textOn(color),
        border: rank <= 3 ? `2px solid ${medal}` : '0',
        fontFamily: fonts.display,
        fontWeight: 700,
        fontSize: 15,
      }}>
        {rank}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography sx={{ color: C.hi, fontFamily: fonts.display, fontWeight: 700, fontSize: 17, lineHeight: 1 }}>
          {team.team_abbreviation || team.team_name}
        </Typography>
        <Typography sx={{ color: C.soft, fontFamily: fonts.body, fontSize: 12.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', mt: 0.35 }}>
          {team.team_name}
        </Typography>
        <Typography sx={{ color: winColor, fontFamily: fonts.mono, fontSize: 10.5, mt: 0.45 }}>
          {team.wins || 0}-{team.losses || 0} - {Math.round(winPct)}%
        </Typography>
      </Box>
      <Box sx={{ textAlign: 'right' }}>
        <Typography sx={{ color: C.lime, fontFamily: fonts.display, fontWeight: 700, fontSize: 19, fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
          {Math.round(Number(team.current_elo || 0))}
        </Typography>
        <Typography sx={{ color: C.low, fontFamily: fonts.mono, fontSize: 9.5, letterSpacing: '0.1em' }}>
          ELO
        </Typography>
      </Box>
    </Box>
  );
};

const LeagueCountsSection = ({ stats, showLeagueCounts = true }) => {
  if (!showLeagueCounts) return null;
  const items = Object.values(stats || {}).sort((a, b) => (b.match_count || 0) - (a.match_count || 0));
  if (!items.length) return null;

  return (
    <Box component="section" sx={{ mb: { xs: 3.75, md: 5.5 } }}>
      <Kicker>05 / Pipeline</Kicker>
      <Typography sx={{ ...sectionTitleSx, fontSize: { xs: 17, md: 20 } }}>League Match Counts</Typography>
      <Typography sx={{ color: C.soft, mt: 0.6, mb: 1.8, fontFamily: fonts.body, fontSize: 13 }}>
        Ingested match totals per competition - data-pipeline health check
      </Typography>
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: 'repeat(2, minmax(0,1fr))', md: 'repeat(4, minmax(0,1fr))', lg: 'repeat(5, minmax(0,1fr))' },
        gap: 1,
      }}>
        {items.map((item) => (
          <Box key={item.competition_key || item.competition} sx={{ p: 1.35, bgcolor: C.muted, border: `1px solid ${C.hairline}`, borderRadius: 2 }}>
            <Typography sx={{ color: C.mid, fontFamily: fonts.display, fontWeight: 700, fontSize: 15, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {item.competition_display || item.competition}
            </Typography>
            <Typography sx={{ color: C.hi, fontFamily: fonts.display, fontWeight: 700, fontSize: 24, fontVariantNumeric: 'tabular-nums', lineHeight: 1.05, mt: 0.7 }}>
              {(item.match_count || 0).toLocaleString()}
            </Typography>
            <Typography sx={{ color: C.low, fontFamily: fonts.mono, fontSize: 10.5, mt: 0.5 }}>
              latest {toDateLabel(item.latest_date)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

const CreditsSection = () => {
  const year = new Date().getFullYear();
  return (
    <Box component="section" sx={{ borderTop: `1px solid ${C.hairline}`, pt: { xs: 2.6, md: 3.3 }, pb: 2 }}>
      <Kicker>06 / Thanks</Kicker>
      <Typography sx={sectionTitleSx}>Credits & Acknowledgements</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 1.3, mt: 1.8 }}>
        <CreditCard title="Data sources">
          <CreditLink href="https://cricsheet.org/">Cricsheet.org</CreditLink>
          <CreditLink href="https://cricmetric.com/">Cricmetric</CreditLink>
        </CreditCard>
        <CreditCard title="Inspiration">
          {['@prasannalara', '@cricketingview', '@IndianMourinho', '@hganjoo_153', '@randomcricstat', '@kaustats', '@cricviz', '@ajarrodkimber'].map((handle) => (
            <CreditChip key={handle} href={`https://twitter.com/${handle.slice(1)}`}>{handle}</CreditChip>
          ))}
        </CreditCard>
        <CreditCard title="Development">
          <Typography sx={{ color: C.mid, fontFamily: fonts.body, fontSize: 13, mb: 1.2 }}>
            Claude and ChatGPT for Vibe Coding my way through this project.
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <CreditChip href="https://github.com/adityabalaji97/cricket-data-thing" icon={<GitHubIcon sx={{ fontSize: 14 }} />}>GitHub</CreditChip>
            <CreditChip href="https://twitter.com/maybe_eybe" icon={<XIcon sx={{ fontSize: 13 }} />}>@maybe_eybe</CreditChip>
          </Box>
          <Typography sx={{ color: C.low, fontFamily: fonts.mono, fontSize: 11, mt: 1.4 }}>
            Hindsight (c) {year}
          </Typography>
        </CreditCard>
      </Box>
    </Box>
  );
};

const CreditCard = ({ title, children }) => (
  <Box sx={{ p: 1.6, bgcolor: C.surface, border: `1px solid ${C.hairline}`, borderRadius: 2.4 }}>
    <Typography sx={{ color: C.hi, fontFamily: fonts.display, fontWeight: 700, fontSize: 17, mb: 1 }}>
      {title}
    </Typography>
    {children}
  </Box>
);

const CreditLink = ({ href, children }) => (
  <Typography component="a" href={href} target="_blank" rel="noopener noreferrer" sx={{
    display: 'block',
    color: C.lime,
    fontFamily: fonts.body,
    fontWeight: 600,
    fontSize: 14,
    textDecoration: 'none',
    mb: 0.8,
    '&:hover': { color: C.limeHover },
  }}>
    {children}
  </Typography>
);

const CreditChip = ({ href, icon, children }) => (
  <Box component="a" href={href} target="_blank" rel="noopener noreferrer" sx={{
    display: 'inline-flex',
    alignItems: 'center',
    gap: 0.5,
    mr: 0.6,
    mb: 0.7,
    px: 0.75,
    py: 0.45,
    color: C.mid,
    bgcolor: C.muted,
    border: `1px solid ${C.hairline}`,
    borderRadius: 1,
    fontFamily: fonts.mono,
    fontSize: 11,
    textDecoration: 'none',
    '&:hover': { color: C.lime, borderColor: 'rgba(182,242,74,0.35)' },
  }}>
    {icon}
    {children}
  </Box>
);

const ExploreDrawer = ({ open, onClose }) => (
  <>
    <Box
      onClick={onClose}
      sx={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        bgcolor: 'rgba(0,0,0,0.45)',
        opacity: open ? 1 : 0,
        pointerEvents: open ? 'auto' : 'none',
        transition: 'opacity 0.28s cubic-bezier(0.22,1,0.36,1)',
      }}
    />
    <Box
      aria-hidden={!open}
      sx={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: { xs: '86%', sm: 380 },
        zIndex: 61,
        bgcolor: C.muted,
        borderLeft: `1px solid ${C.hairlineStrong}`,
        p: 2,
        transform: open ? 'translateX(0)' : 'translateX(102%)',
        visibility: open ? 'visible' : 'hidden',
        pointerEvents: open ? 'auto' : 'none',
        transition: open
          ? 'transform 0.28s cubic-bezier(0.22,1,0.36,1)'
          : 'transform 0.28s cubic-bezier(0.22,1,0.36,1), visibility 0s linear 0.28s',
        boxShadow: '0 0 60px rgba(0,0,0,0.5)',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Kicker>Explore</Kicker>
          <Typography sx={{ color: C.hi, fontFamily: fonts.display, fontWeight: 700, fontSize: 22 }}>
            Hindsight tools
          </Typography>
        </Box>
        <IconButton aria-label="Close explore menu" onClick={onClose} sx={{ color: C.hi }}>
          <CloseIcon />
        </IconButton>
      </Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {EXPLORE_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <Box
              key={item.label}
              component={Link}
              to={item.route}
              onClick={onClose}
              sx={{
                display: 'grid',
                gridTemplateColumns: '42px minmax(0,1fr) 18px',
                alignItems: 'center',
                gap: 1,
                p: 1,
                color: C.hi,
                textDecoration: 'none',
                borderRadius: 2,
                border: `1px solid ${C.hairline}`,
                bgcolor: C.surface,
                '&:hover': { bgcolor: C.raised, borderColor: 'rgba(255,255,255,0.14)' },
              }}
            >
              <Box sx={{ width: 38, height: 38, display: 'grid', placeItems: 'center', borderRadius: 1.6, bgcolor: `${item.color}22`, color: item.color }}>
                <Icon sx={{ fontSize: 20 }} />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 16 }}>{item.label}</Typography>
                <Typography sx={{ color: C.soft, fontFamily: fonts.body, fontSize: 12.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.description}
                </Typography>
              </Box>
              <ChevronRightIcon sx={{ color: C.low, fontSize: 18 }} />
            </Box>
          );
        })}
      </Box>
    </Box>
  </>
);

const LoadingCard = ({ label }) => (
  <Box sx={{ minHeight: 130, display: 'grid', placeItems: 'center', bgcolor: C.surface, border: `1px solid ${C.hairline}`, borderRadius: 2.5 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2, color: C.soft }}>
      <CircularProgress size={18} sx={{ color: C.lime }} />
      <Typography sx={{ fontFamily: fonts.body, fontSize: 14 }}>{label}</Typography>
    </Box>
  </Box>
);

const EmptyCard = ({ label, actionLabel, onAction }) => (
  <Box sx={{ minHeight: 130, width: '100%', display: 'grid', placeItems: 'center', bgcolor: C.surface, border: `1px solid ${C.hairline}`, borderRadius: 2.5, p: 2 }}>
    <Box sx={{ textAlign: 'center' }}>
      <Typography sx={{ color: C.soft, fontFamily: fonts.body, fontSize: 14 }}>{label}</Typography>
      {actionLabel && (
        <Button type="button" onClick={onAction} sx={{ mt: 1, color: C.lime, fontFamily: fonts.display, fontWeight: 700 }}>
          {actionLabel} <ChevronRightIcon sx={{ fontSize: 16 }} />
        </Button>
      )}
    </Box>
  </Box>
);

const LandingPage = ({ showLeagueCounts = true }) => {
  const isMobile = useMediaQuery('(max-width:759px)');
  const [navOpen, setNavOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState(null);
  const [fixtures, setFixtures] = useState([]);
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [recentData, setRecentData] = useState(null);
  const [recentLoading, setRecentLoading] = useState(true);
  const [activeCompetition, setActiveCompetition] = useState('');
  const [teamFilter, setTeamFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [innings, setInnings] = useState([]);
  const [inningsLoading, setInningsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadFixtures = async () => {
      setFixturesLoading(true);
      const nextMatches = await fetchUpcomingMatches(8);
      if (!cancelled) {
        setFixtures(nextMatches);
        setFixturesLoading(false);
      }
    };
    loadFixtures();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadRecent = async () => {
      setRecentLoading(true);
      const params = new URLSearchParams({
        competition: activeCompetition || 'all',
        limit: '18',
        offset: '0',
        per_group: '4',
        window: dateFilter,
      });
      if (teamFilter !== 'all') params.set('team', teamFilter);
      try {
        const response = await fetch(`${config.API_URL}/recent-matches/discover?${params.toString()}`);
        const payload = await response.json();
        if (cancelled) return;
        setRecentData(payload);
        if (!activeCompetition) {
          const nextCompetition = latestCompetition(payload.competition_stats);
          if (nextCompetition) setActiveCompetition(nextCompetition);
        }
      } catch (error) {
        console.error('Error fetching recent matches:', error);
        if (!cancelled) setRecentData(null);
      } finally {
        if (!cancelled) setRecentLoading(false);
      }
    };
    loadRecent();
    return () => { cancelled = true; };
  }, [activeCompetition, teamFilter, dateFilter]);

  useEffect(() => {
    let cancelled = false;
    const loadInnings = async () => {
      setInningsLoading(true);
      try {
        const response = await fetch(`${config.API_URL}/landing/featured-innings`);
        const payload = await response.json();
        if (!cancelled) setInnings(Array.isArray(payload) ? payload : []);
      } catch (error) {
        console.error('Error fetching featured innings:', error);
        if (!cancelled) setInnings([]);
      } finally {
        if (!cancelled) setInningsLoading(false);
      }
    };
    loadInnings();
    return () => { cancelled = true; };
  }, []);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: C.bg,
        color: C.hi,
        fontFamily: fonts.body,
        px: { xs: '14px', md: '34px' },
        pt: { xs: '16px', md: '26px' },
        pb: { xs: '56px', md: '72px' },
        '@keyframes livepulse': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.55 },
        },
      }}
    >
      {openDropdown && <Box onClick={() => setOpenDropdown(null)} sx={{ position: 'fixed', inset: 0, zIndex: 35 }} />}
      <Box sx={{ maxWidth: 1220, mx: 'auto' }}>
        <TopBar navOpen={navOpen} setNavOpen={setNavOpen} isMobile={isMobile} />
        <TodaySection matches={fixtures} loading={fixturesLoading} isMobile={isMobile} />
        <RecentMatchesSection
          data={recentData}
          loading={recentLoading}
          activeCompetition={activeCompetition}
          setActiveCompetition={setActiveCompetition}
          teamFilter={teamFilter}
          setTeamFilter={setTeamFilter}
          dateFilter={dateFilter}
          setDateFilter={setDateFilter}
          openDropdown={openDropdown}
          setOpenDropdown={setOpenDropdown}
          isMobile={isMobile}
        />
        <FeaturedInningsSection innings={innings} loading={inningsLoading} isMobile={isMobile} />
        <EloSection isMobile={isMobile} openDropdown={openDropdown} setOpenDropdown={setOpenDropdown} />
        <LeagueCountsSection stats={recentData?.competition_stats} showLeagueCounts={showLeagueCounts} />
        <CreditsSection />
      </Box>
      <ExploreDrawer open={navOpen} onClose={() => setNavOpen(false)} />
    </Box>
  );
};

export default LandingPage;
