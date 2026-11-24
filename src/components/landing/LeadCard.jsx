import React, { useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import { siteOrigin } from '../ui/ChartExportButton';
import TeamRatings from './TeamRatings';

// Landing plan L7 (decided 17 Nov 2026): the lead card is automatic with a hand-pick override. The override is the
// day's post: an Instagram carousel planned for today (IST) and marked posted in the admin queue
// (GET /snapshots/ig/recent). Without one, the ten IPL sides on the team pages' rating scale, tied to the calendar
// (the auction on 16 Dec 2026). So the card stays India-first and current even on days nothing is posted.

export const AUCTION_DAY = '2026-12-16';
const istToday = (now = Date.now()) => new Date(now + 5.5 * 3600e3).toISOString().slice(0, 10);

// The post to lead with, or null: one planned for today and marked posted.
export const todaysPost = (posts, now = Date.now()) => (posts || []).find((p) => String(p.planned_for || '').slice(0, 10) === istToday(now)) || null;

// The ratings card's kicker and claim, tied to the calendar: before the auction it frames the ratings as where each
// side starts it.
export const ratingsFrame = (now = Date.now()) => {
  const today = istToday(now);
  if (today <= AUCTION_DAY) {
    const label = today === AUCTION_DAY ? 'auction today' : 'auction 16 Dec';
    return { kicker: `IPL 2027 · ${label}`, context: 'auction' };
  }
  return { kicker: 'IPL team ratings', context: null };
};

const PostLead = ({ post }) => (
  <Box component="section" aria-label="Today's post" sx={{ bgcolor: colors.surface1, border: `1px solid ${colors.border}`,
    borderRadius: '20px', p: 1.75, display: 'flex', gap: 1.75, alignItems: 'center' }}>
    <Box component={Link} to={`/g/${post.id}`} sx={{ flexShrink: 0, width: { xs: 112, md: 168 } }}>
      <Box component="img" src={`${siteOrigin()}/img/${post.id}.png?slide=1`} alt="" loading="eager"
        sx={{ width: '100%', aspectRatio: '4 / 5', display: 'block', borderRadius: 1.5, bgcolor: colors.surface2 }} />
    </Box>
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase',
        color: colors.accent }}>
        Today&apos;s post
      </Typography>
      <Typography component="h2" sx={{ m: 0, mt: 0.5, fontFamily: fonts.display, fontWeight: 700, fontSize: { xs: 19, md: 24 },
        lineHeight: 1.15, color: colors.textHi }}>
        {post.title}
      </Typography>
      <Box component={Link} to={`/g/${post.id}`} sx={{ display: 'inline-flex', alignItems: 'center', minHeight: 44,
        color: colors.accent, fontFamily: fonts.mono, fontSize: 12, fontWeight: 600, textDecoration: 'none' }}>
        {post.slides ? `All ${post.slides} slides ›` : 'See it ›'}
      </Box>
      <Typography sx={{ fontSize: 12, color: colors.textFaint }}>
        hindsightcricket.com · Data: Himanish Ganjoo &amp; TechRadar, Cricsheet
      </Typography>
    </Box>
  </Box>
);

const LeadCard = ({ onKind }) => {
  const [post, setPost] = useState(undefined); // undefined: still asking; null: none today

  useEffect(() => {
    let cancelled = false;
    fetch(`${config.API_URL}/snapshots/ig/recent?limit=3`)
      .then((r) => (r.ok ? r.json() : { posts: [] }))
      .then((d) => { if (!cancelled) setPost(todaysPost(d.posts)); })
      .catch(() => { if (!cancelled) setPost(null); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => { if (post !== undefined && onKind) onKind(post ? 'post' : 'ratings'); }, [post, onKind]);

  if (post) return <PostLead post={post} />;
  // The ratings card starts loading at once (it is the usual lead), so a slow post lookup doesn't hold the page.
  const frame = ratingsFrame();
  return (
    <TeamRatings
      kicker={frame.kicker}
      context={frame.context}
      action={(
        <Box component={Link} to="/team" sx={{ display: 'inline-flex', alignItems: 'center', minHeight: 44, color: colors.textLo,
          fontFamily: fonts.mono, fontSize: 12, textDecoration: 'none', whiteSpace: 'nowrap', '&:hover': { color: colors.accent } }}>
          All squads ›
        </Box>
      )}
    />
  );
};

export default LeadCard;
