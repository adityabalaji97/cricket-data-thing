import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import StoryCard from '../story/StoryCard';
import { toStoryCard } from '../story/visuals';

/**
 * /ig/:carouselId/:n — one Instagram carousel slide (services/ig_carousel.py), drawn by the app's own components at
 * 432x540 CSS px. scripts/render_ig_slides.mjs screenshots it at a 2.5x device scale: 1080x1350, the feed size, with
 * every label the size it has on a phone, scaled. A card slide is the match-preview story's StoryCard itself, so the
 * image and the in-app card are the same drawing.
 *
 * `data-ready="true"` on the root tells the renderer the data and the web fonts are in.
 */
export const W = 432;
export const H = 540;

const VERDICT_COLOR = { supported: colors.accent, 'not supported': colors.red, partly: colors.gold, inconclusive: colors.textMed };

const Frame = ({ n, total, children, last }) => (
  <Box sx={{ width: W, height: H, bgcolor: colors.bg, color: colors.textHi, fontFamily: fonts.body, display: 'flex',
    flexDirection: 'column', p: '24px', boxSizing: 'border-box', overflow: 'hidden' }}>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Typography sx={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.3em', color: colors.accent }}>HINDSIGHT</Typography>
      <Typography sx={{ fontSize: 12, color: colors.textLo }}>{n} / {total}</Typography>
    </Box>
    <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>{children}</Box>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
      <Typography sx={{ fontSize: 13, fontWeight: 600, color: colors.textMed }}>{last ? '' : 'Swipe →'}</Typography>
      <Typography sx={{ fontSize: 13, fontWeight: 600, color: colors.accent }}>{last ? '' : 'hindsightcricket.com'}</Typography>
    </Box>
  </Box>
);

const Lines = ({ text, size, color = colors.textHi }) => String(text || '').split(/\n+/).filter(Boolean).map((line) => (
  <Typography key={line} sx={{ fontSize: size, lineHeight: 1.35, color }}>{line}</Typography>
));

const TEXT_SLIDES = {
  hook: (s) => (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
      {s.kicker && <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', color: colors.accent }}>{s.kicker.toUpperCase()}</Typography>}
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 40, lineHeight: 1.04, textWrap: 'balance' }}>{s.text}</Typography>
      {s.sub && <Typography sx={{ fontSize: 16, color: colors.textMed }}>{s.sub}</Typography>}
    </Box>
  ),
  text: (s) => (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
      <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.12em', color: colors.accent }}>{String(s.heading || '').toUpperCase()}</Typography>
      <Lines text={s.body} size={19} />
    </Box>
  ),
  verdict: (s) => (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1 }}>
      <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.12em', color: colors.textMed }}>VERDICT</Typography>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 64, lineHeight: 1,
        color: VERDICT_COLOR[String(s.verdict || '').toLowerCase()] || colors.textHi }}>{s.verdict}</Typography>
      <Lines text={s.body} size={16} color={colors.textMed} />
    </Box>
  ),
  end: (s) => (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 1.5 }}>
      <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.12em', color: colors.textMed }}>{String(s.heading || 'Run it yourself').toUpperCase()}</Typography>
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: 44, lineHeight: 1.05, color: colors.accent }}>hindsightcricket.com</Typography>
      <Lines text={s.body} size={16} color={colors.textMed} />
    </Box>
  ),
};

const Slide = ({ snap, n }) => {
  const slides = snap.data?.slides || [];
  const total = slides.length;
  const slide = slides[n - 1];
  if (!slide) return <Frame n={n} total={total}><Typography>No slide {n}</Typography></Frame>;
  if (slide.type === 'card') {
    // A match-preview story card (or an Instagram post card): the same StoryCard the app shows.
    const card = toStoryCard(slide.card, { isMobile: true, teams: slide.teams, params: null });
    if (!card) return <Frame n={n} total={total}><Typography>Unknown visual {slide.card?.visual}</Typography></Frame>;
    return <StoryCard card={card} width={W} height={H} exportMode corner={`${n} / ${total}`} />;
  }
  if (slide.type === 'chart') {
    // Older carousels: a satori-drawn snapshot image fills the slide.
    return <Box component="img" src={`/img/${slide.snapshot_id}.png`} alt="" sx={{ width: W, height: H, display: 'block' }} />;
  }
  const body = TEXT_SLIDES[slide.type] || TEXT_SLIDES.text;
  return <Frame n={n} total={total} last={slide.type === 'end'}>{body(slide)}</Frame>;
};

const IgSlide = () => {
  const { carouselId, n } = useParams();
  const [snap, setSnap] = useState(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    axios.get(`${config.API_URL}/snapshots/${carouselId}`)
      .then(({ data }) => { if (live) setSnap(data); })
      .catch(() => { if (live) setError('Carousel not found'); });
    return () => { live = false; };
  }, [carouselId]);

  useEffect(() => {
    if (!snap) return undefined;
    let live = true;
    // Fonts, then two frames so charts that measure themselves have laid out.
    (document.fonts?.ready || Promise.resolve()).then(() => requestAnimationFrame(() => requestAnimationFrame(() => {
      if (live) setReady(true);
    })));
    return () => { live = false; };
  }, [snap]);

  return (
    <Box data-ig-slide data-ready={ready ? 'true' : undefined}
      sx={{ width: W, height: H, bgcolor: colors.bg, overflow: 'hidden', m: 0 }}>
      {error && <Typography sx={{ color: colors.red, p: 2 }}>{error}</Typography>}
      {snap && <Slide snap={snap} n={Math.max(1, Number(n) || 1)} />}
    </Box>
  );
};

export default IgSlide;
