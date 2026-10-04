import React from 'react';
import { Box, Typography } from '@mui/material';
import { WinningPhases } from '../ExpectStrip';
import { TeamFormCard, TeamSplitHeader, VenueRecentMatches } from '../MatchHistory';
import { ScoresBarChart, WinPercentagesPie } from '../venue/VenueResultCharts';
import { colors, fonts } from '../../theme/hindsightDark';

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

export const VISUALS = {
  stat: Stat,
  par: Par,
  chase_band: ChaseBand,
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
