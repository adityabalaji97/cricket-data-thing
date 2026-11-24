import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { siteOrigin } from '../ui/ChartExportButton';
import { PROMISE, TAGLINE } from '../../brand';
import { noteDateLabel, previewPassed } from '../../utils/noteDates';

/**
 * /links — the bio link for Instagram (instagram.com/hindsightcricket) and YouTube (youtube.com/@hindsightcricket).
 * Each bio points here with its own ?utm_source, and every link on the page carries it on (utm_medium=bio_link), so the
 * usage report can count visitors per platform. Recent posts are the carousels marked posted in the admin queue
 * (GET /snapshots/ig/recent).
 *
 * Landing plan L8: the same idea as the home page (one logo, one tagline), with what a visitor from a post came for
 * first: the posts themselves, dated, then the day's preview. Team posts link to /team?team=X#squad.
 */
const SOURCES = ['instagram', 'youtube', 'x'];
const CHANNELS = [
  ['Instagram', 'https://www.instagram.com/hindsightcricket'],
  ['YouTube', 'https://www.youtube.com/@hindsightcricket'],
];
const NOTE_KIND = { recap: 'Match recap', preview: 'Preview', analysis: 'Analysis', article: 'Article' };

const dayLabel = (iso) => {
  const d = new Date(`${String(iso || '').slice(0, 10)}T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'Asia/Kolkata' });
};

const Kicker = ({ children }) => (
  <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, letterSpacing: '.14em', textTransform: 'uppercase',
    color: colors.accent, mt: 1.5 }}>
    {children}
  </Typography>
);

const LinkButton = ({ to, title, sub, tagged }) => (
  <Box component={RouterLink} to={tagged(to)} sx={{
    display: 'block', textDecoration: 'none', p: 1.75, borderRadius: 3, bgcolor: colors.surface1,
    border: `1px solid ${colors.border}`, '&:hover': { borderColor: colors.accent },
  }}>
    <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 19, color: colors.textHi }}>{title}</Typography>
    {sub && <Typography sx={{ fontSize: 13, color: colors.textMed, mt: 0.25 }}>{sub}</Typography>}
  </Box>
);

const IgLinks = () => {
  const [posts, setPosts] = useState(null);
  const [notes, setNotes] = useState([]);
  const [fixture, setFixture] = useState(null);
  const [params] = useSearchParams();
  const source = SOURCES.includes(params.get('utm_source')) ? params.get('utm_source') : 'instagram';
  const tagged = (path) => {
    const [base, hash] = path.split('#');
    return `${base}${base.includes('?') ? '&' : '?'}utm_source=${source}&utm_medium=bio_link${hash ? `#${hash}` : ''}`;
  };

  useEffect(() => { document.title = `Hindsight · ${TAGLINE}`; }, []);

  useEffect(() => {
    axios.get(`${config.API_URL}/snapshots/ig/recent`, { params: { limit: 9 } })
      .then(({ data }) => setPosts(data.posts || [])).catch(() => setPosts([]));
    // Dated notes, without previews of matches already played: the fallback when no post is marked posted, and
    // the written pieces behind the posts otherwise.
    axios.get(`${config.API_URL}/notes`, { params: { limit: 8 } })
      .then(({ data }) => setNotes((data.notes || []).filter((n) => !previewPassed(n)).slice(0, 3))).catch(() => {});
    axios.get(`${config.API_URL}/fixtures/upcoming`, { params: { count: 3 } })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : (data.fixtures || []);
        setFixture(list.find((f) => f.team1 === 'India' || f.team2 === 'India') || list[0] || null);
      }).catch(() => {});
  }, []);

  const preview = fixture && `/venue?venue=${encodeURIComponent(fixture.venue)}&team1=${encodeURIComponent(fixture.team1)}`
    + `&team2=${encodeURIComponent(fixture.team2)}&autoload=true&story=1`
    + `&fmt=${fixture.format === 'ODI' ? 'mens-odi' : 'mens-t20'}`;

  return (
    <Box sx={{ maxWidth: 480, mx: 'auto', px: 2, py: 2.5, display: 'grid', gap: 1.25 }}>
      <Box sx={{ textAlign: 'center', mb: 0.5 }}>
        {/* The home page's logo and wordmark, so the bio link and the site read as one place. */}
        <Box component={RouterLink} to={tagged('/')} sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, minHeight: 44,
          textDecoration: 'none' }}>
          <Box component="img" src="/cricket-icon.svg" alt="" sx={{ width: 40, height: 40 }} />
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26, color: colors.textHi }}>Hindsight</Typography>
        </Box>
        <Typography component="h1" sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 22, lineHeight: 1.15,
          color: colors.textHi, mt: 0.75 }}>
          Cricket, ball by ball. <Box component="span" sx={{ color: colors.accent }}>{TAGLINE}.</Box>
        </Typography>
        <Typography sx={{ fontSize: 14, color: colors.textMed, mt: 0.5 }}>{PROMISE}</Typography>
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mt: 0.5 }}>
          {CHANNELS.map(([name, href]) => (
            <Typography key={name} component="a" href={href} target="_blank" rel="noopener noreferrer"
              sx={{ display: 'inline-flex', alignItems: 'center', minHeight: 44, px: 1.25, fontSize: 14, color: colors.accent,
                textDecoration: 'none' }}>
              {name}
            </Typography>
          ))}
        </Box>
      </Box>

      {posts && posts.length > 0 && (
        <>
          <Kicker>Latest posts</Kicker>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0.75 }}>
            {posts.map((p) => (
              <Box key={p.id} component={RouterLink} to={tagged(`/g/${p.id}`)} aria-label={p.title}
                sx={{ textDecoration: 'none', minWidth: 0 }}>
                <Box component="img" src={`${siteOrigin()}/img/${p.id}.png?slide=1`} alt={p.title} loading="lazy"
                  sx={{ width: '100%', aspectRatio: '4 / 5', display: 'block', borderRadius: 1.5, bgcolor: colors.surface2 }} />
                {p.planned_for && (
                  <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textLo, mt: 0.4 }}>
                    {dayLabel(p.planned_for)}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        </>
      )}

      {preview && (
        <>
          <Kicker>Next match</Kicker>
          <LinkButton tagged={tagged} to={preview} title={`${fixture.team1} v ${fixture.team2}: the preview`}
            sub="Par score, matchups, who suits the ground: the full story" />
        </>
      )}

      {notes.length > 0 && (
        <>
          <Kicker>Latest notes</Kicker>
          {notes.map((n) => (
            <LinkButton key={n.id} tagged={tagged} to={`/notes/${n.slug}`} title={n.title}
              sub={[NOTE_KIND[n.kind] || 'Note', noteDateLabel(n)].filter(Boolean).join(' · ')} />
          ))}
        </>
      )}

      <Kicker>Explore</Kicker>
      <LinkButton tagged={tagged} to="/query" title="Ask your own question" sub="Any player, any phase, any matchup, in plain words" />
      <LinkButton tagged={tagged} to="/games/19-0" title="19-0" sub="Draft an IPL XI from 19 seasons. Can it make the playoffs in all 19?" />
      <LinkButton tagged={tagged} to="/games" title="Daily games" sub="Guess the innings, Higher or Lower, Call It" />
      <LinkButton tagged={tagged} to="/" title="Everything else" sub="Today's matches, team ratings, scorecards" />
    </Box>
  );
};

export default IgLinks;
