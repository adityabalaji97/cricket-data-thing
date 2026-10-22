import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import axios from 'axios';
import config from '../../config';
import { colors, fonts } from '../../theme/hindsightDark';
import StoryCard from '../story/StoryCard';
import { toStoryCard } from '../story/visuals';
import { fmt, SHARE_COLOURS } from '../story/postVisuals';

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

/**
 * The cover's hero (services/ig_cover.py): the lead bar chart's top rows under the hook, the subject in the accent, so
 * slide 1 shows a number worth stopping for. Bars run from a centre line when any value is negative.
 */
const ShareHero = ({ hero }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: '8px', mt: 1 }}>
    {hero.rows.map((r) => (
      <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: '108px 1fr', gap: 1, alignItems: 'center' }}>
        <Typography noWrap sx={{ fontSize: 15, fontWeight: 600, color: colors.textHi }}>{r.name}</Typography>
        <Box sx={{ display: 'flex', height: 20, gap: '2px' }}>
          {r.segments.map((seg, i) => (
            <Box key={seg.key} sx={{ width: `${seg.value}%`, bgcolor: SHARE_COLOURS[i], borderRadius: '4px', display: 'flex',
              alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
              {seg.value >= 10 && <Typography sx={{ fontFamily: fonts.mono, fontSize: 12, fontWeight: 700, color: colors.bg }}>{fmt(seg.value, 'pct0')}</Typography>}
            </Box>
          ))}
        </Box>
      </Box>
    ))}
    <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
      {hero.groups.map((g, i) => (
        <Box key={g.key} sx={{ display: 'flex', alignItems: 'center', gap: 0.6 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: '3px', bgcolor: SHARE_COLOURS[i] }} />
          <Typography sx={{ fontSize: 11, color: colors.textMed }}>{g.label}</Typography>
        </Box>
      ))}
    </Box>
  </Box>
);

const Hero = ({ hero }) => {
  if (hero.kind === 'share') return <ShareHero hero={hero} />;
  const rows = hero.rows || [];
  const signed = rows.some((r) => r.value < 0);
  const max = Math.max(...rows.map((r) => Math.abs(r.value)), 1e-9);
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: '7px', mt: 1 }}>
      {rows.map((r) => {
        const width = (100 * Math.abs(r.value)) / max / (signed ? 2 : 1);
        const ink = r.highlight ? colors.accent : colors.textHi;
        return (
          <Box key={r.name} sx={{ display: 'grid', gridTemplateColumns: '108px 1fr 52px', gap: 1, alignItems: 'center' }}>
            <Typography noWrap sx={{ fontSize: 15, fontWeight: r.highlight ? 700 : 500, color: ink }}>{r.name}</Typography>
            <Box sx={{ position: 'relative', height: 16 }}>
              {signed && <Box sx={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: '1px', bgcolor: colors.borderStrong }} />}
              <Box sx={{ position: 'absolute', top: 2, height: 12, borderRadius: '4px',
                bgcolor: r.highlight ? colors.accent : '#5b6b85',
                left: signed ? (r.value >= 0 ? '50%' : `${50 - width}%`) : 0, width: `${Math.max(2, width)}%` }} />
            </Box>
            <Typography sx={{ fontSize: 15, fontWeight: 700, color: ink, textAlign: 'right', fontFamily: fonts.mono }}>{fmt(r.value, hero.format)}</Typography>
          </Box>
        );
      })}
      {hero.label && <Typography sx={{ fontSize: 11, color: colors.textLo }}>{hero.label}</Typography>}
    </Box>
  );
};

const TEXT_SLIDES = {
  hook: (s) => (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: s.hero ? 1.2 : 1.5 }}>
      {s.kicker && <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', color: colors.accent }}>{s.kicker.toUpperCase()}</Typography>}
      <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: s.hero ? 32 : 40, lineHeight: 1.04, textWrap: 'balance' }}>{s.text}</Typography>
      {s.sub && !s.hero && <Typography sx={{ fontSize: 16, color: colors.textMed }}>{s.sub}</Typography>}
      {s.hero && <Hero hero={s.hero} />}
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
    // The counter only where swiping matters: a set of reply images turns it off (data.counter === false).
    return <StoryCard card={card} width={W} height={H} exportMode corner={snap.data?.counter === false ? null : `${n} / ${total}`} />;
  }
  if (slide.type === 'chart') {
    // Older carousels: a satori-drawn snapshot image fills the slide.
    return <Box component="img" src={`/img/${slide.snapshot_id}.png`} alt="" sx={{ width: W, height: H, display: 'block' }} />;
  }
  const body = TEXT_SLIDES[slide.type] || TEXT_SLIDES.text;
  return <Frame n={n} total={total} last={slide.type === 'end'}>{body(slide)}</Frame>;
};

/**
 * ?animate=1 (Reel v2, scripts/record_ig_beats.mjs): the chart is revealed left to right, so bars grow from the left
 * and lines draw in, over REVEAL_MS. The recorder pauses the animation and steps it frame by frame; the finished frame
 * is exactly the static slide.
 */
export const REVEAL_MS = 1400;
const ANIMATE_CSS = `
[data-ig-slide][data-animate] [data-story-chart] { animation: igReveal ${REVEAL_MS}ms cubic-bezier(.22,.7,.2,1) both; }
@keyframes igReveal { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
`;

const IgSlide = () => {
  const { carouselId, n } = useParams();
  const animate = new URLSearchParams(window.location.search).get('animate') === '1';
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
    <Box data-ig-slide data-ready={ready ? 'true' : undefined} data-animate={animate ? 'true' : undefined}
      sx={{ width: W, height: H, bgcolor: colors.bg, overflow: 'hidden', m: 0 }}>
      {animate && <style>{ANIMATE_CSS}</style>}
      {error && <Typography sx={{ color: colors.red, p: 2 }}>{error}</Typography>}
      {snap && <Slide snap={snap} n={Math.max(1, Number(n) || 1)} />}
    </Box>
  );
};

export default IgSlide;
