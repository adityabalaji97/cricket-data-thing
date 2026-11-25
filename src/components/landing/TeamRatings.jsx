import React, { useEffect, useMemo, useState } from 'react';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { getTeamColor, readableOnDark } from '../../utils/teamColors';

// Landing plan L2: one rating, the team page's. The team page rates a side by its Elo after its latest match
// (services/team_page.rating: matches.team1_elo / team2_elo, a renamed side counted as one), so this list does the
// same from /teams/elo-rankings: the ten current IPL franchises (Royal Challengers Bangalore and Bengaluru are one
// side, at their latest; Rising Pune, Kochi and Gujarat Lions are gone), or the top 12 international sides (the team
// page's international peers). No date window: a window only changed which "latest" was picked.

export const IPL_SIDES = ['CSK', 'DC', 'GT', 'KKR', 'LSG', 'MI', 'PBKS', 'RCB', 'RR', 'SRH'];
// models.INTERNATIONAL_TEAMS_RANKED[:12] (services/player_verdict.TOP_TEAMS).
export const TOP_INTERNATIONAL = ['India', 'Australia', 'England', 'West Indies', 'New Zealand', 'South Africa',
  'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan', 'Ireland', 'Zimbabwe'];
const INTL_ABBR = { India: 'IND', Australia: 'AUS', England: 'ENG', 'West Indies': 'WI', 'New Zealand': 'NZ',
  'South Africa': 'SA', Pakistan: 'PAK', 'Sri Lanka': 'SL', Bangladesh: 'BAN', Afghanistan: 'AFG', Ireland: 'IRE',
  Zimbabwe: 'ZIM' };

// The IPL is stored under two names: "Indian Premier League" to 2025 (Cricsheet) and "IPL" from 2026 (the live feed).
// /teams/elo-rankings filters on one, so asking only for the first left every side at its 2025 rating (Mumbai 4th at
// 1528 locally, against the team page's 9th at 1456). Both are fetched and each side kept at its latest.
export const SCOPES = {
  ipl: { label: 'IPL', queries: ['Indian Premier League', 'IPL'].map((league) => ({ include_international: 'false', league, format: 'T20', gender: 'male' })) },
  intl: { label: 'T20Is', queries: [{ include_international: 'true', format: 'T20', gender: 'male' }] },
};

// One row per side at its latest rating: merges a side's old and new names (same abbreviation), keeps the current
// sides only, and re-ranks.
export const currentSides = (rankings, scope) => {
  const bySide = new Map();
  for (const r of rankings || []) {
    const key = scope === 'ipl' ? r.team_abbreviation : r.team_name;
    const keep = scope === 'ipl' ? IPL_SIDES.includes(key) : TOP_INTERNATIONAL.includes(key);
    if (!keep) continue;
    const prev = bySide.get(key);
    if (!prev || String(r.last_match_date || '') > String(prev.last_match_date || '')) bySide.set(key, r);
  }
  return [...bySide.values()]
    .map((r) => ({ name: r.team_name, abbr: scope === 'ipl' ? r.team_abbreviation : (INTL_ABBR[r.team_name] || r.team_name),
      // The team page takes a franchise's code ("MI") or a country's name.
      page: scope === 'ipl' ? r.team_abbreviation : r.team_name,
      rating: Math.round(Number(r.current_elo) || 0), last: r.last_match_date }))
    .sort((a, b) => b.rating - a.rating || a.abbr.localeCompare(b.abbr))
    .map((r, i) => ({ ...r, rank: i + 1 }));
};

export const ordinal = (n) => { const s = ['th', 'st', 'nd', 'rd']; const v = n % 100; return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`; };
export const dayLabel = (iso) => {
  const d = new Date(`${iso}T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

// A franchise by its city, as people say it ("Mumbai are 9th").
const IPL_CITY = { CSK: 'Chennai', DC: 'Delhi', GT: 'Gujarat', KKR: 'Kolkata', LSG: 'Lucknow', MI: 'Mumbai', PBKS: 'Punjab',
  RCB: 'Bengaluru', RR: 'Rajasthan', SRH: 'Hyderabad' };

// The claim: who leads, and who is last. Before the auction (context 'auction') it says where they start it.
export const ratingsClaim = (sides, scope, context = null) => {
  if (sides.length < 2) return '';
  const top = sides[0];
  const last = sides[sides.length - 1];
  const city = (s) => IPL_CITY[s.abbr] || s.name;
  if (scope === 'ipl' && context === 'auction') {
    return `${city(top)} go into the auction as the top-rated side. ${city(last)} are ${ordinal(last.rank)} of ${sides.length}.`;
  }
  // IPL sides by city here too: the full names ran the claim to three lines at 390.
  if (scope === 'ipl') return `${city(top)} are the top-rated IPL side. ${city(last)} are ${ordinal(last.rank)} of ${sides.length}.`;
  const what = 'T20I side among the top 12';
  return `${top.name} are the top-rated ${what}. ${last.name} are ${ordinal(last.rank)} of ${sides.length}.`;
};

export const routeTeam = (abbr) => `/team?team=${encodeURIComponent(abbr)}&autoload=true`;

// One fetch per scope per page load (2 calls for the IPL, 1 for T20Is), shared by the landing card and the /team list,
// so going from one to the other doesn't ask again. A failed fetch is dropped, so "Try again" asks afresh.
const fetched = {};
export const fetchRankings = (scope) => {
  if (!fetched[scope]) {
    fetched[scope] = Promise.all(SCOPES[scope].queries.map((query) => fetch(`${config.API_URL}/teams/elo-rankings?${new URLSearchParams(query)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`elo rankings: ${r.status}`))))))
      .then((all) => all.flatMap((d) => d.rankings || []))
      .catch((e) => { delete fetched[scope]; throw e; });
  }
  return fetched[scope];
};

// { state: {status, rows}, sides (current sides, ranked), retry }.
export const useSides = (scope) => {
  const [state, setState] = useState({ status: 'loading', rows: [] });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading', rows: [] });
    fetchRankings(scope)
      .then((rows) => { if (!cancelled) setState({ status: 'ready', rows }); })
      .catch(() => { if (!cancelled) setState({ status: 'error', rows: [] }); });
    return () => { cancelled = true; };
  }, [scope, attempt]);
  const sides = useMemo(() => currentSides(state.rows, scope), [state.rows, scope]);
  return { state, sides, retry: () => setAttempt((n) => n + 1) };
};

const TeamRatings = ({ initialScope = 'ipl', kicker = 'Team ratings', action = null, context = null }) => {
  const [scope, setScope] = useState(initialScope);
  const { state, sides, retry } = useSides(scope);
  const lo = Math.min(...sides.map((s) => s.rating));
  const hi = Math.max(...sides.map((s) => s.rating));
  const latest = sides.reduce((m, s) => (String(s.last || '') > m ? String(s.last) : m), '');
  const perCol = Math.ceil(sides.length / 2);

  return (
    <Box component="section" aria-label="Team ratings" sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`,
      borderRadius: '20px', px: { xs: 1.75, md: 2.5 }, pt: 1.75, pb: 1.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
        <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase',
          color: colors.accent }}>
          {typeof kicker === 'function' ? kicker(scope) : kicker}
        </Typography>
        {typeof action === 'function' ? action(scope) : action}
      </Box>
      {/* Claim */}
      <Typography component="h2" sx={{ m: 0, mt: 0.75, fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 20, md: 24 },
        lineHeight: 1.15, color: colors.textHi, minHeight: { xs: 46, md: 28 } }}>
        {state.status === 'ready' ? ratingsClaim(sides, scope, context) : ' '}
      </Typography>
      <Box role="tablist" aria-label="Which sides" sx={{ display: 'flex', gap: 0.75, mt: 1 }}>
        {Object.entries(SCOPES).map(([key, s]) => (
          <Box key={key} component="button" type="button" role="tab" aria-selected={scope === key} onClick={() => setScope(key)}
            sx={{ minHeight: 44, px: 1.75, borderRadius: 999, cursor: 'pointer', fontFamily: fonts.mono, fontSize: 12,
              letterSpacing: '0.06em', border: `1px solid ${scope === key ? 'rgba(182,242,74,0.45)' : colors.borderStrong}`,
              bgcolor: scope === key ? 'rgba(182,242,74,0.08)' : 'transparent', color: scope === key ? colors.accent : colors.textMed }}>
            {s.label}
          </Box>
        ))}
      </Box>
      {/* Picture: each side's rating as a dot on one scale, lowest to highest. */}
      {state.status === 'loading' && (
        <Box sx={{ height: 44 * 6, display: 'grid', placeItems: 'center' }}>
          <CircularProgress size={18} sx={{ color: colors.accent }} />
        </Box>
      )}
      {state.status === 'error' && (
        <Box role="alert" sx={{ height: 44 * 6, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
          <Box>
            <Typography sx={{ color: colors.textLo, fontSize: 14 }}>Couldn&apos;t load the ratings.</Typography>
            <Button type="button" onClick={retry} sx={{ mt: 1, minHeight: 44, px: 2, color: colors.accent,
              border: '1px solid rgba(182,242,74,0.35)', borderRadius: 2, fontFamily: fonts.mono, fontSize: 12, fontWeight: 700 }}>
              Try again
            </Button>
          </Box>
        </Box>
      )}
      {state.status === 'ready' && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gridTemplateRows: `repeat(${perCol}, 44px)`,
          gridAutoFlow: 'column', columnGap: { xs: 2, md: 4 }, mt: 0.75, minHeight: 44 * 5 }}>
          {sides.map((s) => {
            const pos = hi > lo ? (s.rating - lo) / (hi - lo) : 0.5;
            const dot = readableOnDark(getTeamColor(s.abbr) || getTeamColor(s.name) || colors.textLo);
            return (
              <Box key={s.abbr} component={Link} to={routeTeam(s.page)} onClick={() => window.scrollTo(0, 0)} aria-label={`${s.name}: ${s.rating}, ${ordinal(s.rank)}`}
                sx={{ display: 'flex', alignItems: 'center', gap: 0.9, minWidth: 0, height: 44, textDecoration: 'none',
                  color: colors.textHi, borderBottom: s.rank % perCol === 0 ? 0 : `1px solid ${colors.border}`,
                  '&:hover .abbr': { color: colors.accent } }}>
                <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textFaint, width: 16, textAlign: 'right', flexShrink: 0 }}>
                  {s.rank}
                </Typography>
                <Typography className="abbr" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 16, width: { xs: 40, md: 48 }, flexShrink: 0,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.abbr}
                </Typography>
                <Box aria-hidden sx={{ flex: 1, minWidth: 20, height: '1px', bgcolor: colors.borderStrong, position: 'relative', mx: 0.75 }}>
                  <Box sx={{ position: 'absolute', top: -5, left: `${pos * 100}%`, ml: '-5.5px', width: 11, height: 11, borderRadius: '50%',
                    bgcolor: dot, boxShadow: `0 0 0 2px ${colors.surface1}, 0 0 0 3px rgba(255,255,255,0.28)` }} />
                </Box>
                <Typography sx={{ fontFamily: fonts.mono, fontWeight: 600, fontSize: 13, color: colors.textMed, width: 36, textAlign: 'right',
                  flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
                  {s.rating}
                </Typography>
              </Box>
            );
          })}
        </Box>
      )}
      {/* Scope and credit */}
      <Box sx={{ mt: 1, pt: 1, borderTop: `1px solid ${colors.border}` }}>
        <Typography sx={{ fontSize: 12, lineHeight: 1.4, color: colors.textLo }}>
          {scope === 'ipl' ? 'Elo rating after each side\'s latest IPL match' : 'Elo rating after each side\'s latest T20I'}
          {latest ? `, to ${dayLabel(latest)}` : ''}. The same rating as each team page; tap a side for its page.
        </Typography>
        <Typography sx={{ fontSize: 12, color: colors.textFaint, mt: 0.25 }}>
          hindsightcricket.com · Data: Cricsheet
        </Typography>
      </Box>
    </Box>
  );
};

export default TeamRatings;
