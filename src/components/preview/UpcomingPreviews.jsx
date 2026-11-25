import React, { useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { colors, fonts } from '../../theme/hindsightDark';
import { fetchUpcomingMatches, localStart, routePreview } from '../../data/iplSchedule';

// /venue with no venue (the bottom nav's Preview): the next fixtures first, each opening its story preview, so the
// tab isn't a bare form (round 2 audit). The form below stays for any other venue and pair. Renders nothing while
// loading, on error or with no fixtures, so the form is never pushed down by an empty box.
const UpcomingPreviews = () => {
  const [matches, setMatches] = useState([]);
  useEffect(() => {
    let cancelled = false;
    fetchUpcomingMatches(6).then((m) => { if (!cancelled) setMatches(m); }).catch(() => {});
    return () => { cancelled = true; };
  }, []);
  if (!matches.length) return null;
  return (
    <Box component="section" aria-label="Upcoming fixtures" sx={{ mb: 2, bgcolor: colors.surface1, border: `1px solid ${colors.border}`,
      borderRadius: '20px', px: { xs: 1.75, md: 2.5 }, pt: 1.75, pb: 1 }}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase',
        color: colors.accent }}>
        Next fixtures
      </Typography>
      <Typography component="h2" sx={{ m: 0, mt: 0.5, mb: 0.5, fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 19, md: 22 },
        lineHeight: 1.15, color: colors.textHi }}>
        Pick a match for its preview
      </Typography>
      <Box component="nav" aria-label="Fixture previews">
        {matches.map((m, i) => {
          const when = m.isLive ? 'LIVE' : (localStart(m).label || '');
          return (
            <Box key={`${m.matchId || i}-${m.date}`} component={Link} to={routePreview(m)} onClick={() => window.scrollTo(0, 0)}
              aria-label={`${m.team1} v ${m.team2}: match preview`}
              sx={{ display: 'flex', alignItems: 'center', gap: 1.25, minHeight: 52, py: 0.5, textDecoration: 'none', color: colors.textHi,
                borderBottom: i === matches.length - 1 ? 0 : `1px solid ${colors.border}`, '&:hover .teams': { color: colors.accent } }}>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography className="teams" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 16, whiteSpace: 'nowrap',
                  overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {m.team1} v {m.team2}
                </Typography>
                <Typography sx={{ fontSize: 12.5, color: colors.textLo, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <Box component="span" sx={{ color: m.isLive ? colors.red : colors.textMed, fontFamily: fonts.mono, fontSize: 12 }}>{when}</Box>
                  {` · ${m.format === 'ODI' ? 'ODI' : 'T20'}, ${String(m.venue || '').split(',')[0]}`}
                </Typography>
              </Box>
              <Box aria-hidden sx={{ color: colors.textFaint, fontSize: 16, flexShrink: 0 }}>›</Box>
            </Box>
          );
        })}
      </Box>
      <Typography sx={{ fontSize: 12, color: colors.textLo, mt: 0.5, pt: 1, borderTop: `1px solid ${colors.border}` }}>
        Or pick any venue and two sides below.
      </Typography>
    </Box>
  );
};

export default UpcomingPreviews;
