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

export const VISUALS = {
  stat: Stat,
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
