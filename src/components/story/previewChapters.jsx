import React from 'react';
import { Box, Typography } from '@mui/material';
import { WinningPhases } from '../ExpectStrip';
import { TeamFormCard, TeamSplitHeader, VenueRecentMatches } from '../MatchHistory';
import { colors, fonts } from '../../theme/hindsightDark';

const SMALL = 15;

/**
 * Chunk 1 of MATCH_PREVIEW_VIZ_PLAN.md: the story shell around modules the preview already has,
 * as they are. Titles, help lines and fitted visuals come with the module registry (chunk 2) and
 * the chapter chunks (5-8). Cards whose data is missing are left out, never shown empty.
 *
 * `charts` passes in VenueNotes' own chart components (WinPercentagesPie, ScoresBarChart) so this
 * module does not import VenueNotes.
 */
const buildPreviewChapters = ({
  venue, startDate, endDate, venueStats, matchHistory, expectBlock, team1, team2, charts, isMobile,
}) => {
  // "2022–26": short enough to stay on one footer line.
  const yearOf = (d) => (d ? String(d).slice(0, 4) : null);
  const startYear = yearOf(startDate);
  const endYear = yearOf(endDate) || String(new Date().getFullYear());
  const span = startYear ? `${startYear}–${endYear.slice(2)}` : `to ${endYear}`;
  const venueMatches = venueStats?.total_matches || 0;
  const venueSample = `${venueMatches} matches at ${venue.split(',')[0]} · ${span}`;
  const hasVenue = venueMatches > 0;

  const glance = [];
  const par = expectBlock?.venue?.avg_winning_score ?? expectBlock?.venue?.avg_first_innings;
  if (par) {
    glance.push({
      id: 'par',
      title: `Par here is about ${par}`,
      help: null,
      sample: `${expectBlock.venue.total_matches} matches at ${venue.split(',')[0]} · ${span}`,
      smallSample: (expectBlock.venue.total_matches || 0) < SMALL,
      info: 'Par is the average first-innings total of sides that went on to win batting first at this ground, in the selected window. Where too few sides won batting first, the average first innings is used instead.',
      render: () => (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 96, lineHeight: 1, color: colors.accent }}>{par}</Typography>
          {expectBlock.venue.avg_first_innings && (
            <Typography sx={{ mt: 1.5, fontSize: 16, color: colors.textMed }}>
              The average first innings here is {expectBlock.venue.avg_first_innings}.
            </Typography>
          )}
        </Box>
      ),
    });
  }

  const ground = [];
  if (expectBlock?.winning_phases) {
    ground.push({
      id: 'winning-phases',
      title: 'How winning innings were built here',
      help: null,
      sample: venueSample,
      smallSample: venueMatches < SMALL,
      info: 'Average runs in the powerplay, middle overs and death overs, for sides that won batting first and sides that won chasing.',
      render: () => <WinningPhases phases={expectBlock.winning_phases} />,
    });
  }
  if (hasVenue && charts?.WinPercentagesPie) {
    ground.push({
      id: 'results',
      title: 'Batting first or chasing: who wins here?',
      help: null,
      sample: venueSample,
      smallSample: venueMatches < SMALL,
      info: 'Matches won by the side batting first, by the side chasing, and with no result, at this ground in the selected window.',
      render: () => <charts.WinPercentagesPie data={venueStats} />,
    });
  }
  if (hasVenue && charts?.ScoresBarChart) {
    ground.push({
      id: 'totals',
      title: 'What total wins here?',
      help: null,
      sample: venueSample,
      smallSample: venueMatches < SMALL,
      info: 'First-innings benchmarks at this ground: totals that were defended, targets that were chased, and the average first innings.',
      render: () => <charts.ScoresBarChart data={venueStats} />,
    });
  }
  if (matchHistory?.venue_results?.length) {
    ground.push({
      id: 'recent-results',
      title: `Recent results at ${venue.split(',')[0]}`,
      help: null,
      sample: `Last ${Math.min(matchHistory.venue_results.length, 5)} matches · ${span}`,
      info: 'The most recent matches at this ground in the selected window; the winning side is highlighted.',
      render: () => <VenueRecentMatches venue={venue} matches={matchHistory.venue_results.slice(0, 5)} isMobile={isMobile} />,
    });
  }

  const teams = [];
  const h2h = matchHistory?.h2h_stats;
  if (h2h && team1 && team2) {
    const meetings = (h2h.team1_wins || 0) + (h2h.team2_wins || 0) + (h2h.draws || 0);
    teams.push({
      id: 'head-to-head',
      title: `${team1} v ${team2}: head to head`,
      help: null,
      sample: `${meetings} meetings · ${span}`,
      smallSample: meetings < SMALL,
      info: 'Results of every meeting between the two sides in the selected window, at any ground.',
      render: () => <TeamSplitHeader team1={team1} team2={team2} stats={h2h} isMobile={isMobile} />,
    });
  }
  if (team1 && team2 && (matchHistory?.team1_results?.length || matchHistory?.team2_results?.length)) {
    teams.push({
      id: 'form',
      title: 'Recent form',
      help: null,
      sample: 'Last 5 matches each · any opponent',
      info: 'Each side\'s last five results; tap a result for the scorecard summary.',
      render: () => (
        <TeamFormCard
          team1={team1}
          team2={team2}
          team1Matches={matchHistory.team1_results}
          team2Matches={matchHistory.team2_results}
          isMobile={isMobile}
        />
      ),
    });
  }

  return [
    { id: 'glance', title: 'At a glance', cards: glance },
    { id: 'ground', title: 'The ground', cards: ground },
    { id: 'teams', title: 'The teams', cards: teams },
  ].filter((chapter) => chapter.cards.length);
};

export default buildPreviewChapters;
