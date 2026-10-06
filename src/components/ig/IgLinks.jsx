import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { siteOrigin } from '../ui/ChartExportButton';

/**
 * /links — the bio link for Instagram (instagram.com/hindsightcricket) and YouTube (youtube.com/@hindsightcricket).
 * Each bio points here with its own ?utm_source, and every link on the page carries it on (utm_medium=bio_link), so the
 * usage report can count visitors per platform. Recent posts are the carousels marked posted in the admin queue
 * (GET /snapshots/ig/recent).
 */
const SOURCES = ['instagram', 'youtube'];
const CHANNELS = [
  ['Instagram', 'https://www.instagram.com/hindsightcricket'],
  ['YouTube', 'https://www.youtube.com/@hindsightcricket'],
];

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
  const [posts, setPosts] = useState([]);
  const [fixture, setFixture] = useState(null);
  const [params] = useSearchParams();
  const source = SOURCES.includes(params.get('utm_source')) ? params.get('utm_source') : 'instagram';
  const tagged = (path) => `${path}${path.includes('?') ? '&' : '?'}utm_source=${source}&utm_medium=bio_link`;

  useEffect(() => {
    axios.get(`${config.API_URL}/snapshots/ig/recent`, { params: { limit: 9 } })
      .then(({ data }) => setPosts(data.posts || [])).catch(() => {});
    axios.get(`${config.API_URL}/fixtures/upcoming`, { params: { count: 3 } })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : (data.fixtures || []);
        setFixture(list.find((f) => f.team1 === 'India' || f.team2 === 'India') || list[0] || null);
      }).catch(() => {});
  }, []);

  const preview = fixture && `/venue?venue=${encodeURIComponent(fixture.venue)}&team1=${encodeURIComponent(fixture.team1)}`
    + `&team2=${encodeURIComponent(fixture.team2)}&autoload=true&story=1`;

  return (
    <Box sx={{ maxWidth: 480, mx: 'auto', px: 2, py: 2.5, display: 'grid', gap: 1.25 }}>
      <Box sx={{ textAlign: 'center', mb: 1 }}>
        <Box component="img" src="/brand/hindsight-mark.svg" alt="" sx={{ width: 56, height: 65 }} />
        <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 26, color: colors.textHi, mt: 0.5 }}>hindsight</Typography>
        <Typography sx={{ fontSize: 14, color: colors.textMed }}>Ball-by-ball data that settles cricket debates</Typography>
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 0.75 }}>
          {CHANNELS.map(([name, href]) => (
            <Typography key={name} component="a" href={href} target="_blank" rel="noopener noreferrer"
              sx={{ fontSize: 13, color: colors.accent, textDecoration: 'none' }}>
              {name}
            </Typography>
          ))}
        </Box>
      </Box>
      {preview && (
        <LinkButton tagged={tagged} to={preview} title={`${fixture.team1} v ${fixture.team2}: the preview`}
          sub="Par score, matchups, who suits the ground: the full story" />
      )}
      <LinkButton tagged={tagged} to="/query" title="Ask your own question" sub="Any player, any phase, any matchup, in plain English" />
      <LinkButton tagged={tagged} to="/games/guess-innings" title="Daily games" sub="Guess the innings, Higher or Lower, Call It" />
      <LinkButton tagged={tagged} to="/notes" title="Myths we tested" sub="Common claims, checked against the data" />
      {posts.length > 0 && (
        <>
          <Typography sx={{ fontSize: 12, letterSpacing: '.12em', textTransform: 'uppercase', color: colors.textLo, mt: 1.5 }}>
            Recent posts
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0.75 }}>
            {posts.map((p) => (
              <Box key={p.id} component={RouterLink} to={tagged(`/g/${p.id}`)} aria-label={p.title}>
                <Box component="img" src={`${siteOrigin()}/img/${p.id}.png?slide=1`} alt={p.title} loading="lazy"
                  sx={{ width: '100%', aspectRatio: '4 / 5', display: 'block', borderRadius: 1.5, bgcolor: colors.surface2 }} />
              </Box>
            ))}
          </Box>
        </>
      )}
    </Box>
  );
};

export default IgLinks;
